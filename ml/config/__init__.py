"""Configuration module for ML pipeline."""

from .thresholds import (
    ClusteringThresholds,
    SimilarityThresholds,
    EntropyThresholds,
    ValidationThresholds,
    ThresholdConfig
)

from .constants import (
    # Dimensions
    SEMANTIC_DIM,
    COVERAGE_DIM,
    COMBINED_DIM,
    # Algorithms
    ALGORITHM_KMEANS,
    ALGORITHM_DBSCAN,
    ALGORITHM_HIERARCHICAL,
    SUPPORTED_ALGORITHMS,
    # Reductions
    REDUCTION_PCA,
    REDUCTION_TSNE,
    REDUCTION_RANDOM,
    SUPPORTED_REDUCTIONS,
    # Formats
    FORMAT_JSON,
    FORMAT_CSV,
    FORMAT_MARKDOWN,
    SUPPORTED_FORMATS,
    # Other constants
    DEFAULT_RANDOM_STATE,
    DEFAULT_N_JOBS,
    MAX_FEATURES_TFIDF,
    MAX_SAMPLES_TSNE
)

__all__ = [
    # Thresholds
    'ClusteringThresholds',
    'SimilarityThresholds',
    'EntropyThresholds',
    'ValidationThresholds',
    'ThresholdConfig',
    # Constants
    'SEMANTIC_DIM',
    'COVERAGE_DIM',
    'COMBINED_DIM',
    'ALGORITHM_KMEANS',
    'ALGORITHM_DBSCAN',
    'ALGORITHM_HIERARCHICAL',
    'SUPPORTED_ALGORITHMS',
    'REDUCTION_PCA',
    'REDUCTION_TSNE',
    'REDUCTION_RANDOM',
    'SUPPORTED_REDUCTIONS',
    'FORMAT_JSON',
    'FORMAT_CSV',
    'FORMAT_MARKDOWN',
    'SUPPORTED_FORMATS',
    'DEFAULT_RANDOM_STATE',
    'DEFAULT_N_JOBS',
    'MAX_FEATURES_TFIDF',
    'MAX_SAMPLES_TSNE'
]