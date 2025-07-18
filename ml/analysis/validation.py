"""Semantic safety validation for test clustering."""

import re
from typing import List, Dict, Set, Tuple, Optional, Any
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class ValidationConfig:
    """Configuration for cluster validation."""
    strict_mode: bool = True
    allow_boundary_merging: bool = False
    min_cluster_size: int = 2


class SemanticValidator:
    """
    Validates clusters against semantic safety constraints.
    
    Prevents merging of tests with opposing intents (e.g., success vs failure)
    even if their vectors are similar due to shared code patterns.
    """
    
    def __init__(self, config: ValidationConfig = None):
        """
        Initialize validator with safety rules.
        
        Args:
            config: Validation configuration
        """
        self.config = config or ValidationConfig()
        self._intent_cache = {}  # Cache for extracted intents
        
        # Define semantic opposition pairs that should never be merged
        self.opposition_pairs = [
            ('success', 'fail|failure|error|exception'),
            ('valid', 'invalid'),
            ('empty', 'notempty|not_empty'),
            ('null', 'notnull|not_null'),
            ('true', 'false'),
            ('found', 'notfound|not_found|missing'),
            ('exists', 'not_exists|doesnt_exist|missing'),
            ('authorized', 'unauthorized|forbidden'),
            ('create|created', 'delete|deleted|destroy'),
            ('with', 'without'),
            ('before', 'after'),
            ('ascending|asc', 'descending|desc'),
            ('min|minimum', 'max|maximum'),
            ('first', 'last'),
            ('single', 'multiple|many'),
            ('enabled', 'disabled'),
            ('active', 'inactive|expired'),
            ('online', 'offline'),
            ('cached|cache_hit', 'uncached|cache_miss'),
            ('sync|synchronous', 'async|asynchronous'),
        ]
        
        # Compile patterns for efficiency
        self.compiled_oppositions = []
        for positive, negative in self.opposition_pairs:
            pos_pattern = re.compile(rf'\b({positive})\b', re.IGNORECASE)
            neg_pattern = re.compile(rf'\b({negative})\b', re.IGNORECASE)
            self.compiled_oppositions.append((pos_pattern, neg_pattern))
    
    def extract_test_intent(self, test_name: str) -> Dict[str, bool]:
        """
        Extract intent indicators from test name with caching.
        
        Args:
            test_name: Name of the test
            
        Returns:
            Dict of intent flags found in the test name
        """
        # Check cache first
        if test_name in self._intent_cache:
            return self._intent_cache[test_name]
        
        intent = {}
        
        # Normalize test name for analysis
        normalized = test_name.lower()
        
        # Check each opposition pair
        for pos_pattern, neg_pattern in self.compiled_oppositions:
            pos_match = pos_pattern.search(normalized)
            neg_match = neg_pattern.search(normalized)
            
            if pos_match:
                intent[pos_match.group(1)] = True
            if neg_match:
                intent[neg_match.group(1)] = False
        
        # Extract assertion types if present
        assertion_patterns = {
            'throws_exception': r'throw|exception|expectexception',
            'returns_null': r'return.*null|null.*return',
            'returns_empty': r'return.*empty|empty.*return',
            'http_success': r'assert(ok|success|200)',
            'http_error': r'assert(error|fail|4\d\d|5\d\d)',
        }
        
        for key, pattern in assertion_patterns.items():
            if re.search(pattern, normalized):
                intent[key] = True
        
        # Cache the result
        self._intent_cache[test_name] = intent
        
        return intent
    
    def tests_have_opposing_intents(self, test1: str, test2: str) -> Tuple[bool, str]:
        """
        Check if two tests have semantically opposing intents.
        
        Args:
            test1: First test name
            test2: Second test name
            
        Returns:
            Tuple of (has_opposition, reason)
        """
        intent1 = self.extract_test_intent(test1)
        intent2 = self.extract_test_intent(test2)
        
        # Check for direct oppositions
        for key in set(intent1.keys()) & set(intent2.keys()):
            if intent1[key] != intent2[key]:
                return True, f"Opposing intents on '{key}'"
        
        # Check specific assertion conflicts
        if intent1.get('throws_exception') and intent2.get('http_success'):
            return True, "Exception test vs success test"
        
        if intent1.get('http_error') and intent2.get('http_success'):
            return True, "Error assertion vs success assertion"
        
        # Check boundary value conflicts
        if self.config.strict_mode and not self.config.allow_boundary_merging:
            boundary_terms = ['min', 'max', 'edge', 'boundary', 'limit']
            has_boundary1 = any(term in test1.lower() for term in boundary_terms)
            has_boundary2 = any(term in test2.lower() for term in boundary_terms)
            
            if has_boundary1 and has_boundary2 and test1 != test2:
                return True, "Different boundary value tests"
        
        return False, ""
    
    def validate_cluster(self, test_names: List[str]) -> Dict[str, Any]:
        """
        Validate a cluster of tests for semantic safety.
        
        Args:
            test_names: List of test names in the cluster
            
        Returns:
            Validation result with details
        """
        conflicts = []
        
        # Check all pairs for conflicts
        for i in range(len(test_names)):
            for j in range(i + 1, len(test_names)):
                has_conflict, reason = self.tests_have_opposing_intents(
                    test_names[i], test_names[j]
                )
                
                if has_conflict:
                    conflicts.append({
                        'test1': test_names[i],
                        'test2': test_names[j],
                        'reason': reason
                    })
        
        # Analyze test categories
        categories = defaultdict(list)
        for test in test_names:
            intent = self.extract_test_intent(test)
            
            # Categorize by primary intent
            if any('success' in k or 'valid' in k for k in intent.keys()):
                categories['positive'].append(test)
            elif any('fail' in k or 'error' in k or 'invalid' in k for k in intent.keys()):
                categories['negative'].append(test)
            elif any('boundary' in test.lower() or 'edge' in test.lower() for test in [test]):
                categories['boundary'].append(test)
            else:
                categories['neutral'].append(test)
        
        # Check category mixing
        has_mixed_categories = len([c for c in categories.values() if c]) > 1
        
        return {
            'is_safe': len(conflicts) == 0,
            'conflicts': conflicts,
            'categories': dict(categories),
            'has_mixed_categories': has_mixed_categories,
            'cluster_size': len(test_names)
        }
    
    def split_unsafe_clusters(self,
                            cluster_data: List[Dict[str, Any]],
                            test_vectors: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], int]:
        """
        Split clusters that violate safety constraints.
        
        Args:
            cluster_data: Original cluster information
            test_vectors: Test vectors with cluster assignments
            
        Returns:
            Tuple of (new_cluster_data, split_count)
        """
        new_clusters = []
        split_count = 0
        
        # Find next cluster ID
        numeric_cluster_ids = [
            c['cluster_id'] for c in cluster_data 
            if isinstance(c['cluster_id'], int)
        ]
        if numeric_cluster_ids:
            next_cluster_id = max(numeric_cluster_ids) + 1
        else:
            next_cluster_id = 1
        
        for cluster in cluster_data:
            validation = self.validate_cluster(cluster['tests'])
            
            if validation['is_safe']:
                # Keep cluster as-is
                new_clusters.append(cluster)
            else:
                # Split cluster based on conflicts
                split_count += 1
                
                # Group by categories
                categories = validation['categories']
                
                for category, tests in categories.items():
                    if tests:  # Non-empty category
                        new_cluster = {
                            'cluster_id': next_cluster_id,
                            'tests': tests,
                            'size': len(tests),
                            'was_split': True,
                            'original_cluster': cluster['cluster_id'],
                            'split_reason': f"Semantic conflicts - {category} tests"
                        }
                        new_clusters.append(new_cluster)
                        next_cluster_id += 1
        
        return new_clusters, split_count
    
    def get_validation_summary(self, 
                             clusters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate validation summary for all clusters.
        
        Args:
            clusters: List of cluster data
            
        Returns:
            Summary statistics
        """
        total_clusters = len(clusters)
        unsafe_clusters = 0
        total_conflicts = 0
        conflict_types = defaultdict(int)
        
        for cluster in clusters:
            validation = self.validate_cluster(cluster['tests'])
            
            if not validation['is_safe']:
                unsafe_clusters += 1
                total_conflicts += len(validation['conflicts'])
                
                for conflict in validation['conflicts']:
                    # Extract conflict type
                    reason = conflict['reason']
                    conflict_types[reason] += 1
        
        return {
            'total_clusters': total_clusters,
            'safe_clusters': total_clusters - unsafe_clusters,
            'unsafe_clusters': unsafe_clusters,
            'total_conflicts': total_conflicts,
            'conflict_types': dict(conflict_types),
            'safety_rate': ((total_clusters - unsafe_clusters) / total_clusters * 100) 
                          if total_clusters > 0 else 100
        }