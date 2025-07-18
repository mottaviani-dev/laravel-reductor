"""Base pipeline classes for modular clustering pipelines."""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from pathlib import Path

from ..utils.logging import get_logger
from .stages import (
    VectorizationStage,
    FingerprintStage,
    ValidationStage,
    AnalysisStage
)
from .results import ResultManager
from ..core.features import FeatureCombiner
from ..analysis import RedundancyAnalyzer, EntropyAnalyzer
from ..io import load_test_sources, load_coverage_data

logger = get_logger(__name__)


class BasePipeline(ABC):
    """Abstract base class for clustering pipelines."""
    
    def __init__(self, config: Any):
        """
        Initialize base pipeline.
        
        Args:
            config: Pipeline configuration object
        """
        self.config = config
        self.result_manager = ResultManager()
        
        # Initialize common stages
        from ..config import SEMANTIC_DIM, COVERAGE_DIM
        
        self.vectorization = VectorizationStage(
            output_dim=SEMANTIC_DIM,
            max_features=5000  # Default max features
        )
        
        self.fingerprint = FingerprintStage(
            fingerprint_size=COVERAGE_DIM
        )
        
        self.feature_combiner = FeatureCombiner(
            semantic_dim=SEMANTIC_DIM,
            coverage_dim=COVERAGE_DIM
        )
        
        from ..analysis.validation import ValidationConfig
        
        # Create validation config with defaults
        validation_config = ValidationConfig(
            strict_mode=False,  # Not too strict by default
            allow_boundary_merging=True,
            min_cluster_size=2
        )
        self.validation = ValidationStage(validation_config)
        
        # Initialize analyzers
        from ..analysis import RedundancyThresholds
        
        self.redundancy_analyzer = RedundancyAnalyzer(
            RedundancyThresholds(
                low=config.similarity.low_redundancy,
                moderate=config.similarity.moderate_redundancy,
                high=config.similarity.high_redundancy,
                very_high=config.similarity.very_high_redundancy
            ),
            semantic_weight=config.similarity.semantic_weight,
            coverage_weight=config.similarity.coverage_weight
        )
        
        # Always create entropy analyzer for now
        self.entropy_analyzer = EntropyAnalyzer()
        
        self.analysis = AnalysisStage(
            self.redundancy_analyzer,
            self.entropy_analyzer
        )
    
    @abstractmethod
    def get_algorithm_name(self) -> str:
        """Get the name of the clustering algorithm."""
        pass
    
    @abstractmethod
    def create_clusterer(self):
        """Create and configure the specific clusterer."""
        pass
    
    @abstractmethod
    def preprocess_features(self, feature_matrix: np.ndarray) -> np.ndarray:
        """
        Preprocess features for the specific algorithm.
        
        Args:
            feature_matrix: Combined feature matrix
            
        Returns:
            Preprocessed feature matrix
        """
        pass
    
    @abstractmethod
    def postprocess_clusters(self, 
                           clusters: Dict[int, List[str]], 
                           clustering_params: Dict[str, Any]) -> Tuple[Dict[int, List[str]], Dict[str, Any]]:
        """
        Post-process clusters for algorithm-specific enhancements.
        
        Args:
            clusters: Raw cluster assignments
            clustering_params: Clustering parameters
            
        Returns:
            Tuple of (processed_clusters, updated_params)
        """
        pass
    
    def run(self,
            test_sources: Optional[Dict[str, str]] = None,
            coverage_data: Optional[Dict[str, List[str]]] = None,
            test_source_file: Optional[str] = None,
            coverage_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Run the complete pipeline.
        
        Args:
            test_sources: Dict mapping test names to source code
            coverage_data: Dict mapping test names to covered lines
            test_source_file: Path to test sources JSON file
            coverage_file: Path to coverage data JSON file
            
        Returns:
            Pipeline results dictionary
        """
        logger.info(f"Starting {self.get_algorithm_name()} pipeline")
        
        # Load data if not provided
        if test_sources is None and test_source_file:
            test_sources = load_test_sources(test_source_file)
        
        if coverage_data is None and coverage_file:
            coverage_data = load_coverage_data(coverage_file)
        
        if not test_sources:
            raise ValueError("No test sources provided. Expected a dictionary mapping test names to source code.")
        if not coverage_data:
            raise ValueError("No coverage data provided. Expected a dictionary mapping test names to lists of covered lines.")
        
        # Step 1: Vectorization
        semantic_vectors = self.vectorization.process(test_sources)
        
        # Step 2: Coverage fingerprinting
        coverage_vectors = self.fingerprint.process(coverage_data)
        
        # Step 3: Feature combination
        combined_vectors = self.feature_combiner.combine_features(
            semantic_vectors, 
            coverage_vectors
        )
        
        # Prepare feature matrix
        test_names = list(test_sources.keys())
        feature_matrix, test_names = self.feature_combiner.prepare_matrix(
            combined_vectors,
            test_names
        )
        
        # Step 4: Algorithm-specific preprocessing
        processed_features = self.preprocess_features(feature_matrix)
        
        # Step 5: Clustering
        clusterer = self.create_clusterer()
        cluster_result = clusterer.cluster(processed_features)
        
        # Convert cluster result to standard format
        clusters = self._standardize_cluster_format(cluster_result, test_names)
        clustering_params = clusterer.get_params()
        
        # Step 6: Algorithm-specific post-processing
        clusters, clustering_params = self.postprocess_clusters(clusters, clustering_params)
        
        # Step 7: Validation
        validated_clusters, split_count = self.validation.process(clusters)
        
        # Step 8: Redundancy analysis
        redundancy_results = self.analysis.process(
            validated_clusters,
            semantic_vectors,
            coverage_vectors
        )
        
        # Compile results
        results = {
            'algorithm': self.get_algorithm_name(),
            'test_count': len(test_names),
            'clusters': validated_clusters,
            'clustering_params': clustering_params,
            'validation': {
                'unsafe_clusters_split': split_count
            },
            'redundancy_analysis': redundancy_results,
            'feature_stats': {
                'semantic_dim': len(next(iter(semantic_vectors.values()))),
                'coverage_dim': len(next(iter(coverage_vectors.values()))),
                'combined_dim': feature_matrix.shape[1]
            }
        }
        
        self.result_manager.set_results(results)
        return results
    
    def _standardize_cluster_format(self, 
                                   cluster_result: Any, 
                                   test_names: List[str]) -> Dict[int, List[str]]:
        """
        Convert various cluster formats to standard format.
        
        Args:
            cluster_result: Raw cluster result from clusterer
            test_names: List of test names
            
        Returns:
            Standard cluster format: {cluster_id: [test_names]}
        """
        # Handle enhanced format (dict with metadata)
        if isinstance(cluster_result, dict) and len(cluster_result) > 0:
            first_value = next(iter(cluster_result.values()))
            if isinstance(first_value, dict) and 'indices' in first_value:
                clusters = {}
                for cluster_id, cluster_data in cluster_result.items():
                    indices = cluster_data.get('indices', [])
                    clusters[int(cluster_id)] = [test_names[idx] for idx in indices]
                return clusters
        
        # Handle simple format (dict of lists)
        if isinstance(cluster_result, dict):
            clusters = {}
            for cluster_id, indices in cluster_result.items():
                clusters[int(cluster_id)] = [test_names[idx] for idx in indices]
            return clusters
        
        # Handle numpy array labels
        if isinstance(cluster_result, np.ndarray):
            clusters = {}
            for idx, label in enumerate(cluster_result):
                label = int(label)
                if label not in clusters:
                    clusters[label] = []
                clusters[label].append(test_names[idx])
            return clusters
        
        raise ValueError(f"Unknown cluster result format: {type(cluster_result)}")
    
    def save_results(self, output_dir: str, **kwargs):
        """Save pipeline results."""
        self.result_manager.save(output_dir, **kwargs)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get results summary."""
        return self.result_manager.get_summary()