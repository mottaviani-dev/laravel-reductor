"""Result management for pipeline."""

from typing import Dict, Any, Union
from pathlib import Path

from ..io import save_clusters, write_redundancy_csv
from ..utils.io import write_json, ensure_directory
from ..utils.logging import get_logger

logger = get_logger(__name__)


class ResultManager:
    """Manages pipeline results and output."""
    
    def __init__(self):
        self.results: Dict[str, Any] = {}
    
    def set_results(self, results: Dict[str, Any]) -> None:
        """Set pipeline results."""
        self.results = results
    
    def save(self, 
             output_dir: Union[str, Path],
             save_vectors: bool = False,
             save_csv: bool = True) -> None:
        """
        Save pipeline results to files.
        
        Args:
            output_dir: Directory to save results
            save_vectors: Whether to save vector files
            save_csv: Whether to save CSV reports
        """
        output_dir = ensure_directory(output_dir)
        logger.info(f"Saving results to {output_dir}")
        
        # Save clusters
        if 'clusters' in self.results:
            save_clusters(
                self.results['clusters'],
                output_dir / 'clusters.json',
                metadata=self.results.get('clustering_params')
            )
        
        # Save redundancy CSV
        if save_csv and 'redundancy_analysis' in self.results:
            write_redundancy_csv(
                self.results['redundancy_analysis']['redundant_tests'],
                output_dir / 'redundancy_report.csv'
            )
        
        # Save complete results
        write_json(self.results, output_dir / 'results.json')
    
    def get_summary(self) -> Dict[str, Any]:
        """Get results summary."""
        summary = {
            'test_count': self.results.get('test_count', 0),
            'cluster_count': len(self.results.get('clusters', {})),
            'algorithm': self.results.get('algorithm', 'unknown')
        }
        
        if 'redundancy_analysis' in self.results:
            redundancy = self.results['redundancy_analysis']['summary']
            summary.update({
                'redundant_tests': redundancy['redundant_tests'],
                'redundancy_rate': redundancy['redundancy_rate']
            })
        
        return summary