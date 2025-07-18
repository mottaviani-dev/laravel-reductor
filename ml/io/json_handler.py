"""JSON data handlers for ML pipeline."""

import json
import numpy as np
from typing import Dict, List, Any, Union, Optional
from pathlib import Path

from ..utils.io import read_json, write_json


class NumpyJSONEncoder(json.JSONEncoder):
    """JSON encoder that handles numpy arrays."""
    
    def default(self, obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        return super().default(obj)


def load_json_file(filepath: Union[str, Path]) -> Any:
    """Load data from JSON file."""
    return read_json(filepath)


def save_json_file(data: Any, 
                   filepath: Union[str, Path],
                   indent: int = 2) -> None:
    """Save data to JSON file with numpy support."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, cls=NumpyJSONEncoder, indent=indent)


def load_test_sources(filepath: Union[str, Path]) -> Dict[str, str]:
    """
    Load test source code from JSON file.
    
    Expected format:
    {
        "test_name": "source_code",
        ...
    }
    
    Args:
        filepath: Path to test sources JSON
        
    Returns:
        Dict mapping test names to source code
    """
    data = load_json_file(filepath)
    
    if not isinstance(data, dict):
        raise ValueError(f"Expected dict, got {type(data)}")
    
    return data


def load_coverage_data(filepath: Union[str, Path]) -> Dict[str, List[str]]:
    """
    Load coverage data from JSON file.
    
    Expected format:
    {
        "test_name": ["file.php:123", "file.php:124", ...],
        ...
    }
    
    Args:
        filepath: Path to coverage JSON
        
    Returns:
        Dict mapping test names to covered lines
    """
    data = load_json_file(filepath)
    
    if not isinstance(data, dict):
        raise ValueError(f"Expected dict, got {type(data)}")
    
    # Ensure all values are lists
    coverage_data = {}
    for test_name, lines in data.items():
        if isinstance(lines, list):
            coverage_data[test_name] = lines
        else:
            raise ValueError(f"Coverage for {test_name} should be a list")
    
    return coverage_data


def load_vectors(filepath: Union[str, Path]) -> Dict[str, np.ndarray]:
    """
    Load vectors from JSON file.
    
    Expected format:
    {
        "test_name": [0.1, 0.2, ...],
        ...
    }
    
    Args:
        filepath: Path to vectors JSON
        
    Returns:
        Dict mapping test names to numpy arrays
    """
    data = load_json_file(filepath)
    
    if not isinstance(data, dict):
        raise ValueError(f"Expected dict, got {type(data)}")
    
    vectors = {}
    for test_name, vector_list in data.items():
        if isinstance(vector_list, list):
            vectors[test_name] = np.array(vector_list, dtype=np.float32)
        else:
            raise ValueError(f"Vector for {test_name} should be a list")
    
    return vectors


def save_vectors(vectors: Dict[str, np.ndarray],
                filepath: Union[str, Path],
                indent: int = 2) -> None:
    """
    Save vectors to JSON file.
    
    Args:
        vectors: Dict mapping test names to vectors
        filepath: Path to output file
        indent: JSON indentation
    """
    # Convert numpy arrays to lists
    data = {
        test_name: vector.tolist() if isinstance(vector, np.ndarray) else vector
        for test_name, vector in vectors.items()
    }
    
    save_json_file(data, filepath, indent)


def save_clusters(clusters: Dict[int, List[str]],
                 filepath: Union[str, Path],
                 metadata: Optional[Dict[str, Any]] = None,
                 indent: int = 2) -> None:
    """
    Save clustering results to JSON file.
    
    Args:
        clusters: Dict mapping cluster IDs to test names
        filepath: Path to output file
        metadata: Optional metadata about clustering
        indent: JSON indentation
    """
    # Recursively convert numpy types
    def convert_numpy_types(obj):
        """Convert numpy types to native Python types."""
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
    
    # Convert the entire data structure
    data = {
        'clusters': convert_numpy_types(clusters),
        'metadata': convert_numpy_types(metadata) if metadata else {}
    }
    
    save_json_file(data, filepath, indent)