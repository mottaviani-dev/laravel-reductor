"""Shared constants for ML pipeline."""

# Vector dimensions
SEMANTIC_DIM = 128
COVERAGE_DIM = 512
COMBINED_DIM = SEMANTIC_DIM + COVERAGE_DIM

# Default parameters
DEFAULT_RANDOM_STATE = 42
DEFAULT_N_JOBS = -1  # Use all available cores

# File patterns
PHP_TEST_PATTERN = r'.*Test\.php$'
COVERAGE_FILE_PATTERN = r'coverage.*\.json$'

# Clustering algorithms
ALGORITHM_KMEANS = 'kmeans'
ALGORITHM_DBSCAN = 'dbscan'
ALGORITHM_HIERARCHICAL = 'hierarchical'

SUPPORTED_ALGORITHMS = [
    ALGORITHM_KMEANS,
    ALGORITHM_DBSCAN,
    ALGORITHM_HIERARCHICAL
]

# Reduction algorithms
REDUCTION_PCA = 'pca'
REDUCTION_TSNE = 'tsne'
REDUCTION_RANDOM = 'random'

SUPPORTED_REDUCTIONS = [
    REDUCTION_PCA,
    REDUCTION_TSNE,
    REDUCTION_RANDOM
]

# Output formats
FORMAT_JSON = 'json'
FORMAT_CSV = 'csv'
FORMAT_MARKDOWN = 'markdown'

SUPPORTED_FORMATS = [
    FORMAT_JSON,
    FORMAT_CSV,
    FORMAT_MARKDOWN
]

# Logging levels
LOG_DEBUG = 'DEBUG'
LOG_INFO = 'INFO'
LOG_WARNING = 'WARNING'
LOG_ERROR = 'ERROR'

# Performance limits
MAX_FEATURES_TFIDF = 5000
MAX_SAMPLES_TSNE = 5000
MAX_ITERATIONS = 1000

# Laravel-specific patterns
LARAVEL_TEST_PATTERNS = [
    r'test[s]?/.*Test\.php$',
    r'tests/Unit/.*Test\.php$',
    r'tests/Feature/.*Test\.php$',
    r'tests/Integration/.*Test\.php$',
]

LARAVEL_ASSERTION_PATTERNS = [
    r'assert[A-Z]\w+',
    r'expect[A-Z]\w+',
    r'see[A-Z]\w+',
    r'dontSee[A-Z]\w+',
]