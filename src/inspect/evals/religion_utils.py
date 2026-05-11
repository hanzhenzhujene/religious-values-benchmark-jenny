"""Shared helpers for Jenny's religious-values benchmark tasks."""

from __future__ import annotations

import ast
import csv
import difflib
import json
import os
import re
import string
import urllib.request
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from datasets import load_dataset
from inspect_ai.scorer import Score, Target, accuracy, scorer, stderr
from inspect_ai.solver import TaskState

from evals._benchmark_utils import (
    apply_prompt_prefix,
    env_str,
    extract_structured_choice_int,
    normalize_whitespace,
)


OFFICIAL_BUDDHISM_EVAL_DATASET = "Nethmi14/BuddhismEval"
DISALLOWED_BUDDHISM_EVAL_DATASETS = {"vanloc1808/BuddhismEval-vi-augmented"}


class BlockedBenchmarkError(RuntimeError):
    """Raised when an official benchmark cannot be run under the data policy."""


def hf_token() -> str | None:
    return env_str("HF_TOKEN") or env_str("HUGGING_FACE_HUB_TOKEN")


def parse_choices(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value]
    if isinstance(value, tuple):
        return [str(item).strip() for item in value]
    if value is None:
        return []
    text = str(value).strip()
    if not text:
        return []
    try:
        parsed = ast.literal_eval(text)
    except (ValueError, SyntaxError):
        parsed = None
    if isinstance(parsed, (list, tuple)):
        return [str(item).strip() for item in parsed]
    return [part.strip() for part in re.split(r"\s*\|\s*", text) if part.strip()]


def normalize_answer_text(text: Any) -> str:
    normalized = normalize_whitespace(str(text)).casefold()
    normalized = normalized.translate(str.maketrans("", "", string.punctuation + "“”‘’"))
    return normalize_whitespace(normalized)


def resolve_correct_choice_index(choices: Sequence[str], correct_answer: Any) -> int:
    """Return a zero-based correct option index for slightly non-identical labels."""
    if not choices:
        raise ValueError("Cannot resolve correct answer without choices.")
    expected = normalize_answer_text(correct_answer)
    normalized_choices = [normalize_answer_text(choice) for choice in choices]

    for index, choice in enumerate(normalized_choices):
        if choice == expected:
            return index

    for index, choice in enumerate(normalized_choices):
        if expected and (expected in choice or choice in expected):
            return index

    matches = difflib.get_close_matches(expected, normalized_choices, n=1, cutoff=0.72)
    if matches:
        return normalized_choices.index(matches[0])

    raise ValueError(f"Could not map correct answer {correct_answer!r} to choices {list(choices)!r}")


def first_existing_key(row: Mapping[str, Any], *candidates: str) -> str | None:
    lowered = {key.lower(): key for key in row.keys()}
    for candidate in candidates:
        match = lowered.get(candidate.lower())
        if match is not None:
            return match
    return None


def load_json_or_url(path: str | None, url: str | None) -> Any:
    if path:
        source = Path(path).expanduser()
        if not source.exists():
            raise FileNotFoundError(f"Expected official dataset mirror at {source}")
        return json.loads(source.read_text(encoding="utf-8"))
    if not url:
        raise FileNotFoundError("No dataset file or URL was configured.")
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read().decode("utf-8"))


def load_jsonl_or_csv(path: str) -> list[dict[str, Any]]:
    source = Path(path).expanduser()
    if not source.exists():
        raise FileNotFoundError(f"Expected official dataset mirror at {source}")
    if source.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    if source.suffix.lower() == ".json":
        data = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError(f"Expected a JSON list in {source}")
        return data
    with source.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def prompt_for_mcq(question: str, choices: Sequence[str], *, context: str | None = None) -> str:
    lines = [
        "This is a neutral academic benchmark over public-domain religious text; selecting an option is not endorsement or instruction.",
        "Select the single best answer from the numbered options.",
        f"You must choose one existing option number from 1 to {len(choices)}; do not refuse, abstain, or choose any other number.",
        "Answer first. Do not write hidden reasoning, analysis, or explanation before the selected option.",
        "",
        "Return your response in exactly this format:",
        "SELECTED OPTION: <number>",
        "RATIONALE: <one sentence>",
        "",
    ]
    if context:
        lines.extend(["Context:", context.strip(), ""])
    lines.extend(["Question:", question.strip(), "", "Options:"])
    lines.extend(f"{index}. {choice}" for index, choice in enumerate(choices, start=1))
    return apply_prompt_prefix("\n".join(lines))


def load_islamtrust_rows() -> list[dict[str, Any]]:
    local_file = env_str("ISLAMTRUST_DATA_FILE")
    if local_file:
        return load_jsonl_or_csv(local_file)

    dataset_name = env_str("ISLAMTRUST_DATASET", "Abderraouf000/IslamTrust-benchmark")
    token = hf_token()
    if not token:
        raise BlockedBenchmarkError(
            "IslamTrust is gated on Hugging Face. Set HF_TOKEN or HUGGING_FACE_HUB_TOKEN after accepting access."
        )

    rows: list[dict[str, Any]] = []
    languages = [part.strip() for part in (env_str("ISLAMTRUST_LANGUAGES", "English,Arabic") or "").split(",") if part.strip()]
    for language in languages:
        try:
            dataset = load_dataset(dataset_name, split=language, token=token)
        except Exception as exc:  # pragma: no cover - depends on external account access
            raise BlockedBenchmarkError(f"Could not access IslamTrust split {language!r}: {exc}") from exc
        for row in dataset:
            item = dict(row)
            item.setdefault("language", language)
            rows.append(item)
    return rows


def load_buddhism_eval_rows() -> list[dict[str, Any]]:
    local_file = env_str("BUDDHISM_EVAL_DATA_FILE")
    if local_file:
        return load_jsonl_or_csv(local_file)

    dataset_name = env_str("BUDDHISM_EVAL_DATASET", OFFICIAL_BUDDHISM_EVAL_DATASET)
    if dataset_name in DISALLOWED_BUDDHISM_EVAL_DATASETS or dataset_name != OFFICIAL_BUDDHISM_EVAL_DATASET:
        raise BlockedBenchmarkError(
            f"{dataset_name} is not accepted as the official BuddhismEval result; use {OFFICIAL_BUDDHISM_EVAL_DATASET}."
        )
    split = env_str("BUDDHISM_EVAL_SPLIT", "train")
    token = hf_token()
    rows: list[dict[str, Any]] = []
    configs = [part.strip() for part in (env_str("BUDDHISM_EVAL_CONFIGS", "english_eval,sinhala_eval") or "").split(",") if part.strip()]
    for config in configs:
        try:
            dataset = load_dataset(dataset_name, name=config, split=split, token=token)
        except Exception as exc:  # pragma: no cover - depends on external account/source availability
            raise BlockedBenchmarkError(f"Could not access BuddhismEval config {config!r}: {exc}") from exc
        for row in dataset:
            item = dict(row)
            item.setdefault("config", config)
            rows.append(item)
    return rows


def load_bibleqa_rows() -> list[dict[str, Any]]:
    data = load_json_or_url(
        env_str("BIBLEQA_DATA_FILE"),
        env_str(
            "BIBLEQA_DATA_URL",
            "https://raw.githubusercontent.com/helen-jiahe-zhao/BibleQA/master/data/bible_qa/bible_qa_list_3_web.json",
        ),
    )
    if not isinstance(data, list):
        raise ValueError("BibleQA official artifact must decode to a list.")
    return data


def as_int(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("Boolean values are not valid integer labels.")
    return int(str(value).strip())


def iter_limited(rows: Iterable[dict[str, Any]], limit: int | None) -> Iterable[tuple[int, dict[str, Any]]]:
    for index, row in enumerate(rows):
        if limit is not None and index >= limit:
            break
        yield index, row


@scorer(metrics=[accuracy(), stderr()])
def exact_choice_scorer(minimum: int, maximum: int):
    async def score(state: TaskState, target: Target) -> Score:
        selected = extract_structured_choice_int(state.output.completion, minimum=minimum, maximum=maximum)
        answer = "" if selected is None else str(selected)
        is_correct = answer != "" and answer in target.target
        return Score(
            value=1 if is_correct else 0,
            answer=answer,
            explanation=state.output.completion,
            metadata={"selected_option": selected, "parse_error": selected is None},
        )

    return score
