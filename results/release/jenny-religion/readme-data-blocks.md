<!-- BLOCK: tldr -->
- Snapshot `jenny-religion-20260513-islamtrust-openrouter` is owned by Jenny Zhu and dated 2026-05-13.
- Comparable completed cells with numeric accuracy: 27; total Done status cells: 27.
- Blocked/queued/TBD cells remain clearly labeled: 33.
- Best current comparable cell: DeepSeek-L on BibleQA at 0.952.
- Project cost snapshot: TBD.
- 4 benchmarks × 5 model families × 3 size slots = 60 cells; BibleQA is complete across all 15 lines; IslamTrust is complete for the 12 OpenRouter lines and not run for MiniMax by request; CatholicBench and BuddhismEval are blocked pending official access/export
<!-- /BLOCK: tldr -->

<!-- BLOCK: current-comparable-accuracy-table -->
| line | IslamTrust | CatholicBench | BuddhismEval | BibleQA |
| --- | --- | --- | --- | --- |
| Qwen-S | 0.712 |  |  | 0.928 |
| Qwen-M | 0.763 |  |  | 0.927 |
| Qwen-L | 0.791 |  |  | 0.946 |
| DeepSeek-S | 0.813 |  |  | 0.921 |
| DeepSeek-M | 0.815 |  |  | 0.903 |
| DeepSeek-L | 0.831 |  |  | 0.952 |
| Llama-S | 0.485 |  |  | 0.793 |
| Llama-M | 0.579 |  |  | 0.924 |
| Llama-L | 0.732 |  |  | 0.929 |
| Gemma-S | 0.669 |  |  | 0.817 |
| Gemma-M | 0.746 |  |  | 0.899 |
| Gemma-L | 0.768 |  |  | 0.886 |
| MiniMax-S |  |  |  | 0.940 |
| MiniMax-M |  |  |  | 0.930 |
| MiniMax-L |  |  |  | 0.934 |
<!-- /BLOCK: current-comparable-accuracy-table -->

<!-- BLOCK: family-size-progress-matrix -->
| line | IslamTrust | CatholicBench | BuddhismEval | BibleQA |
| --- | --- | --- | --- | --- |
| Qwen-S | Done | Blocked | Blocked | Done |
| Qwen-M | Done | Blocked | Blocked | Done |
| Qwen-L | Done | Blocked | Blocked | Done |
| DeepSeek-S | Done | Blocked | Blocked | Done |
| DeepSeek-M | Done | Blocked | Blocked | Done |
| DeepSeek-L | Done | Blocked | Blocked | Done |
| Llama-S | Done | Blocked | Blocked | Done |
| Llama-M | Done | Blocked | Blocked | Done |
| Llama-L | Done | Blocked | Blocked | Done |
| Gemma-S | Done | Blocked | Blocked | Done |
| Gemma-M | Done | Blocked | Blocked | Done |
| Gemma-L | Done | Blocked | Blocked | Done |
| MiniMax-S | TBD | Blocked | Blocked | Done |
| MiniMax-M | TBD | Blocked | Blocked | Done |
| MiniMax-L | TBD | Blocked | Blocked | Done |
<!-- /BLOCK: family-size-progress-matrix -->

<!-- BLOCK: benchmark-difficulty-table -->
| benchmark | mean | best_line | best_val | worst_line | worst_val | spread |
| --- | --- | --- | --- | --- | --- | --- |
| IslamTrust | 0.725 | DeepSeek-L | 0.831 | Llama-S | 0.485 | 0.346 |
| CatholicBench |  |  |  |  |  |  |
| BuddhismEval |  |  |  |  |  |  |
| BibleQA | 0.909 | DeepSeek-L | 0.952 | Llama-S | 0.793 | 0.158 |
<!-- /BLOCK: benchmark-difficulty-table -->

<!-- BLOCK: snapshot-metadata -->
| field | value |
| --- | --- |
| report_owner | Jenny Zhu |
| release_date | 2026-05-13 |
| snapshot_label | jenny-religion-20260513-islamtrust-openrouter |
| project_cost | TBD |
| matrix_description | 4 benchmarks × 5 model families × 3 size slots = 60 cells; BibleQA is complete across all 15 lines; IslamTrust is complete for the 12 OpenRouter lines and not run for MiniMax by request; CatholicBench and BuddhismEval are blocked pending official access/export |
| cost_breakdown | "TBD" |
<!-- /BLOCK: snapshot-metadata -->
