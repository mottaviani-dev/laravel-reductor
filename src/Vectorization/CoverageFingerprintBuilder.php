<?php

namespace Reductor\Vectorization;

use Reductor\Support\Exceptions\VectorizationException;
use Illuminate\Support\Collection;
use Illuminate\Support\Facades\DB;
use Reductor\Cache\QueryCache;

class CoverageFingerprintBuilder
{
    private const FINGERPRINT_SIZE = 256;
    private const BATCH_SIZE = 5000; // Larger batch for better performance
    private const CACHE_SIZE = 10000; // Cache hash computations
    
    private array $hashCache = [];
    private array $cacheAccessOrder = []; // Track access order for LRU eviction
    private ?array $testCoverageCache = null;
    private ?array $sharedCoverageLines = null;
    private ?array $coverageIdfScores = null;
    private bool $excludeSharedCoverage = true;
    private bool $useIdfWeighting = true;
    private $progressCallback = null; // PHP 7.4 doesn't support typed callable

    public function setExcludeSharedCoverage(bool $exclude): void
    {
        $this->excludeSharedCoverage = $exclude;
    }

    public function setUseIdfWeighting(bool $useIdf): void
    {
        $this->useIdfWeighting = $useIdf;
    }

    /**
     * Build coverage fingerprints for all test cases - OPTIMIZED
     */
    public function buildFingerprints(Collection $testCases): array
    {
        if ($testCases->isEmpty()) {
            return [];
        }

        $totalTests = $testCases->count();
        $testRunId = $testCases->first()->test_run_id;
        $testCaseIds = $testCases->pluck('id')->toArray();
        
        // Progress: Loading coverage data
        $this->reportProgress(0, $totalTests, 'Loading coverage data...');
        
        // Load all coverage data in one query
        $this->loadCoverageData($testRunId, $testCaseIds);
        
        // Progress: Analyzing shared coverage
        $this->reportProgress(0, $totalTests, 'Analyzing shared coverage patterns...');
        
        // Identify shared coverage lines and calculate IDF scores
        if ($this->excludeSharedCoverage || $this->useIdfWeighting) {
            $this->identifySharedCoverageLines($testCaseIds);
        }
        
        // Pre-generate hash seeds for better performance
        $hashSeeds = $this->precomputeHashSeeds();
        
        // Generate fingerprints with progress tracking
        $fingerprints = [];
        $processed = 0;
        
        foreach ($testCases as $testCase) {
            $fingerprints[] = $this->generateFingerprintOptimized(
                $testCase->id, 
                $hashSeeds
            );
            
            $processed++;
            
            // Report progress every 10 tests or at specific milestones
            if ($processed % 10 === 0 || $processed === $totalTests || 
                $processed === 1 || $processed === (int)($totalTests * 0.25) || 
                $processed === (int)($totalTests * 0.5) || $processed === (int)($totalTests * 0.75)) {
                $this->reportProgress($processed, $totalTests, 'Generating fingerprints');
            }
        }
        
        // Clear cache to free memory
        $this->clearCache();
        
        // Final progress
        $this->reportProgress($totalTests, $totalTests, 'Fingerprint generation complete');
        
        return $fingerprints;
    }

    /**
     * Load all coverage data in a single optimized query
     */
    private function loadCoverageData(int $testRunId, array $testCaseIds): void
    {
        $this->testCoverageCache = [];
        
        // Use a single query with proper indexing
        DB::table('coverage_lines')
            ->join('test_cases', 'coverage_lines.test_case_id', '=', 'test_cases.id')
            ->where('test_cases.test_run_id', $testRunId)
            ->whereIn('coverage_lines.test_case_id', $testCaseIds)
            ->select(
                'coverage_lines.test_case_id',
                DB::raw("CONCAT(coverage_lines.file, ':', coverage_lines.line) as line_key")
            )
            ->orderBy('coverage_lines.test_case_id')
            ->chunk(self::BATCH_SIZE, function ($lines) {
                foreach ($lines as $line) {
                    if (!isset($this->testCoverageCache[$line->test_case_id])) {
                        $this->testCoverageCache[$line->test_case_id] = [];
                    }
                    $this->testCoverageCache[$line->test_case_id][] = $line->line_key;
                }
            });
        
        // Deduplicate coverage lines for each test
        foreach ($this->testCoverageCache as $testId => &$lines) {
            $lines = array_unique($lines);
        }
    }

    /**
     * Identify shared coverage lines and calculate IDF scores
     */
    private function identifySharedCoverageLines(array $testCaseIds): void
    {
        $lineCounts = [];
        $totalTests = count($testCaseIds);
        // Research methodology: Balanced exclusion to avoid false positives
        // Too aggressive exclusion can make unrelated tests appear identical
        if ($totalTests > 100) {
            // For large suites: exclude lines covered by 60%+ of tests
            // This preserves more distinctive coverage patterns
            $threshold = max(0.6 * $totalTests, 60);
        } elseif ($totalTests > 50) {
            // For medium suites: exclude lines covered by 70%+ of tests
            $threshold = max(0.7 * $totalTests, 35);
        } else {
            // For small suites: original threshold
            $threshold = max(0.8 * $totalTests, 2);
        }
        
        // Count line occurrences
        foreach ($this->testCoverageCache as $testId => $lines) {
            foreach ($lines as $line) {
                $lineCounts[$line] = ($lineCounts[$line] ?? 0) + 1;
            }
        }
        
        // Calculate IDF scores and identify shared lines
        $this->sharedCoverageLines = [];
        $this->coverageIdfScores = [];
        
        foreach ($lineCounts as $line => $count) {
            // IDF = log(totalTests / documentFrequency) + 1
            // Higher IDF means the line is more distinctive (appears in fewer tests)
            $idf = log($totalTests / $count) + 1;
            $this->coverageIdfScores[$line] = $idf;
            
            if ($count >= $threshold) {
                $this->sharedCoverageLines[$line] = true;
            }
        }
        
        // Log statistics about shared coverage
        if ($this->excludeSharedCoverage) {
            $totalLines = count($lineCounts);
            $sharedLines = count($this->sharedCoverageLines);
            $percentage = $totalLines > 0 ? round(($sharedLines / $totalLines) * 100, 2) : 0;
            error_log("Shared coverage exclusion: $sharedLines of $totalLines lines ({$percentage}%) excluded (threshold: $threshold tests)");
        }
        
        if ($this->useIdfWeighting) {
            $avgIdf = array_sum($this->coverageIdfScores) / count($this->coverageIdfScores);
            $maxIdf = max($this->coverageIdfScores);
            $minIdf = min($this->coverageIdfScores);
            error_log("IDF weighting enabled: avg={$avgIdf}, min={$minIdf}, max={$maxIdf}");
        }
    }

    /**
     * Pre-compute hash seeds for all fingerprint positions
     */
    private function precomputeHashSeeds(): array
    {
        $seeds = [];
        for ($i = 0; $i < self::FINGERPRINT_SIZE; $i++) {
            $seeds[$i] = [
                'a' => $i * 0x5bd1e995,
                'b' => ($i * 31) ^ 0x27d4eb2d,
                'c' => $i * 0x85ebca6b
            ];
        }
        return $seeds;
    }

    /**
     * Generate fingerprint with optimizations
     */
    private function generateFingerprintOptimized(int $testCaseId, array $hashSeeds): array
    {
        $coverageLines = $this->testCoverageCache[$testCaseId] ?? [];
        
        if (empty($coverageLines)) {
            return array_fill(0, self::FINGERPRINT_SIZE, 0);
        }
        
        // Filter shared lines if needed
        if ($this->excludeSharedCoverage && !empty($this->sharedCoverageLines)) {
            $coverageLines = array_filter(
                $coverageLines,
                fn($line) => !isset($this->sharedCoverageLines[$line])
            );
        }
        
        if (empty($coverageLines)) {
            return array_fill(0, self::FINGERPRINT_SIZE, 0);
        }
        
        return $this->computeMinHashOptimized($coverageLines, $hashSeeds, $testCaseId);
    }

    /**
     * Optimized MinHash computation with optional IDF weighting
     */
    private function computeMinHashOptimized(array $lines, array $hashSeeds, int $testCaseId): array
    {
        $signature = [];
        
        // Pre-compute all hashes for all lines with IDF weighting
        $lineHashesWithWeights = [];
        foreach ($lines as $line) {
            // Check cache first
            if (!isset($this->hashCache[$line])) {
                $this->hashCache[$line] = $this->computeLineHashes($line, $hashSeeds);
                
                // Implement LRU eviction
                if (count($this->hashCache) > self::CACHE_SIZE) {
                    $this->evictLRUCacheEntries();
                }
            }
            
            // Update access order for LRU
            $this->updateCacheAccessOrder($line);
            
            // Get IDF weight for this line
            $idfWeight = 1.0;
            if ($this->useIdfWeighting && isset($this->coverageIdfScores[$line])) {
                $idfWeight = $this->coverageIdfScores[$line];
            }
            
            $lineHashesWithWeights[] = [
                'hashes' => $this->hashCache[$line],
                'weight' => $idfWeight,
                'line' => $line
            ];
        }
        
        // Find minimum weighted hash for each position
        for ($i = 0; $i < self::FINGERPRINT_SIZE; $i++) {
            $minWeightedHash = PHP_INT_MAX;
            
            foreach ($lineHashesWithWeights as $item) {
                // Apply IDF weighting: divide hash by weight
                // Lines with higher IDF (more distinctive) will have lower weighted hash values
                // and thus are more likely to be selected as the minimum
                $weightedHash = $item['hashes'][$i] / $item['weight'];
                
                if ($weightedHash < $minWeightedHash) {
                    $minWeightedHash = $weightedHash;
                }
            }
            
            // Normalize to [0, 1] range
            $signature[] = $minWeightedHash / PHP_INT_MAX;
        }
        
        return $signature;
    }

    /**
     * Compute all hash values for a line at once using xxHash or MurmurHash
     */
    private function computeLineHashes(string $line, array $hashSeeds): array
    {
        $hashes = [];
        
        // Use xxHash if available (fastest), fallback to MurmurHash3, then CRC32
        if (function_exists('xxhash32')) {
            // xxHash is the fastest non-cryptographic hash
            $base1 = xxhash32($line, 0);
            $base2 = xxhash32($line, 0x5bd1e995);
        } elseif (function_exists('murmur3_32')) {
            // MurmurHash3 is also very fast
            $base1 = murmur3_32($line, 0);
            $base2 = murmur3_32($line, 0x5bd1e995);
        } else {
            // Fallback to CRC32 (still faster than SHA256)
            $base1 = crc32($line);
            $base2 = crc32(strrev($line));
        }
        
        // Use simple multiplicative hashing for speed
        for ($i = 0; $i < self::FINGERPRINT_SIZE; $i++) {
            $seed = $hashSeeds[$i];
            // Simpler computation for better performance
            $hash = abs(($base1 * $seed['a'] + $base2 * $seed['b']) ^ $seed['c']);
            $hashes[] = $hash;
        }
        
        return $hashes;
    }

    /**
     * Clear caches to free memory
     */
    private function clearCache(): void
    {
        $this->hashCache = [];
        $this->testCoverageCache = null;
        $this->sharedCoverageLines = null;
        $this->coverageIdfScores = null;
    }

    /**
     * Calculate Jaccard similarity between two fingerprints
     */
    public function calculateSimilarity(array $fingerprint1, array $fingerprint2): float
    {
        if (count($fingerprint1) !== count($fingerprint2)) {
            throw new VectorizationException(
                "Fingerprint dimensions mismatch: " . count($fingerprint1) . " vs " . count($fingerprint2)
            );
        }

        $matches = 0;
        for ($i = 0; $i < count($fingerprint1); $i++) {
            if (abs($fingerprint1[$i] - $fingerprint2[$i]) < 0.0001) {
                $matches++;
            }
        }

        return $matches / count($fingerprint1);
    }
    
    /**
     * Update cache access order for LRU tracking
     */
    private function updateCacheAccessOrder(string $line): void
    {
        // Remove from current position if exists
        if (($key = array_search($line, $this->cacheAccessOrder)) !== false) {
            unset($this->cacheAccessOrder[$key]);
        }
        
        // Add to the end (most recently used)
        $this->cacheAccessOrder[] = $line;
    }
    
    /**
     * Evict least recently used cache entries
     */
    private function evictLRUCacheEntries(): void
    {
        // Calculate how many entries to evict (remove 20% to avoid frequent evictions)
        $entriesToEvict = intval(self::CACHE_SIZE * 0.2);
        
        // Get the least recently used entries
        $lruEntries = array_slice($this->cacheAccessOrder, 0, $entriesToEvict);
        
        // Remove from cache
        foreach ($lruEntries as $line) {
            unset($this->hashCache[$line]);
        }
        
        // Remove from access order
        $this->cacheAccessOrder = array_slice($this->cacheAccessOrder, $entriesToEvict);
        
        // Re-index array to maintain proper indices
        $this->cacheAccessOrder = array_values($this->cacheAccessOrder);
    }
    
    /**
     * Set progress callback
     */
    public function setProgressCallback(?callable $callback): void
    {
        $this->progressCallback = $callback;
    }
    
    /**
     * Report progress
     */
    private function reportProgress(int $current, int $total, string $message = ''): void
    {
        if ($this->progressCallback !== null) {
            $percentage = $total > 0 ? round(($current / $total) * 100) : 0;
            call_user_func($this->progressCallback, $current, $total, $percentage, $message);
        }
    }
}