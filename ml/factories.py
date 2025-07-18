"""Factory functions for creating ML components."""

from typing import Dict, Any, Optional

from .clustering import (
    Clusterer,
    KMeansClusterer,
    DBSCANClusterer,
    HierarchicalClusterer
)

from .analysis import (
    Reducer,
    PCAReducer,
    TSNEReducer,
    RandomProjectionReducer
)

from .config import (
    ALGORITHM_KMEANS,
    ALGORITHM_DBSCAN,
    ALGORITHM_HIERARCHICAL,
    REDUCTION_PCA,
    REDUCTION_TSNE,
    REDUCTION_RANDOM
)


# Registry of available components
CLUSTERERS = {
    ALGORITHM_KMEANS: KMeansClusterer,
    ALGORITHM_DBSCAN: DBSCANClusterer,
    ALGORITHM_HIERARCHICAL: HierarchicalClusterer
}

REDUCERS = {
    REDUCTION_PCA: PCAReducer,
    REDUCTION_TSNE: TSNEReducer,
    REDUCTION_RANDOM: RandomProjectionReducer
}


def get_clusterer(name: str, **kwargs) -> Clusterer:
    """
    Create clustering algorithm instance.
    
    Args:
        name: Algorithm name
        **kwargs: Algorithm-specific parameters
        
    Returns:
        Clusterer instance
        
    Raises:
        ValueError: If algorithm name is not recognized
    """
    if name not in CLUSTERERS:
        raise ValueError(
            f"Unknown clustering algorithm: {name}. "
            f"Available: {list(CLUSTERERS.keys())}"
        )
    
    return CLUSTERERS[name](**kwargs)


def get_reducer(name: str, **kwargs) -> Reducer:
    """
    Create dimensionality reduction algorithm instance.
    
    Args:
        name: Algorithm name
        **kwargs: Algorithm-specific parameters
        
    Returns:
        Reducer instance
        
    Raises:
        ValueError: If algorithm name is not recognized
    """
    if name not in REDUCERS:
        raise ValueError(
            f"Unknown reduction algorithm: {name}. "
            f"Available: {list(REDUCERS.keys())}"
        )
    
    return REDUCERS[name](**kwargs)


def register_clusterer(name: str, clusterer_class: type) -> None:
    """Register new clustering algorithm."""
    if not issubclass(clusterer_class, Clusterer):
        raise TypeError(f"{clusterer_class} must inherit from Clusterer")
    CLUSTERERS[name] = clusterer_class


def register_reducer(name: str, reducer_class: type) -> None:
    """Register new reduction algorithm."""
    if not issubclass(reducer_class, Reducer):
        raise TypeError(f"{reducer_class} must inherit from Reducer")
    REDUCERS[name] = reducer_class