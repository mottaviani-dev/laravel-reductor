<?php

namespace Reductor\Repositories\Contracts;

use Reductor\Models\TestRun;
use Illuminate\Support\Collection;

interface TestRunRepositoryInterface
{
    /**
     * Find test run by ID
     */
    public function find(int $id): ?TestRun;

    /**
     * Get the most recent test run
     */
    public function latest(): ?TestRun;

    /**
     * Create a new test run
     */
    public function create(array $attributes): TestRun;

    /**
     * Update a test run
     */
    public function update(TestRun $testRun, array $attributes): bool;

    /**
     * Get test runs by date range
     */
    public function getByDateRange(\DateTimeInterface $start, \DateTimeInterface $end): Collection;

    /**
     * Get test runs with statistics
     */
    public function withStatistics(int $id): ?array;

    /**
     * Delete old test runs
     */
    public function deleteOlderThan(\DateTimeInterface $date): int;
}