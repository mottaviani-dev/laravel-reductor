<?php

namespace Reductor\Repositories;

use Reductor\Repositories\Contracts\TestRunRepositoryInterface;
use Reductor\Models\TestRun;
use Illuminate\Support\Collection;
use Illuminate\Support\Facades\DB;

class TestRunRepository implements TestRunRepositoryInterface
{
    /**
     * Find test run by ID
     */
    public function find(int $id): ?TestRun
    {
        return TestRun::find($id);
    }

    /**
     * Get the most recent test run
     */
    public function latest(): ?TestRun
    {
        return TestRun::latest()->first();
    }

    /**
     * Create a new test run
     */
    public function create(array $attributes): TestRun
    {
        return TestRun::create($attributes);
    }

    /**
     * Update a test run
     */
    public function update(TestRun $testRun, array $attributes): bool
    {
        return $testRun->update($attributes);
    }

    /**
     * Get test runs by date range
     */
    public function getByDateRange(\DateTimeInterface $start, \DateTimeInterface $end): Collection
    {
        return TestRun::whereBetween('created_at', [$start, $end])
            ->orderBy('created_at', 'desc')
            ->get();
    }

    /**
     * Get test runs with statistics
     */
    public function withStatistics(int $id): ?array
    {
        $testRun = $this->find($id);
        
        if (!$testRun) {
            return null;
        }

        $stats = DB::table('test_cases')
            ->where('test_run_id', $id)
            ->selectRaw('
                COUNT(*) as total_tests,
                SUM(exec_time_ms) as total_execution_time,
                AVG(exec_time_ms) as avg_execution_time,
                SUM(lines_covered) as total_lines_covered,
                AVG(lines_covered) as avg_lines_covered,
                AVG(recent_fail_rate) as avg_fail_rate
            ')
            ->first();

        $coverageStats = DB::table('coverage_lines')
            ->join('test_cases', 'coverage_lines.test_case_id', '=', 'test_cases.id')
            ->where('test_cases.test_run_id', $id)
            ->selectRaw('
                COUNT(DISTINCT coverage_lines.test_case_id) as tests_with_coverage,
                COUNT(DISTINCT coverage_lines.file) as files_covered,
                COUNT(*) as total_coverage_lines
            ')
            ->first();

        return [
            'test_run' => $testRun->toArray(),
            'statistics' => [
                'total_tests' => $stats->total_tests ?? 0,
                'total_execution_time_ms' => $stats->total_execution_time ?? 0,
                'avg_execution_time_ms' => round($stats->avg_execution_time ?? 0, 2),
                'total_lines_covered' => $stats->total_lines_covered ?? 0,
                'avg_lines_covered' => round($stats->avg_lines_covered ?? 0, 2),
                'avg_fail_rate' => round($stats->avg_fail_rate ?? 0, 4),
                'tests_with_coverage' => $coverageStats->tests_with_coverage ?? 0,
                'files_covered' => $coverageStats->files_covered ?? 0,
                'total_coverage_lines' => $coverageStats->total_coverage_lines ?? 0,
            ],
        ];
    }

    /**
     * Delete old test runs
     */
    public function deleteOlderThan(\DateTimeInterface $date): int
    {
        return TestRun::where('created_at', '<', $date)->delete();
    }
}