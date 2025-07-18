"""Input validation utilities."""

from pathlib import Path
from typing import Dict, List, Union, Any


def validate_file_exists(path: Union[str, Path]) -> Path:
    """
    Validate that file exists.
    
    Args:
        path: File path
        
    Returns:
        Path object
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return path


def validate_input_data(data: Dict[str, Any], 
                       required_keys: List[str]) -> None:
    """
    Validate input data has required keys.
    
    Args:
        data: Input data dictionary
        required_keys: List of required keys
        
    Raises:
        ValueError: If required keys are missing
    """
    missing_keys = set(required_keys) - set(data.keys())
    if missing_keys:
        raise ValueError(f"Missing required keys: {missing_keys}")