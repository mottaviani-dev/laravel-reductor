"""Threshold configuration for redundancy detection."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class ClusteringThresholds:
    """Thresholds for clustering algorithms."""
    # K-Means
    kmeans_min_clusters: int = 2
    kmeans_max_clusters: int = 50
    kmeans_silhouette_threshold: float = 0.3
    
    # DBSCAN
    dbscan_eps_percentile: float = 90
    dbscan_min_samples: int = 3
    
    # General
    min_cluster_size: int = 2
    noise_threshold: float = -1


@dataclass
class SimilarityThresholds:
    """Thresholds for similarity calculations."""
    # Similarity weights
    semantic_weight: float = 0.7
    coverage_weight: float = 0.3
    
    # Redundancy levels
    low_redundancy: float = 0.3
    moderate_redundancy: float = 0.5
    high_redundancy: float = 0.7
    very_high_redundancy: float = 0.85
    
    # Minimum similarities
    min_semantic_similarity: float = 0.1
    min_coverage_similarity: float = 0.1
    min_combined_similarity: float = 0.2


@dataclass
class EntropyThresholds:
    """Thresholds for entropy analysis."""
    # Minimum entropy values
    semantic_min_entropy: float = 0.5
    coverage_min_entropy: float = 0.85
    
    # Quality thresholds
    low_quality_threshold: float = 0.5
    damping_factor: float = 0.8


@dataclass
class ValidationThresholds:
    """Thresholds for semantic validation."""
    # Cluster validation
    max_conflicts_per_cluster: int = 0
    min_category_purity: float = 0.8
    
    # Safety margins
    boundary_test_margin: float = 0.1
    assertion_conflict_penalty: float = 0.5


@dataclass
class ThresholdConfig:
    """Complete threshold configuration."""
    clustering: ClusteringThresholds
    similarity: SimilarityThresholds
    entropy: EntropyThresholds
    validation: ValidationThresholds
    
    @classmethod
    def default(cls) -> 'ThresholdConfig':
        """Create default configuration."""
        return cls(
            clustering=ClusteringThresholds(),
            similarity=SimilarityThresholds(),
            entropy=EntropyThresholds(),
            validation=ValidationThresholds()
        )
    
    @classmethod
    def strict(cls) -> 'ThresholdConfig':
        """Create strict configuration for high precision."""
        config = cls.default()
        
        # Stricter redundancy thresholds
        config.similarity.moderate_redundancy = 0.6
        config.similarity.high_redundancy = 0.8
        config.similarity.very_high_redundancy = 0.9
        
        # Higher quality requirements
        config.entropy.semantic_min_entropy = 0.6
        config.entropy.low_quality_threshold = 0.6
        
        # Stricter validation
        config.validation.min_category_purity = 0.9
        
        return config
    
    @classmethod
    def lenient(cls) -> 'ThresholdConfig':
        """Create lenient configuration for high recall."""
        config = cls.default()
        
        # More lenient redundancy thresholds
        config.similarity.low_redundancy = 0.25
        config.similarity.moderate_redundancy = 0.4
        config.similarity.high_redundancy = 0.6
        
        # Lower quality requirements
        config.entropy.semantic_min_entropy = 0.4
        config.entropy.coverage_min_entropy = 0.8
        
        # More lenient validation
        config.validation.max_conflicts_per_cluster = 2
        config.validation.min_category_purity = 0.7
        
        return config
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary."""
        return {
            'clustering': {
                'kmeans_min_clusters': self.clustering.kmeans_min_clusters,
                'kmeans_max_clusters': self.clustering.kmeans_max_clusters,
                'dbscan_min_samples': self.clustering.dbscan_min_samples,
            },
            'similarity': {
                'semantic_weight': self.similarity.semantic_weight,
                'coverage_weight': self.similarity.coverage_weight,
                'thresholds': {
                    'low': self.similarity.low_redundancy,
                    'moderate': self.similarity.moderate_redundancy,
                    'high': self.similarity.high_redundancy,
                    'very_high': self.similarity.very_high_redundancy
                }
            },
            'entropy': {
                'semantic_threshold': self.entropy.semantic_min_entropy,
                'coverage_threshold': self.entropy.coverage_min_entropy,
                'quality_threshold': self.entropy.low_quality_threshold
            },
            'validation': {
                'strict_mode': self.validation.max_conflicts_per_cluster == 0,
                'category_purity': self.validation.min_category_purity
            }
        }