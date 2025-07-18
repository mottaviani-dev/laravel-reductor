"""Centralized I/O operations."""

import json
from pathlib import Path
from typing import Any, Union


def read_json(path: Union[str, Path]) -> Any:
    """
    Read JSON file.
    
    Args:
        path: Path to JSON file
        
    Returns:
        Parsed JSON data
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json(data: Any, path: Union[str, Path], indent: int = 2) -> None:
    """
    Write data to JSON file.
    
    Args:
        data: Data to write
        path: Output file path
        indent: JSON indentation level
        
    Raises:
        IOError: If file cannot be written
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert numpy types before saving
    import numpy as np
    
    def convert_numpy(obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {(int(k) if isinstance(k, np.integer) else k): convert_numpy(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_numpy(item) for item in obj]
        return obj
    
    data_clean = convert_numpy(data)
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data_clean, f, indent=indent, default=str)


def ensure_directory(path: Union[str, Path]) -> Path:
    """
    Ensure directory exists.
    
    Args:
        path: Directory path
        
    Returns:
        Path object
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path