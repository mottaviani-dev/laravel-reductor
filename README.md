# Laravel Reductor

A powerful Laravel package for detecting and reducing test redundancy using machine learning clustering algorithms. Reductor analyzes your test suite to identify similar tests that provide overlapping coverage, helping you maintain a leaner, more efficient test suite.

## Features

- **ML-Powered Analysis**: Uses advanced clustering algorithms (DBSCAN, Hierarchical, K-means) to identify redundant tests
- **Coverage-Based Detection**: Analyzes code coverage patterns to find tests with similar execution paths
- **Semantic Understanding**: Combines coverage analysis with semantic similarity of test code
- **Safety Validation**: Prevents merging of semantically opposing tests (e.g., success vs failure tests)
- **Multiple Output Formats**: Markdown (default), JSON, YAML, and HTML reports
- **IDF-Weighted Coverage**: Uses Inverse Document Frequency to emphasize unique coverage patterns
- **Configurable Thresholds**: Adjust similarity thresholds to control reduction aggressiveness

## Installation

1. Install the package via Composer:

```bash
composer require mottaviani-dev/laravel-reductor
```

2. Publish the configuration file:

```bash
php artisan vendor:publish --provider="Reductor\ReductorServiceProvider"
```

3. Run migrations to create the necessary database tables:

```bash
php artisan migrate
```

4. Ensure Python 3.8+ is installed with required packages (alpine based images):

```bash
apk add --no-cache build-base python3-dev py3-pip py3-wheel py3-setuptools py3-numpy cmake
```

```bash
pip install -r vendor/mottaviani-dev/laravel-reductor/requirements.txt
```

## Quick Start

### 1. Generate Coverage Data

First, generate PHPUnit coverage in text format:

```bash
XDEBUG_MODE=coverage ./vendor/bin/phpunit --coverage-php=storage/coverage.cov
```

### 2. Ingest Coverage Data

Import the coverage data into Reductor:

```bash
php artisan reductor:ingest-coverage storage/coverage.cov
```

This will output a test run ID that you'll use for analysis.

### 3. Analyze for Redundancy

Run the redundancy detection (K-Means algorithm and Markdown output are defaults):

```bash
php artisan tests:reduce <test-run-id>
```

## Usage Examples

### Basic Usage with Different Algorithms

```bash
# Using K-means (default)
php artisan tests:reduce 46 --algorithm kmeans

# Using DBSCAN (good for varied density data)
php artisan tests:reduce 46 --algorithm dbscan

# Using Hierarchical clustering
php artisan tests:reduce 46 --algorithm hierarchical
```

### Output Formats

```bash
# Markdown report (default, human-readable)
php artisan tests:reduce 46

# JSON format (for programmatic use)
php artisan tests:reduce 46 --format json

# HTML report
php artisan tests:reduce 46 --format html --output report.html

# YAML format
php artisan tests:reduce 46 --format yaml
```

### Adjusting Similarity Thresholds

```bash
# Conservative (95% similarity required)
php artisan tests:reduce 46 --threshold 0.95

# Balanced (85% default)
php artisan tests:reduce 46

# Aggressive (70% similarity)
php artisan tests:reduce 46 --threshold 0.7
```

### Combined Options

```bash
# Full example with all options
php artisan tests:reduce 46 \
  --algorithm dbscan \
  --threshold 0.85 \
  --format markdown \
  --output storage/reductor/analysis.md
```

## Configuration

Edit `config/reductor.php` to customize default settings:

```php
return [
    'analysis' => [
        // Default clustering algorithm
        'algorithm' => env('REDUCTOR_ALGORITHM', 'kmeans'),
        
        // Similarity thresholds
        'similarity_thresholds' => [
            'conservative' => 0.95,  // High confidence
            'balanced' => 0.85,      // Default
            'aggressive' => 0.75,    // More reduction
        ],
        
        // DBSCAN parameters
        'dbscan' => [
            'eps' => null,  // Auto-detect
            'min_samples' => 3,
            'metric' => 'euclidean',
        ],
    ],
    
    'coverage' => [
        // Coverage file search paths
        'auto_detect_paths' => [
            storage_path('coverage.txt'),
            storage_path('coverage.cov'),
            base_path('coverage/coverage.txt'),
        ],
    ],
];
```

## Understanding the Algorithms

### K-means (Default)
- **Centroid-based clustering** that automatically finds optimal number of clusters
- **Most validated algorithm** in research literature (35% of studies)
- **Fast and deterministic** with consistent results across runs
- **Works well** when test clusters have similar sizes

### DBSCAN
- **Density-based clustering** that can identify noise points and outliers
- **Good for varied density** when test clusters have very different sizes
- **Adaptive parameters** based on dataset characteristics

### Hierarchical Clustering
- **Structure-aware clustering** that builds a tree of clusters
- **Useful for** understanding hierarchical relationships between test groups
- **Good alternative** when you need dendrogram visualization

## Interpreting Results

### Redundancy Scores
- **95-100%**: Nearly identical tests - safe to remove
- **85-95%**: Very similar tests - review recommended
- **70-85%**: Related tests - manual review required
- **Below 70%**: Different tests - keep both

### Priority Levels
- **High**: Tests with >90% similarity in large clusters
- **Medium**: Tests with 70-90% similarity
- **Low**: Tests with <70% similarity or small clusters

### Coverage Overlap
- Shows percentage of shared code coverage between tests
- 100% overlap doesn't always mean redundant (different assertions possible)
- Combined with semantic similarity for accurate detection

## Advanced Features

### Safety Validation
Reductor automatically prevents merging tests with opposing semantics:
- Success vs Failure tests
- Valid vs Invalid tests
- Create vs Delete operations
- Authorized vs Unauthorized tests

### IDF-Weighted Coverage
Lines covered by many tests are weighted less than unique coverage patterns, improving discrimination between tests that share common initialization code.

### Dimensionality Reduction
Automatically reduces high-dimensional vectors (640D) to manageable size (128D) while preserving 95%+ variance for accurate clustering.

## Troubleshooting

### "Pipeline failed" Error
- Check Python is installed: `python3 --version`
- Verify ML dependencies: `pip list | grep -E "scikit-learn|numpy"`
- Check logs: `tail -50 storage/logs/laravel.log`

### Poor Clustering Results
- Ensure coverage data is comprehensive
- Try different algorithms (DBSCAN or Hierarchical)
- Adjust threshold based on your needs
- Check for semantic vector issues (all zeros)

## Example Output (Markdown)

```markdown
# Test Redundancy Analysis Report

## Summary
- Total Redundant Tests: 23
- High Priority: 1 findings
- Medium Priority: 2 findings
- Low Priority: 4 findings

## High Priority Findings

### Cluster 1
**Redundancy Score**: 96%
**Representative Test**: UserLoginTest::test_successful_login
**Redundant Tests** (3):
- UserAuthTest::test_user_can_login
- LoginControllerTest::test_login_success
- AuthenticationTest::test_valid_credentials
```

## Contributing

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

The MIT License (MIT). Please see [License File](LICENSE.md) for more information.
