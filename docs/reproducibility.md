# Reproducibility

Jenny's religion harness uses the same Inspect-style runner pattern as the moral-psychology benchmark, with a stricter data gate: official data only.

## Setup

```bash
make setup
cp .env.example .env
```

Fill in:

- `OPENROUTER_API_KEY` for Qwen, DeepSeek, Llama, and Gemma
- `MINIMAX_API_KEY` for MiniMax
- `HF_TOKEN` or `HUGGING_FACE_HUB_TOKEN` after accepting gated IslamTrust access

## Data Access Gate

```bash
make access
```

Blocked benchmarks are expected when official access is missing. CatholicBench is intentionally blocked until official scenarios and rubrics are available.

## Tests

```bash
make test
```

The test suite verifies parsing, official-data adapters, task construction from small local mirrors, and release summary aggregation.

## Smoke Run

```bash
make smoke
```

This runs a 2-sample smoke test on accessible official tasks only. In a fresh environment without HF access, BibleQA is usually the only accessible task.

## Full Run

```bash
./scripts/run_jenny_religion.sh --max-conn 3
```

Use `--models` with 1-based indices to run subsets. Raw logs are written under `results/inspect/full-runs/<run-id>/` and Inspect `.eval` archives under `results/inspect/logs/<run-id>/`.
For failed-cell reruns, use the same command with `--models` and a fresh `--run-id` so provenance stays separate.

## Release Artifacts

```bash
make release
```

Outputs are written to `results/release/jenny-religion/` and `figures/release/`.
