#!/usr/bin/env python3
"""Build lightweight public release artifacts for Jenny's religion sweep."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
RELEASE_DIR = ROOT / "results" / "release" / "jenny-religion"
FIGURES_DIR = ROOT / "figures" / "release"

MODEL_ROWS = [
    ("Qwen", "S", "qwen/qwen3-8b", "OpenRouter"),
    ("Qwen", "M", "qwen/qwen3-32b", "OpenRouter"),
    ("Qwen", "L", "qwen/qwen3-235b-a22b", "OpenRouter"),
    ("DeepSeek", "S", "deepseek/deepseek-r1-distill-llama-70b", "OpenRouter"),
    ("DeepSeek", "M", "deepseek/deepseek-chat-v3.1", "OpenRouter"),
    ("DeepSeek", "L", "deepseek/deepseek-r1", "OpenRouter"),
    ("Llama", "S", "meta-llama/llama-3.2-3b-instruct", "OpenRouter"),
    ("Llama", "M", "meta-llama/llama-3.1-8b-instruct", "OpenRouter"),
    ("Llama", "L", "meta-llama/llama-3.3-70b-instruct", "OpenRouter"),
    ("Gemma", "S", "google/gemma-3-4b-it", "OpenRouter"),
    ("Gemma", "M", "google/gemma-3-12b-it", "OpenRouter"),
    ("Gemma", "L", "google/gemma-3-27b-it", "OpenRouter"),
    ("MiniMax", "S", "minimax/minimax-01", "MiniMax direct API"),
    ("MiniMax", "M", "minimax/minimax-m1", "MiniMax direct API"),
    ("MiniMax", "L", "minimax/minimax-m2.5", "MiniMax direct API"),
]

BENCHMARK_ROWS = [
    ("#35", "IslamTrust", "islamtrust_mc1", "blocked until HF gated access is accepted"),
    ("#47", "CatholicBench", "catholicbench_official", "blocked until official scenarios/rubrics are available"),
    ("#26", "BuddhismEval", "buddhism_eval_mcq", "blocked unless official HF eval subset is reachable"),
    ("#37", "BibleQA", "bibleqa_sentence_selection", "official GitHub candidate-selection artifact"),
]


def write_csv(path: Path, headers: list[str], rows: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(headers)
        writer.writerows(rows)


def strip_trailing_whitespace(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(line.rstrip() for line in lines) + "\n", encoding="utf-8")


def access_status() -> list[dict]:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_dataset_access.py"), "--json"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0 and not result.stdout:
        return []
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return []


def inspect_log_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for eval_path in sorted((ROOT / "results" / "inspect" / "logs").glob("**/*.eval")):
        try:
            with zipfile.ZipFile(eval_path) as archive:
                header = json.loads(archive.read("header.json").decode("utf-8"))
        except Exception:
            rows.append({"path": str(eval_path.relative_to(ROOT)), "status": "unreadable", "model": "", "task": ""})
            continue
        rows.append(
            {
                "path": str(eval_path.relative_to(ROOT)),
                "status": str(header.get("status", "unknown")),
                "model": str(header.get("eval", {}).get("model", "")),
                "task": str(header.get("eval", {}).get("task", "")),
            }
        )
    return rows


def build_access_plot(statuses: list[dict]) -> None:
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    labels = [item["benchmark"] for item in statuses]
    values = [1 if item["status"] == "accessible" else 0 for item in statuses]
    colors = ["#2f855a" if value else "#c2410c" for value in values]
    fig, ax = plt.subplots(figsize=(8, 3.8))
    ax.bar(labels, values, color=colors)
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("Official data accessible")
    ax.set_title("Jenny Religion Benchmark Access Gate")
    ax.set_yticks([0, 1], ["Blocked", "Accessible"])
    ax.tick_params(axis="x", rotation=15)
    fig.tight_layout()
    figure_path = FIGURES_DIR / "jenny_religion_access_gate.svg"
    fig.savefig(figure_path)
    plt.close(fig)
    strip_trailing_whitespace(figure_path)


def main() -> int:
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    statuses = access_status()

    write_csv(
        RELEASE_DIR / "model-roster.csv",
        ["family", "size", "model", "provider"],
        MODEL_ROWS,
    )
    write_csv(
        RELEASE_DIR / "benchmark-catalog.csv",
        ["id", "benchmark", "task", "data_status_note"],
        BENCHMARK_ROWS,
    )
    write_csv(
        RELEASE_DIR / "data-access-status.csv",
        ["benchmark", "task", "status", "note"],
        [(item["benchmark"], item["task"], item["status"], item["note"]) for item in statuses],
    )

    log_rows = inspect_log_rows()
    write_csv(
        RELEASE_DIR / "inspect-log-status.csv",
        ["path", "status", "model", "task"],
        [(row["path"], row["status"], row["model"], row["task"]) for row in log_rows],
    )

    if statuses:
        build_access_plot(statuses)

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "release_dir": str(RELEASE_DIR.relative_to(ROOT)),
        "figures": ["figures/release/jenny_religion_access_gate.svg"] if statuses else [],
        "num_inspect_logs": len(log_rows),
    }
    (RELEASE_DIR / "release-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    lines = [
        "# Jenny Religion Benchmark Release Summary",
        "",
        "This package tracks Jenny's assigned religion benchmarks under the strict official-data policy.",
        "",
        "## Current Access Gate",
        "",
    ]
    for item in statuses:
        lines.append(f"- {item['benchmark']}: {item['status']} - {item['note']}")
    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `benchmark-catalog.csv`",
            "- `model-roster.csv`",
            "- `data-access-status.csv`",
            "- `inspect-log-status.csv`",
            "- `release-manifest.json`",
        ]
    )
    (RELEASE_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote release artifacts to {RELEASE_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
