"""Redundancy classification and analysis."""

from typing import Dict, List, Tuple, Any
import numpy as np
from dataclasses import dataclass
from enum import Enum

from ..core.normalization import combined_similarity


class RedundancyLevel(Enum):
    """Redundancy level classification."""
    NONE = "none"
    LOW = "low_redundancy"
    MODERATE = "moderate_redundancy"
    HIGH = "high_redundancy"
    VERY_HIGH = "very_high_redundancy"


@dataclass
class RedundancyThresholds:
    """Thresholds for redundancy classification."""
    low: float = 0.15
    moderate: float = 0.25
    high: float = 0.40
    very_high: float = 0.60


class RedundancyAnalyzer:
    """Analyzes test redundancy based on similarity scores."""
    
    def __init__(self, 
                 thresholds: RedundancyThresholds = None,
                 semantic_weight: float = 0.7,
                 coverage_weight: float = 0.3):
        """
        Initialize redundancy analyzer.
        
        Args:
            thresholds: Redundancy classification thresholds
            semantic_weight: Weight for semantic similarity
            coverage_weight: Weight for coverage similarity
        """
        self.thresholds = thresholds or RedundancyThresholds()
        self.semantic_weight = semantic_weight
        self.coverage_weight = coverage_weight
    
    def classify_redundancy(self, similarity_score: float) -> RedundancyLevel:
        """
        Classify redundancy level based on similarity score.
        
        Args:
            similarity_score: Combined similarity score (0-1)
            
        Returns:
            Redundancy level
        """
        if similarity_score >= self.thresholds.very_high:
            return RedundancyLevel.VERY_HIGH
        elif similarity_score >= self.thresholds.high:
            return RedundancyLevel.HIGH
        elif similarity_score >= self.thresholds.moderate:
            return RedundancyLevel.MODERATE
        elif similarity_score >= self.thresholds.low:
            return RedundancyLevel.LOW
        else:
            return RedundancyLevel.NONE
    
    def analyze_cluster(self,
                       test_names: List[str],
                       semantic_vectors: Dict[str, np.ndarray],
                       coverage_vectors: Dict[str, np.ndarray]) -> Dict[str, Any]:
        """
        Analyze redundancy within a cluster.
        
        Args:
            test_names: List of test names in cluster
            semantic_vectors: Semantic vectors for tests
            coverage_vectors: Coverage vectors for tests
            
        Returns:
            Cluster redundancy analysis
        """
        if len(test_names) < 2:
            return {
                'size': len(test_names),
                'redundancy_level': RedundancyLevel.NONE.value,
                'avg_similarity': 0.0,
                'redundant_pairs': []
            }
        
        # Calculate pairwise similarities
        similarities = []
        redundant_pairs = []
        
        for i in range(len(test_names)):
            for j in range(i + 1, len(test_names)):
                test1 = test_names[i]
                test2 = test_names[j]
                
                # Get vectors
                sem1 = semantic_vectors.get(test1, np.zeros(128))
                sem2 = semantic_vectors.get(test2, np.zeros(128))
                cov1 = coverage_vectors.get(test1, np.zeros(512))
                cov2 = coverage_vectors.get(test2, np.zeros(512))
                
                # Debug: Check if vectors are zero
                if i == 0 and j == 1:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"Debug vector lookup for {test1} and {test2}:")
                    logger.info(f"  test1 in semantic_vectors: {test1 in semantic_vectors}")
                    logger.info(f"  test2 in semantic_vectors: {test2 in semantic_vectors}")
                    logger.info(f"  test1 in coverage_vectors: {test1 in coverage_vectors}")
                    logger.info(f"  test2 in coverage_vectors: {test2 in coverage_vectors}")
                    logger.info(f"  sem1 norm: {np.linalg.norm(sem1):.4f}")
                    logger.info(f"  sem2 norm: {np.linalg.norm(sem2):.4f}")
                    logger.info(f"  cov1 norm: {np.linalg.norm(cov1):.4f}")
                    logger.info(f"  cov2 norm: {np.linalg.norm(cov2):.4f}")
                    if semantic_vectors:
                        logger.info(f"  Available semantic keys (first 5): {list(semantic_vectors.keys())[:5]}")
                    if coverage_vectors:
                        logger.info(f"  Available coverage keys (first 5): {list(coverage_vectors.keys())[:5]}")
                
                # Calculate similarity
                sim_scores = combined_similarity(
                    sem1, sem2, cov1, cov2,
                    self.semantic_weight, self.coverage_weight
                )
                
                combined_sim = sim_scores['combined_similarity']
                similarities.append(combined_sim)
                
                # Debug: log similarity scores
                if i == 0 and j == 1:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.info(f"Sample similarity between {test1} and {test2}:")
                    logger.info(f"  Semantic: {sim_scores['semantic_similarity']:.4f}")
                    logger.info(f"  Coverage: {sim_scores['coverage_similarity']:.4f}")
                    logger.info(f"  Combined: {combined_sim:.4f}")
                
                # Track redundant pairs
                level = self.classify_redundancy(combined_sim)
                if level not in [RedundancyLevel.NONE, RedundancyLevel.LOW]:
                    redundant_pairs.append({
                        'test1': test1,
                        'test2': test2,
                        'similarity': combined_sim,
                        'level': level.value
                    })
        
        # Calculate average similarity
        avg_similarity = np.mean(similarities) if similarities else 0.0
        
        # Determine cluster redundancy level
        cluster_level = self.classify_redundancy(avg_similarity)
        
        return {
            'size': len(test_names),
            'redundancy_level': cluster_level.value,
            'avg_similarity': float(avg_similarity),
            'redundant_pairs': redundant_pairs,
            'n_redundant_pairs': len(redundant_pairs)
        }
    
    def find_redundant_tests(self,
                           clusters: Dict[int, List[str]],
                           semantic_vectors: Dict[str, np.ndarray],
                           coverage_vectors: Dict[str, np.ndarray]) -> List[Dict[str, Any]]:
        """
        Find all redundant test pairs across clusters.
        
        Args:
            clusters: Dict mapping cluster IDs to test names
            semantic_vectors: Semantic vectors for tests
            coverage_vectors: Coverage vectors for tests
            
        Returns:
            List of redundancy records
        """
        redundancy_records = []
        
        # Debug: Log vector availability
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"find_redundant_tests called with:")
        logger.info(f"  Number of clusters: {len(clusters)}")
        logger.info(f"  Total tests in clusters: {sum(len(tests) for tests in clusters.values())}")
        logger.info(f"  Semantic vectors available: {len(semantic_vectors)}")
        logger.info(f"  Coverage vectors available: {len(coverage_vectors)}")
        
        # Check for vector availability for first cluster
        if clusters:
            first_cluster_id = min(clusters.keys())
            first_cluster_tests = clusters[first_cluster_id]
            logger.info(f"  First cluster ({first_cluster_id}) has {len(first_cluster_tests)} tests")
            if first_cluster_tests:
                test_sample = first_cluster_tests[0]
                logger.info(f"  Sample test name: '{test_sample}'")
                logger.info(f"  Sample test in semantic_vectors: {test_sample in semantic_vectors}")
                logger.info(f"  Sample test in coverage_vectors: {test_sample in coverage_vectors}")
        
        for cluster_id, test_names in clusters.items():
            if len(test_names) < 2:
                continue
            
            # Analyze cluster
            analysis = self.analyze_cluster(
                test_names, semantic_vectors, coverage_vectors
            )
            
            # Create records for each test
            for test_name in test_names:
                # Find similar tests in cluster
                similar_tests = []
                max_similarity = 0.0
                
                for other_test in test_names:
                    if other_test == test_name:
                        continue
                    
                    # Calculate similarity
                    sem1 = semantic_vectors.get(test_name, np.zeros(128))
                    sem2 = semantic_vectors.get(other_test, np.zeros(128))
                    cov1 = coverage_vectors.get(test_name, np.zeros(512))
                    cov2 = coverage_vectors.get(other_test, np.zeros(512))
                    
                    # Debug first pair
                    if cluster_id == min(clusters.keys()) and test_name == test_names[0] and other_test == test_names[1]:
                        import logging
                        logger = logging.getLogger(__name__)
                        logger.info(f"Debug in find_redundant_tests for {test_name} vs {other_test}:")
                        logger.info(f"  Vector norms - sem1: {np.linalg.norm(sem1):.4f}, sem2: {np.linalg.norm(sem2):.4f}")
                        logger.info(f"  Vector norms - cov1: {np.linalg.norm(cov1):.4f}, cov2: {np.linalg.norm(cov2):.4f}")
                    
                    sim_scores = combined_similarity(
                        sem1, sem2, cov1, cov2,
                        self.semantic_weight, self.coverage_weight
                    )
                    
                    if sim_scores['combined_similarity'] >= self.thresholds.moderate:
                        similar_tests.append(other_test)
                        max_similarity = max(max_similarity, sim_scores['combined_similarity'])
                
                # Create record
                record = {
                    'test_name': test_name,
                    'cluster_id': cluster_id,
                    'cluster_size': len(test_names),
                    'similar_tests': similar_tests,
                    'max_similarity': max_similarity,
                    'redundancy_status': self.classify_redundancy(max_similarity).value,
                    'cluster_redundancy': analysis['redundancy_level']
                }
                
                redundancy_records.append(record)
        
        return redundancy_records
    
    def summarize_redundancy(self, 
                           redundancy_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Summarize redundancy analysis results.
        
        Args:
            redundancy_records: List of redundancy records
            
        Returns:
            Summary statistics
        """
        total_tests = len(redundancy_records)
        
        # Count by redundancy level
        level_counts = {level.value: 0 for level in RedundancyLevel}
        for record in redundancy_records:
            status = record.get('redundancy_status', RedundancyLevel.NONE.value)
            level_counts[status] += 1
        
        # Calculate percentages
        level_percentages = {
            level: (count / total_tests * 100) if total_tests > 0 else 0
            for level, count in level_counts.items()
        }
        
        # Count redundant tests (moderate or higher)
        redundant_count = sum(
            level_counts[level.value]
            for level in [RedundancyLevel.MODERATE, RedundancyLevel.HIGH, RedundancyLevel.VERY_HIGH]
        )
        
        return {
            'total_tests': total_tests,
            'redundant_tests': redundant_count,
            'redundancy_rate': (redundant_count / total_tests * 100) if total_tests > 0 else 0,
            'level_counts': level_counts,
            'level_percentages': level_percentages
        }