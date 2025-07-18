"""Dimensionality reduction algorithms."""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple
import numpy as np
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler


class Reducer(ABC):
    """Abstract base class for dimensionality reduction algorithms."""
    
    @abstractmethod
    def reduce(self, 
               vectors: np.ndarray, 
               n_dims: int) -> np.ndarray:
        """
        Reduce dimensionality of vectors.
        
        Args:
            vectors: Input vectors (n_samples, n_features)
            n_dims: Target dimensionality
            
        Returns:
            Reduced vectors (n_samples, n_dims)
        """
        pass
    
    @abstractmethod
    def get_params(self) -> Dict[str, Any]:
        """Get reducer parameters."""
        pass


class PCAReducer(Reducer):
    """Principal Component Analysis dimensionality reduction."""
    
    def __init__(self, 
                 whiten: bool = False,
                 standardize: bool = True,
                 random_state: int = 42):
        """
        Initialize PCA reducer.
        
        Args:
            whiten: Whether to whiten the data
            standardize: Whether to standardize before PCA
            random_state: Random seed
        """
        self.whiten = whiten
        self.standardize = standardize
        self.random_state = random_state
        
        self.pca_: Optional[PCA] = None
        self.scaler_: Optional[StandardScaler] = None
        self.explained_variance_ratio_: Optional[np.ndarray] = None
        
    def reduce(self, 
               vectors: np.ndarray, 
               n_dims: int) -> np.ndarray:
        """
        Reduce dimensionality using PCA.
        
        Args:
            vectors: Input vectors (n_samples, n_features)
            n_dims: Target dimensionality
            
        Returns:
            Reduced vectors (n_samples, n_dims)
        """
        n_samples, n_features = vectors.shape
        
        # Limit dimensions to available features
        n_dims = min(n_dims, n_features, n_samples)
        
        # Standardize if requested
        if self.standardize:
            self.scaler_ = StandardScaler()
            vectors_scaled = self.scaler_.fit_transform(vectors)
        else:
            vectors_scaled = vectors
        
        # Apply PCA
        self.pca_ = PCA(
            n_components=n_dims,
            whiten=self.whiten,
            random_state=self.random_state
        )
        
        reduced_vectors = self.pca_.fit_transform(vectors_scaled)
        self.explained_variance_ratio_ = self.pca_.explained_variance_ratio_
        
        return reduced_vectors
    
    def get_explained_variance(self) -> Tuple[np.ndarray, float]:
        """
        Get explained variance ratios.
        
        Returns:
            Tuple of (variance_ratios, cumulative_variance)
        """
        if self.explained_variance_ratio_ is None:
            raise ValueError("PCA not fitted yet")
        
        cumulative = np.cumsum(self.explained_variance_ratio_)
        return self.explained_variance_ratio_, float(cumulative[-1])
    
    def get_params(self) -> Dict[str, Any]:
        """Get reducer parameters."""
        params = {
            'algorithm': 'pca',
            'whiten': self.whiten,
            'standardize': self.standardize,
            'random_state': self.random_state
        }
        
        if self.explained_variance_ratio_ is not None:
            _, total_variance = self.get_explained_variance()
            params['total_explained_variance'] = total_variance
            params['n_components'] = len(self.explained_variance_ratio_)
        
        return params


class TSNEReducer(Reducer):
    """t-SNE dimensionality reduction."""
    
    def __init__(self,
                 perplexity: float = 30.0,
                 learning_rate: float = 200.0,
                 n_iter: int = 1000,
                 metric: str = 'euclidean',
                 init: str = 'pca',
                 random_state: int = 42):
        """
        Initialize t-SNE reducer.
        
        Args:
            perplexity: Perplexity parameter
            learning_rate: Learning rate
            n_iter: Number of iterations
            metric: Distance metric
            init: Initialization method
            random_state: Random seed
        """
        self.perplexity = perplexity
        self.learning_rate = learning_rate
        self.n_iter = n_iter
        self.metric = metric
        self.init = init
        self.random_state = random_state
        
        self.kl_divergence_: Optional[float] = None
        
    def reduce(self, 
               vectors: np.ndarray, 
               n_dims: int) -> np.ndarray:
        """
        Reduce dimensionality using t-SNE.
        
        Args:
            vectors: Input vectors (n_samples, n_features)
            n_dims: Target dimensionality (typically 2 or 3)
            
        Returns:
            Reduced vectors (n_samples, n_dims)
        """
        if n_dims > 3:
            raise ValueError("t-SNE is typically used for 2D or 3D visualization")
        
        n_samples = vectors.shape[0]
        
        # Adjust perplexity if needed
        perplexity = min(self.perplexity, n_samples - 1)
        
        # Apply t-SNE
        tsne = TSNE(
            n_components=n_dims,
            perplexity=perplexity,
            learning_rate=self.learning_rate,
            n_iter=self.n_iter,
            metric=self.metric,
            init=self.init,
            random_state=self.random_state
        )
        
        reduced_vectors = tsne.fit_transform(vectors)
        self.kl_divergence_ = tsne.kl_divergence_
        
        return reduced_vectors
    
    def get_params(self) -> Dict[str, Any]:
        """Get reducer parameters."""
        params = {
            'algorithm': 'tsne',
            'perplexity': self.perplexity,
            'learning_rate': self.learning_rate,
            'n_iter': self.n_iter,
            'metric': self.metric,
            'init': self.init,
            'random_state': self.random_state
        }
        
        if self.kl_divergence_ is not None:
            params['kl_divergence'] = float(self.kl_divergence_)
        
        return params


class RandomProjectionReducer(Reducer):
    """Random projection dimensionality reduction."""
    
    def __init__(self,
                 eps: float = 0.1,
                 random_state: int = 42):
        """
        Initialize random projection reducer.
        
        Args:
            eps: Tolerance for quality of embedding
            random_state: Random seed
        """
        self.eps = eps
        self.random_state = random_state
        self.projection_matrix_: Optional[np.ndarray] = None
        
    def reduce(self, 
               vectors: np.ndarray, 
               n_dims: int) -> np.ndarray:
        """
        Reduce dimensionality using random projection.
        
        Args:
            vectors: Input vectors (n_samples, n_features)
            n_dims: Target dimensionality
            
        Returns:
            Reduced vectors (n_samples, n_dims)
        """
        n_samples, n_features = vectors.shape
        
        # Generate random projection matrix
        rng = np.random.RandomState(self.random_state)
        
        # Use sparse random projection
        # Elements are drawn from N(0, 1/n_dims)
        self.projection_matrix_ = rng.randn(n_features, n_dims)
        self.projection_matrix_ /= np.sqrt(n_dims)
        
        # Project vectors
        reduced_vectors = vectors @ self.projection_matrix_
        
        return reduced_vectors
    
    def get_params(self) -> Dict[str, Any]:
        """Get reducer parameters."""
        return {
            'algorithm': 'random_projection',
            'eps': self.eps,
            'random_state': self.random_state
        }