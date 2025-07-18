<?php

namespace Reductor\Recommendations;

use Reductor\Support\DTOs\ClusterResultDTO;
use Reductor\Support\DTOs\RedundancyFindingDTO;
use Reductor\Support\DTOs\TestVectorDTO;

class ClusterAnalyzer
{
    private const HIGH_REDUNDANCY_THRESHOLD = 0.95;   // Conservative: 95%+ similar
    private const MEDIUM_REDUNDANCY_THRESHOLD = 0.85;  // Conservative: 85%+ similar
    
    /**
     * Analyze clusters to find redundancy
     *
     * @param TestVectorDTO[] $vectors
     * @return RedundancyFindingDTO[]
     */
    public function analyze(ClusterResultDTO $clusterResult, array $vectors): array
    {
        $findings = [];
        
        // Create vector lookup map
        $vectorMap = $this->createVectorMap($vectors);
        
        // Analyze each cluster
        foreach ($clusterResult->clusters as $clusterId => $testIds) {
            // Skip small clusters
            if (count($testIds) < 2) {
                continue;
            }
            
            // Get vectors for this cluster
            $clusterVectors = array_filter($vectors, function ($vector) use ($testIds) {
                return in_array($vector->testId, $testIds);
            });
            
            if (empty($clusterVectors)) {
                continue;
            }
            
            // Find representative test and redundant tests
            $analysis = $this->analyzeCluster($clusterId, $clusterVectors);
            
            if ($analysis !== null) {
                $findings[] = $analysis;
            }
        }
        
        // Sort findings by priority and score
        usort($findings, function ($a, $b) {
            $priorityOrder = ['high' => 0, 'medium' => 1, 'low' => 2];
            $priorityDiff = $priorityOrder[$a->priority] - $priorityOrder[$b->priority];
            
            if ($priorityDiff !== 0) {
                return $priorityDiff;
            }
            
            return $b->redundancyScore <=> $a->redundancyScore;
        });
        
        return $findings;
    }

    /**
     * Create vector lookup map
     *
     * @param TestVectorDTO[] $vectors
     */
    private function createVectorMap(array $vectors): array
    {
        $map = [];
        foreach ($vectors as $vector) {
            $map[$vector->testId] = $vector;
        }
        return $map;
    }

    /**
     * Analyze a single cluster for redundancy
     *
     * @param TestVectorDTO[] $clusterVectors
     */
    private function analyzeCluster(int|string $clusterId, array $clusterVectors): ?RedundancyFindingDTO
    {
        // Calculate similarity matrix
        $similarities = $this->calculateSimilarityMatrix($clusterVectors);
        
        // Find representative test (most central)
        $representative = $this->findRepresentativeTest($clusterVectors, $similarities);
        
        // Identify redundant tests
        $redundantTests = $this->identifyRedundantTests(
            $representative,
            $clusterVectors,
            $similarities
        );
        
        if (empty($redundantTests)) {
            return null;
        }
        
        // Calculate redundancy score
        $redundancyScore = $this->calculateRedundancyScore($similarities);
        
        // Determine priority
        $priority = $this->determinePriority($redundancyScore, count($redundantTests));
        
        // Generate recommendation
        $recommendation = $this->generateRecommendation(
            $representative,
            $redundantTests,
            $redundancyScore
        );
        
        // Prepare analysis details
        $analysis = [
            'average_similarity' => $redundancyScore,
            'cluster_size' => count($clusterVectors),
            'redundant_count' => count($redundantTests),
            'execution_time_saved' => $this->calculateTimeSaved($clusterVectors, $redundantTests),
            'coverage_overlap' => $this->calculateCoverageOverlap($clusterVectors)
        ];
        
        return new RedundancyFindingDTO(
            clusterId: $clusterId,
            representativeTest: $representative->testId,
            redundantTests: array_map(fn($v) => $v->testId, $redundantTests),
            redundancyScore: $redundancyScore,
            recommendation: $recommendation,
            priority: $priority,
            analysis: $analysis
        );
    }

    /**
     * Calculate similarity matrix for cluster vectors
     */
    private function calculateSimilarityMatrix(array $vectors): array
    {
        $similarities = [];
        $vectorArray = array_values($vectors);
        
        for ($i = 0; $i < count($vectorArray); $i++) {
            for ($j = $i; $j < count($vectorArray); $j++) {
                $similarity = $this->calculateVectorSimilarity(
                    $vectorArray[$i],
                    $vectorArray[$j]
                );
                
                $similarities[$i][$j] = $similarity;
                $similarities[$j][$i] = $similarity;
            }
        }
        
        return $similarities;
    }

    /**
     * Calculate similarity between two test vectors
     */
    private function calculateVectorSimilarity(TestVectorDTO $v1, TestVectorDTO $v2): float
    {
        // Since fingerprints are generated in Python, we only use semantic similarity here
        // The clustering in Python already considers coverage similarity
        return $this->cosineSimilarity($v1->semanticVector, $v2->semanticVector);
    }

    /**
     * Calculate cosine similarity
     */
    private function cosineSimilarity(array $v1, array $v2): float
    {
        $dotProduct = 0.0;
        $norm1 = 0.0;
        $norm2 = 0.0;
        
        for ($i = 0; $i < count($v1); $i++) {
            $dotProduct += $v1[$i] * $v2[$i];
            $norm1 += $v1[$i] * $v1[$i];
            $norm2 += $v2[$i] * $v2[$i];
        }
        
        $norm1 = sqrt($norm1);
        $norm2 = sqrt($norm2);
        
        if ($norm1 * $norm2 == 0) {
            return 0.0;
        }
        
        return $dotProduct / ($norm1 * $norm2);
    }


    /**
     * Find the most representative test in a cluster
     */
    private function findRepresentativeTest(array $vectors, array $similarities): TestVectorDTO
    {
        $vectorArray = array_values($vectors);
        $bestScore = -1;
        $bestIndex = 0;
        
        // Find test with highest average similarity to others
        for ($i = 0; $i < count($vectorArray); $i++) {
            $avgSimilarity = array_sum($similarities[$i]) / (count($similarities[$i]) - 1);
            
            // Factor in execution time and coverage
            $metadata = $vectorArray[$i]->metadata;
            $executionFactor = 1.0 / (1.0 + ($metadata['execution_time_ms'] ?? 0) / 1000);
            $coverageFactor = ($metadata['lines_covered'] ?? 0) / 100;
            
            $score = $avgSimilarity * 0.7 + $executionFactor * 0.2 + $coverageFactor * 0.1;
            
            if ($score > $bestScore) {
                $bestScore = $score;
                $bestIndex = $i;
            }
        }
        
        return $vectorArray[$bestIndex];
    }

    /**
     * Identify redundant tests in a cluster
     */
    private function identifyRedundantTests(
        TestVectorDTO $representative,
        array $clusterVectors,
        array $similarities
    ): array {
        $redundant = [];
        $vectorArray = array_values($clusterVectors);
        $repIndex = array_search($representative, $vectorArray);
        
        for ($i = 0; $i < count($vectorArray); $i++) {
            if ($i === $repIndex) {
                continue;
            }
            
            // Check similarity threshold
            if ($similarities[$repIndex][$i] >= self::MEDIUM_REDUNDANCY_THRESHOLD) {
                // Validate coverage preservation before marking as redundant
                if ($this->validateCoveragePreservation($representative, $vectorArray[$i])) {
                    $redundant[] = $vectorArray[$i];
                }
            }
        }
        
        return $redundant;
    }
    
    /**
     * Validate that removing a test won't lose coverage
     * Following research paper emphasis on coverage preservation
     */
    private function validateCoveragePreservation(
        TestVectorDTO $representative,
        TestVectorDTO $candidate
    ): bool {
        // Get coverage lines from metadata
        $repCoverage = $representative->metadata['coverage_lines'] ?? [];
        $candidateCoverage = $candidate->metadata['coverage_lines'] ?? [];
        
        // If candidate has no unique coverage, it's safe to remove
        if (empty($candidateCoverage)) {
            return true;
        }
        
        // Check if representative covers all candidate's lines
        $repCoverageSet = array_flip($repCoverage);
        $uniqueLines = 0;
        
        foreach ($candidateCoverage as $line) {
            if (!isset($repCoverageSet[$line])) {
                $uniqueLines++;
            }
        }
        
        // Allow removal if representative covers at least 95% of candidate's lines
        // This aligns with research paper's coverage preservation emphasis
        $coverageOverlap = 1.0 - ($uniqueLines / count($candidateCoverage));
        
        return $coverageOverlap >= 0.95;
    }

    /**
     * Calculate overall redundancy score for a cluster
     */
    private function calculateRedundancyScore(array $similarities): float
    {
        $total = 0;
        $count = 0;
        
        for ($i = 0; $i < count($similarities); $i++) {
            for ($j = $i + 1; $j < count($similarities[$i]); $j++) {
                $total += $similarities[$i][$j];
                $count++;
            }
        }
        
        return $count > 0 ? $total / $count : 0.0;
    }

    /**
     * Determine priority based on redundancy score and test count
     */
    private function determinePriority(float $redundancyScore, int $redundantCount): string
    {
        if ($redundancyScore >= self::HIGH_REDUNDANCY_THRESHOLD || $redundantCount >= 10) {
            return 'high';
        } elseif ($redundancyScore >= self::MEDIUM_REDUNDANCY_THRESHOLD || $redundantCount >= 5) {
            return 'medium';
        } else {
            return 'low';
        }
    }

    /**
     * Generate recommendation text
     */
    private function generateRecommendation(
        TestVectorDTO $representative,
        array $redundantTests,
        float $redundancyScore
    ): string {
        $count = count($redundantTests);
        $percentage = round($redundancyScore * 100);
        
        if ($redundancyScore >= self::HIGH_REDUNDANCY_THRESHOLD) {
            return "Remove {$count} highly redundant tests ({$percentage}% similar). " .
                   "Keep only the representative test for this functionality.";
        } elseif ($redundancyScore >= self::MEDIUM_REDUNDANCY_THRESHOLD) {
            return "Consider consolidating {$count} similar tests ({$percentage}% overlap). " .
                   "Review for potential merge or parameterization opportunities.";
        } else {
            return "Review {$count} related tests for optimization opportunities. " .
                   "Minor redundancy detected ({$percentage}% similarity).";
        }
    }

    /**
     * Calculate time saved by removing redundant tests
     */
    private function calculateTimeSaved(array $clusterVectors, array $redundantTests): float
    {
        $timeSaved = 0.0;
        
        foreach ($redundantTests as $test) {
            $timeSaved += $test->metadata['execution_time_ms'] ?? 0;
        }
        
        return round($timeSaved / 1000, 2); // Convert to seconds
    }

    /**
     * Calculate coverage overlap percentage
     */
    private function calculateCoverageOverlap(array $clusterVectors): float
    {
        if (count($clusterVectors) < 2) {
            return 0.0;
        }
        
        // Calculate overlap using raw coverage lines from metadata
        $totalOverlap = 0;
        $comparisons = 0;
        
        $vectorArray = array_values($clusterVectors);
        for ($i = 0; $i < min(10, count($vectorArray)); $i++) {
            for ($j = $i + 1; $j < min(10, count($vectorArray)); $j++) {
                $coverage1 = $vectorArray[$i]->metadata['coverage_lines'] ?? [];
                $coverage2 = $vectorArray[$j]->metadata['coverage_lines'] ?? [];
                
                if (!empty($coverage1) && !empty($coverage2)) {
                    $intersection = count(array_intersect($coverage1, $coverage2));
                    $union = count(array_unique(array_merge($coverage1, $coverage2)));
                    
                    if ($union > 0) {
                        $totalOverlap += $intersection / $union;
                        $comparisons++;
                    }
                }
            }
        }
        
        return $comparisons > 0 ? round($totalOverlap / $comparisons * 100, 2) : 0.0;
    }
}