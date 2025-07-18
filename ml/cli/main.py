"""Main CLI entry point."""

import argparse
import sys
import logging

from ..config import SUPPORTED_ALGORITHMS
from .base import add_common_arguments
from .commands import (
    VectorizeCommand,
    ClusterCommand,
    AnalyzeCommand,
    ValidateCommand
)


def create_parser():
    """Create argument parser for CLI."""
    parser = argparse.ArgumentParser(
        description='ML pipeline for test redundancy detection'
    )
    
    add_common_arguments(parser)
    
    subparsers = parser.add_subparsers(
        dest='command',
        help='Available commands'
    )
    
    # Vectorize command
    vectorize_parser = subparsers.add_parser(
        'vectorize',
        help='Vectorize test source code'
    )
    vectorize_parser.add_argument(
        '--input', '-i',
        required=True,
        help='Input JSON file with test sources'
    )
    vectorize_parser.add_argument(
        '--output', '-o',
        required=True,
        help='Output file for vectors'
    )
    vectorize_parser.add_argument(
        '--output-dim',
        type=int,
        default=128,
        help='Output vector dimension'
    )
    vectorize_parser.add_argument(
        '--max-features',
        type=int,
        default=1000,
        help='Maximum TF-IDF features'
    )
    
    # Cluster command
    cluster_parser = subparsers.add_parser(
        'cluster',
        help='Run complete clustering pipeline'
    )
    cluster_parser.add_argument(
        '--sources', '-s',
        required=True,
        help='Test sources JSON file'
    )
    cluster_parser.add_argument(
        '--coverage', '-c',
        required=True,
        help='Coverage data JSON file'
    )
    cluster_parser.add_argument(
        '--output', '-o',
        required=True,
        help='Output directory for results'
    )
    cluster_parser.add_argument(
        '--algorithm', '-a',
        choices=SUPPORTED_ALGORITHMS,
        default='kmeans',
        help='Clustering algorithm'
    )
    cluster_parser.add_argument(
        '--config',
        choices=['default', 'strict', 'lenient'],
        default='default',
        help='Configuration preset'
    )
    cluster_parser.add_argument(
        '--no-entropy',
        action='store_true',
        help='Disable entropy damping'
    )
    cluster_parser.add_argument(
        '--no-validation',
        action='store_true',
        help='Disable semantic validation'
    )
    cluster_parser.add_argument(
        '--config-file',
        help='JSON file with algorithm-specific configuration'
    )
    
    # Analyze command
    analyze_parser = subparsers.add_parser(
        'analyze',
        help='Analyze existing vectors'
    )
    analyze_parser.add_argument(
        '--semantic-vectors',
        help='Semantic vectors JSON file'
    )
    analyze_parser.add_argument(
        '--coverage-vectors',
        help='Coverage vectors JSON file'
    )
    analyze_parser.add_argument(
        '--entropy',
        action='store_true',
        help='Perform entropy analysis'
    )
    analyze_parser.add_argument(
        '--output', '-o',
        help='Output file for analysis results'
    )
    
    # Validate command
    validate_parser = subparsers.add_parser(
        'validate',
        help='Validate existing clusters'
    )
    validate_parser.add_argument(
        '--clusters', '-c',
        required=True,
        help='Clusters JSON file'
    )
    validate_parser.add_argument(
        '--strict',
        action='store_true',
        help='Use strict validation mode'
    )
    
    return parser


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Configure logging
    if not args.quiet:
        logging.basicConfig(
            level=getattr(logging, args.log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    # Execute command
    if args.command == 'vectorize':
        command = VectorizeCommand(args)
    elif args.command == 'cluster':
        command = ClusterCommand(args)
    elif args.command == 'analyze':
        command = AnalyzeCommand(args)
    elif args.command == 'validate':
        command = ValidateCommand(args)
    else:
        parser.print_help()
        sys.exit(1)
    
    try:
        command.execute()
    except Exception as e:
        logging.error(f"Command failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()