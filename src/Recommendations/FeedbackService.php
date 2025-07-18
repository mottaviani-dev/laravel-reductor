<?php

namespace Reductor\Recommendations;

use Illuminate\Support\Facades\File;
use Illuminate\Support\Facades\Log;

class FeedbackService
{
    private string $feedbackLogPath;
    private array $feedbackCache = [];

    public function __construct(?string $feedbackLogPath = null)
    {
        $this->feedbackLogPath = $feedbackLogPath ?? storage_path('reductor/feedback.log');
        $this->loadFeedback();
    }

    /**
     * Record user feedback for a cluster
     */
    public function recordFeedback(int $clusterId, string $action, string $reason = ''): void
    {
        $feedback = [
            'cluster_id' => $clusterId,
            'action' => $action,
            'reason' => $reason,
            'timestamp' => now()->toIso8601String(),
        ];

        // Update cache
        $this->feedbackCache[$clusterId] = $feedback;

        // Append to log file
        $this->appendToLog($feedback);

        Log::info('Feedback recorded', $feedback);
    }

    /**
     * Get feedback for a specific cluster
     */
    public function getFeedback(int $clusterId): ?array
    {
        return $this->feedbackCache[$clusterId] ?? null;
    }

    /**
     * Get all feedback
     */
    public function getAllFeedback(): array
    {
        return $this->feedbackCache;
    }

    /**
     * Check if cluster has been reviewed
     */
    public function hasBeenReviewed(int $clusterId): bool
    {
        return isset($this->feedbackCache[$clusterId]);
    }

    /**
     * Apply feedback override to a recommendation
     */
    public function applyOverride(array $recommendation, array $feedback): array
    {
        $recommendation['action'] = $feedback['action'];
        $recommendation['user_override'] = true;
        $recommendation['override_reason'] = $feedback['reason'] ?? '';
        $recommendation['override_timestamp'] = $feedback['timestamp'] ?? null;

        // Adjust severity based on user action
        switch ($feedback['action']) {
            case 'keep':
                $recommendation['severity'] = 'none';
                $recommendation['priority'] = 0;
                break;
            case 'ignore':
                $recommendation['severity'] = 'none';
                $recommendation['priority'] = 0;
                break;
            case 'merge':
                $recommendation['severity'] = 'high';
                break;
        }

        return $recommendation;
    }

    /**
     * Clear feedback for a cluster
     */
    public function clearFeedback(int $clusterId): void
    {
        unset($this->feedbackCache[$clusterId]);
        $this->rewriteLog();
    }

    /**
     * Clear all feedback
     */
    public function clearAllFeedback(): void
    {
        $this->feedbackCache = [];
        
        if (File::exists($this->feedbackLogPath)) {
            File::delete($this->feedbackLogPath);
        }
        
        Log::info('All feedback cleared');
    }

    /**
     * Load feedback from log file
     */
    private function loadFeedback(): void
    {
        if (!File::exists($this->feedbackLogPath)) {
            return;
        }

        $lines = File::lines($this->feedbackLogPath);
        
        foreach ($lines as $line) {
            $line = trim($line);
            if (empty($line)) {
                continue;
            }

            try {
                $feedback = json_decode($line, true);
                if (isset($feedback['cluster_id'])) {
                    $this->feedbackCache[$feedback['cluster_id']] = $feedback;
                }
            } catch (\Exception $e) {
                Log::warning('Failed to parse feedback line', ['line' => $line, 'error' => $e->getMessage()]);
            }
        }
    }

    /**
     * Append feedback to log file
     */
    private function appendToLog(array $feedback): void
    {
        $directory = dirname($this->feedbackLogPath);
        
        if (!File::exists($directory)) {
            File::makeDirectory($directory, 0755, true);
        }

        File::append(
            $this->feedbackLogPath,
            json_encode($feedback) . PHP_EOL
        );
    }

    /**
     * Rewrite the entire log file
     */
    private function rewriteLog(): void
    {
        $directory = dirname($this->feedbackLogPath);
        
        if (!File::exists($directory)) {
            File::makeDirectory($directory, 0755, true);
        }

        $content = '';
        foreach ($this->feedbackCache as $feedback) {
            $content .= json_encode($feedback) . PHP_EOL;
        }

        File::put($this->feedbackLogPath, $content);
    }

    /**
     * Export feedback to array
     */
    public function export(): array
    {
        return [
            'feedback_count' => count($this->feedbackCache),
            'feedback' => array_values($this->feedbackCache),
            'exported_at' => now()->toIso8601String(),
        ];
    }

    /**
     * Import feedback from array
     */
    public function import(array $data): void
    {
        if (!isset($data['feedback']) || !is_array($data['feedback'])) {
            throw new \InvalidArgumentException('Invalid feedback import data');
        }

        $this->feedbackCache = [];
        
        foreach ($data['feedback'] as $feedback) {
            if (isset($feedback['cluster_id'])) {
                $this->feedbackCache[$feedback['cluster_id']] = $feedback;
            }
        }

        $this->rewriteLog();
        
        Log::info('Feedback imported', ['count' => count($this->feedbackCache)]);
    }
}