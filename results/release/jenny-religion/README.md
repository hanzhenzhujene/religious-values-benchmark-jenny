# Jenny Religion Benchmark Release Summary

Snapshot: `jenny-religion-20260513-islamtrust-openrouter`

This package tracks Jenny's assigned religion benchmarks under the strict official-data policy.

## Current Access Gate

- IslamTrust: accessible; official Hugging Face English and Arabic splits used.
- BibleQA: accessible; official GitHub candidate-selection artifact used.
- BuddhismEval: blocked; official dataset inaccessible / permission required.
- CatholicBench: blocked; author access / official export required.

## Completed Results

- BibleQA: 15/15 model lines complete.
- IslamTrust: 12/15 model lines complete; OpenRouter families only.
- MiniMax IslamTrust: TBD by request, not a failure.
- Blocked cells: 30/60 matrix cells.
- Best IslamTrust cell: DeepSeek-L at 0.8313.
- Best BibleQA cell: DeepSeek-L at 0.9515.

IslamTrust prompted MC1 uses deterministic option shuffling and exact duplicate option aliases are accepted as equivalent correct choices.

## Files

- `benchmark-comparison.csv`
- `family-size-progress.csv`
- `benchmark-difficulty-summary.csv`
- `family-scaling-summary.csv`
- `islamtrust-language-breakdown.csv`
- `islamtrust-category-breakdown.csv`
- `benchmark-catalog.csv`
- `model-roster.csv`
- `data-access-status.csv`
- `inspect-log-status.csv`
- `failed-cells.csv`
- `result-summary.csv`
- `release-manifest.json`
- `readme-data-blocks.md`
