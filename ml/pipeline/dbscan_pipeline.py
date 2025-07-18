"""DBSCAN specific pipeline implementation."""

from typing import Dict, List, Any, Tuple, Optional
import numpy as np
from sklearn.preprocessing import normalize

from .base import BasePipeline
from ..clustering.dbscan import DBSCANClusterer
from ..clustering.metrics import calculate_pairwise_similarities
from ..utils.logging import get_logger

logger = get_logger(__name__)


class DBSCANPipeline(BasePipeline):
    """DBSCAN clustering pipeline with density-based optimizations."""
    
    def get_algorithm_name(self) -> str:
        """Get the name of the clustering algorithm."""
        return "dbscan"
    
    def create_clusterer(self):
        """Create and configure DBSCAN clusterer."""
        return DBSCANClusterer(
            eps=None,  # Auto-detect
            min_samples=3,
            metric='euclidean',
            algorithm='auto',
            leaf_size=30,
            eps_percentiles=[50, 60, 70, 80, 90],
            max_dimensions=128,
            reduce_dimensions=True
        )
    
    def preprocess_features(self, feature_matrix: np.ndarray) -> np.ndarray:
        """
        Preprocess features for DBSCAN.
        
        DBSCAN specific preprocessing:
        1. Normalization for cosine distance
        2. No standardization (DBSCAN uses actual densities)
        3. Handle outlier features
        """
        logger.info(f"Preprocessing features for DBSCAN: shape={feature_matrix.shape}")
        
        # Store original info
        self._original_shape = feature_matrix.shape
        
        # Check if we should use cosine distance
        metric = 'euclidean'  # Default for now
        
        if metric == 'cosine':
            # Normalize for cosine distance
            logger.info("Normalizing features for cosine distance")
            feature_matrix = normalize(feature_matrix, axis=1, norm='l2')
            self._normalized = True
        else:
            self._normalized = False
        
        # DBSCAN handles high dimensions internally via PCA if configured
        # No additional preprocessing needed here
        
        # Calculate density statistics for analysis
        self._calculate_density_stats(feature_matrix, metric)
        
        return feature_matrix
    
    def postprocess_clusters(self, 
                           clusters: Dict[int, List[str]], 
                           clustering_params: Dict[str, Any]) -> Tuple[Dict[int, List[str]], Dict[str, Any]]:
        """
        Post-process clusters for DBSCAN specific enhancements.
        
        DBSCAN specific post-processing:
        1. Analyze noise points
        2. Add density statistics
        3. Identify border vs core points
        """
        # Add preprocessing info
        clustering_params['preprocessing'] = {
            'normalized': self._normalized,
            'original_dimensions': self._original_shape[1],
            'density_stats': self._density_stats
        }
        
        # Analyze noise points
        if -1 in clusters:
            noise_points = clusters[-1]
            noise_ratio = len(noise_points) / sum(len(tests) for tests in clusters.values())
            
            clustering_params['noise_analysis'] = {
                'noise_points': len(noise_points),
                'noise_ratio': noise_ratio,
                'total_points': sum(len(tests) for tests in clusters.values())
            }
            
            if noise_ratio > 0.3:
                logger.warning(f"High noise ratio: {noise_ratio:.1%}")
                
                # Suggest parameter adjustments
                clustering_params['suggestions'] = {
                    'eps': 'Consider increasing eps parameter',
                    'min_samples': 'Consider decreasing min_samples parameter'
                }
        
        # Calculate cluster density metrics
        cluster_metrics = self._calculate_cluster_metrics(clusters)
        clustering_params['cluster_metrics'] = cluster_metrics
        
        # Identify potential outlier clusters (very small non-noise clusters)
        outlier_clusters = []
        for cid, tests in clusters.items():
            if cid != -1 and len(tests) < 3:
                outlier_clusters.append(cid)
        
        if outlier_clusters:
            clustering_params['outlier_clusters'] = outlier_clusters
            logger.info(f"Found {len(outlier_clusters)} potential outlier clusters")
        
        return clusters, clustering_params
    
    def _calculate_density_stats(self, feature_matrix: np.ndarray, metric: str):
        """Calculate density statistics for the dataset."""
        n_samples = len(feature_matrix)
        
        # Sample if dataset is large
        if n_samples > 1000:
            sample_indices = np.random.choice(n_samples, 1000, replace=False)
            sample_matrix = feature_matrix[sample_indices]
        else:
            sample_matrix = feature_matrix
        
        # Calculate pairwise distances for sample
        from sklearn.metrics.pairwise import pairwise_distances
        distances = pairwise_distances(sample_matrix, metric=metric)
        
        # Get k-nearest distances (k=5)
        k = min(5, len(sample_matrix) - 1)
        k_distances = np.sort(distances, axis=1)[:, 1:k+1].mean(axis=1)
        
        self._density_stats = {
            'k_dist_mean': float(np.mean(k_distances)),
            'k_dist_std': float(np.std(k_distances)),
            'k_dist_min': float(np.min(k_distances)),
            'k_dist_max': float(np.max(k_distances)),
            'k_dist_median': float(np.median(k_distances))
        }
    
    def _calculate_cluster_metrics(self, clusters: Dict[int, List[str]]) -> Dict[str, Any]:
        """Calculate metrics for each cluster."""
        metrics = {
            'cluster_sizes': {},
            'size_distribution': {}
        }
        
        # Size distribution
        sizes = [len(tests) for cid, tests in clusters.items() if cid != -1]
        if sizes:
            metrics['size_distribution'] = {
                'min': min(sizes),
                'max': max(sizes),
                'mean': np.mean(sizes),
                'median': np.median(sizes),
                'std': np.std(sizes)
            }
        
        # Individual cluster info
        for cid, tests in clusters.items():
            if cid != -1:  # Skip noise
                metrics['cluster_sizes'][cid] = len(tests)
        
        return metrics