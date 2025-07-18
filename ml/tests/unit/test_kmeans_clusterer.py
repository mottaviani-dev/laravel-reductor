"""Unit tests for K-Means clusterer."""

import pytest
import numpy as np
from ml.clustering.kmeans import KMeansClusterer


class TestKMeansClusterer:
    """Test cases for KMeansClusterer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create simple test data with 3 clear clusters
        np.random.seed(42)
        self.data = np.vstack([
            np.random.randn(10, 2) + [0, 0],    # Cluster 1
            np.random.randn(10, 2) + [5, 5],    # Cluster 2
            np.random.randn(10, 2) + [-5, 5],   # Cluster 3
        ])
    
    def test_cluster_with_fixed_k(self):
        """Test clustering with fixed number of clusters."""
        clusterer = KMeansClusterer(n_clusters=3)
        clusters = clusterer.cluster(self.data)
        
        assert len(clusters) == 3
        assert sum(len(indices) for indices in clusters.values()) == len(self.data)
        assert clusterer.optimal_k_ == 3
    
    def test_cluster_with_auto_k(self):
        """Test clustering with automatic k selection."""
        clusterer = KMeansClusterer(n_clusters=None, min_clusters=2, max_clusters=5)
        clusters = clusterer.cluster(self.data)
        
        assert 2 <= len(clusters) <= 5
        assert clusterer.optimal_k_ is not None
        assert clusterer.silhouette_score_ is not None
    
    def test_edge_case_single_sample(self):
        """Test handling of single sample."""
        data = np.array([[1, 2]])
        clusterer = KMeansClusterer(n_clusters=1)
        clusters = clusterer.cluster(data)
        
        assert len(clusters) == 1
        assert clusters[0] == [0]
    
    def test_edge_case_two_samples(self):
        """Test handling of two samples."""
        data = np.array([[1, 2], [3, 4]])
        clusterer = KMeansClusterer(n_clusters=2)
        clusters = clusterer.cluster(data)
        
        assert len(clusters) == 2
    
    def test_prepare_clusters_format(self):
        """Test cluster format conversion."""
        labels = np.array([0, 0, 1, 1, 2])
        clusterer = KMeansClusterer()
        clusters = clusterer.prepare_clusters(labels)
        
        assert clusters == {
            0: [0, 1],
            1: [2, 3],
            2: [4]
        }
    
    def test_get_params(self):
        """Test getting clustering parameters."""
        clusterer = KMeansClusterer(n_clusters=3)
        clusterer.cluster(self.data)
        
        params = clusterer.get_params()
        
        assert params['algorithm'] == 'kmeans'
        assert params['n_clusters'] == 3
        assert 'silhouette_score' in params
        assert 'inertia' in params
    
    def test_silhouette_score_calculation(self):
        """Test silhouette score is calculated correctly."""
        clusterer = KMeansClusterer(n_clusters=3)
        clusterer.cluster(self.data)
        
        assert clusterer.silhouette_score_ is not None
        assert -1 <= clusterer.silhouette_score_ <= 1
    
    def test_find_optimal_k_elbow(self):
        """Test optimal k finding with elbow method."""
        clusterer = KMeansClusterer(n_clusters=None, min_clusters=2, max_clusters=5)
        
        # Use private method directly
        optimal_k = clusterer._find_optimal_k(self.data)
        
        assert 2 <= optimal_k <= 5
    
    def test_max_clusters_exceeds_samples(self):
        """Test handling when max_clusters exceeds sample count."""
        small_data = np.array([[1, 2], [3, 4], [5, 6]])
        clusterer = KMeansClusterer(n_clusters=None, min_clusters=2, max_clusters=10)
        
        clusters = clusterer.cluster(small_data)
        
        # Should be limited by sample count
        assert len(clusters) <= len(small_data) - 1
    
    def test_reproducibility_with_random_state(self):
        """Test reproducibility with fixed random state."""
        clusterer1 = KMeansClusterer(n_clusters=3, random_state=42)
        clusterer2 = KMeansClusterer(n_clusters=3, random_state=42)
        
        clusters1 = clusterer1.cluster(self.data)
        clusters2 = clusterer2.cluster(self.data)
        
        # Should produce same clustering
        for cluster_id in clusters1:
            assert sorted(clusters1[cluster_id]) == sorted(clusters2[cluster_id])
    
    def test_inertia_calculation(self):
        """Test that inertia is calculated."""
        clusterer = KMeansClusterer(n_clusters=3)
        clusterer.cluster(self.data)
        
        assert clusterer.inertia_ is not None
        assert clusterer.inertia_ > 0
    
    def test_empty_data(self):
        """Test handling of empty data."""
        data = np.array([]).reshape(0, 2)
        clusterer = KMeansClusterer(n_clusters=3)
        clusters = clusterer.cluster(data)
        
        assert clusters == {0: []}


if __name__ == '__main__':
    pytest.main([__file__])