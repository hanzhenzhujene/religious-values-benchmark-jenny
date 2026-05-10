from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "inspect"))

from evals.religion_utils import (  # noqa: E402
    parse_choices,
    prompt_for_mcq,
    resolve_correct_choice_index,
)


def test_parse_choices_accepts_python_list_string():
    assert parse_choices("['A', 'B', 'C']") == ["A", "B", "C"]


def test_parse_choices_accepts_list_value():
    assert parse_choices([" A ", "B"]) == ["A", "B"]


def test_resolve_correct_choice_handles_punctuation_difference():
    choices = [
        "Bodily sensations",
        "Mind precedes all mental states; they are mind-made",
        "Speech and action",
    ]
    assert resolve_correct_choice_index(choices, "Mind precedes all mental states. They are mind-made") == 1


def test_resolve_correct_choice_raises_for_unmatched_answer():
    with pytest.raises(ValueError):
        resolve_correct_choice_index(["one", "two", "three"], "four")


def test_prompt_for_mcq_uses_strict_numbered_output_contract():
    prompt = prompt_for_mcq("Question?", ["A", "B"])
    assert "SELECTED OPTION: <number>" in prompt
    assert "1. A" in prompt
    assert "2. B" in prompt
