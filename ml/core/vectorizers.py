"""TF-IDF vectorizer for semantic analysis."""

import numpy as np
from typing import List, Dict, Optional, Tuple, Union
from collections import Counter
import math
from scipy.sparse import csr_matrix, spmatrix

from .tokenizer import PHPTokenizer, extract_test_name


class TFIDFVectorizer:
    """TF-IDF vectorizer for PHP test code."""
    
    def __init__(self, 
                 max_features: int = 1000,
                 min_df: float = 0.01,
                 max_df: float = 0.95,
                 use_idf: bool = True,
                 sublinear_tf: bool = True):
        """
        Initialize TF-IDF vectorizer.
        
        Args:
            max_features: Maximum number of features
            min_df: Minimum document frequency (0-1)
            max_df: Maximum document frequency (0-1)
            use_idf: Whether to use IDF weighting
            sublinear_tf: Whether to apply sublinear TF scaling
        """
        self.max_features = max_features
        self.min_df = min_df
        self.max_df = max_df
        self.use_idf = use_idf
        self.sublinear_tf = sublinear_tf
        
        self.tokenizer = PHPTokenizer()
        self.vocabulary_: Optional[Dict[str, int]] = None
        self.idf_: Optional[np.ndarray] = None
        self.document_count_: int = 0
        
    def fit(self, documents: List[str]) -> 'TFIDFVectorizer':
        """
        Fit the vectorizer on documents.
        
        Args:
            documents: List of document texts
            
        Returns:
            Self
        """
        self.document_count_ = len(documents)
        
        # Tokenize all documents
        tokenized_docs = [self.tokenizer.tokenize(doc) for doc in documents]
        
        # Calculate document frequencies
        doc_freq = Counter()
        for tokens in tokenized_docs:
            unique_tokens = set(tokens)
            for token in unique_tokens:
                doc_freq[token] += 1
        
        # Filter by document frequency
        min_count = int(self.min_df * self.document_count_)
        max_count = int(self.max_df * self.document_count_)
        
        filtered_tokens = [
            token for token, count in doc_freq.items()
            if min_count <= count <= max_count
        ]
        
        # Select top features by frequency
        if len(filtered_tokens) > self.max_features:
            filtered_tokens = sorted(
                filtered_tokens, 
                key=lambda x: doc_freq[x], 
                reverse=True
            )[:self.max_features]
        
        # Create vocabulary
        self.vocabulary_ = {token: idx for idx, token in enumerate(sorted(filtered_tokens))}
        
        # Calculate IDF values
        if self.use_idf:
            self.idf_ = np.zeros(len(self.vocabulary_))
            for token, idx in self.vocabulary_.items():
                df = doc_freq[token]
                self.idf_[idx] = math.log(self.document_count_ / df) + 1
        
        return self
    
    def transform(self, documents: List[str]) -> csr_matrix:
        """
        Transform documents to TF-IDF vectors.
        
        Args:
            documents: List of document texts
            
        Returns:
            TF-IDF sparse matrix (n_documents, n_features)
        """
        if self.vocabulary_ is None:
            raise ValueError("TF-IDF vectorizer not fitted. Call fit() method before transform() or use fit_transform() instead.")
        
        n_docs = len(documents)
        n_features = len(self.vocabulary_)
        
        # Use lists to build sparse matrix efficiently
        row_indices = []
        col_indices = []
        data_values = []
        
        for doc_idx, doc in enumerate(documents):
            tokens = self.tokenizer.tokenize(doc)
            
            # Calculate term frequencies
            tf_dict = Counter(tokens)
            
            for token, count in tf_dict.items():
                if token in self.vocabulary_:
                    feature_idx = self.vocabulary_[token]
                    
                    # Apply sublinear TF scaling
                    if self.sublinear_tf:
                        tf = 1 + math.log(count)
                    else:
                        tf = count
                    
                    # Apply IDF weighting
                    if self.use_idf:
                        value = tf * self.idf_[feature_idx]
                    else:
                        value = tf
                    
                    # Store indices and value for sparse matrix
                    row_indices.append(doc_idx)
                    col_indices.append(feature_idx)
                    data_values.append(value)
        
        # Create sparse matrix
        tfidf_matrix = csr_matrix(
            (data_values, (row_indices, col_indices)),
            shape=(n_docs, n_features),
            dtype=np.float32
        )
        
        return tfidf_matrix
    
    def fit_transform(self, documents: List[str]) -> csr_matrix:
        """
        Fit vectorizer and transform documents.
        
        Args:
            documents: List of document texts
            
        Returns:
            TF-IDF sparse matrix (n_documents, n_features)
        """
        self.fit(documents)
        return self.transform(documents)
    
    def get_feature_names(self) -> List[str]:
        """Get feature names (vocabulary)."""
        if self.vocabulary_ is None:
            raise ValueError("Vectorizer not fitted.")
        
        # Sort by index to get features in order
        features = [''] * len(self.vocabulary_)
        for token, idx in self.vocabulary_.items():
            features[idx] = token
        
        return features


class SemanticVectorizer:
    """
    High-level semantic vectorizer that creates fixed-size vectors
    for PHP test code using TF-IDF and dimensionality reduction.
    """
    
    def __init__(self, 
                 output_dim: int = 128,
                 max_features: int = 1000):
        """
        Initialize semantic vectorizer.
        
        Args:
            output_dim: Desired output dimension
            max_features: Maximum features for TF-IDF
        """
        self.output_dim = output_dim
        self.max_features = max_features
        
        self.tfidf_vectorizer = TFIDFVectorizer(
            max_features=max_features,
            min_df=0.01,
            max_df=0.95,
            use_idf=True,
            sublinear_tf=True
        )
        
        self.projection_matrix_: Optional[np.ndarray] = None
        
    def fit(self, test_sources: Dict[str, str]) -> 'SemanticVectorizer':
        """
        Fit the vectorizer on test sources.
        
        Args:
            test_sources: Dict mapping test names to source code
            
        Returns:
            Self
        """
        # Extract documents
        test_names = list(test_sources.keys())
        documents = list(test_sources.values())
        
        # Fit TF-IDF
        tfidf_matrix = self.tfidf_vectorizer.fit_transform(documents)
        
        # Create random projection matrix for dimensionality reduction
        n_features = tfidf_matrix.shape[1]
        
        if n_features > self.output_dim:
            # Use random projection
            rng = np.random.RandomState(42)
            self.projection_matrix_ = rng.randn(n_features, self.output_dim)
            # Normalize columns
            self.projection_matrix_ /= np.linalg.norm(
                self.projection_matrix_, axis=0, keepdims=True
            )
        else:
            # If fewer features than output_dim, pad with zeros
            self.projection_matrix_ = np.eye(n_features, self.output_dim)
        
        return self
    
    def transform(self, test_sources: Dict[str, str]) -> Dict[str, np.ndarray]:
        """
        Transform test sources to semantic vectors.
        
        Args:
            test_sources: Dict mapping test names to source code
            
        Returns:
            Dict mapping test names to semantic vectors
        """
        if self.projection_matrix_ is None:
            raise ValueError("Semantic vectorizer not fitted. The projection matrix is not initialized. Call fit() method before transform() or use fit_transform() instead.")
        
        # Order matters for consistent results
        test_names = list(test_sources.keys())
        documents = [test_sources[name] for name in test_names]
        
        # Transform to TF-IDF (returns sparse matrix)
        tfidf_matrix = self.tfidf_vectorizer.transform(documents)
        
        # Project to lower dimension (sparse @ dense = dense)
        vectors = tfidf_matrix @ self.projection_matrix_
        
        # Ensure vectors is a dense array for normalization
        if hasattr(vectors, 'toarray'):
            vectors = vectors.toarray()
        
        # L2 normalize
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        vectors = np.divide(vectors, norms, where=norms != 0)
        
        # Create result dict
        result = {}
        for i, test_name in enumerate(test_names):
            result[test_name] = vectors[i]
        
        return result
    
    def fit_transform(self, test_sources: Dict[str, str]) -> Dict[str, np.ndarray]:
        """
        Fit vectorizer and transform test sources.
        
        Args:
            test_sources: Dict mapping test names to source code
            
        Returns:
            Dict mapping test names to semantic vectors
        """
        self.fit(test_sources)
        return self.transform(test_sources)