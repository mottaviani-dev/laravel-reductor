"""Base interface for clustering algorithms."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import numpy as np


class Clusterer(ABC):
    """Abstract base class for clustering algorithms."""
    
    @abstractmethod
    def cluster(self, 
                vectors: np.ndarray,
                **kwargs) -> Dict[int, List[int]]:
        """
        Perform clustering on feature vectors.
        
        Args:
            vectors: Feature matrix (n_samples, n_features)
            **kwargs: Algorithm-specific parameters
            
        Returns:
            Dict mapping cluster IDs to lists of sample indices
        """
        pass
    
    @abstractmethod
    def get_params(self) -> Dict[str, Any]:
        """Get clustering parameters."""
        pass
    
    def prepare_clusters(self, 
                        labels: np.ndarray) -> Dict[int, List[int]]:
        """
        Convert cluster labels to dictionary format.
        
        Args:
            labels: Array of cluster labels
            
        Returns:
            Dict mapping cluster IDs to lists of sample indices
        """
        clusters = {}
        
        for idx, label in enumerate(labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(idx)
        
        return clusters