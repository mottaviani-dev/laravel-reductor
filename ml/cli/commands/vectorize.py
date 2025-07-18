"""Vectorize command implementation."""

from ...core.vectorizers import SemanticVectorizer
from ...io import save_vectors
from ..base import BaseCommand


class VectorizeCommand(BaseCommand):
    """Command to vectorize test sources."""
    
    def execute(self) -> None:
        """Execute vectorization."""
        # Load test sources
        test_sources = self.load_input(self.args.input)
        
        # Vectorize
        vectorizer = SemanticVectorizer(
            output_dim=self.args.output_dim,
            max_features=self.args.max_features
        )
        
        vectors = vectorizer.fit_transform(test_sources)
        
        # Save vectors
        save_vectors(vectors, self.args.output)
        
        self.logger.info(f"Vectorized {len(vectors)} tests")
        self.logger.info(f"Vector dimension: {self.args.output_dim}")