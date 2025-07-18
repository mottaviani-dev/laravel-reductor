<?php

namespace Reductor\Commands;

use Reductor\Pipelines\PipelineRunner;
use Reductor\Models\TestRun;
use Reductor\Support\DTOs\ReductorConfig;
use Reductor\Coverage\CoverageIngestor;
use Reductor\IO\FileHandler;
use Reductor\Recommendations\RecommendationBuilder;
use Reductor\PythonBridge\Contracts\PythonBridgeInterface;
use Symfony\Component\Console\Input\InputArgument;

class ReduceTestsCommand extends BaseReductorCommand
{
    protected $signature = 'tests:reduce 
                           {test-run-id? : Test run ID to analyze}
                           {--coverage-file= : Path to coverage file}
                           {--ingest : Ingest coverage data first}';

    protected $description = 'Detect and report redundant tests using ML clustering analysis';

    public function __construct(
        private PipelineRunner $pipelineRunner,
        private CoverageIngestor $coverageIngestor,
        private FileHandler $fileHandler,
        private RecommendationBuilder $recommendationBuilder,
        private PythonBridgeInterface $pythonBridge
    ) {
        parent::__construct();
    }

    protected function configure(): void
    {
        parent::configure();
        $this->configureCommonOptions();
        
        // Add specific options
        $this->addOption('interactive', 'i', \Symfony\Component\Console\Input\InputOption::VALUE_NONE, 'Launch interactive review');
        $this->addOption('quick', null, \Symfony\Component\Console\Input\InputOption::VALUE_NONE, 'Use cached data if available');
        $this->addOption('validate', null, \Symfony\Component\Console\Input\InputOption::VALUE_NONE, 'Run validation benchmarks');
        $this->addOption('research-metrics', null, \Symfony\Component\Console\Input\InputOption::VALUE_NONE, 'Generate research metrics');
        
        // Advanced options
        $this->addOption('metrics', null, \Symfony\Component\Console\Input\InputOption::VALUE_REQUIRED, 'Metrics to calculate (all,precision,recall,f1,mutation)', 'all');
        $this->addOption('dr-method', null, \Symfony\Component\Console\Input\InputOption::VALUE_REQUIRED, 'Dimensionality reduction method (pca,tsne,umap)', 'pca');
        $this->addOption('dr-dimensions', null, \Symfony\Component\Console\Input\InputOption::VALUE_REQUIRED, 'Target dimensions for reduction', '128');
        $this->addOption('export', null, \Symfony\Component\Console\Input\InputOption::VALUE_REQUIRED, 'Export formats (comma-separated: sarif,junit,html,json)', null);
    }

    public function handle(): int
    {
        try {
            $this->displayHeader();
            
            // Validate environment
            if (!$this->validateEnvironment()) {
                return $this->displayError('Environment validation failed');
            }
            
            // Build configuration
            $config = $this->buildConfig();
            $this->validateCommonArguments();
            
            // Get or create test run
            $testRun = $this->getTestRun();
            
            if (!$testRun) {
                return $this->displayError('No test run found. Please provide a test-run-id or use --ingest with --coverage-file');
            }
            
            // Set output for progress
            $this->pipelineRunner->setOutput($this->output);
            
            // Run the pipeline
            $this->info('Starting redundancy detection pipeline...');
            $startTime = microtime(true);
            
            $result = $this->pipelineRunner->run($testRun, $config);
            
            if (!$result->success) {
                return $this->displayError('Pipeline failed: ' . ($result->errors['message'] ?? 'Unknown error'));
            }
            
            // Build recommendations
            $this->info('Building recommendations...');
            $recommendations = $this->recommendationBuilder->buildFromFindings($result->findings->toArray());
            
            // Save results
            $outputPath = $this->saveResults($result, $recommendations, $config);
            
            // Display summary
            $this->displaySummary($result, $outputPath);
            
            // Run validation if requested
            if ($this->option('validate')) {
                $this->runValidation($result);
            }
            
            // Launch interactive review if requested
            if ($this->option('interactive')) {
                $this->launchInteractiveReview($outputPath);
            }
            
            $duration = microtime(true) - $startTime;
            $this->displaySuccess("Analysis completed in " . $this->formatDuration($duration));
            
            return 0;
            
        } catch (\Exception $e) {
            return $this->displayError('Command failed: ' . $e->getMessage(), $e);
        }
    }

    private function displayHeader(): void
    {
        $this->info('Reductor Test Redundancy Detection');
        $this->info('==================================');
        $this->comment('Using ML-powered clustering analysis');
        $this->newLine();
    }

    private function validateEnvironment(): bool
    {
        $this->comment('Validating environment...');
        
        $validation = $this->pythonBridge->validateEnvironment();
        
        if (!empty($validation['errors'])) {
            foreach ($validation['errors'] as $error) {
                $this->error("✗ {$error}");
            }
            return false;
        }
        
        $this->info('✓ Python environment validated');
        $this->info('✓ ML package found');
        
        return true;
    }

    private function getTestRun(): ?TestRun
    {
        // Check if test run ID provided
        if ($this->argument('test-run-id')) {
            $testRunId = $this->argument('test-run-id');
            
            // Validate test run ID is numeric
            if (!is_numeric($testRunId)) {
                $this->error('Invalid test-run-id: must be a numeric value');
                return null;
            }
            
            $testRun = TestRun::find($testRunId);
            if (!$testRun) {
                $this->error('Test run not found with ID: ' . $testRunId);
                return null;
            }
            return $testRun;
        }
        
        // Check if we should ingest coverage
        if ($this->option('ingest') && $this->option('coverage-file')) {
            return $this->ingestCoverage();
        }
        
        // Try to find most recent test run
        $testRun = TestRun::latest()->first();
        if ($testRun) {
            $this->comment("Using most recent test run (ID: {$testRun->id})");
            return $testRun;
        }
        
        return null;
    }

    private function ingestCoverage(): ?TestRun
    {
        $coverageFile = $this->option('coverage-file');
        
        if (!file_exists($coverageFile)) {
            $this->error("Coverage file not found: {$coverageFile}");
            return null;
        }
        
        $this->info('Ingesting coverage data...');
        
        try {
            $testRun = $this->coverageIngestor->ingest($coverageFile);
            $this->info("✓ Ingested coverage data (Test Run ID: {$testRun->id})");
            return $testRun;
        } catch (\Exception $e) {
            $this->error('Failed to ingest coverage: ' . $e->getMessage());
            return null;
        }
    }

    private function saveResults($result, array $recommendations, ReductorConfig $config): string
    {
        $outputPath = $this->getOutputPath('redundancy-report');
        
        // Save findings
        $this->fileHandler->saveFindings(
            $result->findings->toArray(),
            $config->outputFormat,
            $outputPath
        );
        
        // Save recommendations separately if detailed
        if ($this->option('debug')) {
            $recPath = str_replace('.' . $config->outputFormat, '-recommendations.' . $config->outputFormat, $outputPath);
            file_put_contents(
                $recPath,
                json_encode($recommendations, JSON_PRETTY_PRINT)
            );
        }
        
        return $outputPath;
    }

    private function displaySummary($result, string $outputPath): void
    {
        $this->newLine();
        $this->info('Analysis Summary');
        $this->info('================');
        
        $totalTests = $result->metrics['total_tests'] ?? $result->clusterResult->getTestCount();
        $redundantTests = $result->getTotalRedundantTests();
        $reductionPercentage = $totalTests > 0 ? round(($redundantTests / $totalTests) * 100, 2) : 0;
        
        $this->table(
            ['Metric', 'Value'],
            [
                ['Total Tests Analyzed', $totalTests],
                ['Tests in Clusters', $result->clusterResult->getTestCount()],
                ['Clusters Found', $result->clusterResult->getClusterCount()],
                ['Redundancy Findings', $result->findings->count()],
                ['Total Redundant Tests', $redundantTests],
                ['Reduction Percentage', $reductionPercentage . '%'],
                ['High Priority Findings', $result->getHighPriorityFindings()->count()],
                ['Execution Time', $this->formatDuration($result->executionTime)],
            ]
        );
        
        $this->newLine();
        $this->info("Results saved to: {$outputPath}");
    }

    private function runValidation($result): void
    {
        $this->newLine();
        $this->info('Running validation benchmarks...');
        
        // Extract validation results if available
        if (!isset($result['validation_summary'])) {
            $this->warn('No validation data available in results.');
            return;
        }
        
        $summary = $result['validation_summary'];
        
        // Display validation summary
        $this->table(
            ['Metric', 'Value'],
            [
                ['Total Clusters', $summary['total_clusters'] ?? 0],
                ['Safe Clusters', $summary['safe_clusters'] ?? 0],
                ['Unsafe Clusters', $summary['unsafe_clusters'] ?? 0],
                ['Total Conflicts', $summary['total_conflicts'] ?? 0],
                ['Safety Rate', sprintf('%.1f%%', $summary['safety_rate'] ?? 100)],
            ]
        );
        
        // Show conflict types if any
        if (!empty($summary['conflict_types'])) {
            $this->newLine();
            $this->warn('Conflict Types Found:');
            foreach ($summary['conflict_types'] as $type => $count) {
                $this->line("  - {$type}: {$count} occurrences");
            }
        }
        
        // Check if unsafe clusters were split
        if (isset($result['clusters_split']) && $result['clusters_split'] > 0) {
            $this->newLine();
            $this->info("✓ {$result['clusters_split']} unsafe clusters were automatically split");
        }
    }

    private function launchInteractiveReview(string $outputPath): void
    {
        $this->newLine();
        $this->info('Interactive review requested.');
        
        // Since the review command doesn't exist yet, provide manual instructions
        $this->line('Review the results file at: ' . $outputPath);
        $this->newLine();
        
        $format = pathinfo($outputPath, PATHINFO_EXTENSION);
        
        if ($format === 'html') {
            $this->comment('Open the HTML file in your browser to interactively review the results.');
            
            // Attempt to open in default browser on different platforms
            $openCommand = match (PHP_OS_FAMILY) {
                'Darwin' => 'open',
                'Windows' => 'start',
                'Linux' => 'xdg-open',
                default => null
            };
            
            if ($openCommand && $this->confirm('Would you like to open the results in your browser?')) {
                exec("{$openCommand} " . escapeshellarg($outputPath));
            }
        } else {
            $this->comment("You can review the {$format} file using your preferred editor or viewer.");
        }
        
        $this->newLine();
        $this->info('To implement changes based on the review:');
        $this->line('1. Identify test clusters marked as HIGH redundancy');
        $this->line('2. Review the semantic validation warnings');
        $this->line('3. Manually merge or refactor redundant tests');
        $this->line('4. Re-run coverage analysis to verify no regression');
    }
}