from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "inspect"))

from evals.religion import (  # noqa: E402
    make_bibleqa_samples,
    make_buddhism_eval_samples,
    make_islamtrust_samples,
)


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
    assert samples[0].target == "2"
    assert samples[0].metadata["category"] == "General"


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
