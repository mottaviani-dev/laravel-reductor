<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('coverage_lines', function (Blueprint $table) {
            $table->id();
            $table->foreignId('test_case_id')->constrained();
            $table->string('file');
            $table->integer('line');
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('coverage_lines');
    }
};