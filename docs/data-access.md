# Data Access

## IslamTrust

Official source: https://huggingface.co/datasets/Abderraouf000/IslamTrust-benchmark

This dataset is gated. Accept the Hugging Face terms, then set `HF_TOKEN` or `HUGGING_FACE_HUB_TOKEN`. The harness evaluates the official `English` and `Arabic` splits.

## BuddhismEval

Official source: https://huggingface.co/datasets/Nethmi14/BuddhismEval

The harness evaluates `english_eval` and `sinhala_eval` when the official Hugging Face dataset is reachable. It does not evaluate `parallel_corpus`.

## BibleQA

Official source: https://github.com/helen-jiahe-zhao/BibleQA

The harness evaluates `data/bible_qa/bible_qa_list_3_web.json` as the official candidate sentence-selection artifact. It does not use `bible_qa_train.csv`.

## CatholicBench

Public site: https://catholicbench.com/

CatholicBench is blocked until official scenarios and rubrics are provided. Public examples are not treated as official evaluation data.
