"""NumPy array utilities."""

import numpy as np
from typing import List, Dict, Union, Tuple


def to_numpy_array(data: Union[List, np.ndarray], dtype: type = np.float32) -> np.ndarray:
    """
    Convert data to numpy array.
    
    Args:
        data: Input data
        dtype: Target data type
        
    Returns:
        NumPy array
    """
    if isinstance(data, np.ndarray):
        return data.astype(dtype)
    return np.array(data, dtype=dtype)


def arrays_to_matrix(vectors: Dict[str, np.ndarray], 
                    order: List[str] = None) -> Tuple[np.ndarray, List[str]]:
    """
    Convert dictionary of vectors to matrix.
    
    Args:
        vectors: Dict mapping names to vectors
        order: Optional ordering for rows
        
    Returns:
        Tuple of (matrix, row_names)
    """
    if order is None:
        order = sorted(vectors.keys())
    
    matrix = np.vstack([vectors[name] for name in order])
    return matrix, order


def matrix_to_dict(matrix: np.ndarray, 
                  names: List[str]) -> Dict[str, np.ndarray]:
    """
    Convert matrix to dictionary of vectors.
    
    Args:
        matrix: Feature matrix
        names: Row names
        
    Returns:
        Dict mapping names to vectors
    """
    if len(matrix) != len(names):
        raise ValueError(f"Matrix rows ({len(matrix)}) != names ({len(names)})")
    
    return {name: matrix[i] for i, name in enumerate(names)}