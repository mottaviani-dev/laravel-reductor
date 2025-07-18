"""Individual pipeline stages."""

from typing import Dict, List, Optional, Any, Tuple
import numpy as np

from ..core.vectorizers import SemanticVectorizer
from ..core.fingerprints import CoverageFingerprintGenerator
from ..core.features import FeatureCombiner
from ..analysis import EntropyAnalyzer, SemanticValidator
from ..analysis.reduction import PCAReducer
from ..factories import get_clusterer
from ..config import SEMANTIC_DIM, COVERAGE_DIM
from ..utils.logging import get_logger

logger = get_logger(__name__)


class VectorizationStage:
    """Handles test code vectorization."""
    
    def __init__(self, output_dim: int = SEMANTIC_DIM, max_features: int = 5000):
        self.vectorizer = SemanticVectorizer(
            output_dim=output_dim,
            max_features=max_features
        )
    
    def process(self, test_sources: Dict[str, str]) -> Dict[str, np.ndarray]:
        """Vectorize test source code."""
        logger.info(f"Vectorizing {len(test_sources)} tests")
        return self.vectorizer.fit_transform(test_sources)


class FingerprintStage:
    """Handles coverage fingerprint generation."""
    
    def __init__(self, fingerprint_size: int = COVERAGE_DIM):
        self.generator = CoverageFingerprintGenerator(
            fingerprint_size=fingerprint_size
        )
    
    def process(self, coverage_data: Dict[str, List[str]]) -> Dict[str, np.ndarray]:
        """Generate coverage fingerprints."""
        logger.info(f"Generating fingerprints for {len(coverage_data)} tests")
        return self.generator.generate_fingerprints(coverage_data)


class ClusteringStage:
    """Handles test clustering."""
    
    def __init__(self, algorithm: str, config: Any):
        self.algorithm = algorithm
        self.config = config
    
    def process(self, 
                feature_matrix: np.ndarray,
                test_names: List[str]) -> Dict[int, List[str]]:
        """Perform clustering."""
        logger.info(f"Clustering with {self.algorithm}")
        
        # Pass algorithm-specific parameters
        if self.algorithm == 'dbscan':
            clusterer = get_clusterer(
                self.algorithm,
                eps=getattr(self.config.clustering, 'dbscan_eps', None),
                min_samples=getattr(self.config.clustering, 'dbscan_min_samples', 3)
            )
        elif self.algorithm in ['kmeans', 'k-means']:
            clusterer = get_clusterer(
                self.algorithm,
                min_clusters=self.config.clustering.kmeans_min_clusters,
                max_clusters=self.config.clustering.kmeans_max_clusters
            )
        elif self.algorithm == 'hierarchical':
            clusterer = get_clusterer(
                self.algorithm,
                n_clusters=getattr(self.config.clustering, 'hierarchical_n_clusters', None),
                linkage=getattr(self.config.clustering, 'hierarchical_linkage', 'ward')
            )
        else:
            # Default fallback
            clusterer = get_clusterer(self.algorithm)
        
        cluster_result = clusterer.cluster(feature_matrix)
        
        # Check if result is enhanced format (dict with dict values containing 'indices')
        is_enhanced_format = False
        if isinstance(cluster_result, dict) and len(cluster_result) > 0:
            # Check first value to determine format
            first_value = next(iter(cluster_result.values()))
            is_enhanced_format = isinstance(first_value, dict) and 'indices' in first_value
        
        if is_enhanced_format:
            # New enhanced format from DBSCAN
            clusters = {}
            cluster_metadata = {}
            
            for cluster_id, cluster_data in cluster_result.items():
                # Convert numpy int to regular int
                cid = int(cluster_id) if hasattr(cluster_id, 'item') else cluster_id
                
                # Extract indices
                indices = cluster_data.get('indices', [])
                clusters[cid] = [test_names[idx] for idx in indices]
                
                # Store metadata
                cluster_metadata[cid] = {
                    k: v for k, v in cluster_data.items() 
                    if k != 'indices'
                }
            
            # Add metadata to params
            params = clusterer.get_params()
            params['cluster_metadata'] = cluster_metadata
            
            return clusters, params
        else:
            # Old format - simple dict of indices (lists)
            clusters = {}
            for cluster_id, indices in cluster_result.items():
                # Convert numpy int to regular int
                cid = int(cluster_id) if hasattr(cluster_id, 'item') else cluster_id
                clusters[cid] = [test_names[idx] for idx in indices]
            
            return clusters, clusterer.get_params()


class ValidationStage:
    """Handles cluster validation and safety checks."""
    
    def __init__(self, config: Any):
        # Import both validators
        from ..cluster_validator import ClusterValidator
        from ..analysis.validation import SemanticValidator, ValidationConfig
        
        self.safety_validator = ClusterValidator()
        # Create validation config from the general config
        val_config = ValidationConfig() if config is None else ValidationConfig(
            strict_mode=getattr(config, 'strict_mode', True),
            allow_boundary_merging=getattr(config, 'allow_boundary_merging', False),
            min_cluster_size=getattr(config, 'min_cluster_size', 2)
        )
        self.semantic_validator = SemanticValidator(val_config)
    
    def process(self, clusters: Dict[int, List[str]], 
                test_vectors: Dict[str, Dict] = None) -> Tuple[Dict[int, List[str]], int]:
        """Validate and split unsafe clusters."""
        logger.info("Validating clusters for safety")
        
        # First, apply safety validation
        safe_clusters = {}
        split_count = 0
        
        # Get the highest cluster ID to ensure new IDs don't conflict
        max_cluster_id = max(clusters.keys()) if clusters else 0
        next_cluster_id = max_cluster_id + 1
        
        for cluster_id, test_names in clusters.items():
            is_safe, reason = self.safety_validator.validate_cluster_safety(test_names)
            
            if not is_safe:
                logger.warning(f"Cluster {cluster_id} is unsafe: {reason}")
                # Split the unsafe cluster
                subclusters = self.safety_validator._split_by_semantics(test_names)
                for i, subcluster in enumerate(subclusters):
                    if len(subcluster) >= 2:
                        # Use integer cluster IDs to maintain consistency
                        new_id = next_cluster_id + i
                        safe_clusters[new_id] = subcluster
                        split_count += 1
                # Update next_cluster_id for subsequent splits
                next_cluster_id += len(subclusters)
            else:
                safe_clusters[cluster_id] = test_names
        
        # Then apply semantic validation if configured
        cluster_data = [
            {'cluster_id': cid, 'tests': tests}
            for cid, tests in safe_clusters.items()
        ]
        
        new_cluster_data, semantic_split_count = self.semantic_validator.split_unsafe_clusters(
            cluster_data, test_vectors or {}
        )
        
        logger.info(f"Split {split_count + semantic_split_count} unsafe clusters total")
        
        validated_clusters = {}
        for cluster in new_cluster_data:
            validated_clusters[cluster['cluster_id']] = cluster['tests']
        
        return validated_clusters, split_count + semantic_split_count


class AnalysisStage:
    """Handles redundancy analysis."""
    
    def __init__(self, redundancy_analyzer, entropy_analyzer: Optional[EntropyAnalyzer] = None):
        self.redundancy_analyzer = redundancy_analyzer
        self.entropy_analyzer = entropy_analyzer
    
    def process(self,
                clusters: Dict[int, List[str]],
                semantic_vectors: Dict[str, np.ndarray],
                coverage_vectors: Dict[str, np.ndarray]) -> Dict[str, Any]:
        """Analyze redundancy in clusters."""
        logger.info("Analyzing redundancy")
        
        redundancy_records = self.redundancy_analyzer.find_redundant_tests(
            clusters, semantic_vectors, coverage_vectors
        )
        
        summary = self.redundancy_analyzer.summarize_redundancy(redundancy_records)
        
        result = {
            'summary': summary,
            'redundant_tests': redundancy_records
        }
        
        if self.entropy_analyzer:
            result['entropy_summary'] = self.entropy_analyzer.summarize_entropy_analysis()
        
        return result