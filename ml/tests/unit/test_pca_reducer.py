"""Unit tests for PCA reducer."""

import pytest
import numpy as np
from ml.analysis.reduction import PCAReducer


class TestPCAReducer:
    """Test cases for PCAReducer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create test data with known structure
        np.random.seed(42)
        # Data with high variance in first two dimensions
        self.data = np.random.randn(100, 10)
        self.data[:, 0] *= 5  # High variance in first dimension
        self.data[:, 1] *= 3  # Medium variance in second dimension
    
    def test_reduce_basic(self):
        """Test basic dimensionality reduction."""
        reducer = PCAReducer()
        reduced = reducer.reduce(self.data, n_dims=2)
        
        assert reduced.shape == (100, 2)
        assert reducer.pca_ is not None
        assert reducer.explained_variance_ratio_ is not None
    
    def test_reduce_with_standardization(self):
        """Test reduction with standardization."""
        reducer = PCAReducer(standardize=True)
        reduced = reducer.reduce(self.data, n_dims=2)
        
        assert reduced.shape == (100, 2)
        assert reducer.scaler_ is not None
    
    def test_reduce_without_standardization(self):
        """Test reduction without standardization."""
        reducer = PCAReducer(standardize=False)
        reduced = reducer.reduce(self.data, n_dims=2)
        
        assert reduced.shape == (100, 2)
        assert reducer.scaler_ is None
    
    def test_reduce_with_whitening(self):
        """Test reduction with whitening."""
        reducer = PCAReducer(whiten=True)
        reduced = reducer.reduce(self.data, n_dims=2)
        
        # Whitened data should have unit variance
        variances = np.var(reduced, axis=0)
        assert np.allclose(variances, 1.0, atol=0.1)
    
    def test_explained_variance(self):
        """Test explained variance calculation."""
        reducer = PCAReducer()
        reducer.reduce(self.data, n_dims=3)
        
        var_ratios, total_var = reducer.get_explained_variance()
        
        assert len(var_ratios) == 3
        assert 0 <= total_var <= 1
        assert np.all(var_ratios >= 0)
        assert np.all(var_ratios <= 1)
    
    def test_dimension_limiting(self):
        """Test dimension limiting based on data."""
        small_data = np.random.randn(5, 10)  # 5 samples, 10 features
        
        reducer = PCAReducer()
        reduced = reducer.reduce(small_data, n_dims=20)  # Request more dims than possible
        
        # Should be limited by min(samples, features)
        assert reduced.shape[1] <= min(5, 10)
    
    def test_get_params(self):
        """Test getting reducer parameters."""
        reducer = PCAReducer(whiten=True, standardize=True, random_state=123)
        reducer.reduce(self.data, n_dims=2)
        
        params = reducer.get_params()
        
        assert params['algorithm'] == 'pca'
        assert params['whiten'] is True
        assert params['standardize'] is True
        assert params['random_state'] == 123
        assert 'total_explained_variance' in params
        assert params['n_components'] == 2
    
    def test_reproducibility(self):
        """Test reproducibility with fixed random state."""
        reducer1 = PCAReducer(random_state=42)
        reducer2 = PCAReducer(random_state=42)
        
        reduced1 = reducer1.reduce(self.data, n_dims=2)
        reduced2 = reducer2.reduce(self.data, n_dims=2)
        
        # Results should be identical (or very close due to numerical precision)
        assert np.allclose(np.abs(reduced1), np.abs(reduced2))
    
    def test_single_sample(self):
        """Test handling of single sample."""
        single_sample = np.array([[1, 2, 3, 4, 5]])
        
        reducer = PCAReducer()
        reduced = reducer.reduce(single_sample, n_dims=2)
        
        # Should handle gracefully
        assert reduced.shape[0] == 1
        assert reduced.shape[1] <= 1  # Can only have 1 PC with 1 sample
    
    def test_variance_preservation(self):
        """Test that PCA preserves most variance in first components."""
        reducer = PCAReducer()
        reducer.reduce(self.data, n_dims=5)
        
        var_ratios = reducer.explained_variance_ratio_
        
        # Variance ratios should be in descending order
        assert all(var_ratios[i] >= var_ratios[i+1] for i in range(len(var_ratios)-1))
        
        # First component should capture significant variance
        assert var_ratios[0] > 0.1
    
    def test_zero_variance_features(self):
        """Test handling of zero variance features."""
        # Add constant columns
        data_with_constants = self.data.copy()
        data_with_constants[:, 5] = 1.0  # Constant column
        data_with_constants[:, 6] = 0.0  # Zero column
        
        reducer = PCAReducer()
        reduced = reducer.reduce(data_with_constants, n_dims=2)
        
        assert reduced.shape == (100, 2)
    
    def test_get_explained_variance_before_fit(self):
        """Test error when getting variance before fitting."""
        reducer = PCAReducer()
        
        with pytest.raises(ValueError, match="not fitted"):
            reducer.get_explained_variance()


if __name__ == '__main__':
    pytest.main([__file__])