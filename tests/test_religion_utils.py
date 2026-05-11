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
from evals._benchmark_utils import extract_structured_choice_int  # noqa: E402


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
    assert "neutral academic benchmark" in prompt
    assert "from 1 to 2" in prompt
    assert "do not refuse" in prompt
    assert "Answer first" in prompt
    assert "1. A" in prompt
    assert "2. B" in prompt


def test_choice_parser_accepts_answer_is_option_format():
    assert extract_structured_choice_int("The answer is option 3.", minimum=1, maximum=3) == 3


def test_choice_parser_accepts_i_choose_format():
    assert extract_structured_choice_int("I choose option 2 because it matches.", minimum=1, maximum=3) == 2
