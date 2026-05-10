#!/usr/bin/env python3
"""Check which official Jenny religion datasets are currently accessible."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

from datasets import load_dataset
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_BUDDHISM_EVAL_DATASET = "Nethmi14/BuddhismEval"
DISALLOWED_BUDDHISM_EVAL_DATASETS = {"vanloc1808/BuddhismEval-vi-augmented"}


def _load_env() -> None:
    load_dotenv(ROOT / ".env")
    load_dotenv(ROOT / ".env.local", override=True)


def _hf_token() -> str | None:
    return os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")


def _ok(name: str, task: str, note: str) -> dict:
    return {"benchmark": name, "task": task, "status": "accessible", "note": note}


def _blocked(name: str, task: str, note: str) -> dict:
    return {"benchmark": name, "task": task, "status": "blocked", "note": note}


def _looks_like_auth_error(exc: Exception) -> bool:
    text = str(exc).lower()
    return any(marker in text for marker in ["401", "unauthorized", "permission", "gated", "cannot be accessed"])


def check_bibleqa() -> dict:
    local = os.getenv("BIBLEQA_DATA_FILE", "").strip()
    if local:
        path = Path(local).expanduser()
        if path.exists():
            return _ok("BibleQA", "bibleqa_sentence_selection", f"local mirror: {path}")
        return _blocked("BibleQA", "bibleqa_sentence_selection", f"missing local mirror: {path}")

    url = os.getenv(
        "BIBLEQA_DATA_URL",
        "https://raw.githubusercontent.com/helen-jiahe-zhao/BibleQA/master/data/bible_qa/bible_qa_list_3_web.json",
    )
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            if response.status == 200:
                return _ok("BibleQA", "bibleqa_sentence_selection", "official GitHub artifact reachable")
    except Exception as exc:
        return _blocked("BibleQA", "bibleqa_sentence_selection", f"official artifact unavailable: {exc}")
    return _blocked("BibleQA", "bibleqa_sentence_selection", f"unexpected HTTP status for {url}")


def check_islamtrust() -> dict:
    if os.getenv("ISLAMTRUST_DATA_FILE", "").strip():
        path = Path(os.environ["ISLAMTRUST_DATA_FILE"]).expanduser()
        if path.exists():
            return _ok("IslamTrust", "islamtrust_mc1", f"local official mirror: {path}")
        return _blocked("IslamTrust", "islamtrust_mc1", f"missing local mirror: {path}")

    token = _hf_token()
    if not token:
        return _blocked(
            "IslamTrust",
            "islamtrust_mc1",
            "gated Hugging Face dataset; access requested, waiting for response; HF token not configured",
        )

    dataset = os.getenv("ISLAMTRUST_DATASET", "Abderraouf000/IslamTrust-benchmark")
    try:
        load_dataset(dataset, split="English[:1]", token=token)
    except Exception as exc:
        return _blocked("IslamTrust", "islamtrust_mc1", f"HF access failed: {exc}")
    return _ok("IslamTrust", "islamtrust_mc1", "HF gated dataset access accepted")


def check_buddhism_eval() -> dict:
    if os.getenv("BUDDHISM_EVAL_DATA_FILE", "").strip():
        path = Path(os.environ["BUDDHISM_EVAL_DATA_FILE"]).expanduser()
        if path.exists():
            return _ok("BuddhismEval", "buddhism_eval_mcq", f"local official mirror: {path}")
        return _blocked("BuddhismEval", "buddhism_eval_mcq", f"missing local mirror: {path}")

    dataset = os.getenv("BUDDHISM_EVAL_DATASET", OFFICIAL_BUDDHISM_EVAL_DATASET)
    if dataset in DISALLOWED_BUDDHISM_EVAL_DATASETS or dataset != OFFICIAL_BUDDHISM_EVAL_DATASET:
        return _blocked(
            "BuddhismEval",
            "buddhism_eval_mcq",
            f"{dataset} is not accepted as the official BuddhismEval result; use {OFFICIAL_BUDDHISM_EVAL_DATASET}",
        )
    token = _hf_token()
    try:
        load_dataset(dataset, name="english_eval", split="train[:1]", token=token)
    except Exception as exc:
        if _looks_like_auth_error(exc):
            return _blocked(
                "BuddhismEval",
                "buddhism_eval_mcq",
                "official dataset inaccessible / permission required; Jenny will email the author to request access",
            )
        return _blocked(
            "BuddhismEval",
            "buddhism_eval_mcq",
            f"official dataset inaccessible / permission required; Jenny will email the author to request access; raw error: {exc}",
        )
    return _ok("BuddhismEval", "buddhism_eval_mcq", "official HF eval subset reachable")


def check_catholicbench() -> dict:
    path_value = os.getenv("CATHOLICBENCH_DATA_FILE", "").strip()
    if not path_value:
        return _blocked(
            "CatholicBench",
            "catholicbench_official",
            "requires author access / official export needed; public dashboard is not scraped; Jenny will email the author",
        )
    path = Path(path_value).expanduser()
    if path.exists():
        return _ok("CatholicBench", "catholicbench_official", f"official scenario/rubric file configured: {path}")
    return _blocked("CatholicBench", "catholicbench_official", f"configured file does not exist: {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Print JSON status")
    parser.add_argument("--task-list", action="store_true", help="Print comma-separated accessible task names")
    args = parser.parse_args()

    _load_env()
    checks = [check_islamtrust(), check_buddhism_eval(), check_bibleqa(), check_catholicbench()]

    if args.task_list:
        tasks = [item["task"] for item in checks if item["status"] == "accessible"]
        print(",".join(tasks))
        return 0 if tasks else 1

    if args.json:
        print(json.dumps(checks, indent=2, ensure_ascii=False))
        return 0

    for item in checks:
        print(f"{item['benchmark']}: {item['status']} - {item['note']}")
    blocked = [item for item in checks if item["status"] != "accessible"]
    if blocked:
        print("\nBlocked benchmarks are expected when official access is unavailable.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
