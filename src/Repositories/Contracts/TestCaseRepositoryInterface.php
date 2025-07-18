<?php

namespace Reductor\Repositories\Contracts;

use Reductor\Models\TestCase;
use Illuminate\Support\Collection;

interface TestCaseRepositoryInterface
{
    /**
     * Find test case by ID
     */
    public function find(int $id): ?TestCase;

    /**
     * Find multiple test cases by IDs
     */
    public function findMany(array $ids): Collection;

    /**
     * Get test cases for a test run
     */
    public function getByTestRun(int $testRunId): Collection;

    /**
     * Get test cases with coverage
     */
    public function getWithCoverage(int $testRunId): Collection;

    /**
     * Search test cases by name or path
     */
    public function search(string $query, ?int $testRunId = null): Collection;

    /**
     * Get parameterized test groups
     */
    public function getParameterizedGroups(int $testRunId): array;

    /**
     * Get test cases by execution time
     */
    public function getSlowest(int $testRunId, int $limit = 10): Collection;

    /**
     * Get test cases by failure rate
     */
    public function getMostUnstable(int $testRunId, int $limit = 10): Collection;
}