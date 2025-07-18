"""Analyze command implementation."""

from ...analysis import EntropyAnalyzer, EntropyConfig
from ...io import load_vectors
from ..base import BaseCommand


class AnalyzeCommand(BaseCommand):
    """Command to analyze existing vectors."""
    
    def execute(self) -> None:
        """Execute analysis."""
        # Load vectors
        semantic_vectors = {}
        coverage_vectors = {}
        
        if self.args.semantic_vectors:
            semantic_vectors = load_vectors(self.args.semantic_vectors)
        
        if self.args.coverage_vectors:
            coverage_vectors = load_vectors(self.args.coverage_vectors)
        
        # Perform analysis
        results = {}
        
        if self.args.entropy:
            analyzer = EntropyAnalyzer(EntropyConfig())
            weights = analyzer.calculate_entropy_weights(
                semantic_vectors, coverage_vectors
            )
            
            summary = analyzer.summarize_entropy_analysis()
            results['entropy'] = {
                'weights': weights,
                'summary': summary,
                'diagnostics': analyzer.diagnostics
            }
            
            self.logger.info(f"Low quality tests: {summary['low_quality_count']}")
            self.logger.info(f"Mean quality: {summary['overall_quality']['mean']:.3f}")
        
        # Save results if output specified
        if self.args.output:
            self.save_output(results, self.args.output)