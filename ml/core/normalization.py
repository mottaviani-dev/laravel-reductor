"""Vector normalization utilities."""

import numpy as np
from typing import Union, Optional


def l2_normalize(vector: np.ndarray, 
                 axis: Optional[int] = None,
                 epsilon: float = 1e-12) -> np.ndarray:
    """
    L2 normalize a vector or matrix.
    
    Args:
        vector: Input vector or matrix
        axis: Axis along which to normalize (None for vector)
        epsilon: Small value to avoid division by zero
        
    Returns:
        L2 normalized vector/matrix
    """
    norm = np.linalg.norm(vector, axis=axis, keepdims=True)
    # Avoid division by zero
    norm = np.maximum(norm, epsilon)
    return vector / norm


def min_max_normalize(vector: np.ndarray,
                     feature_range: tuple = (0, 1),
                     axis: Optional[int] = None) -> np.ndarray:
    """
    Min-max normalize a vector or matrix.
    
    Args:
        vector: Input vector or matrix
        feature_range: Desired range of transformed data
        axis: Axis along which to normalize
        
    Returns:
        Min-max normalized vector/matrix
    """
    min_val = np.min(vector, axis=axis, keepdims=True)
    max_val = np.max(vector, axis=axis, keepdims=True)
    
    # Avoid division by zero
    range_val = max_val - min_val
    range_val = np.where(range_val == 0, 1, range_val)
    
    # Scale to [0, 1]
    normalized = (vector - min_val) / range_val
    
    # Scale to feature_range
    scale = feature_range[1] - feature_range[0]
    normalized = normalized * scale + feature_range[0]
    
    return normalized


def standardize(vector: np.ndarray,
               axis: Optional[int] = None,
               epsilon: float = 1e-12) -> np.ndarray:
    """
    Standardize a vector or matrix (zero mean, unit variance).
    
    Args:
        vector: Input vector or matrix
        axis: Axis along which to standardize
        epsilon: Small value to avoid division by zero
        
    Returns:
        Standardized vector/matrix
    """
    mean = np.mean(vector, axis=axis, keepdims=True)
    std = np.std(vector, axis=axis, keepdims=True)
    
    # Avoid division by zero
    std = np.maximum(std, epsilon)
    
    return (vector - mean) / std


def cosine_similarity(vector1: np.ndarray, 
                     vector2: np.ndarray) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        vector1: First vector
        vector2: Second vector
        
    Returns:
        Cosine similarity (-1 to 1)
    """
    # Ensure vectors are 1D
    v1 = vector1.flatten()
    v2 = vector2.flatten()
    
    # Calculate dot product
    dot_product = np.dot(v1, v2)
    
    # Calculate norms
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    
    # Avoid division by zero
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(dot_product / (norm1 * norm2))


def euclidean_distance(vector1: np.ndarray, 
                      vector2: np.ndarray) -> float:
    """
    Calculate Euclidean distance between two vectors.
    
    Args:
        vector1: First vector
        vector2: Second vector
        
    Returns:
        Euclidean distance
    """
    return float(np.linalg.norm(vector1 - vector2))


def combined_similarity(semantic_vec1: np.ndarray,
                       semantic_vec2: np.ndarray,
                       coverage_vec1: np.ndarray,
                       coverage_vec2: np.ndarray,
                       semantic_weight: float = 0.7,
                       coverage_weight: float = 0.3) -> dict:
    """
    Calculate combined similarity between test vectors.
    
    Args:
        semantic_vec1: First semantic vector
        semantic_vec2: Second semantic vector
        coverage_vec1: First coverage vector
        coverage_vec2: Second coverage vector
        semantic_weight: Weight for semantic similarity
        coverage_weight: Weight for coverage similarity
        
    Returns:
        Dict with similarity scores
    """
    # Calculate individual similarities
    semantic_sim = cosine_similarity(semantic_vec1, semantic_vec2)
    coverage_sim = cosine_similarity(coverage_vec1, coverage_vec2)
    
    # Calculate weighted combination
    combined_sim = (
        semantic_weight * semantic_sim + 
        coverage_weight * coverage_sim
    )
    
    return {
        'semantic_similarity': semantic_sim,
        'coverage_similarity': coverage_sim,
        'combined_similarity': combined_sim
    }