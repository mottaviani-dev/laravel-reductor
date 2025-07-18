"""Validate command implementation."""

from ...analysis import SemanticValidator, ValidationConfig
from ..base import BaseCommand


class ValidateCommand(BaseCommand):
    """Command to validate clusters."""
    
    def execute(self) -> None:
        """Execute validation."""
        # Load clusters
        cluster_data = self.load_input(self.args.clusters)
        
        if 'clusters' in cluster_data:
            clusters = cluster_data['clusters']
        else:
            clusters = cluster_data
        
        # Validate
        validator = SemanticValidator(
            ValidationConfig(strict_mode=self.args.strict)
        )
        
        # Convert clusters to list format
        cluster_list = [
            {'cluster_id': cid, 'tests': tests}
            for cid, tests in clusters.items()
        ]
        
        summary = validator.get_validation_summary(cluster_list)
        
        # Log summary
        self.logger.info(f"Total clusters: {summary['total_clusters']}")
        self.logger.info(f"Safe clusters: {summary['safe_clusters']}")
        self.logger.info(f"Unsafe clusters: {summary['unsafe_clusters']}")
        self.logger.info(f"Total conflicts: {summary['total_conflicts']}")
        self.logger.info(f"Safety rate: {summary['safety_rate']:.1f}%")
        
        if summary['conflict_types']:
            self.logger.info("Conflict types:")
            for conflict_type, count in summary['conflict_types'].items():
                self.logger.info(f"  - {conflict_type}: {count}")