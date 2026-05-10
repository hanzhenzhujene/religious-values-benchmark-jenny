#!/usr/bin/env python3
"""Plan cheap, targeted rebound runs from Jenny religion Inspect logs."""

from __future__ import annotations

import argparse
import csv
import json
import shlex
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

MODEL_ROSTER = [
    ("qwen_qwen3-8b", 1, "qwen/qwen3-8b"),
    ("qwen_qwen3-32b", 2, "qwen/qwen3-32b"),
    ("qwen_qwen3-235b-a22b", 3, "qwen/qwen3-235b-a22b"),
    ("deepseek_deepseek-r1-distill-llama-70b", 4, "deepseek/deepseek-r1-distill-llama-70b"),
    ("deepseek_deepseek-chat-v3.1", 5, "deepseek/deepseek-chat-v3.1"),
    ("deepseek_deepseek-r1", 6, "deepseek/deepseek-r1"),
    ("meta-llama_llama-3.2-3b-instruct", 7, "meta-llama/llama-3.2-3b-instruct"),
    ("meta-llama_llama-3.1-8b-instruct", 8, "meta-llama/llama-3.1-8b-instruct"),
    ("meta-llama_llama-3.3-70b-instruct", 9, "meta-llama/llama-3.3-70b-instruct"),
    ("google_gemma-3-4b-it", 10, "google/gemma-3-4b-it"),
    ("google_gemma-3-12b-it", 11, "google/gemma-3-12b-it"),
    ("google_gemma-3-27b-it", 12, "google/gemma-3-27b-it"),
    ("minimax_minimax-01", 13, "minimax/minimax-01"),
    ("minimax_minimax-m1", 14, "minimax/minimax-m1"),
    ("minimax_minimax-m2.5", 15, "minimax/minimax-m2.5"),
]
MODEL_BY_SLUG = {slug: {"index": index, "model": model} for slug, index, model in MODEL_ROSTER}


@dataclass
class LogInfo:
    path: Path
    slug: str
    task: str
    model: str
    model_index: int
    status: str
    total_ids: list[str]
    logged_ids: set[str]
    parse_failed_ids: list[str]
    error_message: str


def read_json_member(archive: zipfile.ZipFile, name: str) -> Any | None:
    try:
        return json.loads(archive.read(name).decode("utf-8"))
    except Exception:
        return None


def inspect_log(path: Path) -> LogInfo:
    slug = path.parent.name
    roster = MODEL_BY_SLUG.get(slug, {"index": 0, "model": ""})
    task = ""
    model = str(roster["model"])
    model_index = int(roster["index"])
    status = "unreadable"
    total_ids: list[str] = []
    logged_ids: set[str] = set()
    parse_failed_ids: list[str] = []
    error_message = ""

    try:
        with zipfile.ZipFile(path) as archive:
            start = read_json_member(archive, "_journal/start.json")
            if isinstance(start, dict):
                eval_info = start.get("eval", {})
                task = str(eval_info.get("task", ""))
                model = model or str(eval_info.get("model", "")).removeprefix("openai/")
                total_ids = list(eval_info.get("dataset", {}).get("sample_ids", []))

            header = read_json_member(archive, "header.json")
            if isinstance(header, dict):
                status = str(header.get("status", "unknown"))
                error_message = str((header.get("error") or {}).get("message", ""))
            else:
                status = "partial"

            for member in archive.namelist():
                if not member.startswith("samples/") or not member.endswith(".json"):
                    continue
                sample = read_json_member(archive, member)
                if not isinstance(sample, dict):
                    continue
                sample_id = str(sample.get("id", ""))
                if not sample_id:
                    continue
                logged_ids.add(sample_id)
                score = sample.get("scores", {}).get("exact_choice_scorer", {})
                metadata = score.get("metadata", {})
                if metadata.get("parse_error"):
                    parse_failed_ids.append(sample_id)
    except Exception as exc:
        error_message = f"{type(exc).__name__}: {exc}"

    return LogInfo(
        path=path,
        slug=slug,
        task=task,
        model=model,
        model_index=model_index,
        status=status,
        total_ids=total_ids,
        logged_ids=logged_ids,
        parse_failed_ids=parse_failed_ids,
        error_message=error_message,
    )


def latest_logs(run_id: str) -> list[LogInfo]:
    log_root = ROOT / "results" / "inspect" / "logs" / run_id
    logs = [inspect_log(path) for path in sorted(log_root.glob("**/*.eval"))]
    by_cell: dict[tuple[str, str], LogInfo] = {}
    for log in logs:
        key = (log.slug, log.task)
        if key not in by_cell or str(log.path) > str(by_cell[key].path):
            by_cell[key] = log
    return list(by_cell.values())


def write_ids(path: Path, sample_ids: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(sample_ids) + "\n", encoding="utf-8")


def shell_command(*parts: str) -> str:
    return " ".join(shlex.quote(part) for part in parts)


def plan_rebounds(run_id: str, parse_threshold: float) -> list[dict[str, str]]:
    output_dir = ROOT / "results" / "inspect" / "rebounds" / run_id
    rows: list[dict[str, str]] = []
    for log in latest_logs(run_id):
        if not log.task or not log.total_ids or log.model_index == 0:
            continue
        total_set = set(log.total_ids)
        missing_ids = [sample_id for sample_id in log.total_ids if sample_id not in log.logged_ids]

        plans: list[tuple[str, list[str], str]] = []
        if log.status != "success" and missing_ids:
            plans.append(("missing-after-runtime-error", missing_ids, log.error_message))

        parse_rate = len(log.parse_failed_ids) / len(log.total_ids)
        if log.status == "success" and parse_rate >= parse_threshold and log.parse_failed_ids:
            ordered_parse_ids = [sample_id for sample_id in log.total_ids if sample_id in set(log.parse_failed_ids)]
            plans.append(("parse-failure-rerun", ordered_parse_ids, f"parse_failure_rate={parse_rate:.3f}"))

        for reason, sample_ids, note in plans:
            safe_reason = reason.replace("-", "_")
            ids_path = output_dir / f"{log.slug}__{log.task}__{safe_reason}.ids"
            write_ids(ids_path, sample_ids)
            rebound_run_id = f"{run_id}-rebound-{log.slug}-{safe_reason}"
            max_conn = "1" if reason == "missing-after-runtime-error" else "2"
            command = shell_command(
                "./scripts/run_jenny_religion.sh",
                "--run-id",
                rebound_run_id,
                "--models",
                str(log.model_index),
                "--tasks",
                log.task,
                "--sample-ids-file",
                str(ids_path.relative_to(ROOT)),
                "--max-conn",
                max_conn,
                "--parallel-models",
                "1",
            )
            rows.append(
                {
                    "source_run_id": run_id,
                    "reason": reason,
                    "task": log.task,
                    "model_index": str(log.model_index),
                    "model": log.model,
                    "source_status": log.status,
                    "source_logged_samples": str(len(log.logged_ids.intersection(total_set))),
                    "total_samples": str(len(log.total_ids)),
                    "planned_samples": str(len(sample_ids)),
                    "sample_ids_file": str(ids_path.relative_to(ROOT)),
                    "note": note,
                    "command": command,
                }
            )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True, help="Inspect log run id to inspect")
    parser.add_argument("--parse-threshold", type=float, default=0.05)
    args = parser.parse_args()

    rows = plan_rebounds(args.run_id, args.parse_threshold)
    output_dir = ROOT / "results" / "inspect" / "rebounds" / args.run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    plan_csv = output_dir / "rebound-plan.csv"
    plan_sh = output_dir / "run-rebounds.sh"

    headers = [
        "source_run_id",
        "reason",
        "task",
        "model_index",
        "model",
        "source_status",
        "source_logged_samples",
        "total_samples",
        "planned_samples",
        "sample_ids_file",
        "note",
        "command",
    ]
    with plan_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    script_lines = [
        "#!/usr/bin/env bash",
        "set -uo pipefail",
        "cd \"$(dirname \"$0\")/../../../..\"",
        "",
        "FAILURES=0",
        "run_rebound() {",
        "    local label=\"$1\"",
        "    shift",
        "    echo \"=== Rebound started: $label :: $(date) ===\"",
        "    \"$@\"",
        "    local rc=$?",
        "    echo \"=== Rebound finished: $label rc=$rc :: $(date) ===\"",
        "    if [[ \"$rc\" -ne 0 ]]; then",
        "        FAILURES=$((FAILURES + 1))",
        "    fi",
        "}",
        "",
    ]
    for row in rows:
        label = f"{row['model']} {row['task']} {row['reason']} ({row['planned_samples']} samples)"
        script_lines.append(f"run_rebound {shlex.quote(label)} {row['command']}")
    script_lines.extend(["", "echo \"=== Rebound batch complete; failures=$FAILURES :: $(date) ===\"", "exit \"$FAILURES\""])
    plan_sh.write_text("\n".join(script_lines) + "\n", encoding="utf-8")
    plan_sh.chmod(0o755)

    print(f"Wrote {len(rows)} rebound plan(s) to {plan_csv}")
    for row in rows:
        print(f"- {row['model']} {row['reason']}: {row['planned_samples']} samples")
        print(f"  {row['command']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
