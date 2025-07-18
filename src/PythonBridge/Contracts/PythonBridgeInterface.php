<?php

namespace Reductor\PythonBridge\Contracts;

use Reductor\Support\DTOs\TestVectorDTO;
use Reductor\Support\DTOs\ClusterResultDTO;
use Reductor\Support\DTOs\ReductorConfig;

interface PythonBridgeInterface
{
    /**
     * Execute clustering on test vectors
     *
     * @param TestVectorDTO[] $vectors
     */
    public function cluster(array $vectors, ReductorConfig $config): ClusterResultDTO;

    /**
     * Validate Python environment and dependencies
     */
    public function validateEnvironment(): array;

    /**
     * Check if Python pipeline is available
     */
    public function isAvailable(): bool;
}