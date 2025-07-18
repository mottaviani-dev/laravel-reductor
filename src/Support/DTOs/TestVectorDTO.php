<?php

namespace Reductor\Support\DTOs;

use Illuminate\Contracts\Support\Arrayable;

final class TestVectorDTO implements Arrayable
{
    /**
     * @param array<float> $semanticVector
     * @param array<string,mixed> $metadata
     */
    public function __construct(
        public readonly string $testId,
        public readonly array $semanticVector,
        public readonly array $metadata = []
    ) {
        $this->validateVectorDimensions();
    }

    private function validateVectorDimensions(): void
    {
        $semanticSize = count($this->semanticVector);

        if ($semanticSize !== 384) {
            throw new \InvalidArgumentException(
                "Semantic vector must have 384 dimensions, got {$semanticSize}"
            );
        }
    }

    /**
     * @deprecated Coverage fingerprints are generated in Python
     * @return array<float>
     */
    public function getCombinedVector(): array
    {
        return $this->semanticVector;
    }

    public function toArray(): array
    {
        return [
            'test_id' => $this->testId,
            'semantic_vector' => $this->semanticVector,
            'metadata' => $this->metadata,
        ];
    }

    public static function fromArray(array $data): self
    {
        return new self(
            testId: $data['test_id'],
            semanticVector: $data['semantic_vector'],
            metadata: $data['metadata'] ?? []
        );
    }
}