<?php

namespace Reductor\Support\DTOs;

use Illuminate\Contracts\Support\Arrayable;

final class RedundancyFindingDTO implements Arrayable
{
    /**
     * @param string[] $redundantTests
     * @param array<string,mixed> $analysis
     */
    public function __construct(
        public readonly int|string $clusterId,
        public readonly string $representativeTest,
        public readonly array $redundantTests,
        public readonly float $redundancyScore,
        public readonly string $recommendation,
        public readonly string $priority,
        public readonly array $analysis = []
    ) {
        $this->validatePriority();
        $this->validateScore();
    }

    private function validatePriority(): void
    {
        $validPriorities = ['high', 'medium', 'low'];
        if (!in_array($this->priority, $validPriorities, true)) {
            throw new \InvalidArgumentException(
                "Invalid priority: {$this->priority}. Must be one of: " . implode(', ', $validPriorities)
            );
        }
    }

    private function validateScore(): void
    {
        if ($this->redundancyScore < 0.0 || $this->redundancyScore > 1.0) {
            throw new \InvalidArgumentException(
                "Redundancy score must be between 0.0 and 1.0, got {$this->redundancyScore}"
            );
        }
    }

    public function getRedundantTestCount(): int
    {
        return count($this->redundantTests);
    }

    public function getImpactLevel(): string
    {
        if ($this->redundancyScore >= 0.9) {
            return 'critical';
        } elseif ($this->redundancyScore >= 0.7) {
            return 'high';
        } elseif ($this->redundancyScore >= 0.5) {
            return 'medium';
        } else {
            return 'low';
        }
    }

    public function toArray(): array
    {
        return [
            'cluster_id' => $this->clusterId,
            'representative_test' => $this->representativeTest,
            'redundant_tests' => $this->redundantTests,
            'redundancy_score' => $this->redundancyScore,
            'recommendation' => $this->recommendation,
            'priority' => $this->priority,
            'impact_level' => $this->getImpactLevel(),
            'redundant_test_count' => $this->getRedundantTestCount(),
            'analysis' => $this->analysis,
        ];
    }

    public static function fromArray(array $data): self
    {
        return new self(
            clusterId: $data['cluster_id'],
            representativeTest: $data['representative_test'],
            redundantTests: $data['redundant_tests'],
            redundancyScore: $data['redundancy_score'],
            recommendation: $data['recommendation'],
            priority: $data['priority'],
            analysis: $data['analysis'] ?? []
        );
    }
}