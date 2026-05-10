# Jenny Religious Values Benchmark Harness

This repo is Jenny's personal public backup/workspace for the CEI religious-values benchmark runs. The official CEI repository is kept as `upstream`; do not push there directly unless Jenny explicitly asks.

## Jenny's Assigned Benchmarks

| ID | Benchmark | Task | Status |
| --- | --- | --- | --- |
| #35 | IslamTrust | `islamtrust_mc1` | Gated HF access required |
| #47 | CatholicBench | `catholicbench_official` | Blocked until official scenarios/rubrics are available |
| #26 | BuddhismEval | `buddhism_eval_mcq` | Official HF eval configs required |
| #37 | BibleQA | `bibleqa_sentence_selection` | Official GitHub artifact |

Strict data policy: official test/eval data only. Blocked benchmarks stay blocked instead of being replaced with public examples or synthetic data.

## Quick Start

```bash
make setup
cp .env.example .env
make access
make test
make smoke
```

## Full Matrix

```bash
./scripts/run_jenny_religion.sh --max-conn 8
```

The model matrix is inherited from the moral-psychology benchmark. Qwen, DeepSeek, Llama, and Gemma use OpenRouter. MiniMax uses the direct MiniMax API.

## Outputs

- Raw run logs: `results/inspect/full-runs/`
- Inspect archives: `results/inspect/logs/`
- Release tables: `results/release/jenny-religion/`
- Release figures: `figures/release/`

See [docs/data-access.md](docs/data-access.md) and [docs/reproducibility.md](docs/reproducibility.md).
