"""K-Means clustering implementation with sparse matrix support."""

from typing import Dict, List, Optional, Any, Union
import numpy as np
import warnings
from scipy.sparse import issparse, csr_matrix
from sklearn.cluster import KMeans as SklearnKMeans
from sklearn.metrics import silhouette_score
from sklearn.exceptions import ConvergenceWarning

from .base import Clusterer


class KMeansClusterer(Clusterer):
    """K-Means clustering algorithm."""
    
    def __init__(self,
                 n_clusters: Optional[int] = None,
                 min_clusters: int = 2,
                 max_clusters: int = 10,
                 n_init: int = 10,
                 max_iter: int = 300,
                 random_state: int = 42):
        """
        Initialize K-Means clusterer.
        
        Args:
            n_clusters: Number of clusters (None for auto-selection)
            min_clusters: Minimum clusters for auto-selection
            max_clusters: Maximum clusters for auto-selection
            n_init: Number of initializations
            max_iter: Maximum iterations
            random_state: Random seed
        """
        self.n_clusters = n_clusters
        self.min_clusters = min_clusters
        self.max_clusters = max_clusters
        self.n_init = n_init
        self.max_iter = max_iter
        self.random_state = random_state
        
        self.optimal_k_: Optional[int] = None
        self.silhouette_score_: Optional[float] = None
        self.inertia_: Optional[float] = None
        
    def cluster(self, 
                vectors: Union[np.ndarray, csr_matrix],
                **kwargs) -> Dict[int, List[int]]:
        """
        Perform K-Means clustering with sparse matrix support.
        
        Args:
            vectors: Feature matrix (n_samples, n_features) - dense or sparse
            **kwargs: Additional parameters
            
        Returns:
            Dict mapping cluster IDs to lists of sample indices
        """
        # Validate input
        if not isinstance(vectors, (np.ndarray, csr_matrix)):
            raise ValueError(f"Expected numpy array or sparse matrix, got {type(vectors)}")
        
        if issparse(vectors) and vectors.format != 'csr':
            vectors = vectors.tocsr()
        
        if hasattr(vectors, 'shape'):
            if len(vectors.shape) != 2:
                raise ValueError(f"Expected 2D array, got {len(vectors.shape)}D array with shape {vectors.shape}")
        
        n_samples, n_features = vectors.shape
        
        if n_features == 0:
            raise ValueError("Feature vectors have zero dimensions")
        
        # Check for NaN or infinite values
        if issparse(vectors):
            if np.any(np.isnan(vectors.data)) or np.any(np.isinf(vectors.data)):
                raise ValueError("Input contains NaN or infinite values")
        else:
            if np.any(np.isnan(vectors)) or np.any(np.isinf(vectors)):
                raise ValueError("Input contains NaN or infinite values")
        
        # Handle edge cases
        if n_samples < 2:
            return {0: list(range(n_samples))}
        
        # Determine number of clusters
        if self.n_clusters is None:
            k = self._find_optimal_k(vectors)
        else:
            k = min(self.n_clusters, n_samples)
        
        self.optimal_k_ = k
        
        # Perform clustering
        kmeans = SklearnKMeans(
            n_clusters=k,
            n_init=self.n_init,
            max_iter=self.max_iter,
            random_state=self.random_state
        )
        
        labels = kmeans.fit_predict(vectors)
        self.inertia_ = kmeans.inertia_
        
        # Calculate silhouette score if possible
        if k > 1 and k < n_samples:
            self.silhouette_score_ = silhouette_score(vectors, labels)
        
        return self.prepare_clusters(labels)
    
    def _find_optimal_k(self, vectors: Union[np.ndarray, csr_matrix]) -> int:
        """
        Find optimal number of clusters using elbow method and silhouette score.
        Supports sparse matrices.
        
        Args:
            vectors: Feature matrix (dense or sparse)
            
        Returns:
            Optimal number of clusters
        """
        import logging
        logger = logging.getLogger(__name__)
        
        n_samples = vectors.shape[0]
        
        # Check for unique vectors to avoid convergence warnings
        if issparse(vectors):
            # For sparse matrices, convert to dense for unique check
            # This is acceptable since we're just checking uniqueness
            if n_samples < 1000:  # Only for small datasets
                unique_vectors = np.unique(vectors.toarray(), axis=0)
                n_unique = len(unique_vectors)
            else:
                # For large sparse matrices, skip unique check
                n_unique = n_samples
        else:
            unique_vectors = np.unique(vectors, axis=0)
            n_unique = len(unique_vectors)
        
        if n_unique < n_samples:
            logger.warning(f"Found only {n_unique} unique vectors out of {n_samples} samples. "
                         f"This may indicate duplicate tests or insufficient test diversity.")
        
        # If we have very few unique vectors, adjust our expectations
        if n_unique < self.min_clusters:
            logger.warning(f"Number of unique vectors ({n_unique}) is less than min_clusters ({self.min_clusters}). "
                         f"Adjusting min_clusters to {n_unique}")
            self.min_clusters = max(2, n_unique)  # At least 2 for meaningful clustering
        
        # Limit max_k to the number of unique vectors
        max_k = min(self.max_clusters, n_samples - 1, n_unique)
        
        if max_k < self.min_clusters:
            return self.min_clusters
        
        scores = []
        inertias = []
        valid_k = []
        
        for k in range(self.min_clusters, max_k + 1):
            try:
                # Suppress convergence warnings for cases where k > unique vectors
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=ConvergenceWarning)
                    
                    kmeans = SklearnKMeans(
                        n_clusters=k,
                        n_init=self.n_init,
                        max_iter=self.max_iter,
                        random_state=self.random_state
                    )
                    
                    labels = kmeans.fit_predict(vectors)
                
                # Check if we actually got k clusters
                n_clusters_found = len(np.unique(labels))
                if n_clusters_found < k:
                    logger.info(f"K={k}: Only found {n_clusters_found} clusters. "
                              f"This suggests {k - n_clusters_found} clusters collapsed due to similarity.")
                    # Still evaluate this clustering as it might be informative
                    # The algorithm naturally found fewer clusters than requested
                
                # Calculate silhouette score
                if k < n_samples and n_clusters_found > 1:
                    score = silhouette_score(vectors, labels)
                    scores.append(score)
                    inertias.append(kmeans.inertia_)
                    valid_k.append(k)
            except Exception as e:
                logger.debug(f"Failed to compute k={k}: {e}")
                continue
        
        # Find optimal k (highest silhouette score)
        if scores:
            optimal_idx = np.argmax(scores)
            optimal_k = valid_k[optimal_idx]
            self.silhouette_score_ = scores[optimal_idx]
            logger.info(f"Found optimal k={optimal_k} with silhouette score={self.silhouette_score_:.3f}")
            return optimal_k
        
        # If no valid clustering found, use the minimum of available unique points
        fallback_k = min(self.min_clusters, n_unique)
        logger.warning(f"No valid clustering found, using k={fallback_k}")
        return fallback_k
    
    def get_params(self) -> Dict[str, Any]:
        """Get clustering parameters."""
        return {
            'algorithm': 'kmeans',
            'n_clusters': self.optimal_k_ or self.n_clusters,
            'n_init': self.n_init,
            'max_iter': self.max_iter,
            'random_state': self.random_state,
            'silhouette_score': self.silhouette_score_,
            'inertia': self.inertia_
        }