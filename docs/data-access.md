# Data Access

## IslamTrust

Official source: https://huggingface.co/datasets/Abderraouf000/IslamTrust-benchmark

This dataset is gated, and Jenny's account currently has accepted access. Set `HF_TOKEN` or `HUGGING_FACE_HUB_TOKEN`, or run `hf auth login` and leave `HF_USE_CACHED_TOKEN=1`. The harness evaluates the official `English` and `Arabic` splits.

## BuddhismEval

Official source: https://huggingface.co/datasets/Nethmi14/BuddhismEval

The harness first tries the official/private candidate `Nethmi14/BuddhismEval`. If Hugging Face returns unauthorized/no access, the benchmark is marked `official dataset inaccessible / permission required`. Jenny will email the author to request access.

The harness evaluates `english_eval` and `sinhala_eval` only when the official Hugging Face dataset is reachable. It does not evaluate `parallel_corpus`, and it must not use `vanloc1808/BuddhismEval-vi-augmented` as the official BuddhismEval result.

## BibleQA

Official source: https://github.com/helen-jiahe-zhao/BibleQA

The harness evaluates `data/bible_qa/bible_qa_list_3_web.json` as the official candidate sentence-selection artifact. It does not use `bible_qa_train.csv`.

## CatholicBench

Public site: https://catholicbench.com/

CatholicBench is blocked until author access or an official export is provided. Public dashboard/browser content is visible, but no official downloadable dataset/API/repository has been found. Do not scrape or reconstruct it as official data. Jenny will email the author to request access.
