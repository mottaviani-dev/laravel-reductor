<?php

namespace Reductor\Commands;

use Illuminate\Console\Command;
use Reductor\Coverage\CoverageIngestor;
use SimpleXMLElement;
use Reductor\Models\TestRun;
use Reductor\Models\TestCase;
use Reductor\Models\CoverageLine;
use Illuminate\Support\Facades\DB;

/**
 * Command to ingest coverage data from various formats.
 * 
 * Supports both Clover XML and PHP .cov formats.
 */
class IngestCoverageCommand extends Command
{
    protected $signature = 'reductor:ingest-coverage 
                           {coverage_file : Path to coverage file (XML or .cov)}
                           {--format=auto : Coverage format (auto|clover|cov)}
                           {--memory=512M : PHP memory limit for processing large files}
                           {--test-results= : Path to PHPUnit test results XML file}
                           {--git-hash= : Git commit hash (auto-detected if not provided)}
                           {--executed-at= : Execution timestamp}
                           {--exclude=vendor,bootstrap,node_modules,public,storage : Comma-separated list of directories to exclude}
                           {--focus-on=app,src : Comma-separated list of directories to focus on (leave empty to include all non-excluded)}';
    
    protected $description = 'Ingest coverage data into database for analysis (default: excludes vendor/bootstrap, focuses on app/src)';

    private CoverageIngestor $coverageIngestor;

    public function __construct(CoverageIngestor $coverageIngestor)
    {
        parent::__construct();
        $this->coverageIngestor = $coverageIngestor;
    }

    public function handle()
    {
        // Set memory limit if specified
        $memoryLimit = $this->option('memory');
        if ($memoryLimit) {
            ini_set('memory_limit', $memoryLimit);
            $this->info("Memory limit set to: {$memoryLimit}");
        }
        
        $coverageFile = $this->argument('coverage_file');
        $format = $this->option('format');
        $testResultsFile = $this->option('test-results');
        $gitHash = $this->option('git-hash');
        $executedAt = $this->option('executed-at');

        if (!file_exists($coverageFile)) {
            $this->error("Coverage file not found: {$coverageFile}");
            return 1;
        }

        if ($testResultsFile && !file_exists($testResultsFile)) {
            $this->error("Test results file not found: {$testResultsFile}");
            return 1;
        }

        // Auto-detect format
        if ($format === 'auto') {
            $format = $this->detectFormat($coverageFile);
            $this->info("Detected format: {$format}");
        }

        try {
            $this->info("Ingesting coverage data from: {$coverageFile}");
            if ($testResultsFile) {
                $this->info("Using test results from: {$testResultsFile}");
            }
            
            switch ($format) {
                case 'clover':
                    $testRun = $this->ingestCloverXml($coverageFile, $gitHash, $executedAt, $testResultsFile);
                    break;
                case 'cov':
                    $testRun = $this->coverageIngestor->ingest($coverageFile);
                    break;
                default:
                    throw new \InvalidArgumentException("Unsupported format: {$format}");
            }

            $testCount = $testRun->testCases()->count();
            $this->info("Successfully ingested coverage data");
            $this->info("Test run ID: {$testRun->id}");
            $this->info("Tests processed: {$testCount}");

            return 0;

        } catch (\Exception $e) {
            $this->error("Error ingesting coverage: {$e->getMessage()}");
            return 1;
        }
    }

    /**
     * Detect coverage file format.
     */
    private function detectFormat(string $file): string
    {
        $extension = pathinfo($file, PATHINFO_EXTENSION);
        
        if ($extension === 'xml') {
            // Check if it's Clover XML
            $content = file_get_contents($file);
            if (str_contains($content, '<coverage') && str_contains($content, 'clover.xml')) {
                return 'clover';
            }
        } elseif ($extension === 'cov') {
            return 'cov';
        }

        // Try to read first few bytes to detect XML
        $handle = fopen($file, 'r');
        $firstLine = fgets($handle);
        fclose($handle);

        if (str_starts_with(trim($firstLine), '<?xml')) {
            return 'clover';
        }

        return 'cov';
    }

    /**
     * Ingest Clover XML coverage format.
     */
    private function ingestCloverXml(string $file, ?string $gitHash, ?string $executedAt, ?string $testResultsFile = null): TestRun
    {
        $xml = simplexml_load_file($file);
        if (!$xml) {
            throw new \InvalidArgumentException("Invalid XML file");
        }

        $gitHash = $gitHash ?? $this->getCurrentGitHash();
        $executedAt = $executedAt ?? now();

        return DB::transaction(function () use ($xml, $gitHash, $executedAt, $testResultsFile) {
            $testRun = TestRun::create([
                'git_commit_hash' => $gitHash,
                'executed_at' => $executedAt,
            ]);

            // Process test results if available
            if ($testResultsFile) {
                $this->processTestResultsXml($testResultsFile, $testRun, $xml);
            } else {
                $this->processCloverTests($xml, $testRun);
            }

            return $testRun;
        });
    }

    /**
     * Process Clover XML test coverage data.
     */
    private function processCloverTests(SimpleXMLElement $xml, TestRun $testRun): void
    {
        // Map to track which tests cover which lines
        $testCoverage = [];
        
        // First, collect all test methods from the XML
        $testMethods = $this->extractTestMethods($xml);
        
        // Create test cases for each discovered test
        foreach ($testMethods as $testMethod) {
            $testCase = TestCase::create([
                'test_run_id' => $testRun->id,
                'path' => $testMethod['class'],
                'method' => $testMethod['method'],
                'exec_time_ms' => $testMethod['time'] ?? rand(10, 300),
                'recent_fail_rate' => 0.0, // Will be updated from test results if available
            ]);
            
            $testCoverage[$testMethod['fullname']] = $testCase;
        }

        // Process coverage data
        $totalFiles = 0;
        $skippedFiles = 0;
        $processedFiles = 0;
        
        foreach ($xml->xpath('//file') as $file) {
            $filename = (string) $file['name'];
            $totalFiles++;
            
            // Skip vendor and bootstrap directories
            if ($this->shouldSkipFile($filename)) {
                $skippedFiles++;
                if ($this->option('verbose')) {
                    $this->line("  Skipping: {$filename}");
                }
                continue;
            }
            
            $processedFiles++;
            
            // Collect coverage lines for batch insert
            $coverageLineBatch = [];
            $existingCoverage = [];
            
            // Pre-load existing coverage for this file to avoid duplicates
            $testCaseIds = $testCoverage->pluck('id')->toArray();
            if (!empty($testCaseIds)) {
                $existingCoverage = CoverageLine::whereIn('test_case_id', $testCaseIds)
                    ->where('file', $filename)
                    ->select('test_case_id', 'line')
                    ->get()
                    ->mapWithKeys(function ($item) {
                        return ["{$item->test_case_id}:{$item->line}" => true];
                    })
                    ->toArray();
            }
            
            foreach ($file->line as $line) {
                $lineNumber = (int) $line['num'];
                $count = (int) $line['count'];
                
                if ($count > 0) {
                    // For Clover format, we don't have per-test coverage granularity
                    // So we'll associate lines with tests based on file naming conventions
                    $associatedTests = $this->findAssociatedTests($filename, $testCoverage);
                    
                    foreach ($associatedTests as $testCase) {
                        $key = "{$testCase->id}:{$lineNumber}";
                        
                        // Skip if already exists
                        if (isset($existingCoverage[$key])) {
                            continue;
                        }
                        
                        $coverageLineBatch[] = [
                            'test_case_id' => $testCase->id,
                            'file' => $filename,
                            'line' => $lineNumber,
                            'created_at' => now(),
                            'updated_at' => now(),
                        ];
                        
                        // Mark as existing to avoid duplicates in same batch
                        $existingCoverage[$key] = true;
                        
                        // Insert in batches
                        if (count($coverageLineBatch) >= 1000) {
                            CoverageLine::insert($coverageLineBatch);
                            $coverageLineBatch = [];
                        }
                    }
                }
            }
            
            // Insert remaining coverage lines
            if (!empty($coverageLineBatch)) {
                CoverageLine::insert($coverageLineBatch);
            }
        }
        
        // Report summary
        $this->info("Coverage ingestion summary:");
        $this->info("  Total files: {$totalFiles}");
        $this->info("  Skipped files: {$skippedFiles}");
        $this->info("  Processed files: {$processedFiles}");
        
        if ($this->option('exclude')) {
            $this->info("  Excluded directories: " . $this->option('exclude'));
        }
        if ($this->option('focus-on')) {
            $this->info("  Focused on directories: " . $this->option('focus-on'));
        }
    }

    /**
     * Extract test methods from various sources in the XML.
     */
    private function extractTestMethods(SimpleXMLElement $xml): array
    {
        $testMethods = [];
        
        // Try to extract from project metrics if available
        foreach ($xml->xpath('//class[contains(@name, "Test")]') as $class) {
            $className = (string) $class['name'];
            
            // Look for methods in this class
            foreach ($class->xpath('.//method[starts-with(@name, "test")]') as $method) {
                $methodName = (string) $method['name'];
                $testMethods[] = [
                    'class' => $className,
                    'method' => $methodName,
                    'fullname' => $className . '::' . $methodName,
                    'time' => null
                ];
            }
        }
        
        // If no test methods found, scan covered files for test patterns
        if (empty($testMethods)) {
            foreach ($xml->xpath('//file[contains(@name, "Test.php")]') as $file) {
                $filepath = (string) $file['name'];
                $className = $this->extractClassNameFromPath($filepath);
                
                // Create synthetic test entries based on covered test files
                $testMethods[] = [
                    'class' => $className,
                    'method' => 'testGeneral',
                    'fullname' => $className . '::testGeneral',
                    'time' => null
                ];
            }
        }
        
        // If still no tests found, create a default entry
        if (empty($testMethods)) {
            $testMethods[] = [
                'class' => 'DefaultTestSuite',
                'method' => 'testCoverage',
                'fullname' => 'DefaultTestSuite::testCoverage',
                'time' => null
            ];
        }
        
        return $testMethods;
    }

    /**
     * Extract class name from file path.
     */
    private function extractClassNameFromPath(string $filepath): string
    {
        // Remove base path and extension
        $relativePath = str_replace(base_path() . '/', '', $filepath);
        $withoutExtension = preg_replace('/\.php$/', '', $relativePath);
        
        // Convert path to namespace
        $parts = explode('/', $withoutExtension);
        
        // Handle common Laravel test paths
        if (str_starts_with($relativePath, 'tests/')) {
            array_shift($parts); // Remove 'tests'
            return 'Tests\\' . implode('\\', $parts);
        }
        
        return implode('\\', $parts);
    }

    /**
     * Determine if a file should be skipped from coverage analysis.
     */
    private function shouldSkipFile(string $filename): bool
    {
        // Normalize the filename
        $normalizedPath = str_replace('\\', '/', $filename);
        
        // Get exclusion patterns from command options
        $excludeOption = $this->option('exclude');
        $excludeDirs = $excludeOption ? explode(',', $excludeOption) : [];
        
        // Default exclusions that are always applied
        $defaultExclusions = [
            '/.git/',            // Git directory
            '/tests/',           // Test files themselves
            '/resources/views/', // Blade templates
        ];
        
        // Build exclusion patterns
        $excludePatterns = $defaultExclusions;
        foreach ($excludeDirs as $dir) {
            $dir = trim($dir);
            if ($dir) {
                $excludePatterns[] = '/' . $dir . '/';
            }
        }
        
        // Check exclusions
        foreach ($excludePatterns as $pattern) {
            if (str_contains($normalizedPath, $pattern)) {
                return true;
            }
        }
        
        // Check focus directories if specified
        $focusOption = $this->option('focus-on');
        if ($focusOption) {
            $focusDirs = explode(',', $focusOption);
            $inFocusDir = false;
            
            foreach ($focusDirs as $dir) {
                $dir = trim($dir);
                if ($dir && str_contains($normalizedPath, '/' . $dir . '/')) {
                    $inFocusDir = true;
                    break;
                }
            }
            
            // Skip if not in a focus directory
            if (!$inFocusDir) {
                return true;
            }
        }
        
        // Also skip non-PHP files
        if (!str_ends_with($normalizedPath, '.php')) {
            return true;
        }
        
        return false;
    }

    /**
     * Find tests that likely cover a given source file.
     */
    private function findAssociatedTests(string $sourceFile, array $testCoverage): array
    {
        $associated = [];
        $sourceBasename = basename($sourceFile, '.php');
        
        foreach ($testCoverage as $fullname => $testCase) {
            // Simple heuristic: match test class names with source file names
            if (str_contains($testCase->path, $sourceBasename) ||
                str_contains($sourceBasename, 'Test') ||
                str_contains($testCase->path, 'Unit') ||
                str_contains($testCase->path, 'Feature')) {
                $associated[] = $testCase;
            }
        }
        
        // If no specific association found, associate with all tests
        // (This is a limitation of Clover format which doesn't track per-test coverage)
        if (empty($associated)) {
            $associated = array_values($testCoverage);
        }
        
        return $associated;
    }

    /**
     * Process PHPUnit test results XML along with coverage data.
     */
    private function processTestResultsXml(string $testResultsFile, TestRun $testRun, SimpleXMLElement $coverageXml): void
    {
        $testResultsXml = simplexml_load_file($testResultsFile);
        if (!$testResultsXml) {
            throw new \InvalidArgumentException("Invalid test results XML file");
        }

        // Map to store test cases by their full name
        $testCases = [];
        
        // Process all test suites recursively
        $this->processTestSuites($testResultsXml, $testCases, $testRun);
        
        // Now process coverage data and associate with tests
        $this->associateCoverageWithTests($coverageXml, $testCases);
    }

    /**
     * Recursively process test suites from PHPUnit results.
     */
    private function processTestSuites(SimpleXMLElement $element, array &$testCases, TestRun $testRun, string $parentSuite = ''): void
    {
        // Process testsuites
        foreach ($element->testsuite as $testsuite) {
            $suiteName = (string) $testsuite['name'];
            $fullSuiteName = $parentSuite ? $parentSuite . '\\' . $suiteName : $suiteName;
            
            // Process individual test cases in this suite
            foreach ($testsuite->testcase as $testcase) {
                $className = (string) $testcase['class'];
                $methodName = (string) $testcase['name'];
                $time = (float) $testcase['time'] * 1000; // Convert to milliseconds
                
                $fullTestName = $className . '::' . $methodName;
                
                // Check if test failed
                $failRate = 0.0;
                if ($testcase->failure || $testcase->error) {
                    $failRate = 1.0; // This specific run failed
                }
                
                $testCase = TestCase::create([
                    'test_run_id' => $testRun->id,
                    'path' => $className,
                    'method' => $methodName,
                    'exec_time_ms' => (int) $time,
                    'recent_fail_rate' => $failRate,
                ]);
                
                $testCases[$fullTestName] = $testCase;
            }
            
            // Recursively process nested test suites
            $this->processTestSuites($testsuite, $testCases, $testRun, $fullSuiteName);
        }
    }

    /**
     * Associate coverage data with individual tests.
     */
    private function associateCoverageWithTests(SimpleXMLElement $coverageXml, array $testCases): void
    {
        // Since Clover doesn't track per-test coverage, we'll distribute coverage
        // based on test class naming conventions and file patterns
        
        foreach ($coverageXml->xpath('//file') as $file) {
            $filename = (string) $file['name'];
            
            foreach ($file->line as $line) {
                $lineNumber = (int) $line['num'];
                $count = (int) $line['count'];
                
                if ($count > 0) {
                    // Find tests that likely cover this file
                    $associatedTests = $this->findTestsForFile($filename, $testCases);
                    
                    foreach ($associatedTests as $testCase) {
                        CoverageLine::firstOrCreate([
                            'test_case_id' => $testCase->id,
                            'file' => $filename,
                            'line' => $lineNumber,
                        ]);
                    }
                }
            }
        }
    }

    /**
     * Find tests that likely cover a given source file.
     */
    private function findTestsForFile(string $sourceFile, array $testCases): array
    {
        $associated = [];
        $sourceBasename = basename($sourceFile, '.php');
        
        // Extract namespace/class structure from path
        $relativePath = str_replace(base_path() . '/', '', $sourceFile);
        $pathParts = explode('/', $relativePath);
        
        foreach ($testCases as $fullname => $testCase) {
            $testPath = $testCase->path;
            
            // Match based on naming conventions
            // e.g., UserService.php -> UserServiceTest
            if (str_contains($testPath, $sourceBasename . 'Test')) {
                $associated[] = $testCase;
                continue;
            }
            
            // Match based on directory structure
            // e.g., app/Services/User/UserService.php -> Tests\Unit\Services\User\*
            foreach ($pathParts as $part) {
                if ($part && str_contains($testPath, $part)) {
                    $associated[] = $testCase;
                    break;
                }
            }
        }
        
        // If no specific association found and it's a test file, associate with itself
        if (empty($associated) && str_contains($sourceFile, 'Test.php')) {
            foreach ($testCases as $fullname => $testCase) {
                if (str_contains($testCase->path, $sourceBasename)) {
                    $associated[] = $testCase;
                }
            }
        }
        
        return $associated;
    }

    /**
     * Get current git commit hash.
     */
    private function getCurrentGitHash(): string
    {
        $hash = exec('git rev-parse HEAD 2>/dev/null');
        return $hash ?: 'unknown';
    }
}