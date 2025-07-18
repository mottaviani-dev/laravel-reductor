"""K-means specific pipeline implementation."""

from typing import Dict, List, Any, Tuple
import numpy as np
from sklearn.preprocessing import StandardScaler

from .base import BasePipeline
from ..clustering.kmeans import KMeansClusterer
from ..analysis.reduction import PCAReducer
from ..utils.logging import get_logger

logger = get_logger(__name__)


class KMeansPipeline(BasePipeline):
    """K-means clustering pipeline with specific optimizations."""
    
    def get_algorithm_name(self) -> str:
        """Get the name of the clustering algorithm."""
        return "kmeans"
    
    def create_clusterer(self):
        """Create and configure K-means clusterer."""
        return KMeansClusterer(
            n_clusters=None,  # Auto-detect
            min_clusters=self.config.clustering.kmeans_min_clusters,
            max_clusters=self.config.clustering.kmeans_max_clusters,
            n_init=10,
            max_iter=300,
            random_state=42
        )
    
    def preprocess_features(self, feature_matrix: np.ndarray) -> np.ndarray:
        """
        Preprocess features for K-means.
        
        K-means specific preprocessing:
        1. Standardization (K-means is sensitive to scale)
        2. PCA if high dimensional
        3. Handle sparse features
        """
        logger.info(f"Preprocessing features for K-means: shape={feature_matrix.shape}")
        
        # Store original shape and matrix for reporting
        self._original_shape = feature_matrix.shape
        original_matrix = feature_matrix.copy()
        
        # Step 1: Handle sparse/constant features
        # Remove features with zero variance
        variances = np.var(feature_matrix, axis=0)
        non_constant_mask = variances > 1e-10
        if not np.all(non_constant_mask):
            logger.warning(f"Removing {np.sum(~non_constant_mask)} constant features")
            feature_matrix = feature_matrix[:, non_constant_mask]
            
            # If all features are constant, keep at least a few with smallest variance
            if feature_matrix.shape[1] == 0:
                logger.warning("All features are constant! Keeping top 10 features by variance")
                # Keep features with highest variance (even if very small)
                top_indices = np.argsort(variances)[-min(10, len(variances)):]
                feature_matrix = original_matrix[:, top_indices]
        
        # Step 2: Standardization
        # K-means assumes spherical clusters, so standardization helps
        self.scaler = StandardScaler()
        feature_matrix = self.scaler.fit_transform(feature_matrix)
        
        # Step 3: Dimensionality reduction if needed
        # Simple heuristic: reduce if more than 128 dimensions
        if feature_matrix.shape[1] > 128:
            target_dims = min(128, feature_matrix.shape[0] - 1, feature_matrix.shape[1])
            
            logger.info(f"Applying PCA: {feature_matrix.shape[1]} -> {target_dims} dimensions")
            
            self.pca_reducer = PCAReducer(whiten=True, standardize=False)  # Already standardized
            feature_matrix = self.pca_reducer.reduce(feature_matrix, target_dims)
            
            # Log explained variance
            _, explained_var = self.pca_reducer.get_explained_variance()
            logger.info(f"PCA retained {explained_var:.1%} of variance")
            
            # Store PCA info for results
            self._pca_applied = True
            self._explained_variance = explained_var
        else:
            self._pca_applied = False
        
        # Step 4: Check for duplicate vectors (K-means issue)
        unique_vectors = np.unique(feature_matrix, axis=0)
        if len(unique_vectors) < len(feature_matrix):
            logger.warning(
                f"Found {len(feature_matrix) - len(unique_vectors)} duplicate feature vectors. "
                f"K-means may produce fewer clusters than requested."
            )
            self._n_unique_vectors = len(unique_vectors)
        else:
            self._n_unique_vectors = len(feature_matrix)
        
        return feature_matrix
    
    def postprocess_clusters(self, 
                           clusters: Dict[int, List[str]], 
                           clustering_params: Dict[str, Any]) -> Tuple[Dict[int, List[str]], Dict[str, Any]]:
        """
        Post-process clusters for K-means specific enhancements.
        
        K-means specific post-processing:
        1. Merge very small clusters
        2. Add preprocessing info to params
        3. Calculate cluster quality metrics
        """
        # Add preprocessing info
        clustering_params['preprocessing'] = {
            'standardized': True,
            'original_dimensions': self._original_shape[1],
            'preprocessed_dimensions': getattr(self, 'scaler', None).n_features_in_ if hasattr(self, 'scaler') else self._original_shape[1],
            'pca_applied': self._pca_applied,
            'n_unique_vectors': self._n_unique_vectors
        }
        
        if self._pca_applied:
            clustering_params['preprocessing']['explained_variance'] = self._explained_variance
            clustering_params['preprocessing']['pca_components'] = self.pca_reducer.pca_.n_components_
        
        # Merge very small clusters (K-means can produce singleton clusters)
        min_cluster_size = 2  # Default minimum cluster size
        if min_cluster_size > 1:
            clusters, merge_count = self._merge_small_clusters(clusters, min_cluster_size)
            if merge_count > 0:
                logger.info(f"Merged {merge_count} small clusters")
                clustering_params['post_processing'] = {
                    'small_clusters_merged': merge_count,
                    'min_cluster_size': min_cluster_size
                }
        
        return clusters, clustering_params
    
    def _merge_small_clusters(self, 
                             clusters: Dict[int, List[str]], 
                             min_size: int) -> Tuple[Dict[int, List[str]], int]:
        """
        Merge clusters smaller than min_size into nearest larger cluster.
        
        Args:
            clusters: Original clusters
            min_size: Minimum cluster size
            
        Returns:
            Tuple of (merged_clusters, merge_count)
        """
        small_clusters = {cid: tests for cid, tests in clusters.items() 
                         if len(tests) < min_size and cid != -1}  # Don't merge noise
        
        if not small_clusters:
            return clusters, 0
        
        large_clusters = {cid: tests for cid, tests in clusters.items() 
                         if len(tests) >= min_size}
        
        if not large_clusters:
            # All clusters are small, can't merge
            return clusters, 0
        
        merged_clusters = large_clusters.copy()
        merge_count = 0
        
        # For each small cluster, merge into the largest cluster
        # In a more sophisticated version, we'd merge based on distance
        largest_cluster_id = max(large_clusters.keys(), key=lambda k: len(large_clusters[k]))
        
        for small_id, small_tests in small_clusters.items():
            merged_clusters[largest_cluster_id].extend(small_tests)
            merge_count += 1
        
        # Re-index clusters to be sequential
        reindexed = {}
        for idx, (_, tests) in enumerate(sorted(merged_clusters.items())):
            reindexed[idx] = tests
        
        return reindexed, merge_count