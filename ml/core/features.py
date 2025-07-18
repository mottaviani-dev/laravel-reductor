"""Feature preparation and combination utilities."""

import numpy as np
from typing import Dict, Tuple, List, Optional
from .normalization import l2_normalize


class FeatureCombiner:
    """Combines semantic and coverage features into unified vectors."""
    
    def __init__(self,
                 semantic_dim: int = 128,
                 coverage_dim: int = 512,
                 normalize: bool = True):
        """
        Initialize feature combiner.
        
        Args:
            semantic_dim: Dimension of semantic vectors
            coverage_dim: Dimension of coverage vectors
            normalize: Whether to normalize combined vectors
        """
        self.semantic_dim = semantic_dim
        self.coverage_dim = coverage_dim
        self.total_dim = semantic_dim + coverage_dim
        self.normalize = normalize
    
    def combine_features(self,
                        semantic_vectors: Dict[str, np.ndarray],
                        coverage_vectors: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
        """
        Combine semantic and coverage vectors.
        
        Args:
            semantic_vectors: Dict mapping test names to semantic vectors
            coverage_vectors: Dict mapping test names to coverage vectors
            
        Returns:
            Dict mapping test names to combined vectors
        """
        combined_vectors = {}
        
        # Get all test names (union of both dicts)
        all_tests = set(semantic_vectors.keys()) | set(coverage_vectors.keys())
        
        for test_name in all_tests:
            # Get vectors, using zeros if missing
            semantic_vec = semantic_vectors.get(
                test_name, 
                np.zeros(self.semantic_dim)
            )
            coverage_vec = coverage_vectors.get(
                test_name, 
                np.zeros(self.coverage_dim)
            )
            
            # Validate dimensions
            if semantic_vec.shape[0] != self.semantic_dim:
                raise ValueError(
                    f"Semantic vector for {test_name} has wrong dimension: "
                    f"{semantic_vec.shape[0]} vs expected {self.semantic_dim}"
                )
            if coverage_vec.shape[0] != self.coverage_dim:
                raise ValueError(
                    f"Coverage vector for {test_name} has wrong dimension: "
                    f"{coverage_vec.shape[0]} vs expected {self.coverage_dim}"
                )
            
            # Concatenate features
            combined = np.concatenate([semantic_vec, coverage_vec])
            
            # Normalize if requested
            if self.normalize:
                combined = l2_normalize(combined)
            
            combined_vectors[test_name] = combined
        
        return combined_vectors
    
    def split_features(self, 
                      combined_vector: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Split a combined vector back into semantic and coverage components.
        
        Args:
            combined_vector: Combined feature vector
            
        Returns:
            Tuple of (semantic_vector, coverage_vector)
        """
        if combined_vector.shape[0] != self.total_dim:
            raise ValueError(
                f"Combined vector has wrong dimension: "
                f"{combined_vector.shape[0]} vs expected {self.total_dim}"
            )
        
        semantic_vec = combined_vector[:self.semantic_dim]
        coverage_vec = combined_vector[self.semantic_dim:]
        
        return semantic_vec, coverage_vec
    
    def prepare_matrix(self,
                      vectors: Dict[str, np.ndarray],
                      test_order: Optional[List[str]] = None) -> Tuple[np.ndarray, List[str]]:
        """
        Prepare feature matrix from dictionary of vectors.
        
        Args:
            vectors: Dict mapping test names to vectors
            test_order: Optional list specifying test order
            
        Returns:
            Tuple of (feature_matrix, test_names)
        """
        if test_order is None:
            test_order = sorted(vectors.keys())
        
        # Validate all tests are present
        missing_tests = set(test_order) - set(vectors.keys())
        if missing_tests:
            raise ValueError(f"Missing vectors for tests: {missing_tests}")
        
        # Stack vectors in order
        matrix = np.vstack([vectors[test] for test in test_order])
        
        return matrix, test_order
    
    def vectors_to_dict(self,
                       matrix: np.ndarray,
                       test_names: List[str]) -> Dict[str, np.ndarray]:
        """
        Convert feature matrix back to dictionary.
        
        Args:
            matrix: Feature matrix (n_tests, n_features)
            test_names: List of test names corresponding to rows
            
        Returns:
            Dict mapping test names to vectors
        """
        if matrix.shape[0] != len(test_names):
            raise ValueError(
                f"Matrix rows ({matrix.shape[0]}) != number of test names ({len(test_names)})"
            )
        
        return {
            test_name: matrix[i]
            for i, test_name in enumerate(test_names)
        }