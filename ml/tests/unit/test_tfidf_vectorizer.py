"""Unit tests for TF-IDF vectorizer."""

import pytest
import numpy as np
from ml.core.vectorizers import TFIDFVectorizer


class TestTFIDFVectorizer:
    """Test cases for TFIDFVectorizer."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.documents = [
            "test user login functionality",
            "test user registration process",
            "test post creation workflow",
            "test comment system integration"
        ]
    
    def test_fit_creates_vocabulary(self):
        """Test that fit creates vocabulary correctly."""
        vectorizer = TFIDFVectorizer(max_features=10)
        vectorizer.fit(self.documents)
        
        assert vectorizer.vocabulary_ is not None
        assert len(vectorizer.vocabulary_) > 0
        assert 'test' in vectorizer.vocabulary_
        assert 'user' in vectorizer.vocabulary_
    
    def test_transform_creates_vectors(self):
        """Test that transform creates TF-IDF vectors."""
        vectorizer = TFIDFVectorizer(max_features=10)
        vectorizer.fit(self.documents)
        
        vectors = vectorizer.transform(self.documents)
        
        assert vectors.shape[0] == len(self.documents)
        assert vectors.shape[1] == len(vectorizer.vocabulary_)
        assert np.all(vectors >= 0)  # All values should be non-negative
    
    def test_fit_transform_combined(self):
        """Test fit_transform method."""
        vectorizer = TFIDFVectorizer(max_features=10)
        vectors = vectorizer.fit_transform(self.documents)
        
        assert vectors.shape[0] == len(self.documents)
        assert vectorizer.vocabulary_ is not None
    
    def test_max_features_limit(self):
        """Test that max_features limits vocabulary size."""
        max_features = 5
        vectorizer = TFIDFVectorizer(max_features=max_features)
        vectorizer.fit(self.documents)
        
        assert len(vectorizer.vocabulary_) <= max_features
    
    def test_document_frequency_filtering(self):
        """Test min_df and max_df filtering."""
        # Add a term that appears in all documents
        docs = [doc + " common" for doc in self.documents]
        
        vectorizer = TFIDFVectorizer(
            max_features=10,
            min_df=0.25,  # Must appear in at least 25% of docs
            max_df=0.75   # Must not appear in more than 75% of docs
        )
        vectorizer.fit(docs)
        
        # 'common' appears in 100% of docs, should be filtered by max_df
        assert 'common' not in vectorizer.vocabulary_
        
        # 'test' appears in all docs too
        assert 'test' not in vectorizer.vocabulary_
    
    def test_idf_calculation(self):
        """Test IDF calculation."""
        vectorizer = TFIDFVectorizer(max_features=10, use_idf=True)
        vectorizer.fit(self.documents)
        
        assert vectorizer.idf_ is not None
        assert len(vectorizer.idf_) == len(vectorizer.vocabulary_)
        assert np.all(vectorizer.idf_ > 0)  # IDF values should be positive
    
    def test_no_idf_option(self):
        """Test vectorizer without IDF weighting."""
        vectorizer = TFIDFVectorizer(max_features=10, use_idf=False)
        vectorizer.fit(self.documents)
        
        assert vectorizer.idf_ is None
        
        vectors = vectorizer.transform(self.documents)
        assert vectors is not None
    
    def test_sublinear_tf(self):
        """Test sublinear TF scaling."""
        doc_with_repetition = ["test test test user user login"]
        
        vectorizer_linear = TFIDFVectorizer(sublinear_tf=False)
        vectorizer_sublinear = TFIDFVectorizer(sublinear_tf=True)
        
        vectorizer_linear.fit(doc_with_repetition)
        vectorizer_sublinear.fit(doc_with_repetition)
        
        vectors_linear = vectorizer_linear.transform(doc_with_repetition)
        vectors_sublinear = vectorizer_sublinear.transform(doc_with_repetition)
        
        # Sublinear scaling should produce different values
        assert not np.allclose(vectors_linear, vectors_sublinear)
    
    def test_get_feature_names(self):
        """Test getting feature names."""
        vectorizer = TFIDFVectorizer(max_features=10)
        vectorizer.fit(self.documents)
        
        features = vectorizer.get_feature_names()
        
        assert len(features) == len(vectorizer.vocabulary_)
        assert all(isinstance(f, str) for f in features)
        assert all(f in vectorizer.vocabulary_ for f in features)
    
    def test_empty_documents(self):
        """Test handling of empty documents."""
        vectorizer = TFIDFVectorizer()
        
        # Should handle empty list
        vectorizer.fit([])
        assert vectorizer.vocabulary_ == {}
        
        # Should handle documents with empty strings
        vectorizer.fit(["", "", ""])
        assert vectorizer.vocabulary_ == {}
    
    def test_single_document(self):
        """Test handling of single document."""
        vectorizer = TFIDFVectorizer()
        vectorizer.fit(["single test document"])
        
        assert len(vectorizer.vocabulary_) > 0
        
        vectors = vectorizer.transform(["single test document"])
        assert vectors.shape == (1, len(vectorizer.vocabulary_))
    
    def test_transform_before_fit_raises_error(self):
        """Test that transform before fit raises error."""
        vectorizer = TFIDFVectorizer()
        
        with pytest.raises(ValueError, match="not fitted"):
            vectorizer.transform(self.documents)
    
    def test_consistency_across_transforms(self):
        """Test that multiple transforms produce consistent results."""
        vectorizer = TFIDFVectorizer(max_features=10)
        vectorizer.fit(self.documents)
        
        vectors1 = vectorizer.transform(self.documents)
        vectors2 = vectorizer.transform(self.documents)
        
        assert np.allclose(vectors1, vectors2)


if __name__ == '__main__':
    pytest.main([__file__])