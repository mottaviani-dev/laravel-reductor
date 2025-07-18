<?php

namespace Reductor\IO;

use Reductor\Support\DTOs\RedundancyFindingDTO;
use Reductor\Support\Exceptions\ReductorException;
use Illuminate\Support\Facades\File;
use Symfony\Component\Yaml\Yaml;

class FileHandler
{
    /**
     * Save redundancy findings to file
     *
     * @param RedundancyFindingDTO[]|array[] $findings
     */
    public function saveFindings(array $findings, string $format, string $path): string
    {
        $directory = dirname($path);
        
        // Ensure directory exists
        if (!File::exists($directory)) {
            File::makeDirectory($directory, 0755, true);
        }
        
        // Convert findings to array format if they're DTOs
        $data = array_map(function($f) {
            return is_array($f) ? $f : $f->toArray();
        }, $findings);
        
        // Format and save based on type
        switch (strtolower($format)) {
            case 'json':
                return $this->saveJson($data, $path);
                
            case 'yaml':
                return $this->saveYaml($data, $path);
                
            case 'markdown':
            case 'md':
                return $this->saveMarkdown($findings, $path);
                
            case 'html':
                return $this->saveHtml($findings, $path);
                
            default:
                throw new ReductorException("Unsupported output format: {$format}");
        }
    }

    /**
     * Read test vectors from file
     */
    public function readVectors(string $path): array
    {
        if (!File::exists($path)) {
            throw new ReductorException("File not found: {$path}");
        }
        
        $content = File::get($path);
        $extension = pathinfo($path, PATHINFO_EXTENSION);
        
        switch ($extension) {
            case 'json':
                return json_decode($content, true);
                
            case 'yaml':
            case 'yml':
                return Yaml::parse($content);
                
            default:
                throw new ReductorException("Unsupported file format: {$extension}");
        }
    }

    /**
     * Save data as JSON
     */
    private function saveJson(array $data, string $path): string
    {
        $json = json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
        
        if ($json === false) {
            throw new ReductorException('Failed to encode data as JSON');
        }
        
        File::put($path, $json);
        return $path;
    }

    /**
     * Save data as YAML
     */
    private function saveYaml(array $data, string $path): string
    {
        $yaml = Yaml::dump($data, 4, 2);
        File::put($path, $yaml);
        return $path;
    }

    /**
     * Save findings as Markdown report
     *
     * @param RedundancyFindingDTO[] $findings
     */
    private function saveMarkdown(array $findings, string $path): string
    {
        $markdown = $this->generateMarkdownReport($findings);
        File::put($path, $markdown);
        return $path;
    }

    /**
     * Generate Markdown report
     */
    private function generateMarkdownReport(array $findings): string
    {
        $md = "# Test Redundancy Analysis Report\n\n";
        $md .= "Generated at: " . now()->toIso8601String() . "\n\n";
        
        // Summary
        $totalRedundant = array_sum(array_map(function($f) {
            if (is_array($f)) {
                return count($f['redundant_tests'] ?? []);
            }
            return $f->getRedundantTestCount();
        }, $findings));
        $highPriority = count(array_filter($findings, function($f) {
            return (is_array($f) ? $f['priority'] : $f->priority) === 'high';
        }));
        $mediumPriority = count(array_filter($findings, function($f) {
            return (is_array($f) ? $f['priority'] : $f->priority) === 'medium';
        }));
        $lowPriority = count(array_filter($findings, function($f) {
            return (is_array($f) ? $f['priority'] : $f->priority) === 'low';
        }));
        
        $md .= "## Summary\n\n";
        $md .= "- **Total Redundant Tests**: {$totalRedundant}\n";
        $md .= "- **High Priority**: {$highPriority} findings\n";
        $md .= "- **Medium Priority**: {$mediumPriority} findings\n";
        $md .= "- **Low Priority**: {$lowPriority} findings\n\n";
        
        // Findings by priority
        foreach (['high', 'medium', 'low'] as $priority) {
            $priorityFindings = array_filter($findings, function($f) use ($priority) {
                return (is_array($f) ? $f['priority'] : $f->priority) === $priority;
            });
            
            if (empty($priorityFindings)) {
                continue;
            }
            
            $md .= "## " . ucfirst($priority) . " Priority Findings\n\n";
            
            foreach ($priorityFindings as $finding) {
                $md .= $this->formatFindingMarkdown($finding);
            }
        }
        
        return $md;
    }

    /**
     * Format a single finding as Markdown
     */
    private function formatFindingMarkdown($finding): string
    {
        // Handle both array and DTO formats
        if (is_array($finding)) {
            $clusterId = $finding['cluster_id'] ?? 'Unknown';
            $redundancyScore = $finding['redundancy_score'] ?? 0;
            $recommendation = $finding['recommendation'] ?? 'No recommendation';
            $representativeTest = $finding['representative_test'] ?? 'Unknown';
            $redundantTests = $finding['redundant_tests'] ?? [];
            $analysis = $finding['analysis'] ?? [];
        } else {
            $clusterId = $finding->clusterId;
            $redundancyScore = $finding->redundancyScore;
            $recommendation = $finding->recommendation;
            $representativeTest = $finding->representativeTest;
            $redundantTests = $finding->redundantTests;
            $analysis = $finding->analysis;
        }
        
        $md = "### Cluster {$clusterId}\n\n";
        $md .= "**Redundancy Score**: " . round($redundancyScore * 100) . "%\n\n";
        $md .= "**Recommendation**: {$recommendation}\n\n";
        $md .= "**Representative Test**: `{$representativeTest}`\n\n";
        
        if (!empty($redundantTests)) {
            $testCount = count($redundantTests);
            $md .= "**Redundant Tests** ({$testCount}):\n";
            foreach ($redundantTests as $test) {
                $md .= "- `{$test}`\n";
            }
            $md .= "\n";
        }
        
        if (!empty($analysis)) {
            $md .= "**Analysis**:\n";
            foreach ($analysis as $key => $value) {
                $label = ucwords(str_replace('_', ' ', $key));
                $md .= "- {$label}: {$value}\n";
            }
            $md .= "\n";
        }
        
        $md .= "---\n\n";
        return $md;
    }

    /**
     * Save findings as HTML report
     */
    private function saveHtml(array $findings, string $path): string
    {
        $html = $this->generateHtmlReport($findings);
        File::put($path, $html);
        return $path;
    }

    /**
     * Generate HTML report
     */
    private function generateHtmlReport(array $findings): string
    {
        $html = <<<HTML
<!DOCTYPE html>
<html>
<head>
    <title>Test Redundancy Analysis Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1, h2, h3 { color: #333; }
        .summary { background: #f0f0f0; padding: 20px; border-radius: 5px; margin-bottom: 30px; }
        .finding { border: 1px solid #ddd; padding: 20px; margin-bottom: 20px; border-radius: 5px; }
        .high { border-left: 5px solid #d32f2f; }
        .medium { border-left: 5px solid #f57c00; }
        .low { border-left: 5px solid #388e3c; }
        .test-list { background: #f5f5f5; padding: 10px; border-radius: 3px; }
        code { background: #e0e0e0; padding: 2px 4px; border-radius: 3px; }
    </style>
</head>
<body>
    <h1>Test Redundancy Analysis Report</h1>
    <p>Generated at: {date}</p>
    
    <div class="summary">
        <h2>Summary</h2>
        <ul>
            <li><strong>Total Redundant Tests</strong>: {totalRedundant}</li>
            <li><strong>High Priority</strong>: {highPriority} findings</li>
            <li><strong>Medium Priority</strong>: {mediumPriority} findings</li>
            <li><strong>Low Priority</strong>: {lowPriority} findings</li>
        </ul>
    </div>
    
    {findings}
</body>
</html>
HTML;

        // Calculate summary stats
        $totalRedundant = array_sum(array_map(function($f) {
            if (is_array($f)) {
                return count($f['redundant_tests'] ?? []);
            }
            return $f->getRedundantTestCount();
        }, $findings));
        $highPriority = count(array_filter($findings, function($f) {
            return (is_array($f) ? $f['priority'] : $f->priority) === 'high';
        }));
        $mediumPriority = count(array_filter($findings, function($f) {
            return (is_array($f) ? $f['priority'] : $f->priority) === 'medium';
        }));
        $lowPriority = count(array_filter($findings, function($f) {
            return (is_array($f) ? $f['priority'] : $f->priority) === 'low';
        }));
        
        // Generate findings HTML
        $findingsHtml = '';
        foreach (['high', 'medium', 'low'] as $priority) {
            $priorityFindings = array_filter($findings, function($f) use ($priority) {
                return (is_array($f) ? $f['priority'] : $f->priority) === $priority;
            });
            
            if (empty($priorityFindings)) {
                continue;
            }
            
            $findingsHtml .= "<h2>" . ucfirst($priority) . " Priority Findings</h2>\n";
            
            foreach ($priorityFindings as $finding) {
                $findingsHtml .= $this->formatFindingHtml($finding);
            }
        }
        
        // Replace placeholders
        $html = str_replace('{date}', now()->toIso8601String(), $html);
        $html = str_replace('{totalRedundant}', $totalRedundant, $html);
        $html = str_replace('{highPriority}', $highPriority, $html);
        $html = str_replace('{mediumPriority}', $mediumPriority, $html);
        $html = str_replace('{lowPriority}', $lowPriority, $html);
        $html = str_replace('{findings}', $findingsHtml, $html);
        
        return $html;
    }

    /**
     * Format a single finding as HTML
     */
    private function formatFindingHtml($finding): string
    {
        // Handle both array and DTO formats
        if (is_array($finding)) {
            $score = round(($finding['redundancy_score'] ?? 0) * 100);
            $testCount = count($finding['redundant_tests'] ?? []);
            $priority = $finding['priority'] ?? 'low';
            $clusterId = $finding['cluster_id'] ?? 'Unknown';
            $recommendation = $finding['recommendation'] ?? 'No recommendation';
            $representativeTest = $finding['representative_test'] ?? 'Unknown';
            $redundantTests = $finding['redundant_tests'] ?? [];
            $analysis = $finding['analysis'] ?? [];
        } else {
            $score = round($finding->redundancyScore * 100);
            $testCount = $finding->getRedundantTestCount();
            $priority = $finding->priority;
            $clusterId = $finding->clusterId;
            $recommendation = $finding->recommendation;
            $representativeTest = $finding->representativeTest;
            $redundantTests = $finding->redundantTests;
            $analysis = $finding->analysis;
        }
        
        $html = "<div class='finding {$priority}'>\n";
        $html .= "<h3>Cluster {$clusterId}</h3>\n";
        $html .= "<p><strong>Redundancy Score</strong>: {$score}%</p>\n";
        $html .= "<p><strong>Recommendation</strong>: {$recommendation}</p>\n";
        $html .= "<p><strong>Representative Test</strong>: <code>{$representativeTest}</code></p>\n";
        
        if (!empty($redundantTests)) {
            $html .= "<p><strong>Redundant Tests</strong> ({$testCount}):</p>\n";
            $html .= "<div class='test-list'><ul>\n";
            foreach ($redundantTests as $test) {
                $html .= "<li><code>{$test}</code></li>\n";
            }
            $html .= "</ul></div>\n";
        }
        
        if (!empty($analysis)) {
            $html .= "<p><strong>Analysis</strong>:</p><ul>\n";
            foreach ($analysis as $key => $value) {
                $label = ucwords(str_replace('_', ' ', $key));
                $html .= "<li>{$label}: {$value}</li>\n";
            }
            $html .= "</ul>\n";
        }
        
        $html .= "</div>\n";
        return $html;
    }
}