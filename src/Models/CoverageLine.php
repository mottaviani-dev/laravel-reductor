<?php

namespace Reductor\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class CoverageLine extends Model
{
    public $timestamps = false;

    protected $fillable = [
        'test_case_id',
        'file',
        'line',
    ];

    protected $casts = [
        'line' => 'integer',
    ];

    public function testCase(): BelongsTo
    {
        return $this->belongsTo(TestCase::class);
    }
}