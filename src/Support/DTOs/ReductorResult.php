<?php

namespace Reductor\Support\DTOs;

use Illuminate\Contracts\Support\Arrayable;
use Illuminate\Support\Collection;

final class ReductorResult implements Arrayable
{
    /**
     * @param Collection<RedundancyFindingDTO> $findings
     * @param array<string,mixed> $metrics
     * @param array<string,mixed> $errors
     */
    public function __construct(
        public readonly bool $success,
        public readonly Collection $findings,
        public readonly ClusterResultDTO $clusterResult,
        public readonly array $metrics = [],
        public readonly array $errors = [],
        public readonly float $executionTime = 0.0
    ) {
    }

    public function getTotalRedundantTests(): int
    {
        return $this->findings->sum(fn (RedundancyFindingDTO $finding) => $finding->getRedundantTestCount());
    }

    public function getReductionPercentage(): float
    {
        $totalTests = $this->clusterResult->getTestCount();
        if ($totalTests === 0) {
            return 0.0;
        }

        $redundantTests = $this->getTotalRedundantTests();
        return round(($redundantTests / $totalTests) * 100, 2);
    }

    public function getHighPriorityFindings(): Collection
    {
        return $this->findings->filter(fn (RedundancyFindingDTO $finding) => $finding->priority === 'high');
    }

    public function toArray(): array
    {
        return [
            'success' => $this->success,
            'findings' => $this->findings->map(fn ($f) => $f->toArray())->toArray(),
            'cluster_result' => $this->clusterResult->toArray(),
            'metrics' => array_merge($this->metrics, [
                'total_redundant_tests' => $this->getTotalRedundantTests(),
                'reduction_percentage' => $this->getReductionPercentage(),
                'high_priority_findings' => $this->getHighPriorityFindings()->count(),
                'execution_time_seconds' => $this->executionTime,
            ]),
            'errors' => $this->errors,
        ];
    }

    public static function success(
        Collection $findings,
        ClusterResultDTO $clusterResult,
        array $metrics = [],
        float $executionTime = 0.0
    ): self {
        return new self(
            success: true,
            findings: $findings,
            clusterResult: $clusterResult,
            metrics: $metrics,
            errors: [],
            executionTime: $executionTime
        );
    }

    public static function failure(array $errors, float $executionTime = 0.0): self
    {
        return new self(
            success: false,
            findings: collect(),
            clusterResult: new ClusterResultDTO([], []),
            metrics: [],
            errors: $errors,
            executionTime: $executionTime
        );
    }
}