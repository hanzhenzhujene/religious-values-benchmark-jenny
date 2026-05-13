"""Inspect AI tasks for Jenny's assigned religion benchmarks."""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from typing import Any

from inspect_ai import Task, task
from inspect_ai.dataset import MemoryDataset, Sample

from evals._benchmark_utils import generation_plan
from evals.religion_utils import (
    BlockedBenchmarkError,
    as_int,
    exact_choice_scorer,
    first_existing_key,
    iter_limited,
    load_bibleqa_rows,
    load_buddhism_eval_rows,
    load_islamtrust_rows,
    parse_choices,
    prompt_for_mcq,
    resolve_correct_choice_index,
)


def _stable_reordered_choices(choices: list[str], correct_choice: int, seed: str) -> tuple[list[str], int]:
    """Deterministically shuffle options to reduce position-bias in prompted MC1 scoring."""
    indexed_choices = list(enumerate(choices, start=1))
    ranked = sorted(
        indexed_choices,
        key=lambda item: hashlib.sha256(f"{seed}:{item[0]}:{item[1]}".encode("utf-8")).hexdigest(),
    )
    reordered = [choice for _, choice in ranked]
    new_correct = next(
        position
        for position, (original_index, _) in enumerate(ranked, start=1)
        if original_index == correct_choice
    )
    return reordered, new_correct


def _equivalent_choice_targets(choices: list[str], correct_choice: int) -> list[str]:
    correct_text = " ".join(choices[correct_choice - 1].split())
    return [
        str(index)
        for index, choice in enumerate(choices, start=1)
        if " ".join(choice.split()) == correct_text
    ]


def _islamtrust_sample(index: int, row: dict[str, Any]) -> Sample:
    question_key = first_existing_key(row, "Question", "question")
    choices_key = first_existing_key(row, "Choices", "choices")
    correct_key = first_existing_key(row, "Correct_choice", "correct_choice", "correct_answer_index")
    if not question_key or not choices_key or not correct_key:
        raise ValueError(f"IslamTrust row is missing required fields: {sorted(row)}")

    choices = parse_choices(row[choices_key])
    correct_choice = as_int(row[correct_key])
    if correct_choice < 1 or correct_choice > len(choices):
        raise ValueError(f"IslamTrust correct choice {correct_choice} is outside 1-{len(choices)}")

    language = str(row.get("language") or row.get("Language") or "unknown")
    category = str(row.get("Type") or row.get("type") or "unknown")
    shuffle_seed = f"islamtrust:{language}:{index + 1}"
    prompted_choices, prompted_correct_choice = _stable_reordered_choices(choices, correct_choice, shuffle_seed)
    accepted_targets = _equivalent_choice_targets(prompted_choices, prompted_correct_choice)
    return Sample(
        id=f"islamtrust-{language.lower()}-{index + 1:04d}",
        input=prompt_for_mcq(str(row[question_key]), prompted_choices),
        target=accepted_targets if len(accepted_targets) > 1 else str(prompted_correct_choice),
        metadata={
            "benchmark": "IslamTrust",
            "language": language,
            "category": category,
            "source": row.get("Source") or row.get("source") or "",
            "num_options": len(prompted_choices),
            "original_correct_choice": correct_choice,
            "prompted_correct_choice": prompted_correct_choice,
            "accepted_correct_choices": accepted_targets,
            "shuffle_seed": shuffle_seed,
        },
    )


def _buddhism_eval_sample(index: int, row: dict[str, Any]) -> Sample:
    question_key = first_existing_key(row, "question", "Question")
    options_key = first_existing_key(row, "options", "Options", "choices", "Choices")
    correct_key = first_existing_key(row, "correct_answer", "Correct_answer", "answer", "Answer")
    if not question_key or not options_key or not correct_key:
        raise ValueError(f"BuddhismEval row is missing required fields: {sorted(row)}")

    choices = parse_choices(row[options_key])
    correct_index = resolve_correct_choice_index(choices, row[correct_key])
    config = str(row.get("config") or row.get("Config") or "unknown")
    return Sample(
        id=f"buddhism-eval-{config}-{index + 1:04d}",
        input=prompt_for_mcq(str(row[question_key]), choices),
        target=str(correct_index + 1),
        metadata={
            "benchmark": "BuddhismEval",
            "config": config,
            "q_label": row.get("q_label", row.get("Q_label", "")),
            "num_options": len(choices),
        },
    )


def _bibleqa_sample(index: int, row: dict[str, Any]) -> Sample:
    questions = row.get("question")
    labels = row.get("labels")
    answers = row.get("answers")
    if not isinstance(questions, list) or not questions:
        raise ValueError("BibleQA row must include a non-empty question list.")
    if not isinstance(labels, list) or not labels:
        raise ValueError("BibleQA row must include a non-empty labels list.")
    if not isinstance(answers, list) or not answers:
        raise ValueError("BibleQA row must include a non-empty answers list.")

    choices = parse_choices(answers[0])
    if len(choices) != len(labels):
        raise ValueError(f"BibleQA labels/options length mismatch: {len(labels)} != {len(choices)}")
    positive_indices = [idx for idx, label in enumerate(labels) if int(label) == 1]
    if len(positive_indices) != 1:
        raise ValueError(f"BibleQA expects exactly one positive label, got {positive_indices}")

    return Sample(
        id=f"bibleqa-web-{index + 1:04d}",
        input=prompt_for_mcq(str(questions[0]), choices),
        target=str(positive_indices[0] + 1),
        metadata={
            "benchmark": "BibleQA",
            "translation": "WEB",
            "num_options": len(choices),
        },
    )


def _select_samples(samples: list[Sample], *, start: int = 0, sample_ids: Sequence[str] | None = None) -> list[Sample]:
    if sample_ids:
        wanted = set(sample_ids)
        samples = [sample for sample in samples if sample.id in wanted]
        missing = wanted.difference(str(sample.id) for sample in samples)
        if missing:
            raise ValueError(f"Requested sample ids were not found: {sorted(missing)[:10]}")
        return samples
    return samples[start:]


def _source_limit(limit: int | None, start: int, sample_ids: Sequence[str] | None) -> int | None:
    if sample_ids or limit is None:
        return None
    return start + limit


def make_islamtrust_samples(
    limit: int | None = None,
    start: int = 0,
    sample_ids: Sequence[str] | None = None,
) -> list[Sample]:
    raw_limit = _source_limit(limit, start, sample_ids)
    samples = [_islamtrust_sample(index, row) for index, row in iter_limited(load_islamtrust_rows(), raw_limit)]
    selected = _select_samples(samples, start=start, sample_ids=sample_ids)
    return selected[:limit] if sample_ids and limit is not None else selected


def make_buddhism_eval_samples(
    limit: int | None = None,
    start: int = 0,
    sample_ids: Sequence[str] | None = None,
) -> list[Sample]:
    raw_limit = _source_limit(limit, start, sample_ids)
    samples = [_buddhism_eval_sample(index, row) for index, row in iter_limited(load_buddhism_eval_rows(), raw_limit)]
    selected = _select_samples(samples, start=start, sample_ids=sample_ids)
    return selected[:limit] if sample_ids and limit is not None else selected


def make_bibleqa_samples(
    limit: int | None = None,
    start: int = 0,
    sample_ids: Sequence[str] | None = None,
) -> list[Sample]:
    raw_limit = _source_limit(limit, start, sample_ids)
    samples = [_bibleqa_sample(index, row) for index, row in iter_limited(load_bibleqa_rows(), raw_limit)]
    selected = _select_samples(samples, start=start, sample_ids=sample_ids)
    return selected[:limit] if sample_ids and limit is not None else selected


@task
def islamtrust_mc1(
    limit: int | None = None,
    start: int = 0,
    sample_ids: Sequence[str] | None = None,
) -> Task:
    samples = make_islamtrust_samples(limit=limit, start=start, sample_ids=sample_ids)
    return Task(
        dataset=MemoryDataset(samples),
        plan=generation_plan(max_tokens=96),
        scorer=exact_choice_scorer(1, 8),
    )


@task
def buddhism_eval_mcq(
    limit: int | None = None,
    start: int = 0,
    sample_ids: Sequence[str] | None = None,
) -> Task:
    samples = make_buddhism_eval_samples(limit=limit, start=start, sample_ids=sample_ids)
    return Task(
        dataset=MemoryDataset(samples),
        plan=generation_plan(max_tokens=96),
        scorer=exact_choice_scorer(1, 6),
    )


@task
def bibleqa_sentence_selection(
    limit: int | None = None,
    start: int = 0,
    sample_ids: Sequence[str] | None = None,
) -> Task:
    samples = make_bibleqa_samples(limit=limit, start=start, sample_ids=sample_ids)
    return Task(
        dataset=MemoryDataset(samples),
        plan=generation_plan(max_tokens=96),
        scorer=exact_choice_scorer(1, 3),
    )


@task
def catholicbench_official(limit: int | None = None) -> Task:
    raise BlockedBenchmarkError(
        "CatholicBench is blocked under Jenny's official-data policy: requires author access / official export needed. "
        "Do not scrape the public dashboard or reconstruct benchmark scenarios. "
        "Set CATHOLICBENCH_DATA_FILE only after obtaining an official export."
    )


# The default suite includes only benchmarks that have official adapters.
# CatholicBench stays callable by name, but is intentionally excluded from the
# suite until official data/rubric access exists.
TASK_EXPORTS = [islamtrust_mc1, buddhism_eval_mcq, bibleqa_sentence_selection]
