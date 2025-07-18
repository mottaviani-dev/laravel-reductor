<?php

namespace Reductor\Support\Exceptions;

class PythonBridgeException extends ReductorException
{
    protected ?string $stderr = null;
    protected ?int $exitCode = null;

    public function withStderr(string $stderr): self
    {
        $this->stderr = $stderr;
        return $this;
    }

    public function withExitCode(int $exitCode): self
    {
        $this->exitCode = $exitCode;
        return $this;
    }

    public function getStderr(): ?string
    {
        return $this->stderr;
    }

    public function getExitCode(): ?int
    {
        return $this->exitCode;
    }
}