<?php

namespace Reductor\Cache;

use Illuminate\Support\Facades\Cache;
use Closure;

class QueryCache
{
    /**
     * Cache duration in seconds
     */
    private const DEFAULT_TTL = 3600; // 1 hour
    
    /**
     * Cache key prefix
     */
    private const CACHE_PREFIX = 'reductor:';
    
    /**
     * Get or store a value in cache
     */
    public static function remember(string $key, Closure $callback, ?int $ttl = null): mixed
    {
        $cacheKey = self::CACHE_PREFIX . $key;
        $ttl = $ttl ?? self::DEFAULT_TTL;
        
        return Cache::remember($cacheKey, $ttl, $callback);
    }
    
    /**
     * Get coverage statistics for a test run
     */
    public static function testRunStats(int $testRunId): array
    {
        return self::remember("test_run_stats:{$testRunId}", function () use ($testRunId) {
            return [
                'test_count' => \Reductor\Models\TestCase::where('test_run_id', $testRunId)->count(),
                'coverage_lines' => \Reductor\Models\CoverageLine::whereHas('testCase', function ($query) use ($testRunId) {
                    $query->where('test_run_id', $testRunId);
                })->count(),
                'unique_files' => \Reductor\Models\CoverageLine::whereHas('testCase', function ($query) use ($testRunId) {
                    $query->where('test_run_id', $testRunId);
                })->distinct('file')->count('file'),
            ];
        });
    }
    
    /**
     * Get coverage map for a set of test cases
     */
    public static function coverageMap(array $testCaseIds): array
    {
        $cacheKey = 'coverage_map:' . md5(implode(',', $testCaseIds));
        
        return self::remember($cacheKey, function () use ($testCaseIds) {
            $map = [];
            
            \Illuminate\Support\Facades\DB::table('coverage_lines')
                ->whereIn('test_case_id', $testCaseIds)
                ->select('test_case_id', 'file', 'line')
                ->orderBy('file')
                ->orderBy('line')
                ->chunk(10000, function ($lines) use (&$map) {
                    foreach ($lines as $line) {
                        $key = "{$line->file}:{$line->line}";
                        if (!isset($map[$key])) {
                            $map[$key] = [];
                        }
                        $map[$key][] = $line->test_case_id;
                    }
                });
                
            return $map;
        }, 7200); // Cache for 2 hours
    }
    
    /**
     * Get test metadata for a test run
     */
    public static function testMetadata(int $testRunId): array
    {
        return self::remember("test_metadata:{$testRunId}", function () use ($testRunId) {
            $metadata = [];
            
            $testCases = \Reductor\Models\TestCase::where('test_run_id', $testRunId)
                ->select('id', 'path', 'method', 'exec_time_ms', 'recent_fail_rate')
                ->get();
                
            foreach ($testCases as $testCase) {
                $metadata[$testCase->id] = [
                    'path' => $testCase->path,
                    'method' => $testCase->method,
                    'exec_time_ms' => $testCase->exec_time_ms,
                    'recent_fail_rate' => $testCase->recent_fail_rate,
                    'identifier' => "{$testCase->path}::{$testCase->method}",
                ];
            }
            
            return $metadata;
        });
    }
    
    /**
     * Clear cache for a test run
     */
    public static function clearTestRun(int $testRunId): void
    {
        Cache::forget(self::CACHE_PREFIX . "test_run_stats:{$testRunId}");
        Cache::forget(self::CACHE_PREFIX . "test_metadata:{$testRunId}");
        
        // Clear any coverage maps that might include this test run
        // In a real implementation, we'd track which cache keys to clear
    }
    
    /**
     * Clear all reductor caches
     */
    public static function clearAll(): void
    {
        // In a real implementation with Redis, we could use:
        Cache::tags(['reductor'])->flush();
    }
}