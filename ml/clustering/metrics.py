"""Clustering metrics and similarity calculations."""

import numpy as np
from typing import List, Dict, Tuple, Optional
from scipy.spatial.distance import cdist
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score


def calculate_pairwise_similarities(
    vectors: np.ndarray,
    metric: str = 'cosine'
) -> np.ndarray:
    """
    Calculate pairwise similarity matrix.
    
    Args:
        vectors: Feature matrix (n_samples, n_features)
        metric: Distance metric ('cosine', 'euclidean', etc.)
        
    Returns:
        Similarity matrix (n_samples, n_samples)
    """
    if metric == 'cosine':
        # For cosine similarity, use dot product on normalized vectors
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        normalized = np.divide(vectors, norms, where=norms != 0)
        similarity = normalized @ normalized.T
        # Ensure diagonal is 1.0
        np.fill_diagonal(similarity, 1.0)
        return similarity
    else:
        # For other metrics, convert distance to similarity
        distances = cdist(vectors, vectors, metric=metric)
        # Convert to similarity (inverse)
        max_dist = np.max(distances)
        if max_dist > 0:
            similarity = 1 - (distances / max_dist)
        else:
            similarity = np.ones_like(distances)
        return similarity


def evaluate_clustering(
    vectors: np.ndarray,
    labels: np.ndarray
) -> Dict[str, float]:
    """
    Evaluate clustering quality using multiple metrics.
    
    Args:
        vectors: Feature matrix
        labels: Cluster labels
        
    Returns:
        Dictionary of metric scores
    """
    metrics = {}
    
    # Number of unique clusters (excluding noise)
    unique_labels = set(labels)
    n_clusters = len(unique_labels - {-1})
    n_noise = list(labels).count(-1)
    
    metrics['n_clusters'] = n_clusters
    metrics['n_noise'] = n_noise
    
    # Only calculate metrics if we have valid clusters
    if n_clusters > 1 and n_clusters < len(labels) - n_noise:
        # Filter out noise points for metrics
        non_noise_mask = labels != -1
        if np.sum(non_noise_mask) > n_clusters:
            filtered_vectors = vectors[non_noise_mask]
            filtered_labels = labels[non_noise_mask]
            
            # Silhouette score (higher is better, -1 to 1)
            metrics['silhouette'] = silhouette_score(
                filtered_vectors, filtered_labels
            )
            
            # Calinski-Harabasz score (higher is better)
            metrics['calinski_harabasz'] = calinski_harabasz_score(
                filtered_vectors, filtered_labels
            )
            
            # Davies-Bouldin score (lower is better)
            metrics['davies_bouldin'] = davies_bouldin_score(
                filtered_vectors, filtered_labels
            )
    
    return metrics


def find_optimal_threshold(
    similarity_matrix: np.ndarray,
    percentiles: List[int] = [80, 85, 90, 95]
) -> float:
    """
    Find optimal similarity threshold based on distribution.
    
    Args:
        similarity_matrix: Pairwise similarity matrix
        percentiles: Percentiles to consider
        
    Returns:
        Optimal threshold value
    """
    # Get upper triangle (excluding diagonal)
    n = similarity_matrix.shape[0]
    upper_indices = np.triu_indices(n, k=1)
    similarities = similarity_matrix[upper_indices]
    
    # Calculate percentiles
    thresholds = np.percentile(similarities, percentiles)
    
    # Use knee point or 90th percentile as default
    return float(thresholds[2])  # 90th percentile


def cluster_cohesion(
    vectors: np.ndarray,
    cluster_indices: List[int],
    metric: str = 'euclidean'
) -> float:
    """
    Calculate cluster cohesion (average intra-cluster distance).
    
    Args:
        vectors: Feature matrix
        cluster_indices: Indices of samples in cluster
        metric: Distance metric
        
    Returns:
        Average cohesion score (lower is better)
    """
    if len(cluster_indices) < 2:
        return 0.0
    
    cluster_vectors = vectors[cluster_indices]
    distances = cdist(cluster_vectors, cluster_vectors, metric=metric)
    
    # Average of upper triangle
    n = len(cluster_indices)
    upper_indices = np.triu_indices(n, k=1)
    avg_distance = np.mean(distances[upper_indices])
    
    return float(avg_distance)


def cluster_separation(
    vectors: np.ndarray,
    cluster1_indices: List[int],
    cluster2_indices: List[int],
    metric: str = 'euclidean'
) -> float:
    """
    Calculate separation between two clusters.
    
    Args:
        vectors: Feature matrix
        cluster1_indices: Indices of first cluster
        cluster2_indices: Indices of second cluster
        metric: Distance metric
        
    Returns:
        Average separation score (higher is better)
    """
    if not cluster1_indices or not cluster2_indices:
        return float('inf')
    
    cluster1_vectors = vectors[cluster1_indices]
    cluster2_vectors = vectors[cluster2_indices]
    
    distances = cdist(cluster1_vectors, cluster2_vectors, metric=metric)
    avg_distance = np.mean(distances)
    
    return float(avg_distance)