"""Clustering algorithms and utilities."""

from .base import Clusterer
from .kmeans import KMeansClusterer
from .dbscan import DBSCANClusterer
from .hierarchical import HierarchicalClusterer
from .metrics import (
    calculate_pairwise_similarities,
    evaluate_clustering,
    find_optimal_threshold,
    cluster_cohesion,
    cluster_separation
)

__all__ = [
    'Clusterer',
    'KMeansClusterer',
    'DBSCANClusterer',
    'HierarchicalClusterer',
    'calculate_pairwise_similarities',
    'evaluate_clustering',
    'find_optimal_threshold',
    'cluster_cohesion',
    'cluster_separation'
]