<?php

namespace Reductor\Coverage;

use Reductor\Models\TestRun;
use Reductor\Models\TestCase;
use Reductor\Models\CoverageLine;
use Reductor\Support\Exceptions\ReductorException;
use Reductor\Coverage\Parsers\CovParser;
use Illuminate\Support\Facades\DB;
// use Illuminate\Support\Facades\Log;
use Throwable;
use Carbon\Carbon;

class CoverageIngestor
{
    private const BATCH_SIZE = 100;

    /**
     * Ingest coverage data from file
     */
    public function ingest(string $filePath): TestRun
    {
        if (!file_exists($filePath)) {
            throw new ReductorException("Coverage file not found: {$filePath}");
        }

        // Create test run first
        $testRun = $this->createTestRun($filePath);

        // Import test cases and coverage using streaming approach
        $this->importTestCasesStreaming($testRun, $filePath);

        return $testRun;
    }

    /**
     * Parse coverage by format
     */
    private function parseCoverageByFormat(string $filePath): array
    {
        $extension = pathinfo($filePath, PATHINFO_EXTENSION);
        
        if ($extension === 'cov') {
            // Use CovParser for .cov files
            $parser = new CovParser();
            return $parser->parse($filePath);
        } else {
            // Use text-based parser for other formats
            $content = file_get_contents($filePath);
            if ($content === false) {
                throw new ReductorException("Failed to read coverage file: {$filePath}");
            }
            return $this->parseCoverageFile($content);
        }
    }

    /**
     * Parse coverage file content (text format)
     */
    private function parseCoverageFile(string $content): array
    {
        $lines = explode("\n", $content);
        $coverageData = [];
        $currentTest = null;
        $currentCoverage = [];

        foreach ($lines as $line) {
            $line = trim($line);
            
            if (empty($line)) {
                continue;
            }

            // Check if this is a test header
            if (preg_match('/^TEST: (.+)$/', $line, $matches)) {
                // Save previous test data
                if ($currentTest !== null && !empty($currentCoverage)) {
                    $coverageData[$currentTest] = $currentCoverage;
                }
                
                $currentTest = $matches[1];
                $currentCoverage = [];
                continue;
            }

            // Parse coverage line (format: file:line)
            if ($currentTest !== null && strpos($line, ':') !== false) {
                [$file, $lineNumber] = explode(':', $line, 2);
                $currentCoverage[] = [
                    'file' => trim($file),
                    'line' => (int) trim($lineNumber),
                ];
            }
        }

        // Save last test
        if ($currentTest !== null && !empty($currentCoverage)) {
            $coverageData[$currentTest] = $currentCoverage;
        }

        if (empty($coverageData)) {
            throw new ReductorException('No coverage data found in file');
        }

        return $coverageData;
    }

    /**
     * Create test run record
     */
    private function createTestRun(string $filePath): TestRun
    {
        // Try to get git commit hash
        $gitHash = 'manual-import';
        try {
            $gitHashOutput = shell_exec('git rev-parse HEAD 2>/dev/null');
            if ($gitHashOutput) {
                $gitHash = trim($gitHashOutput);
            }
        } catch (Throwable $e) {
            // Ignore git errors
        }

        return TestRun::create([
            'git_commit_hash' => $gitHash,
            'executed_at' => Carbon::now(),
            'created_at' => Carbon::now(),
            'updated_at' => Carbon::now(),
        ]);
    }

    /**
     * Import test cases and coverage data
     */
    private function importTestCases(TestRun $testRun, array $coverageData): void
    {
        $totalTests = count($coverageData);
        $totalCoverageLines = 0;
        
        // Process test cases in smaller chunks to avoid memory issues
        $chunks = array_chunk($coverageData, self::BATCH_SIZE, true);
        
        foreach ($chunks as $chunkIndex => $chunk) {
            DB::transaction(function () use ($testRun, $chunk, &$totalCoverageLines, $chunkIndex, $totalTests) {
                $testCaseBatch = [];
                $testCaseIdMap = [];
                
                // Prepare test cases for this chunk
                foreach ($chunk as $testIdentifier => $coverage) {
                    [$path, $method] = $this->parseTestIdentifier($testIdentifier);
                    
                    $testCaseBatch[] = [
                        'test_run_id' => $testRun->id,
                        'path' => $path,
                        'method' => $method,
                        'exec_time_ms' => null,
                        'recent_fail_rate' => 0.0,
                        'created_at' => Carbon::now(),
                        'updated_at' => Carbon::now(),
                    ];
                }
                
                // Insert test cases for this chunk
                if (!empty($testCaseBatch)) {
                    DB::table('test_cases')->insert($testCaseBatch);
                }

                // Get inserted test case IDs for this chunk only
                $pathsAndMethods = [];
                foreach ($testCaseBatch as $testCase) {
                    $pathsAndMethods[] = ['path' => $testCase['path'], 'method' => $testCase['method']];
                }
                
                $insertedTestCases = TestCase::where('test_run_id', $testRun->id)
                    ->where(function ($query) use ($pathsAndMethods) {
                        foreach ($pathsAndMethods as $pm) {
                            $query->orWhere(function ($subQuery) use ($pm) {
                                $subQuery->where('path', $pm['path'])
                                         ->where('method', $pm['method']);
                            });
                        }
                    })
                    ->get(['id', 'path', 'method']);

                // Map test identifiers to IDs for this chunk
                foreach ($insertedTestCases as $testCase) {
                    $identifier = "{$testCase->path}::{$testCase->method}";
                    $testCaseIdMap[$identifier] = $testCase->id;
                }

                // Process coverage lines for this chunk in smaller batches
                $coverageLineBatch = [];
                foreach ($chunk as $testIdentifier => $coverage) {
                    $testCaseId = $testCaseIdMap[$testIdentifier] ?? null;
                    
                    if ($testCaseId === null) {
                        continue;
                    }

                    foreach ($coverage as $line) {
                        $coverageLineBatch[] = [
                            'test_case_id' => $testCaseId,
                            'file' => $line['file'],
                            'line' => $line['line'],
                            'created_at' => Carbon::now(),
                            'updated_at' => Carbon::now(),
                        ];

                        // Insert in smaller batches to avoid memory issues
                        if (count($coverageLineBatch) >= 50) {
                            DB::table('coverage_lines')->insert($coverageLineBatch);
                            $totalCoverageLines += count($coverageLineBatch);
                            $coverageLineBatch = [];
                        }
                    }
                }

                // Insert remaining coverage lines for this chunk
                if (!empty($coverageLineBatch)) {
                    DB::table('coverage_lines')->insert($coverageLineBatch);
                    $totalCoverageLines += count($coverageLineBatch);
                }
                
                // Free memory after each chunk
                unset($testCaseBatch, $testCaseIdMap, $insertedTestCases, $coverageLineBatch, $pathsAndMethods);
            });
            
            // Log progress for large imports
            if ($totalTests > 100 && $chunkIndex % 10 === 0) {
                $processedTests = ($chunkIndex + 1) * self::BATCH_SIZE;
                $progress = round(($processedTests / $totalTests) * 100, 1);
                echo "Processing chunk " . ($chunkIndex + 1) . "/" . count($chunks) . " ({$progress}%)\n";
            }
            
            // Force garbage collection after each chunk
            gc_collect_cycles();
        }
    }

    /**
     * Import test cases and coverage using streaming approach
     */
    private function importTestCasesStreaming(TestRun $testRun, string $filePath): void
    {
        $extension = pathinfo($filePath, PATHINFO_EXTENSION);
        
        if ($extension === 'cov') {
            // For .cov files, we need to process them in streaming mode
            $this->importCovFileStreaming($testRun, $filePath);
        } else {
            // For other formats, fall back to original method
            $coverageData = $this->parseCoverageByFormat($filePath);
            $this->importTestCases($testRun, $coverageData);
        }
    }
    
    /**
     * Import .cov file using streaming approach
     */
    private function importCovFileStreaming(TestRun $testRun, string $filePath): void
    {
        try {
            // For very large files, we need to process the serialized data in chunks
            // First, let's check the file size
            $fileSize = filesize($filePath);
            $fileSizeMB = round($fileSize / 1024 / 1024, 2);
            
            echo "Coverage file size: {$fileSizeMB} MB\n";
            
            // Load coverage object
            $coverage = require $filePath;
            
            if (!$coverage instanceof \SebastianBergmann\CodeCoverage\CodeCoverage) {
                throw new ReductorException("Invalid coverage file format. Expected CodeCoverage object.");
            }
            
            // Get test data from coverage
            $tests = $coverage->getTests();
            if (empty($tests)) {
                throw new ReductorException("No test data found in coverage file.");
            }
            
            // Get line coverage data
            $rawData = $coverage->getData(true);
            $lineCoverage = $rawData->lineCoverage();
            
            $totalTests = count($tests);
            $totalCoverageLines = 0;
            
            echo "Found {$totalTests} tests in coverage data\n";
            
            // Process tests in batches
            $testBatches = array_chunk($tests, 50, true);
            
            foreach ($testBatches as $batchIndex => $testBatch) {
                echo "Processing test batch " . ($batchIndex + 1) . "/" . count($testBatches) . "\n";
                
                DB::transaction(function () use ($testRun, $testBatch, $lineCoverage, &$totalCoverageLines) {
                    $testCaseMap = [];
                    
                    // Create test cases
                    foreach ($testBatch as $testId => $testInfo) {
                        // Parse test identifier
                        [$path, $method] = $this->parseTestIdentifier($testId);
                        
                        $testCase = TestCase::create([
                            'test_run_id' => $testRun->id,
                            'path' => $path,
                            'method' => $method,
                            'exec_time_ms' => isset($testInfo['time']) ? (int)($testInfo['time'] * 1000) : null,
                            'recent_fail_rate' => 0.0,
                            'created_at' => Carbon::now(),
                            'updated_at' => Carbon::now(),
                        ]);
                        
                        $testCaseMap[$testId] = $testCase->id;
                    }
                    
                    // Now process coverage lines for these tests
                    foreach ($lineCoverage as $file => $lines) {
                        $coverageLineBatch = [];
                        
                        foreach ($lines as $line => $testIds) {
                            if ($testIds === null || empty($testIds)) {
                                continue;
                            }
                            
                            // For each test that covers this line
                            foreach ($testIds as $testId) {
                                if (isset($testCaseMap[$testId])) {
                                    $coverageLineBatch[] = [
                                        'test_case_id' => $testCaseMap[$testId],
                                        'file' => $file,
                                        'line' => $line,
                                        'created_at' => Carbon::now(),
                                        'updated_at' => Carbon::now(),
                                    ];
                                    
                                    // Insert in batches
                                    if (count($coverageLineBatch) >= 100) {
                                        DB::table('coverage_lines')->insert($coverageLineBatch);
                                        $totalCoverageLines += count($coverageLineBatch);
                                        $coverageLineBatch = [];
                                    }
                                }
                            }
                        }
                        
                        // Insert remaining coverage lines
                        if (!empty($coverageLineBatch)) {
                            DB::table('coverage_lines')->insert($coverageLineBatch);
                            $totalCoverageLines += count($coverageLineBatch);
                        }
                    }
                });
                
                // Force garbage collection after each batch
                gc_collect_cycles();
            }
            
            echo "Completed processing: {$totalTests} tests, {$totalCoverageLines} coverage lines\n";
            
        } catch (\Exception $e) {
            throw new ReductorException("Failed to process .cov file: " . $e->getMessage());
        }
    }
    
    /**
     * Parse test identifier into path and method
     */
    private function parseTestIdentifier(string $identifier): array
    {
        // For the new XDebug coverage format, identifiers look like:
        // "SampleApp\Tests\CalculatorTest::test_addition"
        
        if (strpos($identifier, '::') !== false) {
            [$className, $method] = explode('::', $identifier, 2);
            
            // Convert namespace to file path (this is a simplification)
            // In reality, you'd need to look up the actual file path
            // For now, store the class name as the path
            return [$className, $method];
        }

        // Fallback: use full identifier as method
        return ['Unknown', $identifier];
    }
}