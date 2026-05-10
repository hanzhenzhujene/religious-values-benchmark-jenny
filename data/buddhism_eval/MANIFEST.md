# BuddhismEval Manifest

- Benchmark: #26 BuddhismEval
- Official dataset: https://huggingface.co/datasets/Nethmi14/BuddhismEval
- Current status: use only if official Hugging Face eval configs are reachable
- Intended configs: `english_eval`, `sinhala_eval`
- Excluded config: `parallel_corpus`
- Scoring: multiple-choice accuracy after mapping `correct_answer` to the closest official option
- Data policy: the HF split label may be `train`, but only the official `*_eval` configs are eligible
