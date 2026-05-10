# BuddhismEval Manifest

- Benchmark: #26 BuddhismEval
- Official dataset: https://huggingface.co/datasets/Nethmi14/BuddhismEval
- Current status: official dataset inaccessible / permission required; Jenny will email the author to request access
- Intended configs: `english_eval`, `sinhala_eval`
- Excluded config: `parallel_corpus`
- Disallowed substitute: `vanloc1808/BuddhismEval-vi-augmented`
- Scoring: multiple-choice accuracy after mapping `correct_answer` to the closest official option
- Data policy: the HF split label may be `train`, but only the official `*_eval` configs are eligible
