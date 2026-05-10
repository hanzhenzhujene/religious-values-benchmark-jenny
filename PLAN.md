# Religion Benchmark Run Plan

## Context

- The `moral-psychology-benchmark` repo has working infrastructure (Inspect AI runner, OpenRouter client, model config, Makefile)
- This repo is empty — just scaffolding
- Joseph's assigned benchmarks (6 distinct benchmarks, each gets its own task file and result path):
  - **QASiNa (#42)** — Quranic sciences QA
  - **FatwaSet-Classify (#44)** — fatwa classification by ruling type
  - **FatwaSet-QA (#45)** — fatwa question answering
  - **FaithBench (#TGC)** — theological/Christian knowledge (canonical ID: `faithbench`)
  - **HAQA** — Hadith QA
  - **QUQA** — Quran QA

> **Note on #44/#45:** These are two distinct benchmarks from the same FatwaSet corpus.
> #44 is a classification task (categorize rulings); #45 is an extractive/generative QA task.
> They get separate task files, separate result directories, and separate reporting.
>
> **Note on HAQA/QUQA:** These are two independent datasets (Hadith vs Quran) that happen to
> share a similar QA format. They get separate task files and separate reporting.

## Phase 1: Setup infrastructure

1. Copy harness skeleton from `moral-psychology-benchmark` (config.py, client.py, Makefile, src/inspect/ structure, .env.example)
2. Adapt `config.py` with religion benchmark IDs and same model matrix
3. Set up `.env` with OpenRouter key

## Phase 2: Find & load datasets

| # | Benchmark | Likely source | Format | Separate from |
|---|-----------|--------------|--------|---------------|
| 42 | QASiNa | HuggingFace / paper | MC or short-answer QA on Quranic sciences | — |
| 44 | FatwaSet-Classify | HuggingFace / paper | Classification of Islamic rulings | #45 (same corpus, different task) |
| 45 | FatwaSet-QA | HuggingFace / paper | QA over fatwa texts | #44 (same corpus, different task) |
| — | FaithBench (aka TGC) | GitHub / paper | Theological questions (Christian). ID: `faithbench` | — |
| — | HAQA | HuggingFace | Hadith-based QA | QUQA (different source text) |
| — | QUQA | HuggingFace | Quran-based QA | HAQA (different source text) |

4. Research each dataset: find HuggingFace links, paper DOIs, download method
5. Download datasets locally to `data/<benchmark_id>/`
6. **Pin dataset versions** — record in `data/<benchmark_id>/MANIFEST.md`:
   - HuggingFace dataset revision hash or GitHub commit SHA
   - Download date
   - Any preprocessing applied (with script in `scripts/preprocess_<id>.py`)
   - License and usage constraints
   - Row count and split info

## Phase 3: Define scoring strategy

Before writing task files, define how each benchmark is scored:

| Benchmark | Task type | Scoring method | Notes |
|-----------|-----------|---------------|-------|
| QASiNa (#42) | MC or short-answer | Exact match (MC) or F1/EM (short-answer) | TBD after dataset inspection |
| FatwaSet-Classify (#44) | Classification | Accuracy, macro-F1 over ruling categories | Extract predicted class from free-form output via regex |
| FatwaSet-QA (#45) | Extractive/generative QA | F1 / EM against reference answers | Normalize Arabic text before comparison |
| FaithBench | MC or open-ended | Accuracy (MC) or LLM-as-judge (open) | See "LLM-as-judge protocol" below |
| HAQA | QA over Hadith | F1 / EM | Arabic + English; normalize both |
| QUQA | QA over Quran | F1 / EM | Arabic + English; normalize both |

### LLM-as-judge protocol (for rubric-scored benchmarks)

If FaithBench or any other benchmark requires open-ended rubric scoring:

- **Judge model:** GPT-4o via OpenRouter (`openai/gpt-4o`), pinned to a specific snapshot date
- **Prompt template:** Committed to `src/inspect/evals/data/judge_templates/<benchmark_id>.txt`
- **Scoring output:** Structured JSON (score 1-5 per rubric dimension + rationale)
- **Versioning:** Judge template has a semver in its header; any change = new version, old results not overwritten
- **Inter-rater reliability:** On first run, manually score 20 samples to compute agreement (Cohen's kappa >= 0.7 required before full run)
- **Determinism:** temperature=0, seed fixed, retry on API error (max 3 retries)
- **Fallback:** If agreement < 0.7, downgrade to MC-only subset or flag benchmark as "provisional"

**Open decisions (resolve during Phase 2 dataset inspection):**
- Which benchmarks are multiple-choice vs free-form?
- For free-form: what answer extraction regex/parser is needed?
- For Arabic text: what normalization (diacritics removal, alif/ya unification)?
- For FatwaSet: are there multiple valid rulings per question? If yes, use set-match scoring.

## Phase 4: Write Inspect AI task files

7. Create `src/inspect/evals/qasina.py`
8. Create `src/inspect/evals/fatwaset_classify.py`
9. Create `src/inspect/evals/fatwaset_qa.py`
10. Create `src/inspect/evals/faithbench.py`
11. Create `src/inspect/evals/haqa.py`
12. Create `src/inspect/evals/quqa.py`
13. Register all in `src/inspect/evals/religion.py` task registry
14. Each task file includes its scorer (from Phase 3 decisions)

## Phase 4b: Scorer tests (gate before full runs)

15. Write unit tests in `tests/test_scorers.py` covering:
    - EM/F1 scorers: empty output, exact match, partial match, Arabic normalization edge cases
    - Classification scorer: valid class, invalid class, multi-label edge case
    - LLM-as-judge (if used): mock judge response parsing, malformed JSON handling, retry logic
16. Write integration tests in `tests/test_<benchmark_id>.py` for each task:
    - Load 2-3 real samples from dataset
    - Run through task pipeline with a mocked model response
    - Assert scorer produces expected metric values
17. Run `make test` — **all tests must pass before proceeding to Phase 5**
18. Verify coverage >= 80% on scorer modules

## Phase 5: Run & validate

19. Smoke test each benchmark (limit=2, one small model) — verify output format and scoring pipeline produce valid metrics
20. Full run across model matrix (5 families × 3 sizes)
21. Export results to `results/<benchmark_id>/<timestamp>/`
22. Each benchmark has its own result directory — no merged outputs

## Model Matrix

Inherited from `moral-psychology-benchmark`. Note: L/M/S labels reflect **capability tier within each family**, not raw parameter count. DeepSeek's "S" is a 70B distilled model because R1-distill-70B is the smallest performant DeepSeek variant available via OpenRouter.

| Family | L (largest/flagship) | M (mid) | S (smallest available) |
|--------|---------------------|---------|----------------------|
| Qwen | qwen3-235b-a22b | qwen3-32b | qwen3-8b |
| DeepSeek | deepseek-r1 | deepseek-chat-v3.1 | deepseek-r1-distill-llama-70b |
| Llama | llama-3.3-70b | llama-3.1-8b | llama-3.2-3b |
| Gemma | gemma-3-27b-it | gemma-3-12b-it | gemma-3-4b-it |
| MiniMax | minimax-m2.5 | minimax-m1 | minimax-01 |

> **Why DeepSeek S = 70B:** DeepSeek does not offer a small (<10B) chat model on OpenRouter.
> The distilled 70B is the lowest-cost DeepSeek option with acceptable instruction-following.
> If a true small model becomes available, swap it in.

## Jenny's assigned benchmarks (for reference)

- #35 IslamTrust
- #47 CatholicBench
- #26 BuddhismEval
- #37 BibleQA

## Reproducibility checklist

Before any full run:
- [ ] All datasets pinned with revision hash in `data/<id>/MANIFEST.md`
- [ ] Preprocessing scripts committed (if any transforms applied)
- [ ] Licenses reviewed — no dataset prohibits benchmark use
- [ ] Scoring functions have unit tests (edge cases: empty output, multilingual, multi-answer)
- [ ] `.env.example` updated with all required env vars for religion benchmarks
