"""DBSCAN clustering implementation."""

from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from sklearn.cluster import DBSCAN as SklearnDBSCAN
from sklearn.metrics import silhouette_score, pairwise_distances
from sklearn.neighbors import NearestNeighbors
from sklearn.decomposition import PCA
from sklearn.preprocessing import normalize

from .base import Clusterer


class DBSCANClusterer(Clusterer):
    """DBSCAN clustering algorithm."""
    
    def __init__(self,
                 eps: Optional[float] = None,
                 min_samples: int = 3,
                 metric: str = 'euclidean',
                 algorithm: str = 'auto',
                 leaf_size: int = 30,
                 eps_percentiles: Optional[List[int]] = None,
                 max_dimensions: int = 128,
                 reduce_dimensions: bool = True):
        """
        Initialize DBSCAN clusterer.
        
        Args:
            eps: Maximum distance between samples (None for auto)
            min_samples: Minimum samples in neighborhood
            metric: Distance metric
            algorithm: Algorithm for nearest neighbors
            leaf_size: Leaf size for tree algorithms
            eps_percentiles: List of percentiles to try for eps selection
            max_dimensions: Maximum dimensions before reduction (research: 128)
            reduce_dimensions: Whether to apply dimensionality reduction
        """
        self.eps = eps
        self.min_samples = min_samples
        self.metric = metric
        self.algorithm = algorithm
        self.leaf_size = leaf_size
        self.eps_percentiles = eps_percentiles or [85, 90, 95]
        self.max_dimensions = max_dimensions
        self.reduce_dimensions = reduce_dimensions
        
        self.optimal_eps_: Optional[float] = None
        self.n_clusters_: Optional[int] = None
        self.n_noise_: Optional[int] = None
        self.silhouette_score_: Optional[float] = None
        self.eps_selection_method_: Optional[str] = None
        self.distance_distribution_: Optional[Dict[str, float]] = None
        self.cluster_compactness_: Optional[Dict[int, float]] = None
        self.dimensionality_reduced_: bool = False
        self.pca_model_: Optional[PCA] = None
        
    def preprocess_vectors(self, vectors: np.ndarray) -> np.ndarray:
        """
        Preprocess vectors before clustering.
        Research shows DBSCAN doesn't work well with high-dimensional data.
        
        Args:
            vectors: Feature matrix
            
        Returns:
            Processed vectors
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Store original shape
        self.original_shape_ = vectors.shape
        
        # Always reduce dimensions for test suites with 640-dimensional vectors
        # Research recommendation: Apply dimensionality reduction for high-dimensional data
        if vectors.shape[1] > self.max_dimensions or vectors.shape[1] > 256:
            target_dims = min(self.max_dimensions, 128)  # Target 128 dimensions
            logger.info(f"Reducing dimensions from {vectors.shape[1]} to {target_dims}")
            
            # Use PCA for dimensionality reduction
            # Keep enough components to retain 95% variance or target_dims, whichever is smaller
            self.pca_model_ = PCA(n_components=min(target_dims, vectors.shape[0] - 1), 
                                 random_state=42)
            vectors = self.pca_model_.fit_transform(vectors)
            self.dimensionality_reduced_ = True
            
            # Find how many components needed for 95% variance
            cumsum_var = np.cumsum(self.pca_model_.explained_variance_ratio_)
            n_components_95 = np.argmax(cumsum_var >= 0.95) + 1
            
            # Use the smaller of target_dims or 95% variance components
            if n_components_95 < vectors.shape[1]:
                vectors = vectors[:, :n_components_95]
                logger.info(f"Using {n_components_95} components for 95% variance")
            
            logger.info(f"Explained variance ratio: {self.pca_model_.explained_variance_ratio_.sum():.3f}")
        
        return vectors
        
    def cluster(self, 
                vectors: np.ndarray,
                **kwargs) -> Dict[int, List[int]]:
        """
        Perform DBSCAN clustering.
        
        Args:
            vectors: Feature matrix (n_samples, n_features)
            **kwargs: Additional parameters
            
        Returns:
            Dict mapping cluster IDs to lists of sample indices
        """
        import logging
        logger = logging.getLogger(__name__)
        
        n_samples = vectors.shape[0]
        
        # Log input statistics
        logger.info(f"DBSCAN input: {n_samples} samples, {vectors.shape[1]} features")
        logger.info(f"Vector stats: min={vectors.min():.6f}, max={vectors.max():.6f}, "
                   f"mean={vectors.mean():.6f}, std={vectors.std():.6f}")
        
        # Check for degenerate cases
        if vectors.std() < 1e-10:
            logger.warning("Input vectors have near-zero variance - data may be degenerate")
        
        # Preprocess vectors
        vectors = self.preprocess_vectors(vectors)
        
        # Adaptive min_samples based on dataset size
        # For large test suites, increase min_samples to avoid noise
        if n_samples > 100:
            adaptive_min_samples = max(5, int(n_samples * 0.02))  # 2% of samples
        elif n_samples > 50:
            adaptive_min_samples = max(3, int(n_samples * 0.05))  # 5% of samples
        else:
            adaptive_min_samples = self.min_samples  # Use default
        
        if adaptive_min_samples != self.min_samples:
            self.min_samples = adaptive_min_samples
            logger.info(f"Adjusted min_samples to {self.min_samples} for {n_samples} samples")
        
        # Handle edge cases
        if n_samples < self.min_samples:
            return {-1: list(range(n_samples))}  # All noise
        
        # Determine eps if not provided
        if self.eps is None:
            eps = self._find_optimal_eps(vectors)
        else:
            eps = self.eps
        
        self.optimal_eps_ = eps
        
        # Final safety check
        if eps <= 0:
            logger.error(f"Invalid eps value: {eps}")
            eps = 0.01  # Emergency fallback
            
        logger.info(f"Using eps={eps:.6f}, min_samples={self.min_samples}")
        
        # Perform clustering
        dbscan = SklearnDBSCAN(
            eps=eps,
            min_samples=self.min_samples,
            metric=self.metric,
            algorithm=self.algorithm,
            leaf_size=self.leaf_size
        )
        
        labels = dbscan.fit_predict(vectors)
        
        # Calculate statistics
        unique_labels = set(labels)
        self.n_clusters_ = len(unique_labels - {-1})
        self.n_noise_ = list(labels).count(-1)
        
        # Calculate silhouette score if possible
        if self.n_clusters_ > 1 and self.n_noise_ < n_samples - 1:
            # Only calculate for non-noise points
            non_noise_mask = labels != -1
            if np.sum(non_noise_mask) > 1:
                self.silhouette_score_ = silhouette_score(
                    vectors[non_noise_mask], 
                    labels[non_noise_mask]
                )
        
        # Calculate cluster compactness
        self._calculate_cluster_compactness(vectors, labels)
        
        # Prepare enhanced cluster structure
        return self._prepare_enhanced_clusters(vectors, labels)
    
    def _find_optimal_eps(self, vectors: np.ndarray) -> float:
        """
        Find optimal eps using k-distance graph method with multiple percentiles.
        
        Args:
            vectors: Feature matrix
            
        Returns:
            Optimal eps value
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Use k-nearest neighbors to find distances
        k = self.min_samples
        nbrs = NearestNeighbors(n_neighbors=k, metric=self.metric)
        nbrs.fit(vectors)
        
        # Get k-distances
        distances, indices = nbrs.kneighbors(vectors)
        k_distances = distances[:, -1]  # Distance to k-th neighbor
        
        # Sort distances
        k_distances = np.sort(k_distances)
        
        # Log and store statistics
        self._k_distances_stats = {
            'min': float(k_distances.min()),
            'max': float(k_distances.max()),
            'mean': float(k_distances.mean()),
            'median': float(np.median(k_distances)),
            'std': float(k_distances.std()),
            'percentiles': {
                10: float(np.percentile(k_distances, 10)),
                25: float(np.percentile(k_distances, 25)),
                50: float(np.percentile(k_distances, 50)),
                75: float(np.percentile(k_distances, 75)),
                90: float(np.percentile(k_distances, 90))
            }
        }
        
        logger.info(f"K-distances stats: min={k_distances.min():.6f}, "
                   f"max={k_distances.max():.6f}, "
                   f"mean={k_distances.mean():.6f}, "
                   f"median={np.median(k_distances):.6f}, "
                   f"std={k_distances.std():.6f}")
        
        # Check if vectors are normalized (unit vectors)
        vector_norms = np.linalg.norm(vectors, axis=1)
        is_normalized = np.allclose(vector_norms, 1.0, rtol=1e-5)
        
        # Store for later use
        percentiles_to_try = self.eps_percentiles
        
        if is_normalized:
            logger.info("Vectors appear to be L2 normalized")
            # For normalized vectors, distances are smaller
            # Adjust percentiles for better clustering
            percentiles_to_try = [50, 60, 70, 80, 90]
        
        # Handle case where all k-distances are very small
        if k_distances.max() < 0.01:
            logger.warning(f"All k-distances are very small (max={k_distances.max():.6f})")
            # Use a fraction of the max distance
            return max(0.1 * k_distances.max(), 0.001)
        
        # Try multiple percentiles to find best eps
        best_eps = None
        best_score = -1
        
        # Get number of samples
        n_samples = len(vectors)
        
        # Research methodology: Use multiple percentiles to find optimal eps
        # For large test suites, we need much smaller eps to avoid single giant cluster
        if n_samples > 100:
            percentiles_to_try = [0.1, 0.5, 1, 2, 5] if not is_normalized else [1, 2, 3, 5, 10]
        elif n_samples > 50:
            percentiles_to_try = [1, 5, 10, 15, 20] if not is_normalized else [5, 10, 15, 20, 25]
        else:
            percentiles_to_try = [10, 20, 30, 40, 50] if not is_normalized else [20, 30, 40, 50, 60]
        
        for percentile in percentiles_to_try:
            eps_candidate = np.percentile(k_distances, percentile)
            
            # Skip if eps is too small
            if eps_candidate <= 0:
                logger.debug(f"Skipping percentile {percentile}: eps={eps_candidate}")
                continue
            
            logger.debug(f"Testing percentile {percentile}: eps={eps_candidate:.6f}")
            
            # Test this eps value
            dbscan_test = SklearnDBSCAN(
                eps=eps_candidate,
                min_samples=self.min_samples,
                metric=self.metric
            )
            labels = dbscan_test.fit_predict(vectors)
            
            # Evaluate clustering quality
            n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
            n_noise = list(labels).count(-1)
            
            # Skip if too few clusters or too much noise
            if n_clusters < 2 or n_noise > 0.5 * len(vectors):
                continue
            
            # Calculate silhouette score for non-noise points
            non_noise_mask = labels != -1
            if np.sum(non_noise_mask) > 1:
                try:
                    score = silhouette_score(
                        vectors[non_noise_mask], 
                        labels[non_noise_mask]
                    )
                    
                    if score > best_score:
                        best_score = score
                        best_eps = eps_candidate
                        self.eps_selection_method_ = f'percentile_{percentile}'
                except:
                    continue
        
        # If no good eps found, use knee detection
        if best_eps is None:
            best_eps = self._find_eps_knee(k_distances)
            self.eps_selection_method_ = 'knee_detection'
        
        # Ensure eps is reasonable
        # For normalized vectors, use different bounds
        if is_normalized:
            min_eps = max(0.01, np.percentile(k_distances, 5))  # Higher minimum for unit vectors
            max_eps = min(2.0, np.percentile(k_distances, 99))  # Max distance between unit vectors is 2
        else:
            min_eps = max(1e-10, np.percentile(k_distances, 10))  # Avoid zero
            max_eps = np.percentile(k_distances, 99)
        
        # If still no valid eps, use a safe default
        if best_eps is None or best_eps <= min_eps:
            # Use median of k-distances as fallback
            best_eps = np.median(k_distances)
            self.eps_selection_method_ = 'median_fallback'
            
            # Ensure it's within bounds
            if best_eps <= min_eps:
                best_eps = min_eps * 2  # Double the minimum
        
        best_eps = np.clip(best_eps, min_eps, max_eps)
        
        return float(best_eps)
    
    def _find_eps_knee(self, k_distances: np.ndarray) -> float:
        """
        Find eps using knee/elbow detection in k-distance graph.
        
        Args:
            k_distances: Sorted k-distances
            
        Returns:
            Eps value at knee point
        """
        # Simple knee detection using maximum curvature
        n = len(k_distances)
        x = np.arange(n)
        
        # Handle edge case where all distances are similar
        if k_distances[-1] - k_distances[0] < 1e-10:
            return k_distances[int(0.9 * n)]
        
        # Normalize coordinates
        x_norm = x / x[-1]
        y_norm = (k_distances - k_distances[0]) / (k_distances[-1] - k_distances[0])
        
        # Calculate curvature
        dx = np.gradient(x_norm)
        dy = np.gradient(y_norm)
        d2x = np.gradient(dx)
        d2y = np.gradient(dy)
        
        curvature = np.abs(d2y) / (1 + dy**2)**1.5
        
        # Find maximum curvature point (knee)
        knee_idx = np.argmax(curvature[int(0.1*n):int(0.9*n)]) + int(0.1*n)
        
        return max(1e-10, k_distances[knee_idx])  # Ensure non-zero
    
    def _calculate_adaptive_min_samples(self, n_samples: int) -> int:
        """
        Calculate adaptive min_samples based on dataset size.
        
        Args:
            n_samples: Number of samples in dataset
            
        Returns:
            Adapted min_samples value
        """
        # Base min_samples on dataset size - use smaller values for better clustering
        if n_samples < 50:
            # Small dataset: use very small value
            return 2
        elif n_samples < 500:
            # Medium dataset: scale linearly but smaller
            return max(2, int(0.02 * n_samples))
        elif n_samples < 5000:
            # Large dataset: scale logarithmically
            return max(3, int(1.5 * np.log10(n_samples)))
        else:
            # Very large dataset: cap at reasonable value
            return min(7, max(4, int(np.log10(n_samples))))
    
    def get_params(self) -> Dict[str, Any]:
        """Get clustering parameters."""
        params = {
            'algorithm': 'dbscan',
            'eps': self.optimal_eps_ or self.eps,
            'min_samples': self.min_samples,
            'metric': self.metric,
            'n_clusters': self.n_clusters_,
            'n_noise': self.n_noise_,
            'silhouette_score': self.silhouette_score_,
            'eps_selection_method': self.eps_selection_method_,
            'dimensionality_reduced': self.dimensionality_reduced_,
            'max_dimensions': self.max_dimensions
        }
        
        if self.distance_distribution_:
            params['distance_distribution'] = self.distance_distribution_
            
        if self.cluster_compactness_:
            params['cluster_compactness'] = self.cluster_compactness_
            
        return params
    
    def _reduce_dimensions(self, vectors: np.ndarray) -> np.ndarray:
        """Reduce dimensions using PCA as recommended by research."""
        import logging
        logger = logging.getLogger(__name__)
        
        n_components = min(self.max_dimensions, vectors.shape[0] - 1, vectors.shape[1])
        logger.info(f"Reducing dimensions: {vectors.shape[1]} -> {n_components}")
        
        self.pca_model_ = PCA(n_components=n_components, whiten=True, random_state=42)
        reduced = self.pca_model_.fit_transform(vectors)
        
        explained_var = self.pca_model_.explained_variance_ratio_.sum()
        logger.info(f"PCA retained {explained_var:.2%} of variance")
        
        # Scale to help with distance calculations
        reduced = reduced * 10.0
        
        return reduced
    
    
    def _prepare_cosine_distance(self, vectors: np.ndarray) -> np.ndarray:
        """Prepare vectors for cosine distance computation."""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info("Converting to angular distance for cosine metric")
        
        # Normalize vectors for cosine similarity
        vectors_norm = normalize(vectors, axis=1, norm='l2')
        
        # Convert to angular distance representation
        # This makes DBSCAN work better with cosine metric
        # Angular distance = arccos(cosine_similarity) / pi
        # But we'll use the normalized vectors directly
        self.metric = 'euclidean'  # Use euclidean on normalized vectors
        
        return vectors_norm
    
    def _calculate_cluster_compactness(self, vectors: np.ndarray, labels: np.ndarray) -> None:
        """Calculate average intra-cluster distances."""
        self.cluster_compactness_ = {}
        
        for cluster_id in set(labels):
            if cluster_id == -1:  # Skip noise
                continue
                
            cluster_mask = labels == cluster_id
            cluster_vectors = vectors[cluster_mask]
            
            if len(cluster_vectors) > 1:
                # Calculate pairwise distances within cluster
                distances = pairwise_distances(cluster_vectors)
                # Get average distance (excluding diagonal)
                avg_distance = distances.sum() / (len(cluster_vectors) * (len(cluster_vectors) - 1))
                self.cluster_compactness_[cluster_id] = float(avg_distance)
            else:
                self.cluster_compactness_[cluster_id] = 0.0
    
    def _prepare_enhanced_clusters(self, vectors: np.ndarray, labels: np.ndarray) -> Dict[int, Dict[str, Any]]:
        """Prepare enhanced cluster structure with metadata."""
        clusters = {}
        
        for cluster_id in set(labels):
            if cluster_id == -1:  # Handle noise separately
                clusters[-1] = {
                    'indices': np.where(labels == -1)[0].tolist(),
                    'size': int(np.sum(labels == -1)),
                    'type': 'noise',
                    'compactness': None,
                    'center': None
                }
                continue
            
            cluster_mask = labels == cluster_id
            cluster_indices = np.where(cluster_mask)[0]
            cluster_vectors = vectors[cluster_mask]
            
            # Find cluster center (medoid)
            if len(cluster_vectors) > 0:
                # Calculate pairwise distances
                distances = pairwise_distances(cluster_vectors)
                # Find point with minimum sum of distances to others
                medoid_idx = np.argmin(distances.sum(axis=1))
                center_idx = cluster_indices[medoid_idx]
            else:
                center_idx = None
            
            clusters[cluster_id] = {
                'indices': cluster_indices.tolist(),
                'size': len(cluster_indices),
                'type': 'cluster',
                'compactness': self.cluster_compactness_.get(cluster_id, None),
                'center': int(center_idx) if center_idx is not None else None,
                'representative_test_index': int(center_idx) if center_idx is not None else None,  # Alias for Laravel compatibility
                'avg_distance_to_center': float(distances[medoid_idx].mean()) if len(cluster_vectors) > 0 else None
            }
        
        # Store distance distribution info
        if hasattr(self, '_k_distances_stats'):
            self.distance_distribution_ = self._k_distances_stats
        
        # Convert keys to built-in int for JSON compatibility
        return {int(k): v for k, v in clusters.items()}
    
    def validate_clusters(self, 
                         vectors: np.ndarray, 
                         predicted_labels: np.ndarray,
                         true_labels: Optional[np.ndarray] = None) -> Dict[str, float]:
        """
        Validate clustering results with optional external labels.
        
        Args:
            vectors: Feature vectors used for clustering
            predicted_labels: Cluster labels from DBSCAN
            true_labels: Optional ground truth labels for external validation
            
        Returns:
            Dict of validation metrics
        """
        from sklearn.metrics import (
            adjusted_rand_score, 
            normalized_mutual_info_score,
            homogeneity_score,
            completeness_score,
            v_measure_score
        )
        
        metrics = {}
        
        # Internal validation (always computed)
        if len(set(predicted_labels)) > 1:
            # Silhouette score for non-noise points
            non_noise_mask = predicted_labels != -1
            if np.sum(non_noise_mask) > 1:
                metrics['silhouette_score'] = float(
                    silhouette_score(vectors[non_noise_mask], 
                                   predicted_labels[non_noise_mask])
                )
        
        # External validation (if ground truth provided)
        if true_labels is not None:
            metrics['adjusted_rand_index'] = float(
                adjusted_rand_score(true_labels, predicted_labels)
            )
            metrics['normalized_mutual_info'] = float(
                normalized_mutual_info_score(true_labels, predicted_labels)
            )
            metrics['homogeneity'] = float(
                homogeneity_score(true_labels, predicted_labels)
            )
            metrics['completeness'] = float(
                completeness_score(true_labels, predicted_labels)
            )
            metrics['v_measure'] = float(
                v_measure_score(true_labels, predicted_labels)
            )
        
        return metrics
    
    def to_json(self, cluster_output: Dict[int, Dict[str, Any]]) -> str:
        """
        Convert cluster output to JSON string with proper type handling.
        
        Args:
            cluster_output: Enhanced cluster structure from clustering
            
        Returns:
            JSON string representation
        """
        import json
        import numpy as np
        
        def convert_numpy_types(obj):
            """Recursively convert numpy types to Python native types."""
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            elif isinstance(obj, dict):
                return {convert_numpy_types(k): convert_numpy_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy_types(item) for item in obj]
            return obj
        
        # Convert all numpy types
        clean_output = convert_numpy_types(cluster_output)
        
        # Add metadata
        result = {
            'clusters': clean_output,
            'metadata': {
                'algorithm': 'dbscan',
                'eps': self.optimal_eps_ or self.eps,
                'min_samples': self.min_samples,
                'n_clusters': self.n_clusters_,
                'n_noise': self.n_noise_,
                'dimensionality_reduced': self.dimensionality_reduced_,
                'distance_distribution': self.distance_distribution_ if self.distance_distribution_ else None,
                'cluster_compactness': convert_numpy_types(self.cluster_compactness_) if self.cluster_compactness_ else None
            }
        }
        
        return json.dumps(result, indent=2)