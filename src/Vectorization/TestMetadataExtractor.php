<?php

namespace Reductor\Vectorization;

use Reductor\Models\TestCase;
use Reductor\Models\CoverageLine;
use Illuminate\Support\Collection;
use Illuminate\Support\Facades\DB;
use Reductor\Cache\QueryCache;

class TestMetadataExtractor
{
    /**
     * Extract metadata for a test case
     */
    public function extractMetadata(TestCase $testCase, array $changedFiles = [], ?array $preloadedCoverage = null): array
    {
        return [
            'test_id' => $testCase->id,
            'test_identifier' => "{$testCase->path}::{$testCase->method}",
            'normalized_name' => $this->normalizeTestName($testCase),
            'is_parameterized' => $this->isParameterized($testCase),
            'execution_time_ms' => $testCase->exec_time_ms ?? 0.0,
            'recent_fail_rate' => $testCase->recent_fail_rate ?? 0.0,
            'lines_covered' => $testCase->lines_covered ?? 0,
            'change_impact' => $this->calculateChangeImpact($testCase, $changedFiles, $preloadedCoverage),
            'test_type' => $this->detectTestType($testCase),
            'complexity_score' => $this->calculateComplexityScore($testCase),
        ];
    }

    /**
     * Extract metadata for multiple test cases with optimized queries
     *
     * @param Collection<TestCase> $testCases
     */
    public function extractBulkMetadata(Collection $testCases, array $changedFiles = []): array
    {
        // Pre-load all coverage data for all test cases in one query
        $testCaseIds = $testCases->pluck('id')->toArray();
        
        $coverageData = [];
        if (!empty($testCaseIds)) {
            $coverageData = $this->preloadCoverageData($testCaseIds);
        }
        
        return $testCases->map(function (TestCase $testCase) use ($changedFiles, $coverageData) {
            $preloadedCoverage = $coverageData[$testCase->id] ?? [];
            return $this->extractMetadata($testCase, $changedFiles, $preloadedCoverage);
        })->toArray();
    }

    /**
     * Preload coverage data for multiple test cases
     */
    private function preloadCoverageData(array $testCaseIds): array
    {
        $coverageData = [];
        
        // Load all coverage lines for all test cases in chunks
        CoverageLine::whereIn('test_case_id', $testCaseIds)
            ->select('test_case_id', 'file', 'line')
            ->orderBy('test_case_id')
            ->chunk(10000, function ($coverageLines) use (&$coverageData) {
                foreach ($coverageLines as $line) {
                    if (!isset($coverageData[$line->test_case_id])) {
                        $coverageData[$line->test_case_id] = [];
                    }
                    $coverageData[$line->test_case_id][] = [
                        'file' => $line->file,
                        'line' => $line->line
                    ];
                }
            });
            
        return $coverageData;
    }

    /**
     * Normalize test name by removing parameter variations
     */
    private function normalizeTestName(TestCase $testCase): string
    {
        $testIdentifier = "{$testCase->path}::{$testCase->method}";
        
        // Remove data provider suffixes
        $normalized = preg_replace('/ with data set ["\']?[^"\']*["\']?$/', '', $testIdentifier);
        $normalized = preg_replace('/ with data set #\d+$/', '', $normalized);
        
        // Remove parameter variations from test name
        $normalized = preg_replace('/\s*\([^)]*\)\s*$/', '', $normalized);
        
        return $normalized;
    }

    /**
     * Check if test is parameterized
     */
    private function isParameterized(TestCase $testCase): bool
    {
        $testIdentifier = "{$testCase->path}::{$testCase->method}";
        $normalized = $this->normalizeTestName($testCase);
        
        return $testIdentifier !== $normalized;
    }

    /**
     * Calculate change impact for the test
     */
    private function calculateChangeImpact(TestCase $testCase, array $changedFiles, ?array $preloadedCoverage = null): float
    {
        if (empty($changedFiles)) {
            return 0.0;
        }

        $impactedLines = 0;
        $nearbyLines = 0;
        $totalLines = 0;

        // Use preloaded coverage if available, otherwise query
        if ($preloadedCoverage !== null) {
            foreach ($preloadedCoverage as $line) {
                $totalLines++;
                
                if (isset($changedFiles[$line['file']])) {
                    // Direct hit on changed line
                    if (in_array($line['line'], $changedFiles[$line['file']])) {
                        $impactedLines++;
                    } else {
                        // Check if line is near a change (within 5 lines)
                        foreach ($changedFiles[$line['file']] as $changedLine) {
                            if (abs($line['line'] - $changedLine) <= 5) {
                                $nearbyLines++;
                                break;
                            }
                        }
                    }
                }
            }
        } else {
            // Fallback to chunked query if no preloaded data
            $testCase->coverageLines()
                ->select('file', 'line')
                ->chunk(1000, function ($coverageLines) use ($changedFiles, &$impactedLines, &$nearbyLines, &$totalLines) {
                    foreach ($coverageLines as $line) {
                        $totalLines++;
                        
                        if (isset($changedFiles[$line->file])) {
                            // Direct hit on changed line
                            if (in_array($line->line, $changedFiles[$line->file])) {
                                $impactedLines++;
                            } else {
                                // Check if line is near a change (within 5 lines)
                                foreach ($changedFiles[$line->file] as $changedLine) {
                                    if (abs($line->line - $changedLine) <= 5) {
                                        $nearbyLines++;
                                        break;
                                    }
                                }
                            }
                        }
                    }
                });
        }

        if ($totalLines === 0) {
            return 0.0;
        }

        // Calculate impact score with nearby lines having partial weight
        $directImpact = $impactedLines / $totalLines;
        $nearbyImpact = $nearbyLines / $totalLines * 0.3;
        
        return min(1.0, $directImpact + $nearbyImpact);
    }

    /**
     * Detect test type based on name and content
     */
    private function detectTestType(TestCase $testCase): string
    {
        $method = strtolower($testCase->method);
        $path = strtolower($testCase->path);

        // Integration test patterns
        if (strpos($path, 'integration') !== false || 
            strpos($path, 'feature') !== false ||
            strpos($method, 'integration') !== false) {
            return 'integration';
        }

        // Unit test patterns
        if (strpos($path, 'unit') !== false ||
            strpos($method, 'unit') !== false) {
            return 'unit';
        }

        // E2E test patterns
        if (strpos($path, 'e2e') !== false ||
            strpos($path, 'endtoend') !== false ||
            strpos($method, 'e2e') !== false) {
            return 'e2e';
        }

        // API test patterns
        if (strpos($path, 'api') !== false ||
            strpos($method, 'api') !== false ||
            strpos($method, 'endpoint') !== false) {
            return 'api';
        }

        // Default to unit test
        return 'unit';
    }

    /**
     * Calculate complexity score based on various factors
     */
    private function calculateComplexityScore(TestCase $testCase): float
    {
        $score = 0.0;

        // Factor 1: Execution time (normalized to 0-1)
        if ($testCase->exec_time_ms !== null) {
            $timeScore = min(1.0, $testCase->exec_time_ms / 1000); // Normalize to 1 second
            $score += $timeScore * 0.3;
        }

        // Factor 2: Lines covered (normalized)
        if ($testCase->lines_covered !== null) {
            $coverageScore = min(1.0, $testCase->lines_covered / 100); // Normalize to 100 lines
            $score += $coverageScore * 0.3;
        }

        // Factor 3: Test type weight
        $testType = $this->detectTestType($testCase);
        $typeWeights = [
            'unit' => 0.2,
            'integration' => 0.6,
            'api' => 0.8,
            'e2e' => 1.0,
        ];
        $score += ($typeWeights[$testType] ?? 0.2) * 0.4;

        return round($score, 3);
    }

    /**
     * Detect parameterized test groups
     *
     * @param Collection<TestCase> $testCases
     */
    public function detectParameterizedGroups(Collection $testCases): array
    {
        $groups = [];

        foreach ($testCases as $testCase) {
            $normalized = $this->normalizeTestName($testCase);
            
            if (!isset($groups[$normalized])) {
                $groups[$normalized] = [];
            }
            
            $groups[$normalized][] = $testCase->id;
        }

        // Filter out non-parameterized tests
        return array_filter($groups, fn($group) => count($group) > 1);
    }

    /**
     * Calculate coverage uniqueness for a test
     */
    public function calculateCoverageUniqueness(TestCase $testCase, array $coverageMap): float
    {
        $uniqueLines = 0;
        $totalLines = 0;

        $testCase->coverageLines()
            ->select('file', 'line')
            ->chunk(1000, function ($coverageLines) use ($coverageMap, &$uniqueLines, &$totalLines) {
                foreach ($coverageLines as $line) {
                    $totalLines++;
                    $key = "{$line->file}:{$line->line}";
                    
                    // Count how many tests cover this line
                    $coveringTests = count($coverageMap[$key] ?? []);
                    
                    if ($coveringTests === 1) {
                        $uniqueLines++;
                    }
                }
            });

        return $totalLines > 0 ? $uniqueLines / $totalLines : 0.0;
    }
    
    /**
     * Calculate coverage uniqueness for multiple tests efficiently
     */
    public function calculateBulkCoverageUniqueness(Collection $testCases): array
    {
        $testCaseIds = $testCases->pluck('id')->toArray();
        
        if (empty($testCaseIds)) {
            return [];
        }
        
        // Use cached coverage map
        $coverageMap = QueryCache::coverageMap($testCaseIds);
            
        // Calculate uniqueness for each test
        $uniquenessScores = [];
        
        // Get coverage counts per test
        $coverageCounts = DB::table('coverage_lines')
            ->whereIn('test_case_id', $testCaseIds)
            ->select('test_case_id', DB::raw('COUNT(*) as total_lines'))
            ->groupBy('test_case_id')
            ->pluck('total_lines', 'test_case_id')
            ->toArray();
            
        foreach ($testCaseIds as $testId) {
            $uniqueLines = 0;
            $totalLines = $coverageCounts[$testId] ?? 0;
            
            // Count unique lines for this test
            foreach ($coverageMap as $key => $testIds) {
                if (in_array($testId, $testIds) && count($testIds) === 1) {
                    $uniqueLines++;
                }
            }
            
            $uniquenessScores[$testId] = $totalLines > 0 ? $uniqueLines / $totalLines : 0.0;
        }
        
        return $uniquenessScores;
    }
}