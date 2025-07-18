<?php

namespace Reductor\Support\Exceptions;

class ReductorException extends \Exception
{
    protected array $context = [];

    public function withContext(array $context): self
    {
        $this->context = $context;
        return $this;
    }

    public function getContext(): array
    {
        return $this->context;
    }
}