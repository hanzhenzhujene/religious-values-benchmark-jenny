from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_release_module():
    path = ROOT / "scripts" / "build_release_artifacts.py"
    spec = importlib.util.spec_from_file_location("build_release_artifacts", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_model_roster_includes_direct_minimax_m1():
    module = load_release_module()
    rows = module.MODEL_ROWS
    assert ("MiniMax", "M", "minimax/minimax-m1", "MiniMax direct API") in rows


def test_benchmark_catalog_marks_catholicbench_blocked():
    module = load_release_module()
    catholic_rows = [row for row in module.BENCHMARK_ROWS if row[1] == "CatholicBench"]
    assert catholic_rows
    assert "official export needed" in catholic_rows[0][3]
