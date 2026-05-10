# Jenny Religion Benchmark Release Summary

This package tracks Jenny's assigned religion benchmarks under the strict official-data policy.

## Current Access Gate

- IslamTrust: blocked - gated Hugging Face dataset; HF token not configured
- BuddhismEval: blocked - official HF eval subset unavailable: Dataset 'Nethmi14/BuddhismEval' doesn't exist on the Hub or cannot be accessed.
- BibleQA: accessible - official GitHub artifact reachable
- CatholicBench: blocked - no official scenario/rubric file configured

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
