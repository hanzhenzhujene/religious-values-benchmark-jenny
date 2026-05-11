<!-- BLOCK: tldr -->
- Snapshot `jenny-religion-20260510` is owned by Jenny Zhu and dated 2026-05-11.
- Comparable completed cells with numeric accuracy: 15; total Done status cells: 15.
- Blocked/queued/TBD cells remain clearly labeled: 45.
- Best current comparable cell: DeepSeek-L on BibleQA at 0.952.
- Project cost snapshot: TBD.
- 4 benchmarks × 5 model families × 3 size slots = 60 cells; BibleQA is the only runnable benchmark; IslamTrust, CatholicBench, and BuddhismEval are blocked pending data access
<!-- /BLOCK: tldr -->

<!-- BLOCK: current-comparable-accuracy-table -->
| line | IslamTrust | CatholicBench | BuddhismEval | BibleQA |
| --- | --- | --- | --- | --- |
| Qwen-S |  |  |  | 0.928 |
| Qwen-M |  |  |  | 0.927 |
| Qwen-L |  |  |  | 0.946 |
| MiniMax-S |  |  |  | 0.940 |
| MiniMax-M |  |  |  | 0.930 |
| MiniMax-L |  |  |  | 0.934 |
| DeepSeek-S |  |  |  | 0.921 |
| DeepSeek-M |  |  |  | 0.903 |
| DeepSeek-L |  |  |  | 0.952 |
| Llama-S |  |  |  | 0.793 |
| Llama-M |  |  |  | 0.924 |
| Llama-L |  |  |  | 0.929 |
| Gemma-S |  |  |  | 0.817 |
| Gemma-M |  |  |  | 0.899 |
| Gemma-L |  |  |  | 0.886 |
<!-- /BLOCK: current-comparable-accuracy-table -->

<!-- BLOCK: family-size-progress-matrix -->
| line | IslamTrust | CatholicBench | BuddhismEval | BibleQA |
| --- | --- | --- | --- | --- |
| Qwen-S | Blocked | Blocked | Blocked | Done |
| Qwen-M | Blocked | Blocked | Blocked | Done |
| Qwen-L | Blocked | Blocked | Blocked | Done |
| MiniMax-S | Blocked | Blocked | Blocked | Done |
| MiniMax-M | Blocked | Blocked | Blocked | Done |
| MiniMax-L | Blocked | Blocked | Blocked | Done |
| DeepSeek-S | Blocked | Blocked | Blocked | Done |
| DeepSeek-M | Blocked | Blocked | Blocked | Done |
| DeepSeek-L | Blocked | Blocked | Blocked | Done |
| Llama-S | Blocked | Blocked | Blocked | Done |
| Llama-M | Blocked | Blocked | Blocked | Done |
| Llama-L | Blocked | Blocked | Blocked | Done |
| Gemma-S | Blocked | Blocked | Blocked | Done |
| Gemma-M | Blocked | Blocked | Blocked | Done |
| Gemma-L | Blocked | Blocked | Blocked | Done |
<!-- /BLOCK: family-size-progress-matrix -->

<!-- BLOCK: benchmark-difficulty-table -->
| benchmark | mean | best_line | best_val | worst_line | worst_val | spread |
| --- | --- | --- | --- | --- | --- | --- |
| IslamTrust |  |  |  |  |  |  |
| CatholicBench |  |  |  |  |  |  |
| BuddhismEval |  |  |  |  |  |  |
| BibleQA | 0.909 | DeepSeek-L | 0.952 | Llama-S | 0.793 | 0.158 |
<!-- /BLOCK: benchmark-difficulty-table -->

<!-- BLOCK: snapshot-metadata -->
| field | value |
| --- | --- |
| report_owner | Jenny Zhu |
| release_date | 2026-05-11 |
| snapshot_label | jenny-religion-20260510 |
| project_cost | TBD |
| matrix_description | 4 benchmarks × 5 model families × 3 size slots = 60 cells; BibleQA is the only runnable benchmark; IslamTrust, CatholicBench, and BuddhismEval are blocked pending data access |
| cost_breakdown | "TBD" |
<!-- /BLOCK: snapshot-metadata -->
