"""Unit tests for cosine similarity calculation."""

import pytest
import numpy as np
from ml.core.normalization import cosine_similarity, combined_similarity


class TestCosineSimilarity:
    """Test cases for cosine similarity function."""
    
    def test_identical_vectors(self):
        """Test similarity of identical vectors."""
        vec1 = np.array([1, 2, 3])
        vec2 = np.array([1, 2, 3])
        
        similarity = cosine_similarity(vec1, vec2)
        
        assert pytest.approx(similarity) == 1.0
    
    def test_orthogonal_vectors(self):
        """Test similarity of orthogonal vectors."""
        vec1 = np.array([1, 0])
        vec2 = np.array([0, 1])
        
        similarity = cosine_similarity(vec1, vec2)
        
        assert pytest.approx(similarity) == 0.0
    
    def test_opposite_vectors(self):
        """Test similarity of opposite vectors."""
        vec1 = np.array([1, 2, 3])
        vec2 = np.array([-1, -2, -3])
        
        similarity = cosine_similarity(vec1, vec2)
        
        assert pytest.approx(similarity) == -1.0
    
    def test_scaled_vectors(self):
        """Test that scaling doesn't affect cosine similarity."""
        vec1 = np.array([1, 2, 3])
        vec2 = np.array([2, 4, 6])  # vec1 * 2
        
        similarity = cosine_similarity(vec1, vec2)
        
        assert pytest.approx(similarity) == 1.0
    
    def test_zero_vector(self):
        """Test handling of zero vectors."""
        vec1 = np.array([1, 2, 3])
        vec2 = np.array([0, 0, 0])
        
        similarity = cosine_similarity(vec1, vec2)
        
        assert similarity == 0.0
    
    def test_both_zero_vectors(self):
        """Test handling when both vectors are zero."""
        vec1 = np.array([0, 0, 0])
        vec2 = np.array([0, 0, 0])
        
        similarity = cosine_similarity(vec1, vec2)
        
        assert similarity == 0.0
    
    def test_different_dimensions_flattened(self):
        """Test that multi-dimensional arrays are flattened."""
        vec1 = np.array([[1, 2], [3, 4]])
        vec2 = np.array([[1, 2], [3, 4]])
        
        similarity = cosine_similarity(vec1, vec2)
        
        assert pytest.approx(similarity) == 1.0
    
    def test_high_dimensional_vectors(self):
        """Test with high-dimensional vectors."""
        np.random.seed(42)
        vec1 = np.random.randn(1000)
        vec2 = np.random.randn(1000)
        
        similarity = cosine_similarity(vec1, vec2)
        
        assert -1 <= similarity <= 1
    
    def test_nearly_similar_vectors(self):
        """Test nearly similar vectors."""
        vec1 = np.array([1.0, 2.0, 3.0])
        vec2 = np.array([1.01, 2.01, 3.01])
        
        similarity = cosine_similarity(vec1, vec2)
        
        assert similarity > 0.99
        assert similarity < 1.0


class TestCombinedSimilarity:
    """Test cases for combined similarity function."""
    
    def test_combined_similarity_basic(self):
        """Test basic combined similarity calculation."""
        sem1 = np.array([1, 0, 0])
        sem2 = np.array([1, 0, 0])
        cov1 = np.array([0, 1, 0])
        cov2 = np.array([0, 0, 1])
        
        result = combined_similarity(sem1, sem2, cov1, cov2)
        
        assert 'semantic_similarity' in result
        assert 'coverage_similarity' in result
        assert 'combined_similarity' in result
        
        assert result['semantic_similarity'] == 1.0  # Identical
        assert result['coverage_similarity'] == 0.0  # Orthogonal
        assert result['combined_similarity'] == 0.7  # 0.7 * 1 + 0.3 * 0
    
    def test_combined_similarity_custom_weights(self):
        """Test combined similarity with custom weights."""
        sem1 = np.array([1, 0])
        sem2 = np.array([0, 1])
        cov1 = np.array([1, 0])
        cov2 = np.array([1, 0])
        
        result = combined_similarity(
            sem1, sem2, cov1, cov2,
            semantic_weight=0.5,
            coverage_weight=0.5
        )
        
        assert result['semantic_similarity'] == 0.0  # Orthogonal
        assert result['coverage_similarity'] == 1.0  # Identical
        assert result['combined_similarity'] == 0.5  # 0.5 * 0 + 0.5 * 1
    
    def test_combined_similarity_all_identical(self):
        """Test when all vectors are identical."""
        vec = np.array([1, 2, 3, 4, 5])
        
        result = combined_similarity(vec, vec, vec, vec)
        
        assert result['semantic_similarity'] == 1.0
        assert result['coverage_similarity'] == 1.0
        assert result['combined_similarity'] == 1.0
    
    def test_combined_similarity_all_orthogonal(self):
        """Test when all vectors are orthogonal."""
        sem1 = np.array([1, 0, 0, 0])
        sem2 = np.array([0, 1, 0, 0])
        cov1 = np.array([0, 0, 1, 0])
        cov2 = np.array([0, 0, 0, 1])
        
        result = combined_similarity(sem1, sem2, cov1, cov2)
        
        assert result['semantic_similarity'] == 0.0
        assert result['coverage_similarity'] == 0.0
        assert result['combined_similarity'] == 0.0
    
    def test_weight_validation(self):
        """Test that weights sum to 1.0 conceptually."""
        vec = np.array([1, 2, 3])
        
        # Test with weights that should sum to 1
        result = combined_similarity(
            vec, vec, vec, vec,
            semantic_weight=0.8,
            coverage_weight=0.2
        )
        
        # All similarities are 1.0, so combined should also be 1.0
        assert result['combined_similarity'] == 1.0
    
    def test_zero_vectors_handling(self):
        """Test handling of zero vectors in combined similarity."""
        zero_vec = np.array([0, 0, 0])
        normal_vec = np.array([1, 2, 3])
        
        result = combined_similarity(
            zero_vec, normal_vec,
            zero_vec, normal_vec
        )
        
        assert result['semantic_similarity'] == 0.0
        assert result['coverage_similarity'] == 0.0
        assert result['combined_similarity'] == 0.0


if __name__ == '__main__':
    pytest.main([__file__])