# Jenny Religious Values Benchmark Suite

[![CI](https://github.com/hanzhenzhujene/religious-values-benchmark-jenny/actions/workflows/ci.yml/badge.svg)](https://github.com/hanzhenzhujene/religious-values-benchmark-jenny/actions/workflows/ci.yml)

Jenny Zhu's public release workspace for her assigned CEI religious-values benchmark harness runs.

> Project cost: TBD. Cost breakdown: TBD.

## TL;DR

- BibleQA is complete across all 15 model lines; IslamTrust, CatholicBench, and BuddhismEval remain blocked pending official data access or author export.
- Best current comparable cell: DeepSeek-L on BibleQA at 0.9515.
- BibleQA mean accuracy is 0.9087, with spread 0.1580 from Llama-S at 0.7935 to DeepSeek-L at 0.9515.
- DeepSeek-S was recovered from the earlier empty-output failure to 0.9210 using a 2048-token full rerun plus targeted rebounds; one persistent max-token empty response is counted incorrect.
- Current matrix status: 15 Done cells and 45 Blocked cells. No proxy, scrape, synthetic, or train-split scores are reported as official results.

## Results

Metric definition version: 2026-05-11. BibleQA is scored as exact candidate sentence selection accuracy on the official `bible_qa_list_3_web.json` artifact.

| Line | IslamTrust | CatholicBench | BuddhismEval | BibleQA | Note |
| --- | --- | --- | --- | ---: | --- |
| Qwen-S | n/a | n/a | n/a | 0.9278 | Complete. |
| Qwen-M | n/a | n/a | n/a | 0.9266 | Complete after reasoning-output rebound. |
| Qwen-L | n/a | n/a | n/a | 0.9458 | Second-highest current cell. |
| MiniMax-S | n/a | n/a | n/a | 0.9402 | MiniMax direct API. |
| MiniMax-M | n/a | n/a | n/a | 0.9300 | MiniMax direct API. |
| MiniMax-L | n/a | n/a | n/a | 0.9345 | MiniMax direct API. |
| DeepSeek-S | n/a | n/a | n/a | 0.9210 | 2048-token rerun plus targeted rebounds; 1 persistent empty counted incorrect. |
| DeepSeek-M | n/a | n/a | n/a | 0.9029 | Complete. |
| DeepSeek-L | n/a | n/a | n/a | 0.9515 | Highest current cell; recovered from original runtime error. |
| Llama-S | n/a | n/a | n/a | 0.7935 | Lowest current BibleQA cell. |
| Llama-M | n/a | n/a | n/a | 0.9244 | 1 persistent refusal counted incorrect. |
| Llama-L | n/a | n/a | n/a | 0.9289 | Complete after targeted parse rebounds. |
| Gemma-S | n/a | n/a | n/a | 0.8172 | Complete. |
| Gemma-M | n/a | n/a | n/a | 0.8995 | Highest Gemma slot. |
| Gemma-L | n/a | n/a | n/a | 0.8860 | Complete after targeted parse rebound. |

`n/a` means the benchmark is blocked under the official-data policy, not that the model scored zero. The machine-readable version is saved at [benchmark-comparison.csv](results/release/jenny-religion/benchmark-comparison.csv).

## Visual Summary

[![Benchmark accuracy bars](figures/release/rel_benchmark_accuracy_bars.svg)](figures/release/rel_benchmark_accuracy_bars.svg)
*[Caption: BibleQA is the only benchmark with comparable numeric accuracy in this snapshot; blocked benchmarks remain n/a.]*

[![Accuracy heatmap](figures/release/rel_accuracy_heatmap.svg)](figures/release/rel_accuracy_heatmap.svg)
*[Caption: Darker cells indicate higher BibleQA accuracy; hatched cells mark official-data blocks.]*

[![Family scaling profile](figures/release/rel_family_scaling_profile.svg)](figures/release/rel_family_scaling_profile.svg)
*[Caption: Size-slot patterns are shown only for BibleQA, so these lines are diagnostic rather than general scaling claims.]*

[![Coverage matrix](figures/release/rel_coverage_matrix.svg)](figures/release/rel_coverage_matrix.svg)
*[Caption: Coverage separates the completed BibleQA column from the three blocked benchmark columns.]*

Additional generated figures are available in [figures/release/](figures/release/), including progress overview and benchmark difficulty profile.

## Model Matrix

Small, Medium, and Large are planning slots inherited from the shared moral-psychology/Joseph matrix. They are not vendor taxonomy labels and do not always correspond to raw parameter count; DeepSeek-S is the R1-distill 70B route because that is the smallest performant DeepSeek option available through OpenRouter for this setup.

| Family | Small slot | Medium slot | Large slot | Route |
| --- | --- | --- | --- | --- |
| Qwen | `qwen/qwen3-8b` | `qwen/qwen3-32b` | `qwen/qwen3-235b-a22b` | OpenRouter |
| DeepSeek | `deepseek-r1-distill-llama-70b` | `deepseek-chat-v3.1` | `deepseek-r1` | OpenRouter |
| Llama | `llama-3.2-3b` | `llama-3.1-8b` | `llama-3.3-70b` | OpenRouter |
| Gemma | `gemma-3-4b-it` | `gemma-3-12b-it` | `gemma-3-27b-it` | OpenRouter |
| MiniMax | `minimax-01` | `minimax-m1` | `minimax-m2.5` | MiniMax API |

## Benchmark Status

| ID | Benchmark | Harness task | Data status | What is reported now |
| --- | --- | --- | --- | --- |
| #35 | IslamTrust | `islamtrust_mc1` | Blocked | HF access requested; no official test/eval score yet. |
| #47 | CatholicBench | `catholicbench_official` | Blocked | Requires author access or official export; public dashboard is not scraped. |
| #26 | BuddhismEval | `buddhism_eval_mcq` | Blocked | Official dataset inaccessible; permission required. |
| #37 | BibleQA | `bibleqa_sentence_selection` | Done | Exact sentence-selection accuracy across all 15 model lines. |

Strict data policy: this release uses official test/eval data only. If official data is gated, private, or unavailable, the benchmark is marked Blocked and no public scrape, synthetic substitute, train split, or proxy dataset is treated as the official result.

## Interpretation

| Claim | Evidence | Reading |
| --- | --- | --- |
| Strongest line | DeepSeek-L reaches 0.9515 on BibleQA; Qwen-L follows at 0.9458. | The top cells are close, so this should be read as a snapshot result rather than a broad claim. |
| Hardest measured point | BibleQA spread is 0.1580 across lines. | The task separates weaker and stronger lines, but only one benchmark is currently runnable. |
| Scaling pattern | Qwen, MiniMax, DeepSeek, and Gemma are non-monotonic on BibleQA; Llama is monotonic in this snapshot. | One benchmark is not enough to infer a general scaling law. |
| Access limitation | 45 of 60 matrix cells are Blocked. | The release is intentionally honest about missing official data rather than filling gaps with proxies. |

## Method

1. Register Jenny's four assigned benchmarks and require an official test/eval source before any score enters the comparable matrix.
2. Use temperature 0 and bounded multiple-choice parsing for BibleQA.
3. Route Qwen, DeepSeek, Llama, and Gemma through OpenRouter; route MiniMax through the MiniMax API.
4. Treat provider/runtime failures as rebound candidates. Rerun only missing or unparseable sample IDs, not full cells, unless a full rerun is necessary.
5. Build public CSVs and SVGs from canonical source snapshots under [results/release/jenny-religion/source/](results/release/jenny-religion/source/).

## Reproducibility

| Goal | Command | Requires secrets? |
| --- | --- | --- |
| Rebuild public CSVs and SVGs | `make bootstrap` | No |
| Run unit/task tests | `make test` | No |
| Live smoke test | `make setup && cp .env.example .env && make smoke` | Yes |

Live smoke runs need `OPENROUTER_API_KEY` for OpenRouter-backed families and `MINIMAX_API_KEY` for MiniMax. Gated benchmark access uses `HF_TOKEN` or `HUGGING_FACE_HUB_TOKEN`, plus optional official local export paths such as `BIBLEQA_DATA_FILE`, `ISLAMTRUST_DATA_FILE`, `BUDDHISM_EVAL_DATA_FILE`, and `CATHOLICBENCH_DATA_FILE`.

## Repository Map

```text
.github/                                  # CI workflow
data/                                     # Official-data manifests and local mirror slots
docs/                                     # Data-access and reproducibility notes
figures/release/                          # Public SVG figures
results/release/jenny-religion/           # Public CSVs, source snapshots, and release notes
results/inspect/                          # Local Inspect logs and rebound provenance; raw logs are gitignored
scripts/                                  # Dataset checks, runner, rebound planner, release builder
src/inspect/                              # Inspect task builders and scoring utilities
tests/                                    # Unit and task-construction tests
Makefile                                  # Setup, test, smoke, release, bootstrap targets
pyproject.toml                            # Python package and uv workspace configuration
```

## Data Flow

```text
Official benchmark inputs
  -> Inspect task builders (src/inspect/evals/)
  -> Runner scripts
  -> OpenRouter / MiniMax API
  -> Inspect outputs
  -> Source snapshots
  -> scripts/build_release_artifacts.py
  -> Public CSVs and SVG figures
```

## Source Links

| Benchmark | Source/access | What this repo tests now |
| --- | --- | --- |
| IslamTrust | [HF gated dataset card](https://huggingface.co/datasets/Abderraouf000/IslamTrust-benchmark), [source repo](https://github.com/aii-lab-dot-org/IslamTrust) | Not yet run; access requested. |
| CatholicBench | [Public dashboard](https://catholicbench.com/) | Not yet run; official export required. |
| BuddhismEval | [Official dataset candidate](https://huggingface.co/datasets/Nethmi14/BuddhismEval) | Not yet run; permission required. |
| BibleQA | [arXiv:1810.12118](https://arxiv.org/abs/1810.12118), [official GitHub](https://github.com/helen-jiahe-zhao/BibleQA) | Exact sentence-selection accuracy on `bible_qa_list_3_web.json`. |

## Snapshot

| Field | Value |
| --- | --- |
| Report owner | Jenny Zhu |
| Repo update date | 2026-05-11 |
| Release snapshot | `jenny-religion-20260510` |
| Matrix description | 4 benchmarks x 5 model families x 3 size slots = 60 cells |
| Completed cells | 15 BibleQA cells |
| Blocked cells | 45 official-data/access cells |
| Best comparable cell | DeepSeek-L on BibleQA, 0.9515 |
| Cost | TBD |

## Important Notes

- Blocked means official data or author export is unavailable; it is not an invitation to scrape or reconstruct the benchmark.
- No proxy-only accuracy numbers are reported in this snapshot.
- `n/a` cells are missing official comparable scores, not model failures.
- The BibleQA result is a candidate-selection score and should not be generalized to doctrine, pastoral reasoning, or cross-tradition value alignment without the blocked benchmarks running.
- Family size slots are planning labels; one runnable benchmark is not enough for a general scaling-law claim.

## Citation

Repository citation metadata is in [CITATION.cff](CITATION.cff). Benchmark-specific sources are listed in [Source Links](#source-links).
