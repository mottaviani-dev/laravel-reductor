<?php

namespace Reductor\Repositories;

use Reductor\Repositories\Contracts\TestCaseRepositoryInterface;
use Reductor\Models\TestCase;
use Illuminate\Support\Collection;
use Illuminate\Support\Facades\DB;

class TestCaseRepository implements TestCaseRepositoryInterface
{
    /**
     * Find test case by ID
     */
    public function find(int $id): ?TestCase
    {
        return TestCase::find($id);
    }

    /**
     * Find multiple test cases by IDs
     */
    public function findMany(array $ids): Collection
    {
        return TestCase::whereIn('id', $ids)->get();
    }

    /**
     * Get test cases for a test run
     */
    public function getByTestRun(int $testRunId): Collection
    {
        return TestCase::where('test_run_id', $testRunId)
            ->orderBy('path')
            ->orderBy('method')
            ->get();
    }

    /**
     * Get test cases with coverage
     */
    public function getWithCoverage(int $testRunId): Collection
    {
        return TestCase::where('test_run_id', $testRunId)
            ->with(['coverageLines' => function ($query) {
                $query->select('id', 'test_case_id', 'file', 'line');
            }])
            ->get();
    }

    /**
     * Search test cases by name or path
     */
    public function search(string $query, ?int $testRunId = null): Collection
    {
        $builder = TestCase::query();

        if ($testRunId !== null) {
            $builder->where('test_run_id', $testRunId);
        }

        return $builder->where(function ($q) use ($query) {
                $q->where('path', 'like', "%{$query}%")
                  ->orWhere('method', 'like', "%{$query}%");
            })
            ->orderBy('path')
            ->orderBy('method')
            ->get();
    }

    /**
     * Get parameterized test groups
     */
    public function getParameterizedGroups(int $testRunId): array
    {
        $testCases = $this->getByTestRun($testRunId);
        $groups = [];

        foreach ($testCases as $testCase) {
            // Normalize test name by removing parameter variations
            $normalized = $this->normalizeTestName($testCase);
            
            if (!isset($groups[$normalized])) {
                $groups[$normalized] = [];
            }
            
            $groups[$normalized][] = [
                'id' => $testCase->id,
                'method' => $testCase->method,
                'exec_time_ms' => $testCase->exec_time_ms,
            ];
        }

        // Filter out non-parameterized tests
        return array_filter($groups, fn($group) => count($group) > 1);
    }

    /**
     * Get test cases by execution time
     */
    public function getSlowest(int $testRunId, int $limit = 10): Collection
    {
        return TestCase::where('test_run_id', $testRunId)
            ->whereNotNull('exec_time_ms')
            ->orderBy('exec_time_ms', 'desc')
            ->limit($limit)
            ->get();
    }

    /**
     * Get test cases by failure rate
     */
    public function getMostUnstable(int $testRunId, int $limit = 10): Collection
    {
        return TestCase::where('test_run_id', $testRunId)
            ->whereNotNull('recent_fail_rate')
            ->where('recent_fail_rate', '>', 0)
            ->orderBy('recent_fail_rate', 'desc')
            ->limit($limit)
            ->get();
    }

    /**
     * Normalize test name by removing parameter variations
     */
    private function normalizeTestName(TestCase $testCase): string
    {
        $identifier = "{$testCase->path}::{$testCase->method}";
        
        // Remove data provider suffixes
        $normalized = preg_replace('/ with data set ["\']?[^"\']*["\']?$/', '', $identifier);
        $normalized = preg_replace('/ with data set #\d+$/', '', $normalized);
        
        // Remove parameter variations
        $normalized = preg_replace('/\s*\([^)]*\)\s*$/', '', $normalized);
        
        return $normalized;
    }
}