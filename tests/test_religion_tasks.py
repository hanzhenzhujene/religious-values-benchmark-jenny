from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "inspect"))

from evals.religion import (  # noqa: E402
    make_bibleqa_samples,
    make_buddhism_eval_samples,
    make_islamtrust_samples,
)
from evals.religion_utils import BlockedBenchmarkError  # noqa: E402


def test_make_islamtrust_samples_from_local_official_mirror(tmp_path, monkeypatch):
    data_path = tmp_path / "islamtrust.json"
    data_path.write_text(
        json.dumps(
            [
                {
                    "Question": "Which answer is aligned?",
                    "choices": "['Wrong', 'Right', 'Other']",
                    "Correct_choice": "2",
                    "Type": "General",
                    "Source": "fixture",
                    "language": "English",
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("ISLAMTRUST_DATA_FILE", str(data_path))

    samples = make_islamtrust_samples()

    assert len(samples) == 1
    assert f"{samples[0].target}. Right" in samples[0].input
    assert samples[0].metadata["category"] == "General"
    assert samples[0].metadata["original_correct_choice"] == 2


def test_islamtrust_accepts_duplicate_correct_option_aliases(tmp_path, monkeypatch):
    data_path = tmp_path / "islamtrust.json"
    data_path.write_text(
        json.dumps(
            [
                {
                    "Question": "Which duplicated answer is aligned?",
                    "choices": "['Wrong', 'Right', 'Right']",
                    "Correct_choice": "2",
                    "Type": "General",
                    "Source": "fixture",
                    "language": "English",
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("ISLAMTRUST_DATA_FILE", str(data_path))

    sample = make_islamtrust_samples()[0]

    assert sorted(sample.metadata["accepted_correct_choices"]) == sorted(sample.target)
    assert len(sample.metadata["accepted_correct_choices"]) == 2


def test_make_buddhism_eval_samples_from_local_official_mirror(tmp_path, monkeypatch):
    data_path = tmp_path / "buddhism.json"
    data_path.write_text(
        json.dumps(
            [
                {
                    "question": "According to the Dhammapada, what follows a pure mind?",
                    "options": "['Suffering', 'Happiness follows, like a shadow that never departs.', 'Karma is neutral']",
                    "correct_answer": "Happiness follows, like a shadow that never departs",
                    "q_label": 1,
                    "config": "english_eval",
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("BUDDHISM_EVAL_DATA_FILE", str(data_path))

    samples = make_buddhism_eval_samples()

    assert len(samples) == 1
    assert samples[0].target == "2"
    assert samples[0].metadata["config"] == "english_eval"


def test_buddhism_eval_rejects_augmented_substitute(monkeypatch):
    monkeypatch.delenv("BUDDHISM_EVAL_DATA_FILE", raising=False)
    monkeypatch.setenv("BUDDHISM_EVAL_DATASET", "vanloc1808/BuddhismEval-vi-augmented")

    with pytest.raises(BlockedBenchmarkError):
        make_buddhism_eval_samples()


def test_make_bibleqa_samples_from_local_official_artifact(tmp_path, monkeypatch):
    data_path = tmp_path / "bibleqa.json"
    data_path.write_text(
        json.dumps(
            [
                {
                    "question": ["What was the name of Jesus' mother?"] * 3,
                    "labels": [0, 0, 1],
                    "answers": [["Wrong verse 1", "Wrong verse 2", "Mary verse"]],
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("BIBLEQA_DATA_FILE", str(data_path))

    samples = make_bibleqa_samples()

    assert len(samples) == 1
    assert samples[0].target == "3"
    assert samples[0].metadata["translation"] == "WEB"


def test_make_bibleqa_samples_filters_exact_sample_ids(tmp_path, monkeypatch):
    data_path = tmp_path / "bibleqa.json"
    rows = []
    for index in range(3):
        rows.append(
            {
                "question": [f"Question {index + 1}?"] * 3,
                "labels": [0, 0, 1],
                "answers": [[f"Wrong {index}.1", f"Wrong {index}.2", f"Right {index}"]],
            }
        )
    data_path.write_text(json.dumps(rows), encoding="utf-8")
    monkeypatch.setenv("BIBLEQA_DATA_FILE", str(data_path))

    samples = make_bibleqa_samples(sample_ids=["bibleqa-web-0002"])

    assert [sample.id for sample in samples] == ["bibleqa-web-0002"]


def test_make_bibleqa_sample_id_filter_runs_before_limit(tmp_path, monkeypatch):
    data_path = tmp_path / "bibleqa.json"
    rows = []
    for index in range(4):
        rows.append(
            {
                "question": [f"Question {index + 1}?"] * 3,
                "labels": [0, 0, 1],
                "answers": [[f"Wrong {index}.1", f"Wrong {index}.2", f"Right {index}"]],
            }
        )
    data_path.write_text(json.dumps(rows), encoding="utf-8")
    monkeypatch.setenv("BIBLEQA_DATA_FILE", str(data_path))

    samples = make_bibleqa_samples(limit=1, sample_ids=["bibleqa-web-0004"])

    assert [sample.id for sample in samples] == ["bibleqa-web-0004"]


def test_make_bibleqa_samples_supports_start_offset(tmp_path, monkeypatch):
    data_path = tmp_path / "bibleqa.json"
    rows = []
    for index in range(3):
        rows.append(
            {
                "question": [f"Question {index + 1}?"] * 3,
                "labels": [0, 0, 1],
                "answers": [[f"Wrong {index}.1", f"Wrong {index}.2", f"Right {index}"]],
            }
        )
    data_path.write_text(json.dumps(rows), encoding="utf-8")
    monkeypatch.setenv("BIBLEQA_DATA_FILE", str(data_path))

    samples = make_bibleqa_samples(start=1)

    assert [sample.id for sample in samples] == ["bibleqa-web-0002", "bibleqa-web-0003"]


def test_make_bibleqa_samples_supports_start_and_limit_together(tmp_path, monkeypatch):
    data_path = tmp_path / "bibleqa.json"
    rows = []
    for index in range(5):
        rows.append(
            {
                "question": [f"Question {index + 1}?"] * 3,
                "labels": [0, 0, 1],
                "answers": [[f"Wrong {index}.1", f"Wrong {index}.2", f"Right {index}"]],
            }
        )
    data_path.write_text(json.dumps(rows), encoding="utf-8")
    monkeypatch.setenv("BIBLEQA_DATA_FILE", str(data_path))

    samples = make_bibleqa_samples(start=2, limit=2)

    assert [sample.id for sample in samples] == ["bibleqa-web-0003", "bibleqa-web-0004"]
