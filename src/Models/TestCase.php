<?php

namespace Reductor\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class TestCase extends Model
{
    protected $fillable = [
        'test_run_id',
        'path',
        'method',
        'exec_time_ms',
        'recent_fail_rate',
    ];

    protected $casts = [
        'exec_time_ms' => 'integer',
        'recent_fail_rate' => 'float',
    ];

    public function testRun(): BelongsTo
    {
        return $this->belongsTo(TestRun::class);
    }

    public function coverageLines(): HasMany
    {
        return $this->hasMany(CoverageLine::class);
    }
}