<?php

namespace Reductor\Coverage\Parsers;

use Reductor\Support\Exceptions\ReductorException;
use SebastianBergmann\CodeCoverage\CodeCoverage;

class CovParser
{
    /**
     * Parse a .cov file containing serialized PHP code coverage
     */
    public function parse(string $filePath): array
    {
        if (!file_exists($filePath)) {
            throw new ReductorException("Coverage file not found: {$filePath}");
        }

        // Execute the PHP file to get the coverage object
        $coverage = null;
        
        try {
            // The .cov file should return a CodeCoverage object
            $coverage = require $filePath;
        } catch (\Exception $e) {
            throw new ReductorException("Failed to load coverage data: " . $e->getMessage());
        }

        if (!$coverage instanceof CodeCoverage) {
            throw new ReductorException("Invalid coverage file format. Expected CodeCoverage object.");
        }

        return $this->extractCoverageDataStreaming($coverage);
    }

    /**
     * Extract coverage data from CodeCoverage object using streaming approach
     */
    private function extractCoverageDataStreaming(CodeCoverage $coverage): array
    {
        $result = [];
        $batchSize = 50; // Process in smaller batches
        
        try {
            // Try to get raw data first (PHPUnit 10/11)
            $rawData = $coverage->getData(true);
            $lineCoverage = $rawData->lineCoverage();
            
            // Process files in batches to avoid memory issues
            $files = array_keys($lineCoverage);
            $fileBatches = array_chunk($files, $batchSize);
            
            foreach ($fileBatches as $fileBatch) {
                foreach ($fileBatch as $file) {
                    $lines = $lineCoverage[$file];
                    
                    foreach ($lines as $line => $tests) {
                        if ($tests === null || empty($tests)) {
                            continue;
                        }
                        
                        // Process tests for this line
                        foreach ($tests as $testId) {
                            if (!isset($result[$testId])) {
                                $result[$testId] = [];
                            }
                            
                            $result[$testId][] = [
                                'file' => $file,
                                'line' => $line,
                            ];
                        }
                    }
                }
                
                // Force garbage collection after each batch
                gc_collect_cycles();
            }
            
            // If no test data found, create synthetic entries
            if (empty($result)) {
                $result = $this->createSyntheticTestData($lineCoverage);
            }
            
        } catch (\Exception $e) {
            // Fallback to original method for older PHPUnit versions
            $result = $this->extractCoverageDataFallback($coverage);
        }
        
        return $result;
    }
    
    /**
     * Create synthetic test data when no test associations are available
     */
    private function createSyntheticTestData(array $lineCoverage): array
    {
        $result = [];
        $testId = 1;
        
        foreach ($lineCoverage as $file => $lines) {
            $testName = 'Test_' . basename($file, '.php') . '_' . $testId;
            $result[$testName] = [];
            
            foreach ($lines as $line => $covered) {
                if ($covered !== null) {
                    $result[$testName][] = [
                        'file' => $file,
                        'line' => $line,
                    ];
                }
            }
            
            if (!empty($result[$testName])) {
                $testId++;
            } else {
                unset($result[$testName]);
            }
        }
        
        return $result;
    }
    
    /**
     * Fallback method for older PHPUnit versions
     */
    private function extractCoverageDataFallback(CodeCoverage $coverage): array
    {
        $result = [];
        
        try {
            $data = $coverage->getData();
            
            foreach ($data as $file => $lines) {
                foreach ($lines as $line => $tests) {
                    if (empty($tests)) {
                        continue;
                    }
                    
                    foreach ($tests as $testId => $flag) {
                        if (!isset($result[$testId])) {
                            $result[$testId] = [];
                        }
                        
                        $result[$testId][] = [
                            'file' => $file,
                            'line' => $line,
                        ];
                    }
                }
            }
        } catch (\Exception $e) {
            // Try getTests method as last resort
            $tests = $coverage->getTests();
            
            foreach ($tests as $testId => $testData) {
                if (!isset($result[$testId])) {
                    $result[$testId] = [];
                }
                
                if (isset($testData['files']) && is_array($testData['files'])) {
                    foreach ($testData['files'] as $file => $lines) {
                        foreach ($lines as $line => $covered) {
                            if ($covered > 0) {
                                $result[$testId][] = [
                                    'file' => $file,
                                    'line' => $line,
                                ];
                            }
                        }
                    }
                }
            }
        }
        
        return $result;
    }
    
    /**
     * Extract coverage data from CodeCoverage object (original method)
     */
    private function extractCoverageData(CodeCoverage $coverage): array
    {
        $result = [];
        
        // Try to get raw data first (PHPUnit 10/11)
        try {
            $rawData = $coverage->getData(true);
            
            // In PHPUnit 10/11, we need to check if data is available
            $lineCoverage = $rawData->lineCoverage();
            
            // If we have line coverage but no test associations, create synthetic test IDs
            if (!empty($lineCoverage)) {
                $hasTests = false;
                foreach ($lineCoverage as $file => $lines) {
                    foreach ($lines as $line => $tests) {
                        if ($tests !== null && !empty($tests)) {
                            $hasTests = true;
                            break 2;
                        }
                    }
                }
                
                if (!$hasTests) {
                    // Create synthetic test entries based on files
                    $testId = 1;
                    foreach ($lineCoverage as $file => $lines) {
                        $testName = 'Test_' . basename($file, '.php') . '_' . $testId;
                        $result[$testName] = [];
                        
                        foreach ($lines as $line => $covered) {
                            if ($covered !== null) {
                                $result[$testName][] = [
                                    'file' => $file,
                                    'line' => $line,
                                ];
                            }
                        }
                        
                        if (!empty($result[$testName])) {
                            $testId++;
                        } else {
                            unset($result[$testName]);
                        }
                    }
                    
                    return $result;
                }
            }
            
            // Standard processing when we have test data
            foreach ($lineCoverage as $file => $lines) {
                foreach ($lines as $line => $tests) {
                    if ($tests === null || empty($tests)) {
                        continue;
                    }

                    // Group by test
                    foreach ($tests as $testId) {
                        if (!isset($result[$testId])) {
                            $result[$testId] = [];
                        }

                        $result[$testId][] = [
                            'file' => $file,
                            'line' => $line,
                        ];
                    }
                }
            }
        } catch (\Exception $e) {
            // Fallback for older PHPUnit versions
            $data = $coverage->getData();
            
            foreach ($data as $file => $lines) {
                foreach ($lines as $line => $tests) {
                    if (empty($tests)) {
                        continue;
                    }

                    foreach ($tests as $testId => $flag) {
                        if (!isset($result[$testId])) {
                            $result[$testId] = [];
                        }

                        $result[$testId][] = [
                            'file' => $file,
                            'line' => $line,
                        ];
                    }
                }
            }
        }

        // If still no data, try the getTests method
        if (empty($result)) {
            $tests = $coverage->getTests();
            
            foreach ($tests as $testId => $testData) {
                if (!isset($result[$testId])) {
                    $result[$testId] = [];
                }
                
                // Use test data to build basic coverage info
                if (isset($testData['files']) && is_array($testData['files'])) {
                    foreach ($testData['files'] as $file => $lines) {
                        foreach ($lines as $line => $covered) {
                            if ($covered > 0) {
                                $result[$testId][] = [
                                    'file' => $file,
                                    'line' => $line,
                                ];
                            }
                        }
                    }
                }
            }
        }

        return $result;
    }
}