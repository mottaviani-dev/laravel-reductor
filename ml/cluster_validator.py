"""Cluster validation for safety - prevents merging semantically opposing tests."""

import re
import itertools
from typing import List, Tuple, Dict


class ClusterValidator:
    """
    Validates cluster safety to prevent merging semantically opposing tests.
    Extension beyond academic research for production safety.
    """
    
    def __init__(self):
        self.opposition_pairs = [
            ('success', 'fail|failure|error|exception'),
            ('valid', 'invalid'),
            ('empty', 'notempty|not_empty'),
            ('null', 'notnull|not_null'),
            ('authorized', 'unauthorized|forbidden'),
            ('authenticated', 'unauthenticated|guest'),
            ('create', 'delete|destroy|remove'),
            ('add', 'remove|delete'),
            ('enable', 'disable'),
            ('start', 'stop|end'),
            ('show', 'hide'),
            ('open', 'close'),
            ('accept', 'reject|deny'),
            ('allow', 'block|prevent'),
            ('connect', 'disconnect'),
            ('login', 'logout'),
            ('subscribe', 'unsubscribe'),
            ('lock', 'unlock'),
            ('activate', 'deactivate'),
            ('online', 'offline'),
            ('available', 'unavailable'),
            ('public', 'private'),
            ('visible', 'hidden|invisible'),
        ]
    
    def validate_cluster_safety(self, cluster_tests: List[str]) -> Tuple[bool, str]:
        """
        Validates that a cluster doesn't contain semantically opposing tests.
        Uses early termination for better performance.
        
        Args:
            cluster_tests: List of test names in the cluster
            
        Returns:
            Tuple of (is_safe, reason)
        """
        # Early termination: skip small clusters (2-3 tests are usually safe)
        if len(cluster_tests) <= 2:
            return True, "Small cluster - minimal conflict risk"
        
        # Check for exception handling tests first (fastest check)
        if self._contains_mixed_exception_tests(cluster_tests):
            return False, "Cluster mixes normal flow with exception handling tests"
        
        # Check for boundary value tests
        if self._contains_boundary_tests(cluster_tests):
            return False, "Cluster contains boundary value tests that should remain separate"
        
        # Check for opposing test pairs (most expensive check)
        # Use early termination in the loop
        for test_a, test_b in itertools.combinations(cluster_tests, 2):
            is_opposing, reason = self._are_semantically_opposing(test_a, test_b)
            if is_opposing:
                return False, f"Opposing tests found: {reason}"
        
        return True, "Cluster is safe for merging"
    
    def _are_semantically_opposing(self, test_a: str, test_b: str) -> Tuple[bool, str]:
        """Check if two tests are semantically opposing with early termination."""
        test_a_lower = test_a.lower()
        test_b_lower = test_b.lower()
        
        # Quick check: if test names are very similar, they're likely not opposing
        if self._similarity_ratio(test_a_lower, test_b_lower) > 0.8:
            return False, ""
        
        for positive, negative_pattern in self.opposition_pairs:
            # Check both directions with early termination
            if positive in test_a_lower and re.search(negative_pattern, test_b_lower):
                return True, f"{positive} vs {negative_pattern}"
            
            if positive in test_b_lower and re.search(negative_pattern, test_a_lower):
                return True, f"{negative_pattern} vs {positive}"
        
        return False, ""
    
    def _similarity_ratio(self, s1: str, s2: str) -> float:
        """Quick string similarity check using set intersection."""
        set1 = set(s1.split('_'))
        set2 = set(s2.split('_'))
        if not set1 or not set2:
            return 0.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0
    
    def _contains_boundary_tests(self, tests: List[str]) -> bool:
        """Check if cluster contains boundary value tests."""
        boundary_patterns = [
            r'min|minimum',
            r'max|maximum',
            r'zero|empty',
            r'boundary|edge|limit',
            r'overflow|underflow',
        ]
        
        boundary_count = 0
        for test in tests:
            test_lower = test.lower()
            for pattern in boundary_patterns:
                if re.search(pattern, test_lower):
                    boundary_count += 1
                    break
        
        # If more than 30% are boundary tests, keep them separate
        return boundary_count > len(tests) * 0.3
    
    def _contains_mixed_exception_tests(self, tests: List[str]) -> bool:
        """Check if cluster mixes normal and exception tests."""
        exception_patterns = [
            r'exception|error|fail',
            r'throw|throws|raising',
            r'invalid|malformed|corrupt',
        ]
        
        has_exception_tests = False
        has_normal_tests = False
        
        for test in tests:
            test_lower = test.lower()
            is_exception_test = any(re.search(pattern, test_lower) 
                                   for pattern in exception_patterns)
            
            if is_exception_test:
                has_exception_tests = True
            else:
                has_normal_tests = True
            
            # Early exit if we found both types
            if has_exception_tests and has_normal_tests:
                return True
        
        return False
    
    def split_unsafe_clusters(self, clusters: Dict[int, List[str]], 
                             test_vectors: Dict[str, Dict]) -> Dict[int, List[str]]:
        """
        Split clusters that contain opposing tests.
        
        Args:
            clusters: Dictionary mapping cluster_id to list of test names
            test_vectors: Dictionary mapping test names to their feature vectors
            
        Returns:
            New clusters dictionary with unsafe clusters split
        """
        new_clusters = {}
        next_cluster_id = max(clusters.keys()) + 1
        
        for cluster_id, test_names in clusters.items():
            is_safe, reason = self.validate_cluster_safety(test_names)
            
            if is_safe:
                new_clusters[cluster_id] = test_names
            else:
                # Split the cluster based on semantic opposition
                subclusters = self._split_by_semantics(test_names)
                
                for i, subcluster in enumerate(subclusters):
                    if len(subcluster) >= 2:  # Only keep clusters with 2+ tests
                        new_clusters[next_cluster_id + i] = subcluster
                
                next_cluster_id += len(subclusters)
        
        return new_clusters
    
    def _split_by_semantics(self, tests: List[str]) -> List[List[str]]:
        """Split tests into semantically coherent groups."""
        groups = []
        remaining = set(tests)
        
        while remaining:
            # Start a new group with an arbitrary test
            current_group = [remaining.pop()]
            
            # Find all tests that are NOT opposing to any in current group
            tests_to_add = []
            for test in remaining:
                can_add = True
                for group_test in current_group:
                    is_opposing, _ = self._are_semantically_opposing(test, group_test)
                    if is_opposing:
                        can_add = False
                        break
                
                if can_add:
                    tests_to_add.append(test)
            
            # Add compatible tests to current group
            for test in tests_to_add:
                current_group.append(test)
                remaining.remove(test)
            
            groups.append(current_group)
        
        return groups