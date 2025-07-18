<?php

namespace Reductor\Pipelines;

use Reductor\Models\TestRun;
use Reductor\Support\DTOs\ReductorConfig;
use Reductor\Support\DTOs\ReductorResult;
use Reductor\Support\DTOs\TestVectorDTO;
use Reductor\Support\DTOs\RedundancyFindingDTO;
use Reductor\Support\Exceptions\ReductorException;
use Reductor\Vectorization\SemanticVectorBuilder;
use Reductor\Vectorization\TestMetadataExtractor;
use Reductor\PythonBridge\Contracts\PythonBridgeInterface;
use Reductor\Recommendations\ClusterAnalyzer;
use Reductor\IO\FileHandler;
use Illuminate\Support\Facades\Log;
use Illuminate\Console\OutputStyle;
use Reductor\Cache\QueryCache;

class PipelineRunner
{
    private ?OutputStyle $output = null;
    private array $metrics = [];
    private float $startTime;

    public function __construct(
        private SemanticVectorBuilder $semanticBuilder,
        private TestMetadataExtractor $metadataExtractor,
        private PythonBridgeInterface $pythonBridge,
        private ClusterAnalyzer $clusterAnalyzer,
        private FileHandler $fileHandler
    ) {
    }

    /**
     * Set console output for progress updates
     */
    public function setOutput(?OutputStyle $output): void
    {
        $this->output = $output;
    }

    /**
     * Run the complete redundancy detection pipeline
     */
    public function run(TestRun $testRun, ReductorConfig $config): ReductorResult
    {
        $this->startTime = microtime(true);
        $this->metrics = [];

        try {
            $this->info('Starting redundancy detection pipeline...');

            // Step 1: Load test cases
            $testCases = $this->loadTestCases($testRun);
            
            // Step 2: Get changed files if available
            $changedFiles = $this->getChangedFiles($config);
            
            // Step 3: Build feature vectors
            $vectors = $this->buildFeatureVectors($testCases, $changedFiles);
            
            // Step 4: Execute clustering
            $clusterResult = $this->executeClustering($vectors, $config);
            
            // Step 5: Analyze clusters for redundancy
            $findings = $this->analyzeRedundancy($clusterResult, $vectors);
            
            // Step 6: Save results if configured
            $this->saveResults($findings, $config);
            
            $executionTime = microtime(true) - $this->startTime;
            
            return ReductorResult::success(
                findings: collect($findings),
                clusterResult: $clusterResult,
                metrics: $this->metrics,
                executionTime: $executionTime
            );
            
        } catch (\Exception $e) {
            Log::error('Pipeline execution failed', [
                'error' => $e->getMessage(),
                'trace' => $e->getTraceAsString()
            ]);
            
            $executionTime = microtime(true) - $this->startTime;
            
            return ReductorResult::failure(
                errors: [
                    'message' => $e->getMessage(),
                    'type' => get_class($e)
                ],
                executionTime: $executionTime
            );
        }
    }

    /**
     * Load test cases from test run
     */
    private function loadTestCases(TestRun $testRun): \Illuminate\Support\Collection
    {
        $this->info('Loading test cases...');
        
        // For large test suites, we might need to process in chunks
        // But for ML clustering, we need all data at once
        // Get cached test run stats
        $stats = QueryCache::testRunStats($testRun->id);
        $totalCount = $stats['test_count'];
        
        if ($totalCount === 0) {
            throw new ReductorException('No test cases found in test run');
        }
        
        $this->metrics['total_tests'] = $totalCount;
        $this->metrics['total_coverage_lines'] = $stats['coverage_lines'];
        $this->metrics['unique_files'] = $stats['unique_files'];
        
        // For very large test suites, warn the user
        if ($totalCount > 10000) {
            $this->warn("Large test suite detected ({$totalCount} tests). This may require significant memory.");
        }
        
        // Use cursor for memory-efficient loading
        $testCases = collect();
        $processedCount = 0;
        
        $testRun->testCases()
            ->with(['coverageLines' => function ($query) {
                $query->select('id', 'test_case_id', 'file', 'line');
            }])
            ->chunk(1000, function ($chunk) use (&$testCases, &$processedCount, $totalCount) {
                $testCases = $testCases->concat($chunk);
                $processedCount += $chunk->count();
                
                // Show progress for large test suites
                if ($totalCount > 5000 && $processedCount % 5000 === 0) {
                    $this->comment("Progress: {$processedCount}/{$totalCount} tests loaded...");
                }
            });
        
        $this->comment("Loaded {$testCases->count()} test cases");
        
        return $testCases;
    }

    /**
     * Get changed files from git or configuration
     */
    private function getChangedFiles(ReductorConfig $config): array
    {
        // TODO: Implement git integration to get changed files
        // For now, return empty array
        return [];
    }

    /**
     * Build feature vectors for all test cases
     *
     * @return TestVectorDTO[]
     */
    private function buildFeatureVectors($testCases, array $changedFiles): array
    {
        $this->info('Building feature vectors...');
        
        // Build semantic vectors
        $this->comment('Computing semantic vectors...');
        $semanticVectors = $this->semanticBuilder->buildVectors($testCases);
        
        // Note: Coverage fingerprints are generated in Python to avoid duplication
        // The PHP CoverageFingerprintBuilder exists for standalone usage if needed
        
        // Extract metadata
        $this->comment('Extracting test metadata...');
        $metadata = $this->metadataExtractor->extractBulkMetadata($testCases, $changedFiles);
        
        // Combine into DTOs
        $vectors = [];
        foreach ($testCases as $index => $testCase) {
            // Add source code and coverage to metadata
            $testMetadata = $metadata[$index];
            $testMetadata['source_code'] = $testCase->path . '::' . $testCase->method;
            $testMetadata['path'] = $testCase->path;
            
            // Get coverage lines
            $coverageLines = [];
            foreach ($testCase->coverageLines as $line) {
                $coverageLines[] = $line->file . ':' . $line->line;
            }
            $testMetadata['coverage_lines'] = $coverageLines;
            
            $vectors[] = new TestVectorDTO(
                testId: $testCase->path . '::' . $testCase->method,
                semanticVector: $semanticVectors[$index],
                metadata: $testMetadata
            );
        }
        
        $this->metrics['vectors_generated'] = count($vectors);
        $this->comment("Generated {$this->metrics['vectors_generated']} feature vectors");
        
        return $vectors;
    }


    /**
     * Execute clustering via Python bridge
     */
    private function executeClustering(array $vectors, ReductorConfig $config): \Reductor\Support\DTOs\ClusterResultDTO
    {
        $this->info('Executing clustering algorithm...');
        
        $clusterResult = $this->pythonBridge->cluster($vectors, $config);
        
        $this->metrics['clusters_found'] = $clusterResult->getClusterCount();
        $this->comment("Found {$this->metrics['clusters_found']} clusters");
        
        return $clusterResult;
    }

    /**
     * Analyze clusters for redundancy findings
     *
     * @return RedundancyFindingDTO[]
     */
    private function analyzeRedundancy($clusterResult, array $vectors): array
    {
        $this->info('Analyzing clusters for redundancy...');
        
        $findings = $this->clusterAnalyzer->analyze($clusterResult, $vectors);
        
        $this->metrics['redundancy_findings'] = count($findings);
        $this->metrics['redundant_tests'] = array_sum(
            array_map(fn($f) => $f->getRedundantTestCount(), $findings)
        );
        
        $this->comment("Found {$this->metrics['redundancy_findings']} redundancy findings");
        $this->comment("Total redundant tests: {$this->metrics['redundant_tests']}");
        
        return $findings;
    }

    /**
     * Save results to file if configured
     */
    private function saveResults(array $findings, ReductorConfig $config): void
    {
        if (!empty($config->outputPath)) {
            $this->info('Saving results...');
            
            $outputPath = $this->fileHandler->saveFindings(
                findings: $findings,
                format: $config->outputFormat,
                path: $config->outputPath
            );
            
            $this->comment("Results saved to: {$outputPath}");
        }
    }

    /**
     * Output info message
     */
    private function info(string $message): void
    {
        if ($this->output) {
            $this->output->info($message);
        }
        
        Log::info("[PipelineRunner] {$message}");
    }

    /**
     * Output comment message
     */
    private function comment(string $message): void
    {
        if ($this->output) {
            $this->output->comment($message);
        }
        
        Log::debug("[PipelineRunner] {$message}");
    }

    /**
     * Output warning message
     */
    private function warn(string $message): void
    {
        if ($this->output) {
            $this->output->warn($message);
        }
        
        Log::warning("[PipelineRunner] {$message}");
    }
}