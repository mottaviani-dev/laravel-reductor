"""Coverage fingerprint generation using multi-hash Bloom filter approach."""

import numpy as np
from typing import Dict, List, Set, Tuple
import hashlib
try:
    import mmh3
    HAS_MMH3 = True
except ImportError:
    HAS_MMH3 = False


class CoverageFingerprintGenerator:
    """
    Generates binary fingerprints from code coverage data using
    a multi-hash Bloom filter approach.
    """
    
    def __init__(self, 
                 fingerprint_size: int = 512,
                 num_hashes: int = 3,
                 seed: int = 42,
                 progress_callback=None):
        """
        Initialize fingerprint generator.
        
        Args:
            fingerprint_size: Size of the fingerprint vector
            num_hashes: Number of hash functions to use
            seed: Random seed for consistent hashing
            progress_callback: Optional callback for progress reporting
        """
        self.fingerprint_size = fingerprint_size
        self.num_hashes = num_hashes
        self.seed = seed
        self.progress_callback = progress_callback
        
    def generate_fingerprint(self, covered_lines: Set[str]) -> np.ndarray:
        """
        Generate a binary fingerprint from covered lines.
        
        Args:
            covered_lines: Set of covered line identifiers (e.g., "file.php:123")
            
        Returns:
            Binary fingerprint vector
        """
        fingerprint = np.zeros(self.fingerprint_size, dtype=np.float32)
        
        for line in covered_lines:
            # Get hash positions for this line
            positions = self._get_hash_positions(line)
            
            # Set bits at hash positions
            for pos in positions:
                fingerprint[pos] = 1.0
        
        return fingerprint
    
    def generate_fingerprints(self, 
                            coverage_data: Dict[str, List[str]]) -> Dict[str, np.ndarray]:
        """
        Generate fingerprints for multiple tests with progress tracking.
        
        Args:
            coverage_data: Dict mapping test names to lists of covered lines
            
        Returns:
            Dict mapping test names to fingerprint vectors
        """
        fingerprints = {}
        total_tests = len(coverage_data)
        processed = 0
        
        # Report initial progress
        self._report_progress(0, total_tests, 'Starting fingerprint generation')
        
        for test_name, covered_lines in coverage_data.items():
            # Convert to set for efficient operations
            lines_set = set(covered_lines)
            
            # Generate fingerprint
            fingerprints[test_name] = self.generate_fingerprint(lines_set)
            
            processed += 1
            
            # Report progress at intervals
            if processed % 10 == 0 or processed == total_tests or processed == 1:
                self._report_progress(processed, total_tests, 'Generating fingerprints')
        
        # Final progress report
        self._report_progress(total_tests, total_tests, 'Fingerprint generation complete')
        
        return fingerprints
    
    def _report_progress(self, current: int, total: int, message: str = ''):
        """Report progress if callback is set."""
        if self.progress_callback:
            percentage = (current / total * 100) if total > 0 else 0
            self.progress_callback(current, total, percentage, message)
    
    def _get_hash_positions(self, line: str) -> List[int]:
        """
        Get hash positions for a covered line using multiple hash functions.
        
        Args:
            line: Line identifier (e.g., "file.php:123")
            
        Returns:
            List of positions in the fingerprint
        """
        positions = []
        
        if HAS_MMH3:
            # Use MurmurHash3 for much faster hashing
            line_bytes = line.encode('utf-8')
            for i in range(self.num_hashes):
                # Use different seeds for each hash function
                hash_value = mmh3.hash(line_bytes, seed=self.seed + i, signed=False)
                position = hash_value % self.fingerprint_size
                positions.append(position)
        else:
            # Fallback to SHA256 (slower but always available)
            for i in range(self.num_hashes):
                hash_input = f"{line}:{self.seed}:{i}".encode('utf-8')
                hash_value = hashlib.sha256(hash_input).hexdigest()
                position = int(hash_value, 16) % self.fingerprint_size
                positions.append(position)
        
        return positions
    
    def estimate_similarity(self, 
                          fingerprint1: np.ndarray, 
                          fingerprint2: np.ndarray) -> float:
        """
        Estimate coverage similarity between two fingerprints.
        
        Uses Jaccard similarity on the binary vectors.
        
        Args:
            fingerprint1: First fingerprint
            fingerprint2: Second fingerprint
            
        Returns:
            Similarity score (0-1)
        """
        # Calculate intersection and union
        intersection = np.sum(fingerprint1 * fingerprint2)
        union = np.sum(np.maximum(fingerprint1, fingerprint2))
        
        if union == 0:
            return 0.0
        
        return float(intersection / union)
    
    def estimate_coverage_overlap(self,
                                fingerprints: Dict[str, np.ndarray],
                                threshold: float = 0.3) -> np.ndarray:
        """
        Calculate pairwise coverage overlap matrix using LSH.
        
        Uses Locality Sensitive Hashing to efficiently find similar fingerprints
        without computing all pairwise similarities.
        
        Args:
            fingerprints: Dict mapping test names to fingerprints
            threshold: Minimum similarity threshold to consider (default 0.3)
            
        Returns:
            Sparse symmetric matrix of coverage similarities
        """
        test_names = list(fingerprints.keys())
        n_tests = len(test_names)
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Computing similarity matrix for {n_tests} tests using LSH")
        
        # Convert fingerprints to matrix
        fingerprint_matrix = np.array([fingerprints[name] for name in test_names])
        
        # Initialize sparse similarity matrix
        similarity_matrix = np.zeros((n_tests, n_tests))
        np.fill_diagonal(similarity_matrix, 1.0)
        
        # Configure LSH parameters based on threshold
        # Higher threshold needs fewer bands (more selective)
        # Lower threshold needs more bands (less selective)
        if threshold >= 0.7:
            n_bands = 10
        elif threshold >= 0.5:
            n_bands = 15
        else:
            n_bands = 20
            
        rows_per_band = self.fingerprint_size // n_bands
        
        # Track candidate pairs from all bands
        candidate_pairs = set()
        
        # Process each band
        for band_idx in range(n_bands):
            start_idx = band_idx * rows_per_band
            end_idx = min(start_idx + rows_per_band, self.fingerprint_size)
            
            # Extract band for all fingerprints
            band_data = fingerprint_matrix[:, start_idx:end_idx]
            
            # Group fingerprints by band hash
            band_buckets = {}
            for i in range(n_tests):
                # Create hash from band data
                band_hash = hash(tuple(band_data[i]))
                if band_hash not in band_buckets:
                    band_buckets[band_hash] = []
                band_buckets[band_hash].append(i)
            
            # Add pairs from same bucket as candidates
            for indices in band_buckets.values():
                if len(indices) > 1:
                    for i in range(len(indices)):
                        for j in range(i + 1, len(indices)):
                            candidate_pairs.add((indices[i], indices[j]))
        
        # Calculate exact similarity only for candidate pairs
        computed_pairs = 0
        for idx_i, idx_j in candidate_pairs:
            # Calculate exact Jaccard similarity
            intersection = np.sum(fingerprint_matrix[idx_i] & fingerprint_matrix[idx_j])
            union = np.sum(fingerprint_matrix[idx_i] | fingerprint_matrix[idx_j])
            
            if union > 0:
                similarity = intersection / union
                if similarity >= threshold:
                    similarity_matrix[idx_i, idx_j] = similarity
                    similarity_matrix[idx_j, idx_i] = similarity
                    computed_pairs += 1
        
        logger.info(f"LSH found {len(candidate_pairs)} candidate pairs, "
                   f"{computed_pairs} above threshold {threshold}")
        
        return similarity_matrix
    def get_coverage_density(self, fingerprint: np.ndarray) -> float:
        """
        Calculate the density of coverage (proportion of bits set).
        
        Args:
            fingerprint: Binary fingerprint vector
            
        Returns:
            Coverage density (0-1)
        """
        return float(np.sum(fingerprint) / self.fingerprint_size)