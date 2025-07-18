"""Entropy-based vector analysis for test redundancy detection."""

import numpy as np
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass


@dataclass
class EntropyConfig:
    """Configuration for entropy analysis."""
    semantic_threshold: float = 0.5
    coverage_threshold: float = 0.85
    semantic_weight: float = 0.7
    coverage_weight: float = 0.3


class EntropyAnalyzer:
    """
    Analyzes vector entropy to detect and dampen overly uniform patterns.
    
    High entropy = diverse, informative vector
    Low entropy = uniform, potentially misleading vector
    """
    
    def __init__(self, config: EntropyConfig = None):
        """
        Initialize entropy analyzer.
        
        Args:
            config: Entropy analysis configuration
        """
        self.config = config or EntropyConfig()
        self.diagnostics: List[Dict[str, Any]] = []
    
    def calculate_shannon_entropy(self, vector: np.ndarray, is_binary: bool = False) -> float:
        """
        Calculate Shannon entropy for a vector.
        
        For continuous vectors: H = -Σ(p_i * log2(p_i))
        For binary vectors: Treats as probability distribution
        
        Returns entropy normalized to [0, 1]
        """
        if vector.size == 0:
            return 0.0
        
        if is_binary:
            # For binary vectors, calculate entropy based on bit distribution
            ones = np.sum(vector)
            zeros = len(vector) - ones
            
            if ones == 0 or zeros == 0:
                return 0.0  # Completely uniform
            
            p_one = ones / len(vector)
            p_zero = zeros / len(vector)
            
            # Binary entropy
            entropy = -p_one * np.log2(p_one) - p_zero * np.log2(p_zero)
            
            # Already normalized for binary
            return float(entropy)
        else:
            # For continuous vectors, normalize and treat as probability distribution
            # Handle negative values by taking absolute values
            abs_vector = np.abs(vector)
            
            # Skip zero vectors
            if np.sum(abs_vector) == 0:
                return 0.0
            
            # Normalize to probability distribution
            prob_dist = abs_vector / np.sum(abs_vector)
            
            # Remove zeros to avoid log(0)
            prob_dist = prob_dist[prob_dist > 0]
            
            # Shannon entropy
            entropy = -np.sum(prob_dist * np.log2(prob_dist))
            
            # Normalize by maximum possible entropy
            max_entropy = np.log2(len(vector))
            if max_entropy > 0:
                normalized_entropy = entropy / max_entropy
            else:
                normalized_entropy = 0.0
            
            return float(normalized_entropy)
    
    def analyze_vector_quality(self, 
                             semantic_vector: np.ndarray,
                             coverage_vector: np.ndarray) -> Dict[str, float]:
        """
        Analyze entropy and quality metrics for test vectors.
        
        Args:
            semantic_vector: Semantic feature vector
            coverage_vector: Coverage fingerprint vector
            
        Returns:
            Dict with quality metrics
        """
        results = {}
        
        # Analyze semantic vector
        semantic_entropy = self.calculate_shannon_entropy(semantic_vector, is_binary=False)
        results['semantic_entropy'] = semantic_entropy
        
        # Calculate quality score based on entropy threshold
        if semantic_entropy >= self.config.semantic_threshold:
            results['semantic_quality'] = 1.0
        else:
            # Linear scaling below threshold
            results['semantic_quality'] = semantic_entropy / self.config.semantic_threshold
        
        # Analyze coverage fingerprint
        coverage_entropy = self.calculate_shannon_entropy(coverage_vector, is_binary=True)
        results['coverage_entropy'] = coverage_entropy
        
        # Calculate quality score based on entropy threshold
        if coverage_entropy >= self.config.coverage_threshold:
            results['coverage_quality'] = 1.0
        else:
            # Linear scaling below threshold
            results['coverage_quality'] = coverage_entropy / self.config.coverage_threshold
        
        # Calculate overall quality (weighted average)
        results['overall_quality'] = (
            self.config.semantic_weight * results['semantic_quality'] + 
            self.config.coverage_weight * results['coverage_quality']
        )
        
        # Additional metrics
        results['is_low_quality'] = results['overall_quality'] < 0.5
        results['quality_issues'] = []
        
        if results['semantic_entropy'] < self.config.semantic_threshold:
            results['quality_issues'].append(
                f"Low semantic entropy ({results['semantic_entropy']:.3f} < {self.config.semantic_threshold})"
            )
        
        if results['coverage_entropy'] < self.config.coverage_threshold:
            results['quality_issues'].append(
                f"Low coverage entropy ({results['coverage_entropy']:.3f} < {self.config.coverage_threshold})"
            )
        
        return results
    
    def calculate_entropy_weights(self,
                                semantic_vectors: Dict[str, np.ndarray],
                                coverage_vectors: Dict[str, np.ndarray]) -> Dict[str, Dict[str, float]]:
        """
        Calculate entropy-based damping weights for all test vectors.
        
        Args:
            semantic_vectors: Dict of semantic vectors
            coverage_vectors: Dict of coverage vectors
            
        Returns:
            Dict mapping test names to weight factors
        """
        weights = {}
        self.diagnostics = []
        
        # Get all test names
        all_tests = set(semantic_vectors.keys()) | set(coverage_vectors.keys())
        
        for test_name in all_tests:
            # Get vectors, using zeros if missing
            sem_vec = semantic_vectors.get(test_name, np.zeros(128))
            cov_vec = coverage_vectors.get(test_name, np.zeros(512))
            
            # Analyze quality
            quality = self.analyze_vector_quality(sem_vec, cov_vec)
            
            # Store diagnostics
            self.diagnostics.append({
                'test': test_name,
                **quality
            })
            
            # Calculate damping weights based on quality
            weights[test_name] = {
                'semantic_weight': quality['semantic_quality'],
                'coverage_weight': quality['coverage_quality'],
                'overall_weight': quality['overall_quality'],
                'quality_metrics': quality
            }
        
        return weights
    
    def apply_entropy_damping(self, 
                            feature_matrix: np.ndarray,
                            test_names: List[str],
                            weights: Dict[str, Dict[str, float]],
                            n_semantic: int = 128) -> np.ndarray:
        """
        Apply entropy-based damping to feature matrix.
        
        Low-entropy vectors are scaled down to reduce their influence
        during clustering similarity computation.
        
        Args:
            feature_matrix: Combined feature matrix
            test_names: List of test names corresponding to rows
            weights: Entropy weights for each test
            n_semantic: Number of semantic features
            
        Returns:
            Damped feature matrix
        """
        if len(feature_matrix) != len(test_names):
            raise ValueError(f"Matrix size {len(feature_matrix)} doesn't match test names {len(test_names)}")
        
        damped_matrix = feature_matrix.copy()
        
        for i, test_name in enumerate(test_names):
            if test_name in weights:
                weight_info = weights[test_name]
                
                # Apply damping to semantic portion
                semantic_damping = weight_info['semantic_weight']
                damped_matrix[i, :n_semantic] *= semantic_damping
                
                # Apply damping to coverage portion
                coverage_damping = weight_info['coverage_weight']
                damped_matrix[i, n_semantic:] *= coverage_damping
                
                # Re-normalize after damping to maintain unit vectors
                norm = np.linalg.norm(damped_matrix[i])
                if norm > 0:
                    damped_matrix[i] /= norm
        
        return damped_matrix
    
    def get_low_quality_tests(self, threshold: float = 0.5) -> List[str]:
        """Get list of test names with quality below threshold."""
        return [d['test'] for d in self.diagnostics 
                if d['overall_quality'] < threshold]
    
    def summarize_entropy_analysis(self) -> Dict[str, Any]:
        """Generate summary statistics for entropy analysis."""
        if not self.diagnostics:
            return {'error': 'No entropy analysis data available'}
        
        semantic_entropies = [d['semantic_entropy'] for d in self.diagnostics]
        coverage_entropies = [d['coverage_entropy'] for d in self.diagnostics]
        overall_qualities = [d['overall_quality'] for d in self.diagnostics]
        
        return {
            'total_tests': len(self.diagnostics),
            'low_quality_count': len(self.get_low_quality_tests()),
            'semantic_entropy': {
                'min': float(np.min(semantic_entropies)),
                'max': float(np.max(semantic_entropies)),
                'mean': float(np.mean(semantic_entropies)),
                'std': float(np.std(semantic_entropies))
            },
            'coverage_entropy': {
                'min': float(np.min(coverage_entropies)),
                'max': float(np.max(coverage_entropies)),
                'mean': float(np.mean(coverage_entropies)),
                'std': float(np.std(coverage_entropies))
            },
            'overall_quality': {
                'min': float(np.min(overall_qualities)),
                'max': float(np.max(overall_qualities)),
                'mean': float(np.mean(overall_qualities)),
                'std': float(np.std(overall_qualities))
            }
        }