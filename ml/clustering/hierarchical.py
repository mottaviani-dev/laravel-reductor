"""Hierarchical clustering implementation."""

from typing import Dict, List, Optional, Any, Literal
import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import silhouette_score
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import pdist

from .base import Clusterer


class HierarchicalClusterer(Clusterer):
    """Hierarchical (Agglomerative) clustering algorithm."""
    
    def __init__(self,
                 n_clusters: Optional[int] = None,
                 linkage: Literal['ward', 'complete', 'average', 'single'] = 'ward',
                 affinity: str = 'euclidean',
                 distance_threshold: Optional[float] = None):
        """
        Initialize Hierarchical clusterer.
        
        Args:
            n_clusters: Number of clusters (None if using distance_threshold)
            linkage: Linkage criterion
            affinity: Metric for distance computation
            distance_threshold: Distance threshold for clustering
        """
        self.n_clusters = n_clusters
        self.linkage = linkage
        self.affinity = affinity
        self.distance_threshold = distance_threshold
        
        self.n_clusters_: Optional[int] = None
        self.silhouette_score_: Optional[float] = None
        self.linkage_matrix_: Optional[np.ndarray] = None
        
    def cluster(self, 
                vectors: np.ndarray,
                **kwargs) -> Dict[int, List[int]]:
        """
        Perform hierarchical clustering.
        
        Args:
            vectors: Feature matrix (n_samples, n_features)
            **kwargs: Additional parameters
            
        Returns:
            Dict mapping cluster IDs to lists of sample indices
        """
        n_samples = vectors.shape[0]
        
        # Handle edge cases
        if n_samples < 2:
            return {0: list(range(n_samples))}
        
        # Build linkage matrix for analysis
        if self.linkage == 'ward' and self.affinity == 'euclidean':
            condensed_dist = pdist(vectors, metric='euclidean')
            self.linkage_matrix_ = linkage(condensed_dist, method='ward')
        
        # Configure clustering
        if self.distance_threshold is not None:
            # Use distance threshold
            clustering = AgglomerativeClustering(
                n_clusters=None,
                linkage=self.linkage,
                metric=self.affinity,
                distance_threshold=self.distance_threshold
            )
        else:
            # Use fixed number of clusters
            n_clusters = self.n_clusters or self._find_optimal_clusters(vectors)
            n_clusters = min(n_clusters, n_samples)
            
            clustering = AgglomerativeClustering(
                n_clusters=n_clusters,
                linkage=self.linkage,
                metric=self.affinity
            )
        
        # Perform clustering
        labels = clustering.fit_predict(vectors)
        
        # Store number of clusters found
        self.n_clusters_ = len(set(labels))
        
        # Calculate silhouette score if possible
        if self.n_clusters_ > 1 and self.n_clusters_ < n_samples:
            self.silhouette_score_ = silhouette_score(vectors, labels)
        
        return self.prepare_clusters(labels)
    
    def _find_optimal_clusters(self, vectors: np.ndarray) -> int:
        """
        Find optimal number of clusters using silhouette analysis.
        
        Args:
            vectors: Feature matrix
            
        Returns:
            Optimal number of clusters
        """
        n_samples = vectors.shape[0]
        max_clusters = min(10, n_samples - 1)
        
        if max_clusters < 2:
            return 2
        
        scores = []
        
        for k in range(2, max_clusters + 1):
            clustering = AgglomerativeClustering(
                n_clusters=k,
                linkage=self.linkage,
                metric=self.affinity
            )
            
            labels = clustering.fit_predict(vectors)
            score = silhouette_score(vectors, labels)
            scores.append(score)
        
        # Find optimal k (highest silhouette score)
        if scores:
            optimal_idx = np.argmax(scores)
            return 2 + optimal_idx
        
        return 2
    
    def get_dendrogram_data(self, vectors: np.ndarray) -> Dict[str, Any]:
        """
        Get dendrogram data for visualization.
        
        Args:
            vectors: Feature matrix
            
        Returns:
            Dendrogram data dictionary
        """
        if self.linkage_matrix_ is None:
            condensed_dist = pdist(vectors, metric=self.affinity)
            self.linkage_matrix_ = linkage(condensed_dist, method=self.linkage)
        
        return dendrogram(self.linkage_matrix_, no_plot=True)
    
    def get_params(self) -> Dict[str, Any]:
        """Get clustering parameters."""
        return {
            'algorithm': 'hierarchical',
            'n_clusters': self.n_clusters_,
            'linkage': self.linkage,
            'affinity': self.affinity,
            'distance_threshold': self.distance_threshold,
            'silhouette_score': self.silhouette_score_
        }