"""Pipeline factory for creating algorithm-specific pipelines."""

from typing import Dict, Any, Optional
from .base import BasePipeline
from .kmeans_pipeline import KMeansPipeline
from .dbscan_pipeline import DBSCANPipeline
from .hierarchical_pipeline import HierarchicalPipeline
from ..utils.logging import get_logger

logger = get_logger(__name__)


class PipelineFactory:
    """Factory for creating clustering pipelines."""
    
    # Registry of available pipelines
    _pipelines: Dict[str, type] = {
        'kmeans': KMeansPipeline,
        'k-means': KMeansPipeline,  # Alias
        'dbscan': DBSCANPipeline,
        'hierarchical': HierarchicalPipeline,
        'agglomerative': HierarchicalPipeline,  # Alias
        'hac': HierarchicalPipeline,  # Alias
    }
    
    @classmethod
    def create(cls, algorithm: str, config: Any) -> BasePipeline:
        """
        Create a pipeline for the specified algorithm.
        
        Args:
            algorithm: Name of the clustering algorithm
            config: Pipeline configuration object
            
        Returns:
            Configured pipeline instance
            
        Raises:
            ValueError: If algorithm is not supported
        """
        algorithm_lower = algorithm.lower()
        
        if algorithm_lower not in cls._pipelines:
            available = list(cls._pipelines.keys())
            raise ValueError(
                f"Unsupported algorithm: '{algorithm}'. "
                f"Available algorithms: {available}"
            )
        
        pipeline_class = cls._pipelines[algorithm_lower]
        logger.info(f"Creating {pipeline_class.__name__} for algorithm '{algorithm}'")
        
        return pipeline_class(config)
    
    @classmethod
    def register(cls, algorithm: str, pipeline_class: type):
        """
        Register a new pipeline class.
        
        Args:
            algorithm: Algorithm name
            pipeline_class: Pipeline class (must inherit from BasePipeline)
        """
        if not issubclass(pipeline_class, BasePipeline):
            raise ValueError(
                f"Pipeline class must inherit from BasePipeline, "
                f"got {pipeline_class}"
            )
        
        cls._pipelines[algorithm.lower()] = pipeline_class
        logger.info(f"Registered pipeline for algorithm '{algorithm}'")
    
    @classmethod
    def list_algorithms(cls) -> Dict[str, str]:
        """
        List available algorithms and their pipeline classes.
        
        Returns:
            Dict mapping algorithm names to pipeline class names
        """
        return {
            algo: pipeline_class.__name__
            for algo, pipeline_class in cls._pipelines.items()
        }
    
    @classmethod
    def get_algorithm_info(cls, algorithm: str) -> Dict[str, Any]:
        """
        Get information about a specific algorithm's pipeline.
        
        Args:
            algorithm: Algorithm name
            
        Returns:
            Dictionary with algorithm information
        """
        algorithm_lower = algorithm.lower()
        
        if algorithm_lower not in cls._pipelines:
            raise ValueError(f"Unknown algorithm: '{algorithm}'")
        
        pipeline_class = cls._pipelines[algorithm_lower]
        
        # Get docstring and other metadata
        info = {
            'name': algorithm,
            'pipeline_class': pipeline_class.__name__,
            'description': pipeline_class.__doc__.strip() if pipeline_class.__doc__ else None,
            'module': pipeline_class.__module__,
            'aliases': [k for k, v in cls._pipelines.items() if v == pipeline_class]
        }
        
        return info


def create_pipeline(algorithm: str, config: Any) -> BasePipeline:
    """
    Convenience function to create a pipeline.
    
    Args:
        algorithm: Name of the clustering algorithm
        config: Pipeline configuration object
        
    Returns:
        Configured pipeline instance
    """
    return PipelineFactory.create(algorithm, config)