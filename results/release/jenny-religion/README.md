# Jenny Religion Benchmark Release Summary

This package tracks Jenny's assigned religion benchmarks under the strict official-data policy.

## Current Access Gate

- IslamTrust: blocked - gated Hugging Face dataset; access requested, waiting for response; HF token not configured
- BuddhismEval: blocked - official dataset inaccessible / permission required; Jenny will email the author to request access
- BibleQA: accessible - official GitHub artifact reachable
- CatholicBench: blocked - requires author access / official export needed; public dashboard is not scraped; Jenny will email the author

## Completed Results

- Complete result cells: 13
- Best current BibleQA cells:
  - Qwen L: accuracy 0.945
  - MiniMax S: accuracy 0.940
  - MiniMax L: accuracy 0.935
- Non-success full-run cells:
  - DeepSeek L: error, 124/886 samples logged
  - Qwen S: error, 325/886 samples logged

## Files

- `benchmark-catalog.csv`
- `model-roster.csv`
- `data-access-status.csv`
- `inspect-log-status.csv`
- `failed-cells.csv`
- `result-summary.csv`
- `release-manifest.json`
