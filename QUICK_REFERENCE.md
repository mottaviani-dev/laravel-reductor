# Laravel Reductor - Quick Reference

## Essential Commands

### 1. Generate Coverage
```bash
XDEBUG_MODE=coverage ./vendor/bin/phpunit --coverage-text=storage/coverage.txt
```

### 2. Ingest Coverage
```bash
php artisan reductor:ingest-coverage storage/coverage.txt
```

### 3. Run Analysis (Basic)
```bash
php artisan tests:reduce <test-run-id>
```

## Common Options

| Option | Values | Default | Example |
|--------|--------|---------|---------|
| `--algorithm` | dbscan, hierarchical, kmeans | dbscan | `--algorithm hierarchical` |
| `--threshold` | 0.0-1.0 | 0.85 | `--threshold 0.95` |
| `--format` | markdown, json, yaml, html | markdown | `--format json` |
| `--output` | file path | none | `--output report.md` |

## Quick Examples

```bash
# Conservative analysis with HTML output
php artisan tests:reduce 46 --threshold 0.95 --format html --output report.html

# Aggressive reduction with DBSCAN
php artisan tests:reduce 46 --threshold 0.7

# Hierarchical clustering with JSON output
php artisan tests:reduce 46 --algorithm hierarchical --format json

# Default (recommended) settings
php artisan tests:reduce 46
```

## Thresholds Guide

- **0.95+** = Very conservative (only nearly identical tests)
- **0.85** = Balanced (default, recommended)
- **0.70** = Aggressive (more false positives)
- **0.50** = Very aggressive (manual review required)

## Algorithm Selection

- **DBSCAN** Best for test data (default)
- **Hierarchical** Good alternative
- **K-means** Poor performance on test data