<?php

return [
    /*
    |--------------------------------------------------------------------------
    | ML Backend Configuration
    |--------------------------------------------------------------------------
    |
    | Configuration for the Python machine learning backend. The ML driver
    | provides more sophisticated analysis but requires Python dependencies.
    |
    */
    'ml_backend' => [
        'python_path' => env('REDUCTOR_PYTHON_PATH', 'python3'),
        'timeout' => env('REDUCTOR_ML_TIMEOUT', 300),
        'memory_limit' => env('REDUCTOR_ML_MEMORY_LIMIT', '512M'),
    ],

    /*
    |--------------------------------------------------------------------------
    | Coverage Configuration
    |--------------------------------------------------------------------------
    |
    | Settings for code coverage file detection and processing. The package
    | will automatically search these paths if no coverage file is specified.
    |
    */
    'coverage' => [
        'default_path' => env('REDUCTOR_COVERAGE_PATH', storage_path('coverage.cov')),
        'auto_detect_paths' => [
            storage_path('coverage.cov'),
            storage_path('app/coverage.cov'),
            storage_path('coverage/coverage.cov'),
            base_path('coverage/coverage.cov'),
            base_path('build/coverage/coverage.cov'),
            base_path('storage/coverage/coverage.cov'),
        ],
        'ignore_patterns' => [
            '**/vendor/**',
            '**/node_modules/**',
            '**/storage/framework/**',
            '**/bootstrap/cache/**',
        ],
    ],

    /*
    |--------------------------------------------------------------------------
    | Analysis Configuration
    |--------------------------------------------------------------------------
    |
    | Fine-tune the test redundancy analysis parameters. These settings
    | control how similar tests need to be to be considered redundant.
    |
    | Algorithm selection follows Sebastian et al. (2024) research findings:
    | - K-means: Most validated (35% of studies) - now default
    | - DBSCAN: Density-based clustering (good for varied density data)
    | - Hierarchical: Structure-aware clustering (9% of studies)
    |
    */
    'analysis' => [
        // Primary clustering algorithm
        'algorithm' => env('REDUCTOR_ALGORITHM', 'kmeans'),
        
        // Minimum similarity score to consider tests for reduction (0.0-1.0)
        'min_similarity_threshold' => env('REDUCTOR_MIN_SIMILARITY', 0.5),
        
        // validated similarity thresholds by confidence level
        'similarity_thresholds' => [
            'conservative' => 0.95,  // High confidence, minimal reduction
            'balanced' => 0.85,      // validated default (Sebastian et al.)
            'aggressive' => 0.75,    // Higher reduction, more risk
        ],
        
        // K-Means clustering parameters (primary algorithm - 35% of studies)
        'kmeans' => [
            'n_clusters' => env('REDUCTOR_KMEANS_CLUSTERS', 'auto'),
            'max_iterations' => env('REDUCTOR_KMEANS_MAX_ITER', 300),
            'random_state' => 42,
            'silhouette_validation' => true,
        ],
        
        // DBSCAN clustering parameters (density-based - 6% of studies)
        'dbscan' => [
            'eps' => env('REDUCTOR_DBSCAN_EPS', null), // Auto-detect if null
            'min_samples' => env('REDUCTOR_DBSCAN_MIN_SAMPLES', 3),
            'metric' => 'euclidean', // For normalized vectors
            'eps_percentiles' => [50, 60, 70, 80, 90], // For auto-detection
        ],
        
        // Hierarchical clustering parameters (structure-aware - 9% of studies)
        'hierarchical' => [
            'linkage' => 'ward',
            'n_clusters' => env('REDUCTOR_HIERARCHICAL_CLUSTERS', 'auto'),
            'distance_threshold' => 0.15,
        ],
        
        // TF-IDF vectorization parameters
        'vectorization' => [
            '_dimensions' => 128,
            'coverage_dimensions' => 512,
            'min_token_length' => 3,
            'max_vocabulary_size' => 5000,
        ],
        
        // Dimensionality reduction (addresses research gap - only 3% of studies use this)
        'dimensionality_reduction' => [
            'enabled' => env('REDUCTOR_DIMENSIONALITY_REDUCTION', true),
            'method' => env('REDUCTOR_DR_METHOD', 'auto'), // 'pca', 'tsne', 'auto'
            'target_dimensions' => env('REDUCTOR_DR_TARGET_DIMS', 256),
            'variance_threshold' => 0.95, // For PCA: preserve 95% of variance
        ],
    ],

    /*
    |--------------------------------------------------------------------------
    | Git Integration
    |--------------------------------------------------------------------------
    |
    | Configure how Reductor integrates with your Git repository for
    | change impact analysis and historical tracking.
    |
    */
    'git' => [
        'default_base_branch' => env('REDUCTOR_BASE_BRANCH', 'origin/develop'),
        'analyze_changed_files' => env('REDUCTOR_ANALYZE_CHANGES', true),
        'change_impact_weight' => 0.3,
        'proximity_lines' => 5,
    ],

    /*
    |--------------------------------------------------------------------------
    | Database Configuration
    |--------------------------------------------------------------------------
    |
    | Reductor can store historical test data for trend analysis. Configure
    | the database connection to use for storing this data.
    |
    */
    'database' => [
        'connection' => env('REDUCTOR_DB_CONNECTION', config('database.default')),
        'table_prefix' => env('REDUCTOR_TABLE_PREFIX', 'reductor_'),
        'cleanup_after_days' => env('REDUCTOR_CLEANUP_DAYS', 90),
    ],

    /*
    |--------------------------------------------------------------------------
    | Reporting Configuration
    |--------------------------------------------------------------------------
    |
    | Configure how Reductor generates and stores analysis reports.
    | validated metrics based on Sebastian et al. (2024):
    | - Coverage: 29% of studies
    | - Test suite size reduction: 29% of studies
    | - Fault detection effectiveness: 9% of studies
    | - Execution time: 18% of studies
    |
    */
    'reports' => [
        'output_directory' => env('REDUCTOR_REPORTS_DIR', storage_path('reductor/reports')),
        'keep_historical' => env('REDUCTOR_KEEP_REPORTS', true),
        'max_reports' => env('REDUCTOR_MAX_REPORTS', 100),
        'formats' => ['json', 'markdown', 'yaml'],
        
        // validated evaluation metrics
        'metrics' => [
            // Primary metrics (most common in research)
            'coverage_preservation' => true,
            'test_suite_size_reduction' => true,
            
            // Secondary metrics (moderately common)
            'execution_time_reduction' => true,
            'fault_detection_effectiveness' => env('REDUCTOR_FAULT_DETECTION_METRICS', false),
            
            // Advanced metrics (less common but valuable)
            'precision' => true,
            'recall' => true,
            'f_measure' => true,
            'mutation_score' => env('REDUCTOR_MUTATION_TESTING', false),
            
            // Production-specific metrics
            'maintenance_effort_reduction' => true,
            'ci_pipeline_improvement' => true,
        ],
    ],

    /*
    |--------------------------------------------------------------------------
    | Performance Configuration
    |--------------------------------------------------------------------------
    |
    | Settings to optimize Reductor's performance for large test suites.
    |
    */
    'performance' => [
        'chunk_size' => env('REDUCTOR_CHUNK_SIZE', 100),
        'parallel_processing' => env('REDUCTOR_PARALLEL', true),
        'max_workers' => env('REDUCTOR_MAX_WORKERS', 4),
        'cache_ttl' => env('REDUCTOR_CACHE_TTL', 3600),
    ],

    /*
    |--------------------------------------------------------------------------
    | Test Exclusions
    |--------------------------------------------------------------------------
    |
    | Define patterns for tests that should never be considered for reduction.
    | These tests will be excluded from analysis but not from execution.
    |
    */
    'exclusions' => [
        'patterns' => [
            '**/CriticalTest.php',
            '**/External/**',
            '**/Legacy/**',
        ],
        'methods' => [
            'test_external_*',
            'test_legacy_*',
            'test_critical_*',
        ],
        'attributes' => [
            '@critical',
            '@no-reduce',
            '@external',
        ],
    ],

    /*
    |--------------------------------------------------------------------------
    | Notification Configuration
    |--------------------------------------------------------------------------
    |
    | Configure notifications for test reduction analysis results.
    |
    */
    'notifications' => [
        'enabled' => env('REDUCTOR_NOTIFICATIONS', false),
        'channels' => ['mail', 'slack'],
        'recipients' => [
            'mail' => env('REDUCTOR_MAIL_TO'),
            'slack' => env('REDUCTOR_SLACK_WEBHOOK'),
        ],
        'events' => [
            'high_redundancy_found' => true,
            'analysis_complete' => false,
            'reduction_applied' => true,
        ],
    ],
];