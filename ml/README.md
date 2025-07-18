# Laravel Reductor ML Pipeline - Modular Architecture

This directory contains the modular Python codebase for the Laravel Reductor test redundancy detection system.

## Directory Structure

```
ml/
├── core/                    # Core functionality
│   ├── tokenizer.py        # PHP code tokenization
│   ├── vectorizers.py      # TF-IDF semantic vectorization
│   ├── fingerprints.py     # Coverage fingerprint generation
│   ├── features.py         # Feature combination utilities
│   └── normalization.py    # Vector normalization utilities
│
├── clustering/             # Clustering algorithms
│   ├── base.py            # Abstract base clusterer
│   ├── kmeans.py          # K-Means implementation
│   ├── dbscan.py          # DBSCAN implementation
│   ├── hierarchical.py    # Hierarchical clustering
│   └── metrics.py         # Clustering metrics
│
├── analysis/              # Analysis modules
│   ├── reduction.py       # Dimensionality reduction (PCA, t-SNE)
│   ├── redundancy.py      # Redundancy classification
│   ├── entropy.py         # Entropy-based quality analysis
│   └── validation.py      # Semantic safety validation
│
├── config/                # Configuration
│   ├── thresholds.py      # Threshold configurations
│   └── constants.py       # Shared constants
│
├── io/                    # Input/Output utilities
│   ├── json_handler.py    # JSON I/O operations
│   └── csv_handler.py     # CSV report generation
│
├── cli/                   # Command-line interface
│   └── commands.py        # CLI commands
│
├── tests/                 # Unit tests
│   └── unit/              # Unit test modules
│
└── core.py                # Main pipeline orchestrator
```

## Usage

### As a Python Package

```python
from ml import RedundancyPipeline, ThresholdConfig

# Create pipeline with default configuration
pipeline = RedundancyPipeline(ThresholdConfig.default())

# Run the pipeline
results = pipeline.run(
    test_sources='test_sources.json',
    coverage_data='coverage_data.json',
    algorithm='kmeans'
)

# Save results
pipeline.save_results('output_dir/')
```

### Command Line Interface

```bash
# Run complete clustering pipeline
python -m ml.cli.commands cluster \
    --sources test_sources.json \
    --coverage coverage_data.json \
    --output results/ \
    --algorithm kmeans

# Vectorize tests only
python -m ml.cli.commands vectorize \
    --input test_sources.json \
    --output vectors.json

# Validate existing clusters
python -m ml.cli.commands validate \
    --clusters clusters.json \
    --strict
```

### Using the New Model Runner

```bash
# Run clustering
python model_runner.py cluster input.json output_dir/ kmeans

# Generate vectors only
python model_runner.py vectorize test_sources.json vectors.json

# Analyze results
python model_runner.py analyze results.json report.json
```

## 🧪 Testing

Run unit tests with pytest:

```bash
# Run all tests
pytest tests/

# Run specific test module
pytest tests/unit/test_tfidf_vectorizer.py

# Run with coverage
pytest --cov=ml tests/
```

## 🔧 Configuration

### Threshold Presets

- **Default**: Balanced configuration for most use cases
- **Strict**: Higher precision, fewer false positives
- **Lenient**: Higher recall, catches more redundancy

```python
# Use strict configuration
config = ThresholdConfig.strict()
pipeline = RedundancyPipeline(config)
```

### Custom Configuration

```python
from ml.config import ThresholdConfig, SimilarityThresholds

config = ThresholdConfig.default()
config.similarity.moderate_redundancy = 0.6
config.entropy.semantic_min_entropy = 0.55
```

## Key Components

### 1. Semantic Vectorization
- Extracts semantic features from PHP test code
- Uses TF-IDF with PHP-specific tokenization
- Produces 128-dimensional vectors

### 2. Coverage Fingerprints
- Multi-hash Bloom filter approach
- Generates 512-dimensional binary vectors
- Captures test coverage patterns

### 3. Clustering Algorithms
- **K-Means**: Automatic k selection using silhouette score
- **DBSCAN**: Density-based clustering with automatic eps
- **Hierarchical**: Agglomerative clustering with dendrogram support

### 4. Analysis Modules
- **Entropy Analysis**: Detects low-quality uniform patterns
- **Redundancy Classification**: 5-level redundancy classification
- **Semantic Validation**: Prevents unsafe test merging