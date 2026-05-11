# Jenny Religion Benchmark Release Summary

This package tracks Jenny's assigned religion benchmarks under the strict official-data policy.

## Current Access Gate

- IslamTrust: blocked - gated Hugging Face dataset; access requested, waiting for response; HF token not configured
- BuddhismEval: blocked - official dataset inaccessible / permission required; Jenny will email the author to request access
- BibleQA: accessible - official GitHub artifact reachable
- CatholicBench: blocked - requires author access / official export needed; public dashboard is not scraped; Jenny will email the author

## Completed Results

- Complete BibleQA result cells: 15/15 model lines
- Blocked official-data cells: 45/60 matrix cells
- Best current BibleQA cells:
  - DeepSeek L: accuracy 0.952
  - Qwen L: accuracy 0.946
  - MiniMax S: accuracy 0.940
- Recovered cells:
  - Qwen S: original partial/error run recovered to 886/886 samples
  - DeepSeek L: original runtime-error run recovered to 886/886 samples
  - DeepSeek S: old empty-output run replaced by 2048-token rerun and targeted rebounds; one persistent max-token empty response counted incorrect

## Files

- `benchmark-comparison.csv`
- `family-size-progress.csv`
- `benchmark-difficulty-summary.csv`
- `family-scaling-summary.csv`
- `benchmark-catalog.csv`
- `model-roster.csv`
- `data-access-status.csv`
- `inspect-log-status.csv`
- `failed-cells.csv`
- `result-summary.csv`
- `release-manifest.json`
- `readme-data-blocks.md`
