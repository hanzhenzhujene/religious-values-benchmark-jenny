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

SIZE_ORDER = {"S": 0, "M": 1, "L": 2}
MODEL_BY_SLUG = {
    model.replace("/", "_").replace(":", "_"): {
        "family": family,
        "size": size,
        "model": model,
        "provider": provider,
    }
    for family, size, model, provider in MODEL_ROWS
}


def write_csv(path: Path, headers: list[str], rows: list[tuple]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(headers)
        writer.writerows(rows)


def strip_trailing_whitespace(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    path.write_text("\n".join(line.rstrip() for line in lines) + "\n", encoding="utf-8")


def metric_value(header: dict, metric_name: str) -> float | None:
    for score in header.get("results", {}).get("scores", []):
        metrics = score.get("metrics", {})
        metric = metrics.get(metric_name)
        if metric is not None:
            return float(metric.get("value"))
    return None


def count_samples(names: list[str]) -> int:
    return sum(1 for name in names if name.startswith("samples/") and name.endswith(".json"))


def read_json_member(archive: zipfile.ZipFile, name: str) -> dict | list | None:
    try:
        return json.loads(archive.read(name).decode("utf-8"))
    except Exception:
        return None


def inspect_log_result(eval_path: Path) -> dict[str, object]:
    rel_path = str(eval_path.relative_to(ROOT))
    slug = eval_path.parent.name
    model_info = MODEL_BY_SLUG.get(slug, {})
    row: dict[str, object] = {
        "path": rel_path,
        "status": "unreadable",
        "task": "",
        "model": model_info.get("model", ""),
        "family": model_info.get("family", ""),
        "size": model_info.get("size", ""),
        "provider": model_info.get("provider", ""),
        "total_samples": "",
        "completed_samples": "",
        "accuracy": "",
        "stderr": "",
        "valid_response_rate": "",
        "parse_failure_rate": "",
        "started_at": "",
        "completed_at": "",
        "error_message": "",
    }

    try:
        with zipfile.ZipFile(eval_path) as archive:
            names = archive.namelist()
            row["completed_samples"] = count_samples(names)
            start = read_json_member(archive, "_journal/start.json")
            if isinstance(start, dict):
                eval_info = start.get("eval", {})
                row["task"] = eval_info.get("task", "")
                row["model"] = row["model"] or eval_info.get("model", "")
                row["total_samples"] = eval_info.get("dataset", {}).get("samples", "")
                row["started_at"] = start.get("stats", {}).get("started_at", "")

            header = read_json_member(archive, "header.json")
            if not isinstance(header, dict):
                row["status"] = "partial"
                return row

            eval_info = header.get("eval", {})
            results = header.get("results", {})
            stats = header.get("stats", {})
            accuracy = metric_value(header, "accuracy")
            stderr = metric_value(header, "stderr")
            row.update(
                {
                    "status": header.get("status", "unknown"),
                    "task": eval_info.get("task", row["task"]),
                    "model": row["model"] or eval_info.get("model", ""),
                    "total_samples": results.get("total_samples", row["total_samples"]),
                    "completed_samples": results.get("completed_samples", row["completed_samples"]),
                    "accuracy": accuracy if accuracy is not None else "",
                    "stderr": stderr if stderr is not None else "",
                    "started_at": stats.get("started_at", row["started_at"]),
                    "completed_at": stats.get("completed_at", ""),
                    "error_message": (header.get("error") or {}).get("message", ""),
                }
            )

            reductions = read_json_member(archive, "reductions.json")
            scored = 0
            parse_failures = 0
            if isinstance(reductions, list):
                for reduction in reductions:
                    if reduction.get("scorer") != "exact_choice_scorer":
                        continue
                    for sample in reduction.get("samples", []):
                        scored += 1
                        metadata = sample.get("metadata", {})
                        if metadata.get("parse_error"):
                            parse_failures += 1
            if scored:
                row["valid_response_rate"] = (scored - parse_failures) / scored
                row["parse_failure_rate"] = parse_failures / scored
    except Exception:
        return row
    return row


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


def inspect_log_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for eval_path in sorted((ROOT / "results" / "inspect" / "logs").glob("**/*.eval")):
        rows.append(inspect_log_result(eval_path))
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


def successful_result_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        row
        for row in rows
        if row.get("status") == "success"
        and row.get("accuracy") != ""
        and row.get("task")
        and "/logs/smoke/" not in str(row.get("path", ""))
    ]


def short_model_label(row: dict[str, object]) -> str:
    family = str(row.get("family") or "")
    size = str(row.get("size") or "")
    model = str(row.get("model") or "")
    if family and size:
        return f"{family} {size}"
    return model.replace("openai/", "")


def build_accuracy_heatmap(rows: list[dict[str, object]]) -> Path | None:
    successful = successful_result_rows(rows)
    if not successful:
        return None
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    successful.sort(key=lambda row: (str(row.get("family")), SIZE_ORDER.get(str(row.get("size")), 99)))
    labels = [short_model_label(row) for row in successful]
    values = [[float(row["accuracy"]) for row in successful]]

    width = max(8.0, 0.62 * len(successful))
    fig, ax = plt.subplots(figsize=(width, 2.6))
    image = ax.imshow(values, vmin=0, vmax=1, cmap="YlGnBu", aspect="auto")
    ax.set_xticks(range(len(labels)), labels, rotation=45, ha="right")
    ax.set_yticks([0], ["BibleQA"])
    ax.set_title("BibleQA Accuracy by Model")
    for col, value in enumerate(values[0]):
        ax.text(col, 0, f"{value:.2f}", ha="center", va="center", fontsize=8, color="black")
    fig.colorbar(image, ax=ax, fraction=0.025, pad=0.02, label="Accuracy")
    fig.tight_layout()
    path = FIGURES_DIR / "jenny_religion_accuracy_heatmap.svg"
    fig.savefig(path)
    plt.close(fig)
    strip_trailing_whitespace(path)
    return path


def build_family_size_plot(rows: list[dict[str, object]]) -> Path | None:
    successful = successful_result_rows(rows)
    if not successful:
        return None
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    by_family: dict[str, list[dict[str, object]]] = {}
    for row in successful:
        family = str(row.get("family") or "Other")
        by_family.setdefault(family, []).append(row)

    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for family, family_rows in sorted(by_family.items()):
        ordered = sorted(family_rows, key=lambda row: SIZE_ORDER.get(str(row.get("size")), 99))
        xs = [SIZE_ORDER.get(str(row.get("size")), 99) for row in ordered]
        ys = [float(row["accuracy"]) for row in ordered]
        labels = [str(row.get("size")) for row in ordered]
        ax.plot(xs, ys, marker="o", linewidth=1.8, label=family)
        for x, y, label in zip(xs, ys, labels):
            ax.text(x, y + 0.008, label, ha="center", va="bottom", fontsize=8)
    ax.set_xticks([0, 1, 2], ["S", "M", "L"])
    ax.set_ylim(0, 1)
    ax.set_xlabel("Capability tier within family")
    ax.set_ylabel("BibleQA accuracy")
    ax.set_title("Family/Size Accuracy Pattern")
    ax.legend(ncol=2, fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    path = FIGURES_DIR / "jenny_religion_family_size.svg"
    fig.savefig(path)
    plt.close(fig)
    strip_trailing_whitespace(path)
    return path


def build_benchmark_difficulty_plot(rows: list[dict[str, object]]) -> Path | None:
    successful = successful_result_rows(rows)
    if not successful:
        return None
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    by_task: dict[str, list[float]] = {}
    for row in successful:
        by_task.setdefault(str(row["task"]), []).append(float(row["accuracy"]))
    labels = list(by_task)
    difficulty = [1 - (sum(values) / len(values)) for values in by_task.values()]

    fig, ax = plt.subplots(figsize=(7, 3.4))
    ax.bar(labels, difficulty, color="#7c3aed")
    ax.set_ylim(0, 1)
    ax.set_ylabel("1 - mean accuracy")
    ax.set_title("Observed Benchmark Difficulty")
    ax.tick_params(axis="x", rotation=10)
    for idx, value in enumerate(difficulty):
        ax.text(idx, value + 0.015, f"{value:.2f}", ha="center", va="bottom", fontsize=9)
    fig.tight_layout()
    path = FIGURES_DIR / "jenny_religion_benchmark_difficulty.svg"
    fig.savefig(path)
    plt.close(fig)
    strip_trailing_whitespace(path)
    return path


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
        [
            "path",
            "status",
            "task",
            "model",
            "family",
            "size",
            "provider",
            "total_samples",
            "completed_samples",
            "accuracy",
            "stderr",
            "valid_response_rate",
            "parse_failure_rate",
            "error_message",
        ],
        [
            (
                row["path"],
                row["status"],
                row["task"],
                row["model"],
                row["family"],
                row["size"],
                row["provider"],
                row["total_samples"],
                row["completed_samples"],
                row["accuracy"],
                row["stderr"],
                row["valid_response_rate"],
                row["parse_failure_rate"],
                row["error_message"],
            )
            for row in log_rows
        ],
    )

    failed_rows = [
        row
        for row in log_rows
        if row["status"] != "success" and "/logs/smoke/" not in str(row.get("path", ""))
    ]
    write_csv(
        RELEASE_DIR / "failed-cells.csv",
        ["task", "family", "size", "model", "provider", "status", "completed_samples", "total_samples", "error_message", "log_path"],
        [
            (
                row["task"],
                row["family"],
                row["size"],
                row["model"],
                row["provider"],
                row["status"],
                row["completed_samples"],
                row["total_samples"],
                row["error_message"],
                row["path"],
            )
            for row in failed_rows
        ],
    )

    result_rows = successful_result_rows(log_rows)
    write_csv(
        RELEASE_DIR / "result-summary.csv",
        [
            "benchmark",
            "task",
            "family",
            "size",
            "model",
            "provider",
            "accuracy",
            "stderr",
            "valid_response_rate",
            "parse_failure_rate",
            "completed_samples",
            "log_path",
        ],
        [
            (
                "BibleQA" if row["task"] == "bibleqa_sentence_selection" else row["task"],
                row["task"],
                row["family"],
                row["size"],
                row["model"],
                row["provider"],
                row["accuracy"],
                row["stderr"],
                row["valid_response_rate"],
                row["parse_failure_rate"],
                row["completed_samples"],
                row["path"],
            )
            for row in result_rows
        ],
    )

    figure_paths: list[str] = []
    if statuses:
        build_access_plot(statuses)
        figure_paths.append("figures/release/jenny_religion_access_gate.svg")
    for figure_path in [
        build_accuracy_heatmap(log_rows),
        build_family_size_plot(log_rows),
        build_benchmark_difficulty_plot(log_rows),
    ]:
        if figure_path is not None:
            figure_paths.append(str(figure_path.relative_to(ROOT)))

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "release_dir": str(RELEASE_DIR.relative_to(ROOT)),
        "figures": figure_paths,
        "num_inspect_logs": len(log_rows),
        "num_successful_result_logs": len(result_rows),
    }
    (RELEASE_DIR / "release-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    best_rows = sorted(result_rows, key=lambda row: float(row["accuracy"]), reverse=True)[:3]
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
    lines.extend(["", "## Completed Results", ""])
    if result_rows:
        lines.append(f"- Successful Inspect logs: {len(result_rows)}")
        lines.append("- Best current BibleQA cells:")
        for row in best_rows:
            lines.append(f"  - {short_model_label(row)}: accuracy {float(row['accuracy']):.3f}")
        if failed_rows:
            lines.append("- Non-success full-run cells:")
            for row in failed_rows:
                lines.append(
                    f"  - {short_model_label(row)}: {row['status']}, "
                    f"{row['completed_samples']}/{row['total_samples']} samples logged"
                )
    else:
        lines.append("- No completed full-result logs yet.")
    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `benchmark-catalog.csv`",
            "- `model-roster.csv`",
            "- `data-access-status.csv`",
            "- `inspect-log-status.csv`",
            "- `failed-cells.csv`",
            "- `result-summary.csv`",
            "- `release-manifest.json`",
        ]
    )
    (RELEASE_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote release artifacts to {RELEASE_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
