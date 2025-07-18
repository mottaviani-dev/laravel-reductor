<?php

namespace Reductor\Commands;

use Illuminate\Console\Command;
use Illuminate\Support\Facades\Log;
use Reductor\Support\DTOs\ReductorConfig;
use Symfony\Component\Console\Input\InputOption;
use Reductor\Support\Exceptions\ReductorException;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Output\OutputInterface;

abstract class BaseReductorCommand extends Command
{
    /**
     * Common options for all Reductor commands
     */
    protected function configureCommonOptions(): void
    {
        $this->addOption('algorithm', 'a', InputOption::VALUE_REQUIRED, 'Clustering algorithm (kmeans, dbscan, hierarchical)', 'kmeans');
        $this->addOption('threshold', 't', InputOption::VALUE_REQUIRED, 'Similarity threshold (0.0–1.0)', '0.85');
        $this->addOption('output', 'o', InputOption::VALUE_REQUIRED, 'Output file path');
        $this->addOption('format', 'f', InputOption::VALUE_REQUIRED, 'Output format (markdown, json, yaml, html)', 'markdown');
        $this->addOption('debug', 'd', InputOption::VALUE_NONE, 'Enable debug output');
        $this->addOption('quiet', 'q', InputOption::VALUE_NONE, 'Suppress all output except errors');
    }

    /**
     * Initialize command execution
     */
    protected function initialize(InputInterface $input, OutputInterface $output): void
    {
        parent::initialize($input, $output);

        // Set up logging
        if ($input->getOption('debug')) {
            Log::channel('reductor')->debug('Command started', [
                'command' => $this->getName(),
                'arguments' => $input->getArguments(),
                'options' => $input->getOptions(),
            ]);
        }
    }

    /**
     * Build configuration from command options
     */
    protected function buildConfig(): ReductorConfig
    {
        try {
            $config = ReductorConfig::fromLaravelConfig();

            // Override with command options
            if ($this->hasOption('algorithm') && $this->option('algorithm')) {
                $config = new ReductorConfig(
                    algorithm: $this->option('algorithm'),
                    threshold: $config->threshold,
                    outputFormat: $config->outputFormat,
                    maxClusters: $config->maxClusters,
                    minClusterSize: $config->minClusterSize,
                    useDimensionalityReduction: $config->useDimensionalityReduction,
                    reducedDimensions: $config->reducedDimensions,
                    excludePaths: $config->excludePaths,
                    algorithmParams: $config->algorithmParams,
                    debug: $config->debug,
                    timeout: $config->timeout
                );
            }

            if ($this->hasOption('threshold') && $this->option('threshold')) {
                $config = new ReductorConfig(
                    algorithm: $config->algorithm,
                    threshold: (float) $this->option('threshold'),
                    outputFormat: $config->outputFormat,
                    maxClusters: $config->maxClusters,
                    minClusterSize: $config->minClusterSize,
                    useDimensionalityReduction: $config->useDimensionalityReduction,
                    reducedDimensions: $config->reducedDimensions,
                    excludePaths: $config->excludePaths,
                    algorithmParams: $config->algorithmParams,
                    debug: $config->debug,
                    timeout: $config->timeout
                );
            }

            if ($this->hasOption('format') && $this->option('format')) {
                $config = new ReductorConfig(
                    algorithm: $config->algorithm,
                    threshold: $config->threshold,
                    outputFormat: $this->option('format'),
                    maxClusters: $config->maxClusters,
                    minClusterSize: $config->minClusterSize,
                    useDimensionalityReduction: $config->useDimensionalityReduction,
                    reducedDimensions: $config->reducedDimensions,
                    excludePaths: $config->excludePaths,
                    algorithmParams: $config->algorithmParams,
                    debug: $config->debug,
                    timeout: $config->timeout
                );
            }

            if ($this->hasOption('debug') && $this->option('debug')) {
                $config = new ReductorConfig(
                    algorithm: $config->algorithm,
                    threshold: $config->threshold,
                    outputFormat: $config->outputFormat,
                    maxClusters: $config->maxClusters,
                    minClusterSize: $config->minClusterSize,
                    useDimensionalityReduction: $config->useDimensionalityReduction,
                    reducedDimensions: $config->reducedDimensions,
                    excludePaths: $config->excludePaths,
                    algorithmParams: $config->algorithmParams,
                    debug: true,
                    timeout: $config->timeout
                );
            }

            return $config;

        } catch (\Exception $e) {
            throw new ReductorException('Failed to build configuration: ' . $e->getMessage());
        }
    }

    /**
     * Validate common arguments
     */
    protected function validateCommonArguments(): void
    {
        // Validate threshold
        if ($this->hasOption('threshold')) {
            $threshold = $this->option('threshold');
            if ($threshold !== null) {
                $value = (float) $threshold;
                if ($value < 0.0 || $value > 1.0) {
                    throw new ReductorException('Threshold must be between 0.0 and 1.0');
                }
            }
        }

        // Validate algorithm
        if ($this->hasOption('algorithm')) {
            $algorithm = $this->option('algorithm');
            if ($algorithm !== null && !in_array($algorithm, ['kmeans', 'dbscan', 'hierarchical'])) {
                throw new ReductorException('Invalid algorithm. Must be one of: kmeans, dbscan, hierarchical');
            }
        }

        // Validate format
        if ($this->hasOption('format')) {
            $format = $this->option('format');
            if ($format !== null && !in_array($format, ['json', 'yaml', 'markdown', 'html'])) {
                throw new ReductorException('Invalid format. Must be one of: json, yaml, markdown, html');
            }
        }
    }

    /**
     * Display error and exit
     */
    protected function displayError(string $message, \Exception $exception = null): int
    {
        $this->error($message);

        if ($this->option('debug') && $exception) {
            $this->error('Exception: ' . get_class($exception));
            $this->error('Stack trace:');
            $this->line($exception->getTraceAsString());
        }

        Log::error('Command failed', [
            'command' => $this->getName(),
            'message' => $message,
            'exception' => $exception ? [
                'class' => get_class($exception),
                'message' => $exception->getMessage(),
                'file' => $exception->getFile(),
                'line' => $exception->getLine(),
            ] : null,
        ]);

        return 1;
    }

    /**
     * Display success message
     */
    protected function displaySuccess(string $message): void
    {
        if (!$this->option('quiet')) {
            $this->info($message);
        }

        Log::info('Command succeeded', [
            'command' => $this->getName(),
            'message' => $message,
        ]);
    }

    /**
     * Display progress
     */
    protected function displayProgress(string $task, int $current, int $total): void
    {
        if ($this->option('quiet')) {
            return;
        }

        $percentage = $total > 0 ? round(($current / $total) * 100) : 0;
        $this->output->write("\r{$task}: {$current}/{$total} ({$percentage}%)");

        if ($current >= $total) {
            $this->output->writeln(''); // New line when complete
        }
    }

    /**
     * Display table data
     */
    protected function displayTable(array $headers, array $rows): void
    {
        if ($this->option('quiet')) {
            return;
        }

        $this->table($headers, $rows);
    }

    /**
     * Ask for confirmation with default
     */
    protected function confirmWithDefault(string $question, bool $default = false): bool
    {
        if ($this->option('no-interaction')) {
            return $default;
        }

        return $this->confirm($question, $default);
    }

    /**
     * Get output path with fallback
     */
    protected function getOutputPath(string $defaultFilename): string
    {
        if ($this->hasOption('output') && $this->option('output')) {
            return $this->option('output');
        }

        $format = $this->option('format') ?? 'json';
        return storage_path("reductor/{$defaultFilename}.{$format}");
    }

    /**
     * Format duration for display
     */
    protected function formatDuration(float $seconds): string
    {
        if ($seconds < 1) {
            return round($seconds * 1000) . 'ms';
        } elseif ($seconds < 60) {
            return round($seconds, 1) . 's';
        } else {
            $minutes = floor($seconds / 60);
            $remainingSeconds = $seconds % 60;
            return "{$minutes}m " . round($remainingSeconds) . 's';
        }
    }

    /**
     * Format file size for display
     */
    protected function formatBytes(int $bytes): string
    {
        $units = ['B', 'KB', 'MB', 'GB'];
        $i = 0;
        
        while ($bytes >= 1024 && $i < count($units) - 1) {
            $bytes /= 1024;
            $i++;
        }

        return round($bytes, 2) . ' ' . $units[$i];
    }
}