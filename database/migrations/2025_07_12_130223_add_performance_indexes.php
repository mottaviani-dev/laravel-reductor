<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('test_cases', function (Blueprint $table) {
            $table->index('test_run_id', 'test_cases_test_run_idx');
            
            // Composite index for common queries
            $table->index(['test_run_id', 'path', 'method'], 'test_cases_run_path_method_idx');
            
            // Index for path-based lookups (e.g., finding tests from same class)
            $table->index('path', 'test_cases_path_idx');
            
            // Index for performance-based queries
            $table->index('exec_time_ms', 'test_cases_exec_time_idx');
            
            // Index for failure rate queries
            $table->index('recent_fail_rate', 'test_cases_fail_rate_idx');
        });

        Schema::table('coverage_lines', function (Blueprint $table) {
            // Index for file and line lookups (coverage overlap queries)
            $table->index(['file', 'line'], 'coverage_lines_file_line_idx');
            
            // Separate index on test_case_id for faster foreign key lookups
            $table->index('test_case_id', 'coverage_lines_test_case_idx');
            
            // Index on line for range queries
            $table->index('line', 'coverage_lines_line_idx');

            // Add composite index for the join query
            $table->index(['test_case_id', 'file', 'line'], 'coverage_lines_test_file_line_idx');
        });

        Schema::table('test_runs', function (Blueprint $table) {
            // Index for finding runs by commit
            $table->index('git_commit_hash', 'test_runs_git_commit_idx');
            
            // Index for chronological queries
            $table->index('executed_at', 'test_runs_executed_at_idx');
            
            // Index for recent runs
            $table->index(['executed_at', 'created_at'], 'test_runs_recent_idx');
        });
    }

    public function down(): void
    {
        Schema::table('test_cases', function (Blueprint $table) {
            $table->dropIndex('test_cases_run_path_method_idx');
            $table->dropIndex('test_cases_path_idx');
            $table->dropIndex('test_cases_exec_time_idx');
            $table->dropIndex('test_cases_fail_rate_idx');
            $table->dropIndex('test_cases_test_run_idx');
        });

        Schema::table('coverage_lines', function (Blueprint $table) {
            $table->dropIndex('coverage_lines_file_line_idx');
            $table->dropIndex('coverage_lines_test_case_idx');
            $table->dropIndex('coverage_lines_line_idx');
            $table->dropIndex('coverage_lines_test_file_line_idx');
        });

        Schema::table('test_runs', function (Blueprint $table) {
            $table->dropIndex('test_runs_git_commit_idx');
            $table->dropIndex('test_runs_executed_at_idx');
            $table->dropIndex('test_runs_recent_idx');
        });
    }
};