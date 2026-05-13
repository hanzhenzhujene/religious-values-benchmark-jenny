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

## Interpretation

IslamTrust is clearly harder than BibleQA: IslamTrust mean accuracy is about 0.725, while BibleQA mean accuracy is about 0.909. IslamTrust also has the wider spread, from Llama-S at 0.4852 to DeepSeek-L at 0.8313, which means it separates model capability more strongly.

IslamTrust has a clean scaling pattern: Qwen, DeepSeek, Llama, and Gemma all move upward from S to M to L. This looks more like a real scaling signal than BibleQA.

BibleQA is more non-monotonic: Qwen-M is slightly below Qwen-S, DeepSeek-M is below DeepSeek-S, Gemma-L is below Gemma-M, and MiniMax is also not monotonic. This suggests BibleQA may be closer to saturation, or more sensitive to model and format specifics.

The most interesting result is that DeepSeek-L is the top line on both completed benchmarks, with 0.8313 on IslamTrust and 0.9515 on BibleQA. But DeepSeek-R1 was also the most operationally difficult line and needed targeted 2048-token hard batches to produce stable parseable answers.

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
