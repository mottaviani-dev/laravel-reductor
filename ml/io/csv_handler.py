"""CSV output utilities for redundancy reports."""

import csv
from typing import List, Dict, Union, Any
from pathlib import Path


def write_redundancy_csv(
    redundancy_data: List[Dict[str, Any]],
    filepath: Union[str, Path],
    delimiter: str = ','
) -> None:
    """
    Write redundancy analysis results to CSV.
    
    Args:
        redundancy_data: List of redundancy records
        filepath: Path to output CSV file
        delimiter: CSV delimiter
    """
    if not redundancy_data:
        # Create empty file
        Path(filepath).touch()
        return
    
    # Define CSV columns
    fieldnames = [
        'test_name',
        'cluster_id',
        'semantic_similarity',
        'coverage_similarity',
        'combined_similarity',
        'redundancy_status',
        'similar_tests'
    ]
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()
        
        for record in redundancy_data:
            # Format similar tests as semicolon-separated list
            similar_tests = record.get('similar_tests', [])
            similar_tests_str = '; '.join(similar_tests) if similar_tests else ''
            
            row = {
                'test_name': record.get('test_name', ''),
                'cluster_id': record.get('cluster_id', ''),
                'semantic_similarity': f"{record.get('semantic_similarity', 0):.1%}",
                'coverage_similarity': f"{record.get('coverage_similarity', 0):.1%}",
                'combined_similarity': f"{record.get('combined_similarity', 0):.1%}",
                'redundancy_status': record.get('redundancy_status', ''),
                'similar_tests': similar_tests_str
            }
            
            writer.writerow(row)


def write_cluster_summary_csv(
    cluster_summary: List[Dict[str, Any]],
    filepath: Union[str, Path],
    delimiter: str = ','
) -> None:
    """
    Write cluster summary to CSV.
    
    Args:
        cluster_summary: List of cluster summary records
        filepath: Path to output CSV file
        delimiter: CSV delimiter
    """
    if not cluster_summary:
        Path(filepath).touch()
        return
    
    fieldnames = [
        'cluster_id',
        'size',
        'avg_semantic_similarity',
        'avg_coverage_similarity',
        'avg_combined_similarity',
        'redundancy_level',
        'tests'
    ]
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()
        
        for cluster in cluster_summary:
            # Format tests as semicolon-separated list
            tests = cluster.get('tests', [])
            tests_str = '; '.join(tests) if tests else ''
            
            row = {
                'cluster_id': cluster.get('cluster_id', ''),
                'size': cluster.get('size', 0),
                'avg_semantic_similarity': f"{cluster.get('avg_semantic_similarity', 0):.1%}",
                'avg_coverage_similarity': f"{cluster.get('avg_coverage_similarity', 0):.1%}",
                'avg_combined_similarity': f"{cluster.get('avg_combined_similarity', 0):.1%}",
                'redundancy_level': cluster.get('redundancy_level', ''),
                'tests': tests_str
            }
            
            writer.writerow(row)


def write_metrics_csv(
    metrics: Dict[str, Any],
    filepath: Union[str, Path]
) -> None:
    """
    Write clustering metrics to CSV.
    
    Args:
        metrics: Dictionary of metrics
        filepath: Path to output CSV file
    """
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Metric', 'Value'])
        
        for metric_name, value in metrics.items():
            if isinstance(value, float):
                formatted_value = f"{value:.4f}"
            else:
                formatted_value = str(value)
            
            writer.writerow([metric_name, formatted_value])