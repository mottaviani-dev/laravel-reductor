<?php

namespace Reductor\Support\DTOs;

use Illuminate\Contracts\Support\Arrayable;

final class ClusterResultDTO implements Arrayable
{
    /**
     * @param array<int,array<string>> $clusters Map of cluster ID to test IDs
     * @param array<string,int> $testToCluster Map of test ID to cluster ID
     * @param array<int,float> $clusterSizes Size of each cluster
     * @param array<int,float> $clusterScores Quality scores for each cluster
     * @param array<string,mixed> $metadata Additional cluster metadata
     */
    public function __construct(
        public readonly array $clusters,
        public readonly array $testToCluster,
        public readonly array $clusterSizes = [],
        public readonly array $clusterScores = [],
        public readonly array $metadata = []
    ) {
        $this->validateConsistency();
    }

    private function validateConsistency(): void
    {
        $totalTests = 0;
        foreach ($this->clusters as $clusterId => $testIds) {
            $totalTests += count($testIds);
            
            foreach ($testIds as $testId) {
                if (!isset($this->testToCluster[$testId]) || $this->testToCluster[$testId] !== $clusterId) {
                    throw new \InvalidArgumentException(
                        "Inconsistent cluster mapping for test {$testId}"
                    );
                }
            }
        }

        if ($totalTests !== count($this->testToCluster)) {
            throw new \InvalidArgumentException(
                "Cluster test count mismatch: {$totalTests} vs " . count($this->testToCluster)
            );
        }
    }

    public function getClusterCount(): int
    {
        return count($this->clusters);
    }

    public function getTestCount(): int
    {
        return count($this->testToCluster);
    }

    public function getClusterForTest(string $testId): ?int
    {
        return $this->testToCluster[$testId] ?? null;
    }

    public function getTestsInCluster(int $clusterId): array
    {
        return $this->clusters[$clusterId] ?? [];
    }

    public function toArray(): array
    {
        return [
            'clusters' => $this->clusters,
            'test_to_cluster' => $this->testToCluster,
            'cluster_sizes' => $this->clusterSizes,
            'cluster_scores' => $this->clusterScores,
            'metadata' => $this->metadata,
            'summary' => [
                'total_clusters' => $this->getClusterCount(),
                'total_tests' => $this->getTestCount(),
                'average_cluster_size' => $this->getTestCount() > 0 
                    ? round($this->getTestCount() / $this->getClusterCount(), 2)
                    : 0,
            ],
        ];
    }

    public static function fromArray(array $data): self
    {
        return new self(
            clusters: $data['clusters'],
            testToCluster: $data['test_to_cluster'],
            clusterSizes: $data['cluster_sizes'] ?? [],
            clusterScores: $data['cluster_scores'] ?? [],
            metadata: $data['metadata'] ?? []
        );
    }
}