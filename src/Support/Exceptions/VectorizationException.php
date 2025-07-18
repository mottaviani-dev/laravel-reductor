<?php

namespace Reductor\Support\Exceptions;

class VectorizationException extends ReductorException
{
    protected ?string $testId = null;

    public function withTestId(string $testId): self
    {
        $this->testId = $testId;
        return $this;
    }

    public function getTestId(): ?string
    {
        return $this->testId;
    }
}