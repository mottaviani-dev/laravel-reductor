"""PHP code tokenizer for semantic analysis."""

import re
from typing import List, Optional


class PHPTokenizer:
    """Tokenizer for PHP test code."""
    
    def __init__(self):
        # Common stop words to filter out
        self.stop_words = {
            'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'a', 'an', 'is', 'it', 'this', 'that', 'these',
            'those', 'are', 'was', 'were', 'been', 'be', 'have', 'has',
            'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could',
            'can', 'may', 'might', 'must', 'shall', 'as', 'if', 'when',
            'where', 'why', 'how', 'what', 'which', 'who', 'whom', 'whose'
        }
    
    def tokenize(self, text: str, lowercase: bool = True) -> List[str]:
        """
        Tokenize PHP code into semantic tokens.
        
        Args:
            text: The PHP code to tokenize
            lowercase: Whether to convert tokens to lowercase
            
        Returns:
            List of tokens
        """
        # Remove PHP comments
        text = self._remove_comments(text)
        
        # Extract meaningful tokens
        tokens = self._extract_tokens(text)
        
        # Process tokens
        if lowercase:
            tokens = [token.lower() for token in tokens]
            
        # Filter out stop words
        tokens = [token for token in tokens if token not in self.stop_words]
        
        return tokens
    
    def _remove_comments(self, text: str) -> str:
        """Remove PHP comments from code."""
        # Remove single-line comments
        text = re.sub(r'//.*?$', '', text, flags=re.MULTILINE)
        # Remove multi-line comments
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
        # Remove shell-style comments
        text = re.sub(r'#.*?$', '', text, flags=re.MULTILINE)
        return text
    
    def _extract_tokens(self, text: str) -> List[str]:
        """Extract meaningful tokens from PHP code."""
        # Extract function names
        function_names = re.findall(r'function\s+(\w+)', text)
        
        # Extract class names (but filter out test class names to avoid false differences)
        class_names = re.findall(r'class\s+(\w+)', text)
        # Filter out test class names that end with Test/TestCase/Spec
        class_names = [name for name in class_names if not re.match(r'.*Test(Case|Duplicate)?$', name)]
        
        # Extract method calls
        method_calls = re.findall(r'->(\w+)\s*\(', text)
        
        # Extract assertions
        assertions = re.findall(r'assert\w*', text, re.IGNORECASE)
        
        # Extract test-related keywords
        test_keywords = re.findall(r'\b(test|expect|mock|stub|spy|fake|fixture|teardown|setup)\w*\b', text, re.IGNORECASE)
        
        # Extract variable names (meaningful ones)
        variables = re.findall(r'\$([a-zA-Z_]\w{2,})', text)  # Skip short vars
        
        # Extract strings (for test descriptions)
        strings = re.findall(r'["\']([^"\']{3,})["\']', text)  # Min 3 chars
        
        # Combine all tokens
        all_tokens = (
            function_names + 
            class_names + 
            method_calls + 
            assertions + 
            test_keywords + 
            variables + 
            strings
        )
        
        # Split camelCase and snake_case
        processed_tokens = []
        for token in all_tokens:
            # Split camelCase
            camel_split = re.sub(r'([a-z])([A-Z])', r'\1 \2', token).split()
            # Split snake_case
            snake_split = token.split('_')
            
            # Add both original and split tokens
            processed_tokens.append(token)
            processed_tokens.extend(camel_split)
            processed_tokens.extend(snake_split)
        
        # Filter out empty tokens and single characters
        processed_tokens = [t for t in processed_tokens if len(t) > 1]
        
        return processed_tokens


def extract_test_name(test_path: str) -> Optional[str]:
    """
    Extract test name from file path.
    
    Args:
        test_path: Path to test file or test identifier
        
    Returns:
        Test name or None if not found
    """
    # Try to extract from common patterns
    patterns = [
        r'([^/\\]+)(?:Test)?\.php$',  # filename.php or filenameTest.php
        r'::(\w+)$',  # Class::method
        r'#(\w+)$',  # Test#method
        r'@(\w+)$',  # Test@method
    ]
    
    for pattern in patterns:
        match = re.search(pattern, test_path)
        if match:
            return match.group(1)
    
    # If no pattern matches, return the last component
    components = re.split(r'[/\\::#@]', test_path)
    if components:
        last = components[-1]
        # Remove .php extension if present
        if last.endswith('.php'):
            last = last[:-4]
        return last if last else None
    
    return None