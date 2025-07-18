<?php

namespace Reductor\Recommendations;

use Reductor\Support\DTOs\RedundancyFindingDTO;
use Reductor\Support\DTOs\TestVectorDTO;
use Reductor\Models\TestCase;

class RecommendationBuilder
{
    private FeedbackService $feedbackService;

    public function __construct(FeedbackService $feedbackService)
    {
        $this->feedbackService = $feedbackService;
    }

    /**
     * Build enhanced recommendations from redundancy findings
     */
    public function buildFromFindings(array $findings): array
    {
        $recommendations = [];

        foreach ($findings as $finding) {
            if (!($finding instanceof RedundancyFindingDTO)) {
                continue;
            }

            $recommendation = $this->buildRecommendation($finding);
            
            // Apply feedback override if available
            $feedback = $this->feedbackService->getFeedback($finding->clusterId);
            if ($feedback) {
                $recommendation = $this->feedbackService->applyOverride($recommendation, $feedback);
            }

            $recommendations[] = $recommendation;
        }

        return $recommendations;
    }

    /**
     * Build a single recommendation from a finding
     */
    private function buildRecommendation(RedundancyFindingDTO $finding): array
    {
        // Load test details for enhanced information
        $representativeTest = $this->loadTestDetails($finding->representativeTest);
        $redundantTests = $this->loadMultipleTestDetails($finding->redundantTests);

        return [
            'cluster_id' => $finding->clusterId,
            'action' => $this->determineAction($finding),
            'severity' => $finding->priority,
            'priority' => $this->calculateNumericPriority($finding),
            'recommendation' => $finding->recommendation,
            'rationale' => $this->buildRationale($finding),
            'representative_test' => [
                'id' => $finding->representativeTest,
                'path' => $representativeTest->path ?? '',
                'method' => $representativeTest->method ?? '',
                'execution_time' => $representativeTest->exec_time_ms ?? 0,
            ],
            'redundant_tests' => array_map(function ($testId, $test) {
                return [
                    'id' => $testId,
                    'path' => $test->path ?? '',
                    'method' => $test->method ?? '',
                    'execution_time' => $test->exec_time_ms ?? 0,
                ];
            }, $finding->redundantTests, $redundantTests),
            'similarity_score' => $finding->redundancyScore,
            'cluster_size' => $finding->getRedundantTestCount() + 1,
            'potential_savings' => $this->calculateSavings($finding, $redundantTests),
            'metadata' => array_merge($finding->analysis, [
                'reviewed' => $this->feedbackService->hasBeenReviewed($finding->clusterId),
            ]),
        ];
    }

    /**
     * Determine action based on redundancy score
     */
    private function determineAction(RedundancyFindingDTO $finding): string
    {
        if ($finding->redundancyScore >= 0.95) {
            return 'merge';
        } elseif ($finding->redundancyScore >= 0.85) {
            return 'consolidate';
        } elseif ($finding->redundancyScore >= 0.70) {
            return 'review';
        } else {
            return 'monitor';
        }
    }

    /**
     * Calculate numeric priority for sorting
     */
    private function calculateNumericPriority(RedundancyFindingDTO $finding): float
    {
        $basePriority = match ($finding->priority) {
            'high' => 100,
            'medium' => 50,
            'low' => 10,
            default => 0,
        };

        // Factor in redundancy score
        $scoreFactor = $finding->redundancyScore * 20;

        // Factor in test count
        $countFactor = min($finding->getRedundantTestCount() * 2, 20);

        // Factor in time savings
        $timeFactor = min(($finding->analysis['execution_time_saved'] ?? 0) / 100, 10);

        return $basePriority + $scoreFactor + $countFactor + $timeFactor;
    }

    /**
     * Build detailed rationale
     */
    private function buildRationale(RedundancyFindingDTO $finding): array
    {
        $rationale = [];

        // Similarity reasoning
        if ($finding->redundancyScore >= 0.95) {
            $rationale[] = sprintf(
                'Tests are %d%% similar, indicating nearly identical functionality',
                round($finding->redundancyScore * 100)
            );
        } elseif ($finding->redundancyScore >= 0.85) {
            $rationale[] = sprintf(
                'High similarity (%d%%) suggests significant overlap in test coverage',
                round($finding->redundancyScore * 100)
            );
        }

        // Size reasoning
        $count = $finding->getRedundantTestCount();
        if ($count >= 10) {
            $rationale[] = "Large number of redundant tests ({$count}) amplifies impact";
        } elseif ($count >= 5) {
            $rationale[] = "Multiple redundant tests ({$count}) offer consolidation opportunity";
        }

        // Time reasoning
        $timeSaved = $finding->analysis['execution_time_saved'] ?? 0;
        if ($timeSaved > 10) {
            $rationale[] = sprintf('Removing redundant tests would save %.1fs per test run', $timeSaved);
        }

        // Coverage reasoning
        $coverageOverlap = $finding->analysis['coverage_overlap'] ?? 0;
        if ($coverageOverlap > 90) {
            $rationale[] = sprintf('Tests have %d%% coverage overlap', round($coverageOverlap));
        }

        return $rationale;
    }

    /**
     * Calculate potential savings
     */
    private function calculateSavings(RedundancyFindingDTO $finding, array $redundantTests): array
    {
        $totalTime = 0;
        $totalLines = 0;

        foreach ($redundantTests as $test) {
            $totalTime += $test->exec_time_ms ?? 0;
            $totalLines += $test->lines_covered ?? 0;
        }

        return [
            'time_saved_ms' => $totalTime,
            'time_saved_seconds' => round($totalTime / 1000, 2),
            'lines_reduction' => $totalLines,
            'test_count_reduction' => count($redundantTests),
            'percentage_reduction' => round(
                (count($redundantTests) / ($finding->getRedundantTestCount() + 1)) * 100,
                1
            ),
        ];
    }

    /**
     * Load test details from database
     */
    private function loadTestDetails(string $testId): ?TestCase
    {
        try {
            return TestCase::find($testId);
        } catch (\Exception $e) {
            return null;
        }
    }

    /**
     * Load multiple test details
     */
    private function loadMultipleTestDetails(array $testIds): array
    {
        try {
            $tests = TestCase::whereIn('id', $testIds)->get();
            $indexed = [];
            
            foreach ($tests as $test) {
                $indexed[$test->id] = $test;
            }
            
            // Return in same order as input
            $result = [];
            foreach ($testIds as $id) {
                $result[] = $indexed[$id] ?? null;
            }
            
            return $result;
        } catch (\Exception $e) {
            return array_fill(0, count($testIds), null);
        }
    }

    /**
     * Format recommendations for display
     */
    public function formatForDisplay(array $recommendations): array
    {
        $formatted = [];

        foreach ($recommendations as $rec) {
            $formatted[] = [
                'cluster' => $rec['cluster_id'],
                'action' => strtoupper($rec['action']),
                'severity' => $rec['severity'],
                'similarity' => round($rec['similarity_score'] * 100) . '%',
                'tests_affected' => $rec['cluster_size'],
                'time_saved' => $rec['potential_savings']['time_saved_seconds'] . 's',
                'recommendation' => $rec['recommendation'],
                'representative' => $rec['representative_test']['path'] . '::' . $rec['representative_test']['method'],
                'redundant_count' => count($rec['redundant_tests']),
            ];
        }

        return $formatted;
    }
}