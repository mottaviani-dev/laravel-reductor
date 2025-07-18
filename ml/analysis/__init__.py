"""Analysis modules for test redundancy detection."""

from .reduction import (
    Reducer,
    PCAReducer,
    TSNEReducer,
    RandomProjectionReducer
)

from .redundancy import (
    RedundancyLevel,
    RedundancyThresholds,
    RedundancyAnalyzer
)

from .entropy import (
    EntropyConfig,
    EntropyAnalyzer
)

from .validation import (
    ValidationConfig,
    SemanticValidator
)

__all__ = [
    # Reduction
    'Reducer',
    'PCAReducer',
    'TSNEReducer',
    'RandomProjectionReducer',
    # Redundancy
    'RedundancyLevel',
    'RedundancyThresholds',
    'RedundancyAnalyzer',
    # Entropy
    'EntropyConfig',
    'EntropyAnalyzer',
    # Validation
    'ValidationConfig',
    'SemanticValidator'
]