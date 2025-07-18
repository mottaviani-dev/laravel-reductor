<?php

namespace Reductor\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Carbon\Carbon;

class TestRun extends Model
{
    protected $fillable = [
        'git_commit_hash',
        'executed_at',
    ];

    protected $casts = [
        'executed_at' => 'datetime',
    ];

    public function testCases(): HasMany
    {
        return $this->hasMany(TestCase::class);
    }
}