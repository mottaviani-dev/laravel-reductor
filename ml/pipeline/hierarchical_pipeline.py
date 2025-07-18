"""Hierarchical clustering specific pipeline implementation."""

from typing import Dict, List, Any, Tuple, Optional
import numpy as np
from scipy.cluster.hierarchy import dendrogram, fcluster
from scipy.spatial.distance import pdist

from .base import BasePipeline
from ..clustering.hierarchical import HierarchicalClusterer
from ..utils.logging import get_logger

logger = get_logger(__name__)


class HierarchicalPipeline(BasePipeline):
    """Hierarchical clustering pipeline with structure-aware optimizations."""
    
    def get_algorithm_name(self) -> str:
        """Get the name of the clustering algorithm."""
        return "hierarchical"
    
    def create_clusterer(self):
        """Create and configure Hierarchical clusterer."""
        return HierarchicalClusterer(
            n_clusters=None,  # Auto-detect
            linkage='ward',
            affinity='euclidean',
            distance_threshold=None
        )
    
    def preprocess_features(self, feature_matrix: np.ndarray) -> np.ndarray:
        """
        Preprocess features for Hierarchical clustering.
        
        Hierarchical specific preprocessing:
        1. Handle distance metrics compatibility
        2. Scale features if using Ward linkage
        3. Compute linkage matrix for analysis
        """
        logger.info(f"Preprocessing features for Hierarchical: shape={feature_matrix.shape}")
        
        # Store original info
        self._original_shape = feature_matrix.shape
        self._feature_matrix = feature_matrix  # Store for dendrogram generation
        
        linkage = 'ward'
        affinity = 'euclidean'
        
        # Ward linkage requires Euclidean distance
        if linkage == 'ward' and affinity != 'euclidean':
            logger.warning(f"Ward linkage requires euclidean distance, ignoring affinity='{affinity}'")
            self._affinity_override = True
        else:
            self._affinity_override = False
        
        # For Ward linkage, standardization can help
        if linkage == 'ward':
            from sklearn.preprocessing import StandardScaler
            logger.info("Standardizing features for Ward linkage")
            self.scaler = StandardScaler()
            feature_matrix = self.scaler.fit_transform(feature_matrix)
            self._standardized = True
        else:
            self._standardized = False
        
        # Pre-compute distance matrix for analysis (on a sample if large)
        self._compute_distance_distribution(feature_matrix, affinity)
        
        return feature_matrix
    
    def postprocess_clusters(self, 
                           clusters: Dict[int, List[str]], 
                           clustering_params: Dict[str, Any]) -> Tuple[Dict[int, List[str]], Dict[str, Any]]:
        """
        Post-process clusters for Hierarchical specific enhancements.
        
        Hierarchical specific post-processing:
        1. Add dendrogram information
        2. Compute optimal cut heights
        3. Add hierarchy structure info
        """
        # Add preprocessing info
        clustering_params['preprocessing'] = {
            'standardized': self._standardized,
            'original_dimensions': self._original_shape[1],
            'affinity_override': self._affinity_override,
            'distance_distribution': self._distance_stats
        }
        
        # Add hierarchy analysis
        hierarchy_info = self._analyze_hierarchy(clusters)
        clustering_params['hierarchy_analysis'] = hierarchy_info
        
        # Suggest alternative cuts if current clustering seems suboptimal
        if len(clusters) < 3 or any(len(tests) < 2 for tests in clusters.values()):
            suggestions = self._suggest_alternative_cuts()
            if suggestions:
                clustering_params['suggestions'] = suggestions
        
        # Add cluster balance metrics
        balance_metrics = self._calculate_balance_metrics(clusters)
        clustering_params['balance_metrics'] = balance_metrics
        
        return clusters, clustering_params
    
    def _compute_distance_distribution(self, feature_matrix: np.ndarray, affinity: str):
        """Compute distance distribution statistics."""
        n_samples = len(feature_matrix)
        
        # Sample for large datasets
        if n_samples > 500:
            indices = np.random.choice(n_samples, 500, replace=False)
            sample_matrix = feature_matrix[indices]
        else:
            sample_matrix = feature_matrix
        
        # Compute condensed distance matrix
        if affinity == 'euclidean':
            distances = pdist(sample_matrix, metric='euclidean')
        elif affinity == 'cosine':
            distances = pdist(sample_matrix, metric='cosine')
        else:
            distances = pdist(sample_matrix, metric=affinity)
        
        self._distance_stats = {
            'min': float(np.min(distances)),
            'max': float(np.max(distances)),
            'mean': float(np.mean(distances)),
            'median': float(np.median(distances)),
            'std': float(np.std(distances)),
            'percentiles': {
                10: float(np.percentile(distances, 10)),
                25: float(np.percentile(distances, 25)),
                50: float(np.percentile(distances, 50)),
                75: float(np.percentile(distances, 75)),
                90: float(np.percentile(distances, 90))
            }
        }
    
    def _analyze_hierarchy(self, clusters: Dict[int, List[str]]) -> Dict[str, Any]:
        """Analyze the hierarchical structure."""
        # Get cluster sizes
        sizes = [len(tests) for tests in clusters.values()]
        
        # Compute imbalance ratio (max/min size)
        if len(sizes) > 1:
            imbalance_ratio = max(sizes) / max(min(sizes), 1)
        else:
            imbalance_ratio = 1.0
        
        return {
            'n_clusters': len(clusters),
            'cluster_sizes': sizes,
            'imbalance_ratio': imbalance_ratio,
            'singleton_clusters': sum(1 for s in sizes if s == 1),
            'large_clusters': sum(1 for s in sizes if s > 10)
        }
    
    def _suggest_alternative_cuts(self) -> Optional[Dict[str, Any]]:
        """Suggest alternative cutting heights for the dendrogram."""
        # This would require access to the linkage matrix
        # For now, return general suggestions
        return {
            'message': 'Current clustering may be suboptimal',
            'recommendations': [
                'Try setting explicit n_clusters between 3 and 8',
                'Consider using distance_threshold instead of n_clusters',
                'Experiment with different linkage methods (complete, average)'
            ]
        }
    
    def _calculate_balance_metrics(self, clusters: Dict[int, List[str]]) -> Dict[str, float]:
        """Calculate cluster balance metrics."""
        sizes = [len(tests) for tests in clusters.values()]
        
        if not sizes:
            return {}
        
        # Gini coefficient for cluster size distribution
        # 0 = perfect equality, 1 = perfect inequality
        sorted_sizes = sorted(sizes)
        n = len(sorted_sizes)
        index = np.arange(1, n + 1)
        gini = (2 * np.sum(index * sorted_sizes)) / (n * np.sum(sorted_sizes)) - (n + 1) / n
        
        # Entropy of cluster distribution
        total = sum(sizes)
        if total > 0:
            proportions = np.array(sizes) / total
            entropy = -np.sum(proportions * np.log2(proportions + 1e-10))
            max_entropy = np.log2(len(sizes))
            normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0
        else:
            normalized_entropy = 0
        
        return {
            'gini_coefficient': float(gini),
            'normalized_entropy': float(normalized_entropy),
            'size_variance': float(np.var(sizes)),
            'size_cv': float(np.std(sizes) / np.mean(sizes)) if np.mean(sizes) > 0 else 0
        }