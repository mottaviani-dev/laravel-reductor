"""Base classes and utilities for CLI commands."""

import argparse
from abc import ABC, abstractmethod
from typing import Any, Dict
from pathlib import Path

from ..utils.io import read_json, write_json, ensure_directory
from ..utils.logging import get_logger

logger = get_logger(__name__)


class BaseCommand(ABC):
    """Base class for CLI commands."""
    
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.logger = get_logger(self.__class__.__name__)
    
    @abstractmethod
    def execute(self) -> None:
        """Execute the command."""
        pass
    
    def load_input(self, path: str) -> Any:
        """Load input data from JSON file."""
        self.logger.info(f"Loading input from {path}")
        return read_json(path)
    
    def save_output(self, data: Any, path: str) -> None:
        """Save output data to JSON file."""
        self.logger.info(f"Saving output to {path}")
        write_json(data, path)
    
    def ensure_output_dir(self, path: str) -> Path:
        """Ensure output directory exists."""
        return ensure_directory(path)


def add_common_arguments(parser: argparse.ArgumentParser) -> None:
    """Add common arguments to parser."""
    parser.add_argument(
        '--log-level',
        default='INFO',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Logging level'
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress output'
    )