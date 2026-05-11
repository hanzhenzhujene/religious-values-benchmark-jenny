#!/usr/bin/env python3
"""Build public release artifacts from Jenny religion source snapshots.

This is the single public-release builder. It reads only the canonical
``results/release/jenny-religion/source`` snapshots and writes CSVs, SVG figures,
and README data blocks. It intentionally does not inspect raw run logs.
"""

import argparse
import json
import math
import sys
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any

try:
    import pandas as pd
except ImportError as exc:  # pragma: no cover - depends on local env
    raise ImportError(
        "pandas is required. Install release-builder dependencies with: "
        "python -m pip install pandas matplotlib"
    ) from exc

try:
    import matplotlib  # noqa: F401  # Imported to enforce the declared dependency.
except ImportError as exc:  # pragma: no cover - depends on local env
    raise ImportError(
        "matplotlib is required. Install release-builder dependencies with: "
        "python -m pip install pandas matplotlib"
    ) from exc


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "results" / "release" / "jenny-religion" / "source"
RELEASE_DIR = ROOT / "results" / "release" / "jenny-religion"
FIGURES_DIR = ROOT / "figures" / "release"

SCORES_PATH = SOURCE_DIR / "benchmark_scores.csv"
REGISTRY_PATH = SOURCE_DIR / "model_registry.csv"
META_PATH = SOURCE_DIR / "meta.json"

CSV_OUTPUTS = [
    RELEASE_DIR / "benchmark-comparison.csv",
    RELEASE_DIR / "family-size-progress.csv",
    RELEASE_DIR / "benchmark-difficulty-summary.csv",
    RELEASE_DIR / "family-scaling-summary.csv",
]
SVG_OUTPUTS = [
    FIGURES_DIR / "rel_family_size_progress_overview.svg",
    FIGURES_DIR / "rel_benchmark_accuracy_bars.svg",
    FIGURES_DIR / "rel_accuracy_heatmap.svg",
    FIGURES_DIR / "rel_benchmark_difficulty_profile.svg",
    FIGURES_DIR / "rel_family_scaling_profile.svg",
    FIGURES_DIR / "rel_coverage_matrix.svg",
]
README_BLOCKS_PATH = RELEASE_DIR / "readme-data-blocks.md"

BENCHMARK_ORDER = ["IslamTrust", "CatholicBench", "BuddhismEval", "BibleQA"]
SIZE_ORDER = {"S": 0, "M": 1, "L": 2}
SIZE_SLOTS = ["S", "M", "L"]
VALID_STATUSES = {"Done", "Blocked", "Partial", "Error", "Queue", "TBD", "Proxy"}

FAMILY_PALETTE = ["#4C72B0", "#DD8452", "#55A868", "#C44E52", "#8172B2"]
STATUS_COLORS = {
    "Done": "#55A868",
    "Partial": "#4C72B0",
    "Blocked": "#C44E52",
    "Error": "#C44E52",
    "Queue": "#8172B2",
    "TBD": "#999999",
    "Proxy": "#DD8452",
    "n/a": "#eeeeee",
}
STATUS_ABBREVIATIONS = {
    "Done": "D",
    "Partial": "P",
    "Blocked": "B",
    "Error": "E",
    "Queue": "Q",
    "TBD": "T",
    "Proxy": "X",
    "n/a": "-",
}

# Compatibility constants for existing repo tests. Runtime generation is driven
# by source/model_registry.csv, not by these lists.
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
    ("#35", "IslamTrust", "islamtrust_mc1", "access requested; waiting for HF gated access response"),
    ("#47", "CatholicBench", "catholicbench_official", "requires author access / official export needed"),
    ("#26", "BuddhismEval", "buddhism_eval_mcq", "official dataset inaccessible / permission required"),
    ("#37", "BibleQA", "bibleqa_sentence_selection", "official GitHub candidate-selection artifact"),
]


@dataclass(frozen=True)
class SourceBundle:
    scores: pd.DataFrame
    registry: pd.DataFrame
    meta: dict[str, Any]


@dataclass(frozen=True)
class ReleaseFrames:
    enriched_scores: pd.DataFrame
    benchmark_comparison: pd.DataFrame
    family_size_progress: pd.DataFrame
    benchmark_difficulty: pd.DataFrame
    family_scaling: pd.DataFrame


def source_paths() -> list[Path]:
    return [SCORES_PATH, REGISTRY_PATH, META_PATH]


def output_paths() -> list[Path]:
    return [*CSV_OUTPUTS, *SVG_OUTPUTS, README_BLOCKS_PATH]


def die(message: str) -> None:
    raise SystemExit(message)


def require_file(path: Path) -> None:
    if not path.exists():
        die(f"Missing required source file: {path.relative_to(ROOT)}")


def require_columns(df: pd.DataFrame, expected: set[str], path: Path) -> None:
    missing = expected.difference(df.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        die(f"Source file {path.relative_to(ROOT)} is missing required columns: {missing_text}")


def require_meta_fields(meta: dict[str, Any]) -> None:
    expected = {
        "report_owner",
        "release_date",
        "snapshot_label",
        "project_cost",
        "cost_breakdown",
        "matrix_description",
    }
    missing = expected.difference(meta)
    if missing:
        missing_text = ", ".join(sorted(missing))
        die(f"Source file {META_PATH.relative_to(ROOT)} is missing required fields: {missing_text}")


def read_sources() -> SourceBundle:
    for path in source_paths():
        require_file(path)

    scores = pd.read_csv(SCORES_PATH)
    registry = pd.read_csv(REGISTRY_PATH)
    with META_PATH.open("r", encoding="utf-8") as handle:
        meta = json.load(handle)

    require_columns(scores, {"line", "benchmark", "metric", "value", "status", "note"}, SCORES_PATH)
    require_columns(
        registry,
        {"family", "size_slot", "model_id", "route", "has_vision", "coverage_note"},
        REGISTRY_PATH,
    )
    require_meta_fields(meta)
    validate_scores(scores)
    validate_registry(registry)
    return SourceBundle(scores=scores, registry=registry, meta=meta)


def validate_scores(scores: pd.DataFrame) -> None:
    scores["line"] = scores["line"].astype(str)
    scores["benchmark"] = scores["benchmark"].astype(str)
    scores["metric"] = scores["metric"].fillna("n/a").astype(str)
    scores["status"] = scores["status"].astype(str)
    scores["note"] = scores["note"].fillna("").astype(str)
    scores["value"] = pd.to_numeric(scores["value"], errors="coerce")

    bad_status = sorted(set(scores["status"]).difference(VALID_STATUSES))
    if bad_status:
        die(f"Unknown benchmark_scores.csv status values: {', '.join(bad_status)}")

    values = scores["value"].dropna()
    if not values.between(0, 1).all():
        die("benchmark_scores.csv contains value entries outside [0, 1]")

    duplicates = scores.duplicated(subset=["line", "benchmark"], keep=False)
    if duplicates.any():
        pairs = scores.loc[duplicates, ["line", "benchmark"]].drop_duplicates()
        examples = "; ".join(f"{row.line}/{row.benchmark}" for row in pairs.itertuples(index=False))
        die(f"benchmark_scores.csv contains duplicate line+benchmark rows: {examples}")


def validate_registry(registry: pd.DataFrame) -> None:
    registry["family"] = registry["family"].astype(str)
    registry["size_slot"] = registry["size_slot"].astype(str)
    registry["model_id"] = registry["model_id"].astype(str)
    registry["route"] = registry["route"].astype(str)
    registry["coverage_note"] = registry["coverage_note"].fillna("").astype(str)
    registry["has_vision"] = registry["has_vision"].astype(str)

    bad_sizes = sorted(set(registry["size_slot"]).difference(SIZE_ORDER))
    if bad_sizes:
        die(f"model_registry.csv contains unknown size_slot values: {', '.join(bad_sizes)}")

    duplicates = registry.duplicated(subset=["family", "size_slot"], keep=False)
    if duplicates.any():
        pairs = registry.loc[duplicates, ["family", "size_slot"]].drop_duplicates()
        examples = "; ".join(f"{row.family}-{row.size_slot}" for row in pairs.itertuples(index=False))
        die(f"model_registry.csv contains duplicate family+size_slot rows: {examples}")


def registry_with_lines(registry: pd.DataFrame) -> pd.DataFrame:
    out = registry.copy()
    out["line"] = out["family"].astype(str) + "-" + out["size_slot"].astype(str)
    out["_family_order"] = out["family"].map({name: idx for idx, name in enumerate(out["family"].drop_duplicates())})
    out["_size_order"] = out["size_slot"].map(SIZE_ORDER)
    out["_line_order"] = range(len(out))
    return out


def ordered_benchmarks(scores: pd.DataFrame) -> list[str]:
    seen = [bench for bench in BENCHMARK_ORDER if bench in set(scores["benchmark"])]
    extras = [bench for bench in scores["benchmark"].drop_duplicates().tolist() if bench not in seen]
    return seen + extras


def infer_line_parts(line: str) -> tuple[str, str]:
    if "-" in line:
        family, size = line.rsplit("-", 1)
        if size in SIZE_ORDER:
            return family, size
    return line, ""


def complete_score_frame(scores: pd.DataFrame, registry: pd.DataFrame) -> pd.DataFrame:
    reg = registry_with_lines(registry)
    benchmarks = ordered_benchmarks(scores)
    base = reg[["line", "family", "size_slot", "model_id", "route", "has_vision", "coverage_note", "_family_order", "_size_order", "_line_order"]].merge(
        pd.DataFrame({"benchmark": benchmarks}),
        how="cross",
    )
    merged = base.merge(scores, on=["line", "benchmark"], how="left", suffixes=("", "_score"))

    extra_scores = scores[~scores["line"].isin(set(reg["line"]))].copy()
    if not extra_scores.empty:
        extra_scores[["family", "size_slot"]] = extra_scores["line"].apply(lambda value: pd.Series(infer_line_parts(str(value))))
        extra_scores["model_id"] = ""
        extra_scores["route"] = ""
        extra_scores["has_vision"] = ""
        extra_scores["coverage_note"] = ""
        family_order_start = len(reg["family"].drop_duplicates())
        extra_family_order = {name: family_order_start + idx for idx, name in enumerate(extra_scores["family"].drop_duplicates())}
        extra_scores["_family_order"] = extra_scores["family"].map(extra_family_order)
        extra_scores["_size_order"] = extra_scores["size_slot"].map(SIZE_ORDER).fillna(99).astype(int)
        extra_scores["_line_order"] = range(len(reg), len(reg) + len(extra_scores))
        merged = pd.concat([merged, extra_scores], ignore_index=True, sort=False)

    merged["metric"] = merged["metric"].fillna("n/a")
    merged["status"] = merged["status"].fillna("TBD")
    merged["note"] = merged["note"].fillna("not present in source snapshot")
    merged["value"] = pd.to_numeric(merged["value"], errors="coerce")
    merged["comparable_value"] = merged["value"].where((merged["status"] == "Done") & merged["value"].notna())
    merged["_family_order"] = merged["_family_order"].fillna(99).astype(int)
    merged["_size_order"] = merged["_size_order"].fillna(99).astype(int)
    merged["_line_order"] = merged["_line_order"].fillna(9999).astype(int)
    merged = merged.sort_values(["_family_order", "_size_order", "_line_order", "benchmark"]).reset_index(drop=True)
    return merged


def ordered_lines(df: pd.DataFrame) -> list[str]:
    line_order = (
        df[["line", "_family_order", "_size_order", "_line_order"]]
        .drop_duplicates("line")
        .sort_values(["_family_order", "_size_order", "_line_order", "line"])
    )
    return line_order["line"].tolist()


def family_color_map(df: pd.DataFrame) -> dict[str, str]:
    families = (
        df[["family", "_family_order"]]
        .drop_duplicates("family")
        .sort_values(["_family_order", "family"])["family"]
        .tolist()
    )
    return {family: FAMILY_PALETTE[idx % len(FAMILY_PALETTE)] for idx, family in enumerate(families)}


def build_release_frames(bundle: SourceBundle) -> ReleaseFrames:
    enriched = complete_score_frame(bundle.scores.copy(), bundle.registry.copy())
    lines = ordered_lines(enriched)
    benchmarks = ordered_benchmarks(enriched)

    comparison = (
        enriched.pivot(index="line", columns="benchmark", values="comparable_value")
        .reindex(index=lines, columns=benchmarks)
        .reset_index()
    )

    progress = (
        enriched.pivot(index="line", columns="benchmark", values="status")
        .reindex(index=lines, columns=benchmarks)
        .reset_index()
    )

    difficulty_rows: list[dict[str, Any]] = []
    valid = enriched[enriched["comparable_value"].notna()].copy()
    for benchmark in benchmarks:
        subset = valid[valid["benchmark"] == benchmark].copy()
        if subset.empty:
            difficulty_rows.append(
                {
                    "benchmark": benchmark,
                    "mean": math.nan,
                    "best_line": "",
                    "best_val": math.nan,
                    "worst_line": "",
                    "worst_val": math.nan,
                    "spread": math.nan,
                }
            )
            continue
        best_idx = subset["comparable_value"].idxmax()
        worst_idx = subset["comparable_value"].idxmin()
        best = subset.loc[best_idx]
        worst = subset.loc[worst_idx]
        difficulty_rows.append(
            {
                "benchmark": benchmark,
                "mean": float(subset["comparable_value"].mean()),
                "best_line": str(best["line"]),
                "best_val": float(best["comparable_value"]),
                "worst_line": str(worst["line"]),
                "worst_val": float(worst["comparable_value"]),
                "spread": float(subset["comparable_value"].max() - subset["comparable_value"].min()),
            }
        )
    difficulty = pd.DataFrame(difficulty_rows)

    scaling = enriched[["family", "benchmark", "size_slot", "comparable_value"]].rename(columns={"comparable_value": "value"})
    scaling = scaling.sort_values(["family", "benchmark", "size_slot"]).reset_index(drop=True)

    return ReleaseFrames(
        enriched_scores=enriched,
        benchmark_comparison=comparison,
        family_size_progress=progress,
        benchmark_difficulty=difficulty,
        family_scaling=scaling,
    )


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def atomic_write_csv(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    df.to_csv(tmp, index=False, lineterminator="\n")
    tmp.replace(path)


def format_float(value: Any, digits: int = 3) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"{float(value):.{digits}f}"


def format_cell(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    if isinstance(value, float):
        return format_float(value)
    return str(value)


def markdown_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = []
    for row in rows:
        body.append("| " + " | ".join(format_cell(row.get(col, "")) for col in columns) + " |")
    return "\n".join([header, separator, *body])


def svg_title(title: str) -> str:
    return f"<title>{escape(title)}</title>"


def svg_style() -> str:
    return """<style>
        text { font-family: system-ui, sans-serif; fill: #222; }
        .title { font-size: 14px; font-weight: 700; }
        .axis { font-size: 11px; }
        .small { font-size: 9px; }
        .tiny { font-size: 8px; }
        .grid { stroke: #dddddd; stroke-width: 1; }
        .axis-line { stroke: #333333; stroke-width: 1; }
        .outline { stroke: #ffffff; stroke-width: 1; }
    </style>"""


def svg_doc(title: str, body: str, defs: str = "") -> str:
    defs_block = f"<defs>{defs}</defs>" if defs else ""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 480" role="img">\n'
        f"{svg_title(title)}\n"
        f"{svg_style()}\n"
        f"{defs_block}\n"
        f"{body}\n"
        "</svg>\n"
    )


def txt(x: float, y: float, content: Any, cls: str = "axis", anchor: str = "start", extra: str = "") -> str:
    return f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" text-anchor="{anchor}" {extra}>{escape(str(content))}</text>'


def rect(x: float, y: float, w: float, h: float, fill: str, cls: str = "", extra: str = "") -> str:
    cls_attr = f' class="{cls}"' if cls else ""
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w, 0):.1f}" height="{max(h, 0):.1f}" fill="{fill}"{cls_attr} {extra}/>'


def line(x1: float, y1: float, x2: float, y2: float, cls: str = "axis-line", extra: str = "") -> str:
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="{cls}" {extra}/>'


def circle(x: float, y: float, r: float, fill: str, stroke: str = "#333333", extra: str = "") -> str:
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="1.5" {extra}/>'


def heat_color(value: float) -> str:
    low = (247, 251, 255)
    high = (8, 81, 156)
    v = max(0.0, min(1.0, value))
    rgb = tuple(round(low[i] + (high[i] - low[i]) * v) for i in range(3))
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def render_status_legend(x: float, y: float, statuses: list[str]) -> str:
    parts = []
    for idx, status in enumerate(statuses):
        sx = x + idx * 92
        parts.append(rect(sx, y - 11, 12, 12, STATUS_COLORS.get(status, "#999999")))
        parts.append(txt(sx + 17, y, status, "small"))
    return "\n".join(parts)


def generate_family_size_progress_overview(df: pd.DataFrame, path: Path = SVG_OUTPUTS[0], dry_run: bool = False) -> str:
    title = "Family-Size Progress Overview"
    lines = ordered_lines(df)
    benchmarks = ordered_benchmarks(df)
    status_map = {(row.line, row.benchmark): row.status for row in df.itertuples(index=False)}

    left = 128
    bar_x = 220
    bar_w = 540
    top = 52
    row_h = min(23, max(13, 345 / max(len(lines), 1)))
    bar_h = min(16, row_h - 3)
    seg_w = bar_w / max(len(benchmarks), 1)
    parts = [txt(450, 24, title, "title", "middle")]
    parts.append(txt(left, 42, "Model line", "axis", "end"))
    for idx, benchmark in enumerate(benchmarks):
        parts.append(txt(bar_x + idx * seg_w + seg_w / 2, 42, benchmark[:12], "tiny", "middle"))
    for row_idx, model_line in enumerate(lines):
        y = top + row_idx * row_h
        parts.append(txt(left, y + bar_h - 3, model_line, "axis", "end"))
        for idx, benchmark in enumerate(benchmarks):
            status = status_map.get((model_line, benchmark), "TBD")
            color = STATUS_COLORS.get(status, "#999999")
            parts.append(rect(bar_x + idx * seg_w, y, seg_w - 1, bar_h, color, "outline"))
    parts.append(render_status_legend(160, 445, ["Done", "Partial", "Blocked", "Error", "Queue", "TBD"]))
    svg = svg_doc(title, "\n".join(parts))
    if not dry_run:
        atomic_write_text(path, svg)
    return str(path)


def generate_benchmark_accuracy_bars(df: pd.DataFrame, path: Path = SVG_OUTPUTS[1], dry_run: bool = False) -> str:
    title = "Benchmark Accuracy Bars"
    lines = ordered_lines(df)
    benchmarks = ordered_benchmarks(df)
    family_colors = family_color_map(df)
    lookup = {(row.line, row.benchmark): row for row in df.itertuples(index=False)}
    line_family = df.drop_duplicates("line").set_index("line")["family"].to_dict()

    x0 = 238
    x1 = 760
    top = 50
    available_h = 370
    row_h = max(4.2, min(7.2, available_h / max(len(lines) * len(benchmarks) + len(benchmarks), 1)))
    bar_h = max(2.8, row_h - 1.0)
    parts = [txt(450, 24, title, "title", "middle")]
    for tick in [0, 0.25, 0.5, 0.75, 1.0]:
        x = x0 + tick * (x1 - x0)
        parts.append(line(x, 42, x, 430, "grid"))
        parts.append(txt(x, 444, f"{tick:.2f}", "small", "middle"))
    parts.append(txt((x0 + x1) / 2, 465, "Accuracy", "axis", "middle"))

    y = top
    for benchmark in benchmarks:
        parts.append(txt(20, y + 8, benchmark, "axis"))
        for model_line in lines:
            row = lookup.get((model_line, benchmark))
            value = float(row.comparable_value) if row is not None and not pd.isna(row.comparable_value) else math.nan
            family = line_family.get(model_line, "")
            color = family_colors.get(family, "#4C72B0")
            label = "n/a" if pd.isna(value) else f"{value:.2f}"
            width = 9 if pd.isna(value) else max(2, value * (x1 - x0))
            fill = "#dddddd" if pd.isna(value) else color
            parts.append(txt(150, y + bar_h, model_line, "tiny", "end"))
            parts.append(rect(x0, y, width, bar_h, fill))
            parts.append(txt(x0 + width + 4, y + bar_h, label, "tiny"))
            y += row_h
        y += row_h * 0.7
    svg = svg_doc(title, "\n".join(parts))
    if not dry_run:
        atomic_write_text(path, svg)
    return str(path)


def generate_accuracy_heatmap(df: pd.DataFrame, path: Path = SVG_OUTPUTS[2], dry_run: bool = False) -> str:
    title = "Accuracy Heatmap"
    lines = ordered_lines(df)
    benchmarks = ordered_benchmarks(df)
    lookup = {(row.line, row.benchmark): row for row in df.itertuples(index=False)}
    left = 160
    top = 62
    grid_w = 560
    grid_h = 310
    cell_w = grid_w / max(len(benchmarks), 1)
    cell_h = grid_h / max(len(lines), 1)
    defs = """
        <pattern id="diagonalHatch" patternUnits="userSpaceOnUse" width="8" height="8">
            <path d="M-2,2 l4,-4 M0,8 l8,-8 M6,10 l4,-4" stroke="#bbbbbb" stroke-width="1"/>
        </pattern>
        <linearGradient id="heatLegend" x1="0%" x2="100%" y1="0%" y2="0%">
            <stop offset="0%" stop-color="#f7fbff"/>
            <stop offset="100%" stop-color="#08519c"/>
        </linearGradient>
    """
    parts = [txt(450, 24, title, "title", "middle")]
    for idx, benchmark in enumerate(benchmarks):
        parts.append(txt(left + idx * cell_w + cell_w / 2, 50, benchmark, "axis", "middle"))
    for row_idx, model_line in enumerate(lines):
        y = top + row_idx * cell_h
        parts.append(txt(left - 8, y + cell_h * 0.68, model_line, "axis", "end"))
        for col_idx, benchmark in enumerate(benchmarks):
            row = lookup.get((model_line, benchmark))
            value = float(row.comparable_value) if row is not None and not pd.isna(row.comparable_value) else math.nan
            x = left + col_idx * cell_w
            if pd.isna(value):
                parts.append(rect(x, y, cell_w - 1, cell_h - 1, "#eeeeee"))
                parts.append(rect(x, y, cell_w - 1, cell_h - 1, "url(#diagonalHatch)"))
                label = "n/a"
            else:
                parts.append(rect(x, y, cell_w - 1, cell_h - 1, heat_color(value)))
                label = f"{value:.2f}"
            parts.append(txt(x + cell_w / 2, y + cell_h * 0.68, label, "tiny", "middle"))
    parts.append(rect(750, 100, 24, 180, "url(#heatLegend)", extra='transform="rotate(90 762 190)"'))
    parts.append(txt(790, 104, "1.0", "small"))
    parts.append(txt(790, 282, "0.0", "small"))
    parts.append(txt(762, 315, "Accuracy", "axis", "middle"))
    svg = svg_doc(title, "\n".join(parts), defs=defs)
    if not dry_run:
        atomic_write_text(path, svg)
    return str(path)


def generate_benchmark_difficulty_profile(df: pd.DataFrame, path: Path = SVG_OUTPUTS[3], dry_run: bool = False) -> str:
    title = "Benchmark Difficulty Profile"
    benchmarks = ordered_benchmarks(df)
    valid = df[df["comparable_value"].notna()]
    left = 190
    x0 = 250
    x1 = 760
    top = 80
    row_h = 72
    parts = [txt(450, 24, title, "title", "middle")]
    for tick in [0, 0.25, 0.5, 0.75, 1.0]:
        x = x0 + tick * (x1 - x0)
        parts.append(line(x, 52, x, 390, "grid"))
        parts.append(txt(x, 414, f"{tick:.2f}", "small", "middle"))
    parts.append(txt((x0 + x1) / 2, 450, "Accuracy", "axis", "middle"))
    for idx, benchmark in enumerate(benchmarks):
        y = top + idx * row_h
        subset = valid[valid["benchmark"] == benchmark]
        parts.append(txt(left, y + 4, benchmark, "axis", "end"))
        if subset.empty:
            parts.append(txt(x0, y + 4, "n/a", "axis"))
            continue
        values = subset["comparable_value"].astype(float)
        mean = float(values.mean())
        min_val = float(values.min())
        max_val = float(values.max())
        best = subset.loc[values.idxmax()]
        worst = subset.loc[values.idxmin()]
        min_x = x0 + min_val * (x1 - x0)
        max_x = x0 + max_val * (x1 - x0)
        mean_x = x0 + mean * (x1 - x0)
        parts.append(line(min_x, y, max_x, y, "axis-line", 'stroke-width="3"'))
        parts.append(line(min_x, y - 8, min_x, y + 8, "axis-line"))
        parts.append(line(max_x, y - 8, max_x, y + 8, "axis-line"))
        parts.append(circle(mean_x, y, 5, "#4C72B0", "#333333"))
        parts.append(txt(mean_x + 10, y + 4, f"mean {mean:.3f}", "small"))
        parts.append(txt(x0, y + 22, f"best {best.line} {max_val:.3f}; worst {worst.line} {min_val:.3f}", "tiny"))
    svg = svg_doc(title, "\n".join(parts))
    if not dry_run:
        atomic_write_text(path, svg)
    return str(path)


def generate_family_scaling_profile(df: pd.DataFrame, path: Path = SVG_OUTPUTS[4], dry_run: bool = False) -> str:
    title = "Family Scaling Profile"
    benchmarks = ordered_benchmarks(df)
    family_colors = family_color_map(df)
    families = list(family_colors)
    left = 82
    right = 740
    top = 54
    subplot_h = 82
    x_positions = {"S": left + 80, "M": left + 190, "L": left + 300}
    parts = [txt(450, 24, title, "title", "middle")]
    for row_idx, benchmark in enumerate(benchmarks):
        y0 = top + row_idx * subplot_h
        y1 = y0 + 56
        parts.append(txt(20, y0 + 30, benchmark, "axis"))
        parts.append(line(left, y1, right, y1, "grid"))
        parts.append(line(left, y0, left, y1, "axis-line"))
        for tick in [0, 0.5, 1.0]:
            y = y1 - tick * (y1 - y0)
            parts.append(line(left - 3, y, right, y, "grid"))
            parts.append(txt(left - 8, y + 3, f"{tick:.1f}", "tiny", "end"))
        for size, x in x_positions.items():
            parts.append(txt(x, y1 + 14, size, "small", "middle"))

        for family in families:
            fam_df = df[(df["family"] == family) & (df["benchmark"] == benchmark)]
            point_coords: list[tuple[float, float]] = []
            color = family_colors[family]
            for size in SIZE_SLOTS:
                row = fam_df[fam_df["size_slot"] == size]
                x = x_positions[size]
                if row.empty or pd.isna(row.iloc[0]["comparable_value"]):
                    parts.append(circle(x, y1 - 3, 3, "#ffffff", color))
                    continue
                value = float(row.iloc[0]["comparable_value"])
                y = y1 - value * (y1 - y0)
                point_coords.append((x, y))
                parts.append(circle(x, y, 3.5, color, color))
            if len(point_coords) >= 2:
                path_d = " ".join(("M" if idx == 0 else "L") + f"{x:.1f},{y:.1f}" for idx, (x, y) in enumerate(point_coords))
                parts.append(f'<path d="{path_d}" fill="none" stroke="{color}" stroke-width="1.6"/>')

    legend_x = 470
    legend_y = 62
    for idx, family in enumerate(families):
        y = legend_y + idx * 18
        parts.append(line(legend_x, y - 4, legend_x + 18, y - 4, extra=f'stroke="{family_colors[family]}" stroke-width="2"'))
        parts.append(txt(legend_x + 24, y, family, "small"))
    svg = svg_doc(title, "\n".join(parts))
    if not dry_run:
        atomic_write_text(path, svg)
    return str(path)


def generate_coverage_matrix(df: pd.DataFrame, path: Path = SVG_OUTPUTS[5], dry_run: bool = False) -> str:
    title = "Coverage Matrix"
    lines = ordered_lines(df)
    benchmarks = ordered_benchmarks(df)
    lookup = {(row.line, row.benchmark): row.status for row in df.itertuples(index=False)}
    left = 135
    top = 80
    cell_w = min(45, 700 / max(len(lines), 1))
    cell_h = 42
    parts = [txt(450, 24, title, "title", "middle")]
    for col, model_line in enumerate(lines):
        x = left + col * cell_w + cell_w / 2
        parts.append(txt(x, 68, model_line, "tiny", "middle", 'transform="rotate(-45 {0:.1f} 68)"'.format(x)))
    for row_idx, benchmark in enumerate(benchmarks):
        y = top + row_idx * cell_h
        parts.append(txt(left - 8, y + 25, benchmark, "axis", "end"))
        for col, model_line in enumerate(lines):
            status = lookup.get((model_line, benchmark), "TBD")
            color = STATUS_COLORS.get(status, "#999999")
            x = left + col * cell_w
            parts.append(rect(x, y, cell_w - 2, cell_h - 3, color))
            parts.append(txt(x + cell_w / 2 - 1, y + 24, STATUS_ABBREVIATIONS.get(status, "?"), "axis", "middle"))
    key_statuses = ["Done", "Partial", "Blocked", "Error", "Queue", "TBD", "Proxy"]
    parts.append(render_status_legend(95, 435, key_statuses))
    svg = svg_doc(title, "\n".join(parts))
    if not dry_run:
        atomic_write_text(path, svg)
    return str(path)


def build_tldr(frames: ReleaseFrames, meta: dict[str, Any]) -> list[str]:
    df = frames.enriched_scores
    done_values = df[df["comparable_value"].notna()]
    done_cells = int((df["status"] == "Done").sum())
    blocked = int(df["status"].isin(["Blocked", "TBD", "Queue"]).sum())
    bullets = [
        f"Snapshot `{meta['snapshot_label']}` is owned by {meta['report_owner']} and dated {meta['release_date']}.",
        f"Comparable completed cells with numeric accuracy: {len(done_values)}; total Done status cells: {done_cells}.",
    ]
    if blocked:
        bullets.append(f"Blocked/queued/TBD cells remain clearly labeled: {blocked}.")
    if not done_values.empty:
        best = done_values.loc[done_values["comparable_value"].idxmax()]
        bullets.append(f"Best current comparable cell: {best.line} on {best.benchmark} at {float(best.comparable_value):.3f}.")
    if meta.get("project_cost") not in {"", None}:
        bullets.append(f"Project cost snapshot: {meta['project_cost']}.")
    if meta.get("matrix_description"):
        bullets.append(str(meta["matrix_description"]))
    return bullets[:6]


def comparable_accuracy_markdown(frames: ReleaseFrames) -> str:
    rows = []
    for record in frames.benchmark_comparison.to_dict("records"):
        rows.append({key: format_float(value) if key != "line" else value for key, value in record.items()})
    return markdown_table(rows, list(frames.benchmark_comparison.columns))


def progress_markdown(frames: ReleaseFrames) -> str:
    return markdown_table(frames.family_size_progress.to_dict("records"), list(frames.family_size_progress.columns))


def difficulty_markdown(frames: ReleaseFrames) -> str:
    rows = []
    columns = ["benchmark", "mean", "best_line", "best_val", "worst_line", "worst_val", "spread"]
    for record in frames.benchmark_difficulty.to_dict("records"):
        rows.append(
            {
                "benchmark": record["benchmark"],
                "mean": format_float(record["mean"]),
                "best_line": record["best_line"],
                "best_val": format_float(record["best_val"]),
                "worst_line": record["worst_line"],
                "worst_val": format_float(record["worst_val"]),
                "spread": format_float(record["spread"]),
            }
        )
    return markdown_table(rows, columns)


def metadata_markdown(meta: dict[str, Any]) -> str:
    rows = []
    for key in ["report_owner", "release_date", "snapshot_label", "project_cost", "matrix_description"]:
        rows.append({"field": key, "value": meta.get(key, "")})
    rows.append({"field": "cost_breakdown", "value": json.dumps(meta.get("cost_breakdown", ""), sort_keys=True)})
    return markdown_table(rows, ["field", "value"])


def block(name: str, content: str) -> str:
    return f"<!-- BLOCK: {name} -->\n{content.rstrip()}\n<!-- /BLOCK: {name} -->"


def build_readme_blocks(frames: ReleaseFrames, meta: dict[str, Any]) -> str:
    tldr = "\n".join(f"- {item}" for item in build_tldr(frames, meta))
    blocks = [
        block("tldr", tldr),
        block("current-comparable-accuracy-table", comparable_accuracy_markdown(frames)),
        block("family-size-progress-matrix", progress_markdown(frames)),
        block("benchmark-difficulty-table", difficulty_markdown(frames)),
        block("snapshot-metadata", metadata_markdown(meta)),
    ]
    return "\n\n".join(blocks) + "\n"


def write_artifacts(frames: ReleaseFrames, meta: dict[str, Any], dry_run: bool = False) -> list[Path]:
    written: list[Path] = []
    csv_frames = {
        CSV_OUTPUTS[0]: frames.benchmark_comparison,
        CSV_OUTPUTS[1]: frames.family_size_progress,
        CSV_OUTPUTS[2]: frames.benchmark_difficulty,
        CSV_OUTPUTS[3]: frames.family_scaling,
    }
    for path, df in csv_frames.items():
        if not dry_run:
            atomic_write_csv(path, df)
        written.append(path)

    for figure_func in [
        generate_family_size_progress_overview,
        generate_benchmark_accuracy_bars,
        generate_accuracy_heatmap,
        generate_benchmark_difficulty_profile,
        generate_family_scaling_profile,
        generate_coverage_matrix,
    ]:
        figure_path = Path(figure_func(frames.enriched_scores, dry_run=dry_run))
        written.append(figure_path)

    if not dry_run:
        atomic_write_text(README_BLOCKS_PATH, build_readme_blocks(frames, meta))
    written.append(README_BLOCKS_PATH)
    return written


def print_summary(paths: list[Path], dry_run: bool = False) -> None:
    if dry_run:
        print("Dry run complete. Planned outputs:")
        for path in paths:
            print(f"- {path.relative_to(ROOT)}")
        print("No files written.")
        return
    print("Release artifacts written:")
    for path in paths:
        size = path.stat().st_size if path.exists() else 0
        print(f"- {path.relative_to(ROOT)} ({size} bytes)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Validate inputs and list planned outputs without writing")
    args = parser.parse_args(argv)

    bundle = read_sources()
    frames = build_release_frames(bundle)
    paths = write_artifacts(frames, bundle.meta, dry_run=args.dry_run)
    print_summary(paths, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
