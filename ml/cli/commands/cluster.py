"""Cluster command implementation."""

from pathlib import Path

from ...pipeline import RedundancyPipeline
from ...config import ThresholdConfig
from ..base import BaseCommand


class ClusterCommand(BaseCommand):
    """Command to run clustering pipeline."""
    
    def execute(self) -> None:
        """Execute clustering pipeline."""
        # Select configuration
        if self.args.config == 'strict':
            config = ThresholdConfig.strict()
        elif self.args.config == 'lenient':
            config = ThresholdConfig.lenient()
        else:
            config = ThresholdConfig.default()
        
        # Load config file if provided
        if hasattr(self.args, 'config_file') and self.args.config_file:
            import json
            with open(self.args.config_file, 'r') as f:
                config_data = json.load(f)
            
            # Update config with algorithm-specific parameters
            if 'clustering' in config_data:
                clustering_config = config_data['clustering']
                
                # Update clustering parameters
                for key, value in clustering_config.items():
                    if hasattr(config.clustering, key):
                        setattr(config.clustering, key, value)
        
        # Create pipeline
        pipeline = RedundancyPipeline(config)
        
        # Run pipeline
        self.logger.info(f"Running clustering with {self.args.algorithm} algorithm")
        results = pipeline.run(
            test_sources=self.args.sources,
            coverage_data=self.args.coverage,
            algorithm=self.args.algorithm,
            apply_entropy_damping=not self.args.no_entropy,
            validate_clusters=not self.args.no_validation
        )
        
        # Save results
        output_dir = self.ensure_output_dir(self.args.output)
        pipeline.save_results(output_dir, save_csv=True)
        
        # Log summary
        self.logger.info(f"Results saved to: {output_dir}")
        self.logger.info(f"Total tests: {results['test_count']}")
        self.logger.info(f"Clusters found: {len(results['clusters'])}")
        
        if 'redundancy_analysis' in results:
            summary = results['redundancy_analysis']['summary']
            self.logger.info(f"Redundant tests: {summary['redundant_tests']}")
            self.logger.info(f"Redundancy rate: {summary['redundancy_rate']:.1f}%")