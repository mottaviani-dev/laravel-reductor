<?php

namespace Reductor;

use Illuminate\Support\ServiceProvider;
use Reductor\PythonBridge\Contracts\PythonBridgeInterface;
use Reductor\PythonBridge\PythonBridgeService;
use Reductor\Repositories\Contracts\TestRunRepositoryInterface;
use Reductor\Repositories\Contracts\TestCaseRepositoryInterface;
use Reductor\Repositories\TestRunRepository;
use Reductor\Repositories\TestCaseRepository;
use Reductor\Vectorization\SemanticVectorBuilder;
use Reductor\Vectorization\CoverageFingerprintBuilder;
use Reductor\Vectorization\TestMetadataExtractor;
use Reductor\Pipelines\PipelineRunner;
use Reductor\Recommendations\ClusterAnalyzer;
use Reductor\Recommendations\FeedbackService;
use Reductor\Recommendations\RecommendationBuilder;
use Reductor\IO\FileHandler;
use Reductor\Coverage\CoverageIngestor;

class ReductorServiceProvider extends ServiceProvider
{
    /**
     * Register services.
     */
    public function register(): void
    {
        // Merge configuration
        $this->mergeConfigFrom(
            __DIR__ . '/../config/reductor.php',
            'reductor'
        );

        // Register repositories
        $this->app->bind(TestRunRepositoryInterface::class, TestRunRepository::class);
        $this->app->bind(TestCaseRepositoryInterface::class, TestCaseRepository::class);

        // Register Python bridge
        $this->app->singleton(PythonBridgeInterface::class, PythonBridgeService::class);

        // Register vectorization services
        $this->app->singleton(SemanticVectorBuilder::class);
        $this->app->singleton(CoverageFingerprintBuilder::class);
        $this->app->singleton(TestMetadataExtractor::class);

        // Register recommendation services
        $this->app->singleton(ClusterAnalyzer::class);
        $this->app->singleton(FeedbackService::class, function ($app) {
            return new FeedbackService(
                config('reductor.feedback.log_path', storage_path('reductor/feedback.log'))
            );
        });
        $this->app->singleton(RecommendationBuilder::class);

        // Register IO services
        $this->app->singleton(FileHandler::class);
        $this->app->singleton(CoverageIngestor::class);

        // Register pipeline runner
        $this->app->singleton(PipelineRunner::class);
    }

    /**
     * Bootstrap services.
     */
    public function boot(): void
    {
        // Load migrations
        $this->loadMigrationsFrom(__DIR__ . '/../database/migrations');

        // Publish configuration
        $this->publishes([
            __DIR__ . '/../config/reductor.php' => config_path('reductor.php'),
        ], 'reductor-config');

        // Register commands
        if ($this->app->runningInConsole()) {
            $this->commands([
                Commands\ReduceTestsCommand::class,
                Commands\IngestCoverageCommand::class,
            ]);
        }
    }

    /**
     * Get the services provided by the provider.
     *
     * @return array
     */
    public function provides(): array
    {
        return [
            PythonBridgeInterface::class,
            TestRunRepositoryInterface::class,
            TestCaseRepositoryInterface::class,
            SemanticVectorBuilder::class,
            CoverageFingerprintBuilder::class,
            TestMetadataExtractor::class,
            ClusterAnalyzer::class,
            FeedbackService::class,
            RecommendationBuilder::class,
            FileHandler::class,
            CoverageIngestor::class,
            PipelineRunner::class,
        ];
    }
}