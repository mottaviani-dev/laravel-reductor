"""Pipeline orchestrator for test redundancy detection."""

from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import warnings

from ..config import ThresholdConfig, SEMANTIC_DIM, COVERAGE_DIM
from ..core.features import FeatureCombiner
from ..analysis import (
    EntropyAnalyzer,
    EntropyConfig,
    RedundancyAnalyzer,
    RedundancyThresholds,
    ValidationConfig
)
from ..io import load_test_sources, load_coverage_data
from ..utils.logging import get_logger

from .stages import (
    VectorizationStage,
    FingerprintStage,
    ClusteringStage,
    ValidationStage,
    AnalysisStage
)
from .results import ResultManager
from .factory import create_pipeline, PipelineFactory

logger = get_logger(__name__)


class RedundancyPipeline:
    """Main pipeline for test redundancy detection."""
    
    def __init__(self, config: ThresholdConfig = None):
        """Initialize redundancy detection pipeline."""
        self.config = config or ThresholdConfig.default()
        
        # Initialize stages
        self.vectorization = VectorizationStage(
            output_dim=SEMANTIC_DIM,
            max_features=self.config.clustering.kmeans_max_clusters * 100
        )
        
        self.fingerprinting = FingerprintStage(
            fingerprint_size=COVERAGE_DIM
        )
        
        self.feature_combiner = FeatureCombiner(
            semantic_dim=SEMANTIC_DIM,
            coverage_dim=COVERAGE_DIM
        )
        
        self.entropy_analyzer = EntropyAnalyzer(
            EntropyConfig(
                semantic_threshold=self.config.entropy.semantic_min_entropy,
                coverage_threshold=self.config.entropy.coverage_min_entropy,
                semantic_weight=self.config.similarity.semantic_weight,
                coverage_weight=self.config.similarity.coverage_weight
            )
        )
        
        self.redundancy_analyzer = RedundancyAnalyzer(
            RedundancyThresholds(
                low=self.config.similarity.low_redundancy,
                moderate=self.config.similarity.moderate_redundancy,
                high=self.config.similarity.high_redundancy,
                very_high=self.config.similarity.very_high_redundancy
            ),
            semantic_weight=self.config.similarity.semantic_weight,
            coverage_weight=self.config.similarity.coverage_weight
        )
        
        self.result_manager = ResultManager()
    
    def run(self,
            test_sources: Union[str, Path, Dict[str, str]],
            coverage_data: Union[str, Path, Dict[str, List[str]]],
            algorithm: str = 'kmeans',
            apply_entropy_damping: bool = True,
            validate_clusters: bool = True,
            use_new_pipeline: bool = None) -> Dict[str, Any]:
        """
        Run the complete redundancy detection pipeline.
        
        Args:
            test_sources: Test source code data or path
            coverage_data: Coverage data or path
            algorithm: Clustering algorithm to use
            apply_entropy_damping: Whether to apply entropy-based feature weighting
            validate_clusters: Whether to validate and split unsafe clusters
            use_new_pipeline: Use new modular pipeline architecture (None = auto-detect)
        """
        logger.info("Starting redundancy detection pipeline")
        
        # Auto-detect whether to use new pipeline based on algorithm
        if use_new_pipeline is None:
            # Use new pipeline for algorithms that have specific implementations
            use_new_pipeline = algorithm.lower() in PipelineFactory.list_algorithms()
        
        if use_new_pipeline:
            logger.info(f"Using new modular pipeline for {algorithm}")
            # Delegate to algorithm-specific pipeline
            specific_pipeline = create_pipeline(algorithm, self.config)
            
            # Convert data format if needed
            if isinstance(test_sources, (str, Path)):
                test_source_file = str(test_sources)
                test_sources = None
            else:
                test_source_file = None
                
            if isinstance(coverage_data, (str, Path)):
                coverage_file = str(coverage_data)
                coverage_data = None
            else:
                coverage_file = None
            
            # Run the specific pipeline
            results = specific_pipeline.run(
                test_sources=test_sources,
                coverage_data=coverage_data,
                test_source_file=test_source_file,
                coverage_file=coverage_file
            )
            
            # Store results for backward compatibility
            self.result_manager.set_results(results)
            return results
        
        # Original implementation for backward compatibility
        logger.info("Using legacy pipeline implementation")
        
        # Load data if paths provided
        if isinstance(test_sources, (str, Path)):
            test_sources = load_test_sources(test_sources)
        
        if isinstance(coverage_data, (str, Path)):
            coverage_data = load_coverage_data(coverage_data)
        
        # Execute pipeline stages
        semantic_vectors = self.vectorization.process(test_sources)
        coverage_vectors = self.fingerprinting.process(coverage_data)
        
        combined_vectors = self.feature_combiner.combine_features(
            semantic_vectors, coverage_vectors
        )
        
        # Apply entropy damping if requested
        if apply_entropy_damping:
            entropy_weights = self.entropy_analyzer.calculate_entropy_weights(
                semantic_vectors, coverage_vectors
            )
        else:
            entropy_weights = None
        
        # Prepare feature matrix
        matrix, test_names = self.feature_combiner.prepare_matrix(combined_vectors)
        
        if entropy_weights:
            matrix = self.entropy_analyzer.apply_entropy_damping(
                matrix, test_names, entropy_weights, SEMANTIC_DIM
            )
        
        # Clustering
        clustering = ClusteringStage(algorithm, self.config)
        clusters, clustering_params = clustering.process(matrix, test_names)
        
        # Validation
        if validate_clusters:
            validation = ValidationStage(
                ValidationConfig(
                    strict_mode=self.config.validation.max_conflicts_per_cluster == 0
                )
            )
            clusters, split_count = validation.process(clusters)
        else:
            split_count = 0
        
        # Analysis
        analysis = AnalysisStage(
            self.redundancy_analyzer,
            self.entropy_analyzer if apply_entropy_damping else None
        )
        redundancy_results = analysis.process(
            clusters, semantic_vectors, coverage_vectors
        )
        
        # Compile results
        results = {
            'test_count': len(test_sources),
            'algorithm': algorithm,
            'clusters': clusters,
            'clustering_params': clustering_params,
            'redundancy_analysis': redundancy_results,
            'validation_info': {
                'clusters_split': split_count,
                'original_clusters': len(clusters) - split_count,
                'final_clusters': len(clusters)
            } if validate_clusters else None,
            'config': self.config.to_dict()
        }
        
        self.result_manager.set_results(results)
        logger.info("Pipeline completed successfully")
        
        return results
    
    def save_results(self, output_dir: Union[str, Path], **kwargs) -> None:
        """Save pipeline results."""
        self.result_manager.save(output_dir, **kwargs)