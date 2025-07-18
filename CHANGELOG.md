# Changelog

All notable changes to Laravel Reductor will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2024-07-18

### Added
- Initial release of Laravel Reductor
- ML-powered test redundancy detection
- Support for K-means, DBSCAN, and Hierarchical clustering
- Coverage fingerprint generation using MinHash
- Semantic vectorization using TF-IDF
- Multiple output formats (JSON, YAML, Markdown, HTML)
- PHPUnit coverage ingestion
- Database storage for historical analysis
- IDF (Inverse Document Frequency) weighting for coverage fingerprints to better distinguish unique coverage patterns
- Safety validation to prevent merging semantically opposing tests (success vs failure, valid vs invalid, etc.)
- Dimensionality reduction using PCA for high-dimensional vectors (640D → 128D)
- Quick reference guide for common commands
- Comprehensive documentation with examples
- Cluster validation to split unsafe clusters based on semantic oppositions
- Adaptive DBSCAN parameters based on dataset size
- Improved semantic vectorization to preserve test method names and important keywords
- Adjusted shared coverage exclusion thresholds (60% for large suites, 70% for medium)
- Enhanced MinHash algorithm with IDF weighting
- Increased redundancy thresholds to be more conservative (HIGH: 0.90→0.95, MEDIUM: 0.70→0.85)
- Updated help text to list DBSCAN first as the recommended algorithm