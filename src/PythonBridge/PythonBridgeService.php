<?php

namespace Reductor\PythonBridge;

use Reductor\PythonBridge\Contracts\PythonBridgeInterface;
use Reductor\Support\DTOs\TestVectorDTO;
use Reductor\Support\DTOs\ClusterResultDTO;
use Reductor\Support\DTOs\ReductorConfig;
use Reductor\Support\Exceptions\PythonBridgeException;
use Symfony\Component\Process\Process;
use Symfony\Component\Process\Exception\ProcessFailedException;
use Illuminate\Support\Facades\Log;

class PythonBridgeService implements PythonBridgeInterface
{
    private $progressCallback = null;
    private string $pythonPath;
    private string $mlPath;
    private int $timeout;

    public function __construct()
    {
        $this->pythonPath = config('reductor.ml.python_path', 'python3');
        
        // Use the package directory for ml path
        $this->mlPath = config('reductor.ml.ml_path', __DIR__ . '/../../ml');
        if (!is_dir($this->mlPath)) {
            // Try relative to package root
            $this->mlPath = dirname(dirname(__DIR__)) . '/ml';
        }
        
        $this->timeout = config('reductor.ml.execution.timeout', 300);
    }

    /**
     * Execute clustering on test vectors
     */
    public function cluster(array $vectors, ReductorConfig $config): ClusterResultDTO
    {
        // Validate environment first
        if (!$this->isAvailable()) {
            throw new PythonBridgeException('Python ML pipeline is not available');
        }

        // Prepare input data in the format the Python CLI expects
        $sourcesData = [];
        $coverageData = [];
        
        foreach ($vectors as $vector) {
            if ($vector instanceof TestVectorDTO) {
                // Sources file format - just the content string
                $sourcesData[$vector->testId] = $vector->metadata['source_code'] ?? '';
                
                // Coverage file format
                $coverageData[$vector->testId] = $vector->metadata['coverage_lines'] ?? [];
            }
        }
        
        // Write to temporary files - both as direct dicts
        $sourcesFile = $this->writeTemporaryFile($sourcesData);
        $coverageFile = $this->writeTemporaryFile($coverageData);
        $outputDir = sys_get_temp_dir() . '/reductor_output_' . uniqid();
        mkdir($outputDir);

        $configFile = null;
        try {
            // Build command
            $command = $this->buildClusterCommand($sourcesFile, $coverageFile, $outputDir, $config);
            
            // Extract config file from command for cleanup
            $configFileIndex = array_search('--config-file', $command);
            if ($configFileIndex !== false && isset($command[$configFileIndex + 1])) {
                $configFile = $command[$configFileIndex + 1];
            }
            
            // Execute Python process
            $result = $this->executePythonCommand($command);
            
            // Read and parse output
            $outputFile = $outputDir . '/clusters.json';
            if (!file_exists($outputFile)) {
                throw new PythonBridgeException('Python pipeline did not generate clusters.json');
            }
            
            $output = $this->readOutputFile($outputFile);
            
            return $this->parseClusterResult($output);
            
        } finally {
            // Cleanup temporary files
            $filesToCleanup = [$sourcesFile, $coverageFile];
            if ($configFile) {
                $filesToCleanup[] = $configFile;
            }
            $this->cleanupFiles($filesToCleanup);
            if (is_dir($outputDir)) {
                array_map('unlink', glob("$outputDir/*"));
                rmdir($outputDir);
            }
        }
    }

    /**
     * Validate Python environment and dependencies
     */
    public function validateEnvironment(): array
    {
        $validation = [
            'python_version' => null,
            'ml_package' => false,
            'dependencies' => [],
            'errors' => []
        ];

        // Check Python version
        try {
            $process = new Process([$this->pythonPath, '--version']);
            $process->run();
            
            if ($process->isSuccessful()) {
                $validation['python_version'] = trim($process->getOutput());
            } else {
                $validation['errors'][] = 'Python not found or not executable';
            }
        } catch (\Exception $e) {
            $validation['errors'][] = 'Failed to check Python version: ' . $e->getMessage();
        }

        // Check ML package
        if (is_dir($this->mlPath) && file_exists($this->mlPath . '/setup.py')) {
            $validation['ml_package'] = true;
        } else {
            $validation['errors'][] = 'ML package not found at: ' . $this->mlPath;
        }

        // Check dependencies
        try {
            $process = new Process([
                $this->pythonPath,
                '-c',
                'import numpy, scipy, sklearn; print("Dependencies OK")'
            ]);
            $process->run();
            
            if ($process->isSuccessful()) {
                $validation['dependencies'] = ['numpy', 'scipy', 'scikit-learn'];
            } else {
                $validation['errors'][] = 'Required Python dependencies not installed';
            }
        } catch (\Exception $e) {
            $validation['errors'][] = 'Failed to check dependencies: ' . $e->getMessage();
        }

        return $validation;
    }



    /**
     * Check if Python pipeline is available
     */
    public function isAvailable(): bool
    {
        $validation = $this->validateEnvironment();
        return empty($validation['errors']);
    }


    /**
     * Write data to temporary file
     */
    private function writeTemporaryFile(array $data): string
    {
        $tempFile = tempnam(sys_get_temp_dir(), 'reductor_');
        
        $json = json_encode($data, JSON_THROW_ON_ERROR);
        
        if (file_put_contents($tempFile, $json) === false) {
            throw new PythonBridgeException('Failed to write temporary input file');
        }

        return $tempFile;
    }

    /**
     * Build cluster command
     */
    private function buildClusterCommand(string $sourcesFile, string $coverageFile, string $outputDir, ReductorConfig $config): array
    {
        $command = [
            $this->pythonPath,
            $this->mlPath . '/run_ml.py',
            'cluster',
            '--sources', $sourcesFile,
            '--coverage', $coverageFile,
            '--output', $outputDir,
            '--algorithm', $config->algorithm,
        ];

        // Pass algorithm-specific parameters through config file
        $configData = [
            'clustering' => [
                'kmeans_min_clusters' => $config->minClusterSize,
                'kmeans_max_clusters' => $config->maxClusters,
                'dbscan_eps' => $config->dbscanEps,
                'dbscan_min_samples' => $config->dbscanMinSamples,
                'hierarchical_n_clusters' => $config->hierarchicalNClusters,
                'hierarchical_linkage' => $config->hierarchicalLinkage,
            ]
        ];
        
        // Write config to temporary file
        $configFile = $this->writeTemporaryFile($configData);
        $command[] = '--config-file';
        $command[] = $configFile;

        // Note: The Python CLI doesn't support --reduce-dimensions yet
        // TODO: Add support for dimensionality reduction in Python CLI

        if ($config->debug) {
            $command[] = '--debug';
        }

        return $command;
    }

    /**
     * Execute Python command
     */
    private function executePythonCommand(array $command): array
    {
        $process = new Process($command, $this->mlPath);
        $process->setTimeout($this->timeout);
        
        // Add the ml directory to PYTHONPATH
        $env = $_ENV;
        $env['PYTHONPATH'] = $this->mlPath . ':' . ($env['PYTHONPATH'] ?? '');
        $process->setEnv($env);

        // Set up progress monitoring if callback provided
        if ($this->progressCallback) {
            $process->run(function ($type, $buffer) {
                if ($type === Process::OUT && $this->progressCallback) {
                    // Parse progress from output
                    if (preg_match('/Progress: (\d+)%/', $buffer, $matches)) {
                        call_user_func($this->progressCallback, (int) $matches[1]);
                    }
                }
            });
        } else {
            $process->run();
        }

        if (!$process->isSuccessful()) {
            $errorMessage = 'Python pipeline execution failed';
            $stderr = $process->getErrorOutput();
            
            // Add more context to the error
            if (!empty($stderr)) {
                $errorMessage .= ': ' . $stderr;
            }
            
            $exception = (new PythonBridgeException($errorMessage))
                ->withStderr($stderr)
                ->withExitCode($process->getExitCode());
            
            Log::error('Python bridge error', [
                'command' => implode(' ', $command),
                'cwd' => $this->mlPath,
                'stderr' => $stderr,
                'stdout' => $process->getOutput(),
                'exit_code' => $process->getExitCode()
            ]);
            
            throw $exception;
        }

        return [
            'stdout' => $process->getOutput(),
            'stderr' => $process->getErrorOutput(),
            'exit_code' => $process->getExitCode()
        ];
    }

    /**
     * Read output file
     */
    private function readOutputFile(string $outputFile): array
    {
        if (!file_exists($outputFile)) {
            throw new PythonBridgeException('Python pipeline did not generate output file');
        }

        $content = file_get_contents($outputFile);
        if ($content === false) {
            throw new PythonBridgeException('Failed to read output file');
        }

        try {
            return json_decode($content, true, 512, JSON_THROW_ON_ERROR);
        } catch (\JsonException $e) {
            throw new PythonBridgeException('Invalid JSON in output file: ' . $e->getMessage());
        }
    }

    /**
     * Parse cluster result from Python output
     */
    private function parseClusterResult(array $output): ClusterResultDTO
    {
        // Python outputs direct format only
        if (!isset($output['clusters'])) {
            throw new PythonBridgeException('Invalid cluster result format: missing clusters key');
        }
        
        $clusters = $output['clusters'];
        $metadata = $output['metadata'] ?? [];
        
        // Build test_to_cluster mapping
        $testToCluster = [];
        $clusterSizes = [];
        $clusterScores = [];
        
        foreach ($clusters as $clusterId => $cluster) {
            if (isset($cluster['tests'])) {
                // Cluster object format
                $testIds = $cluster['tests'];
                $clusterScores[$clusterId] = $cluster['score'] ?? 0.5;
            } else {
                // Simple array format (default from Python)
                $testIds = $cluster;
                $clusterScores[$clusterId] = 0.5;
            }
            
            $clusterSizes[$clusterId] = count($testIds);
            foreach ($testIds as $testId) {
                $testToCluster[$testId] = $clusterId;
            }
        }

        return new ClusterResultDTO(
            clusters: $clusters,
            testToCluster: $testToCluster,
            clusterSizes: $clusterSizes,
            clusterScores: $clusterScores,
            metadata: $metadata
        );
    }

    /**
     * Cleanup temporary files
     */
    private function cleanupFiles(array $files): void
    {
        foreach ($files as $file) {
            if (file_exists($file)) {
                unlink($file);
            }
        }
    }
}