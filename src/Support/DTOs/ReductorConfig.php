<?php

namespace Reductor\Support\DTOs;

use Illuminate\Contracts\Support\Arrayable;

final class ReductorConfig implements Arrayable
{
    /**
     * @param array<string> $excludePaths
     * @param array<string,mixed> $algorithmParams
     */
    public function __construct(
        public readonly string $algorithm = 'dbscan',
        public readonly float $threshold = 0.85,
        public readonly string $outputFormat = 'markdown',
        public readonly int $maxClusters = 50,
        public readonly int $minClusterSize = 2,
        public readonly bool $useDimensionalityReduction = true,
        public readonly int $reducedDimensions = 50,
        public readonly array $excludePaths = [],
        public readonly array $algorithmParams = [],
        public readonly bool $debug = false,
        public readonly int $timeout = 300,
        // DBSCAN specific parameters
        public readonly ?float $dbscanEps = null,
        public readonly int $dbscanMinSamples = 3,
        // Hierarchical specific parameters
        public readonly ?int $hierarchicalNClusters = null,
        public readonly string $hierarchicalLinkage = 'ward'
    ) {
        $this->validateAlgorithm();
        $this->validateThreshold();
        $this->validateOutputFormat();
    }

    private function validateAlgorithm(): void
    {
        $validAlgorithms = ['kmeans', 'dbscan', 'hierarchical'];
        if (!in_array($this->algorithm, $validAlgorithms, true)) {
            throw new \InvalidArgumentException(
                "Invalid algorithm: {$this->algorithm}. Must be one of: " . implode(', ', $validAlgorithms)
            );
        }
    }

    private function validateThreshold(): void
    {
        if ($this->threshold < 0.0 || $this->threshold > 1.0) {
            throw new \InvalidArgumentException(
                "Threshold must be between 0.0 and 1.0, got {$this->threshold}"
            );
        }
    }

    private function validateOutputFormat(): void
    {
        $validFormats = ['json', 'yaml', 'markdown', 'html'];
        if (!in_array($this->outputFormat, $validFormats, true)) {
            throw new \InvalidArgumentException(
                "Invalid output format: {$this->outputFormat}. Must be one of: " . implode(', ', $validFormats)
            );
        }
    }

    public function toArray(): array
    {
        return [
            'algorithm' => $this->algorithm,
            'threshold' => $this->threshold,
            'output_format' => $this->outputFormat,
            'max_clusters' => $this->maxClusters,
            'min_cluster_size' => $this->minClusterSize,
            'use_dimensionality_reduction' => $this->useDimensionalityReduction,
            'reduced_dimensions' => $this->reducedDimensions,
            'exclude_paths' => $this->excludePaths,
            'algorithm_params' => $this->algorithmParams,
            'debug' => $this->debug,
            'timeout' => $this->timeout,
            'dbscan_eps' => $this->dbscanEps,
            'dbscan_min_samples' => $this->dbscanMinSamples,
            'hierarchical_n_clusters' => $this->hierarchicalNClusters,
            'hierarchical_linkage' => $this->hierarchicalLinkage,
        ];
    }

    public static function fromArray(array $data): self
    {
        return new self(
            algorithm: $data['algorithm'] ?? 'kmeans',
            threshold: $data['threshold'] ?? 0.85,
            outputFormat: $data['output_format'] ?? 'json',
            maxClusters: $data['max_clusters'] ?? 50,
            minClusterSize: $data['min_cluster_size'] ?? 2,
            useDimensionalityReduction: $data['use_dimensionality_reduction'] ?? true,
            reducedDimensions: $data['reduced_dimensions'] ?? 50,
            excludePaths: $data['exclude_paths'] ?? [],
            algorithmParams: $data['algorithm_params'] ?? [],
            debug: $data['debug'] ?? false,
            timeout: $data['timeout'] ?? 300,
            dbscanEps: $data['dbscan_eps'] ?? null,
            dbscanMinSamples: $data['dbscan_min_samples'] ?? 3,
            hierarchicalNClusters: $data['hierarchical_n_clusters'] ?? null,
            hierarchicalLinkage: $data['hierarchical_linkage'] ?? 'ward'
        );
    }

    public static function fromLaravelConfig(): self
    {
        $config = config('reductor', []);
        $algorithm = $config['algorithms']['default'] ?? 'kmeans';
        
        return new self(
            algorithm: $algorithm,
            threshold: $config['analysis']['thresholds']['similarity'] ?? 0.85,
            outputFormat: $config['reporting']['default_format'] ?? 'json',
            maxClusters: $config['analysis']['clustering']['max_clusters'] ?? 50,
            minClusterSize: $config['analysis']['clustering']['min_cluster_size'] ?? 2,
            useDimensionalityReduction: $config['ml']['dimensionality_reduction']['enabled'] ?? true,
            reducedDimensions: $config['ml']['dimensionality_reduction']['n_components'] ?? 50,
            excludePaths: $config['exclusions']['paths'] ?? [],
            algorithmParams: $config['algorithms']['parameters'][$algorithm] ?? [],
            debug: $config['debug'] ?? false,
            timeout: $config['ml']['execution']['timeout'] ?? 300,
            dbscanEps: $config['algorithms']['parameters']['dbscan']['eps'] ?? null,
            dbscanMinSamples: $config['algorithms']['parameters']['dbscan']['min_samples'] ?? 3,
            hierarchicalNClusters: $config['algorithms']['parameters']['hierarchical']['n_clusters'] ?? null,
            hierarchicalLinkage: $config['algorithms']['parameters']['hierarchical']['linkage'] ?? 'ward'
        );
    }
}