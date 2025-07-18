#!/usr/bin/env python3
"""Runner script for ML CLI that handles imports properly."""

import sys
import os

# Get the directory containing this script
script_dir = os.path.dirname(os.path.abspath(__file__))
# Add parent directory to path so 'ml' package can be imported
parent_dir = os.path.dirname(script_dir)
sys.path.insert(0, parent_dir)

# Now import and run
from ml.cli.main import main

if __name__ == '__main__':
    main()