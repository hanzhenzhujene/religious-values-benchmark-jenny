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

FAMILY_PALETTE = ["#2563EB", "#F97316", "#059669", "#DC2626", "#7C3AED"]
STATUS_COLORS = {
    "Done": "#15803D",
    "Partial": "#2563EB",
    "Blocked": "#B42318",
    "Error": "#7F1D1D",
    "Queue": "#7C3AED",
    "TBD": "#6B7280",
    "Proxy": "#B45309",
    "n/a": "#E5E7EB",
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

INK = "#111827"
MUTED = "#6B7280"
GRID = "#E5E7EB"
SURFACE = "#FFFFFF"
BACKGROUND = "#F8FAFC"
HATCH = "#9CA3AF"

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
        text { font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: #111827; }
        .title { font-size: 16px; font-weight: 750; }
        .subtitle { font-size: 11px; fill: #6B7280; }
        .axis { font-size: 11px; }
        .small { font-size: 10px; }
        .tiny { font-size: 8.5px; }
        .value { font-size: 10px; font-weight: 650; }
        .cell-label { font-size: 10px; font-weight: 750; fill: #ffffff; }
        .muted { font-size: 10px; fill: #6B7280; }
        .grid { stroke: #E5E7EB; stroke-width: 1; }
        .axis-line { stroke: #374151; stroke-width: 1; }
        .outline { stroke: #ffffff; stroke-width: 1; }
        .panel { stroke: #E5E7EB; stroke-width: 1; }
    </style>"""


def svg_doc(title: str, body: str, defs: str = "") -> str:
    defs_block = f"<defs>{defs}</defs>" if defs else ""
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 480" role="img">\n'
        f"{svg_title(title)}\n"
        f"{svg_style()}\n"
        f"{defs_block}\n"
        f'<rect x="0" y="0" width="900" height="480" fill="{BACKGROUND}"/>\n'
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
        sx = x + idx * 94
        parts.append(rect(sx, y - 12, 14, 14, STATUS_COLORS.get(status, "#999999")))
        parts.append(txt(sx + 19, y, status, "small"))
    return "\n".join(parts)


def render_family_legend(family_colors: dict[str, str], x: float, y: float, step: float = 98) -> str:
    parts = []
    for idx, (family, color) in enumerate(family_colors.items()):
        sx = x + idx * step
        parts.append(rect(sx, y - 12, 14, 14, color))
        parts.append(txt(sx + 19, y, family, "small"))
    return "\n".join(parts)


def row_fill(index: int) -> str:
    return "#FFFFFF" if index % 2 == 0 else "#F3F4F6"


def generate_family_size_progress_overview(df: pd.DataFrame, path: Path = SVG_OUTPUTS[0], dry_run: bool = False) -> str:
    title = "Family-Size Progress Overview"
    lines = ordered_lines(df)
    benchmarks = ordered_benchmarks(df)
    status_map = {(row.line, row.benchmark): row.status for row in df.itertuples(index=False)}
    done_cells = sum(1 for status in status_map.values() if status == "Done")
    blocked_cells = sum(1 for status in status_map.values() if status == "Blocked")

    label_x = 138
    grid_x = 170
    grid_y = 72
    grid_w = 540
    row_h = 20
    cell_h = 15
    cell_w = grid_w / max(len(benchmarks), 1)
    parts = [
        rect(28, 40, 844, 378, SURFACE, "panel"),
        txt(450, 24, title, "title", "middle"),
        txt(450, 44, "One row per model line; each segment is one assigned benchmark.", "subtitle", "middle"),
        txt(label_x, 62, "Line", "axis", "end"),
    ]
    for idx, benchmark in enumerate(benchmarks):
        parts.append(txt(grid_x + idx * cell_w + cell_w / 2, 62, benchmark, "axis", "middle"))

    for row_idx, model_line in enumerate(lines):
        y = grid_y + row_idx * row_h
        parts.append(rect(40, y - 3, 760, row_h, row_fill(row_idx)))
        parts.append(txt(label_x, y + 10, model_line, "axis", "end"))
        for idx, benchmark in enumerate(benchmarks):
            status = status_map.get((model_line, benchmark), "TBD")
            color = STATUS_COLORS.get(status, STATUS_COLORS["TBD"])
            x = grid_x + idx * cell_w
            parts.append(rect(x, y, cell_w - 3, cell_h, color, "outline"))
            parts.append(txt(x + cell_w / 2, y + 11, STATUS_ABBREVIATIONS.get(status, "?"), "cell-label", "middle"))

    summary_x = 735
    parts.append(rect(summary_x, 80, 112, 84, "#F9FAFB", "panel"))
    parts.append(txt(summary_x + 12, 104, f"{done_cells} Done", "value"))
    parts.append(txt(summary_x + 12, 126, f"{blocked_cells} Blocked", "value"))
    parts.append(txt(summary_x + 12, 148, "0 Proxy", "muted"))
    parts.append(render_status_legend(95, 445, ["Done", "Blocked", "Partial", "Error", "Queue", "TBD"]))
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
    measured_benchmarks = [
        benchmark
        for benchmark in benchmarks
        if any(
            (lookup.get((model_line, benchmark)) is not None)
            and not pd.isna(lookup[(model_line, benchmark)].comparable_value)
            for model_line in lines
        )
    ]

    x0 = 210
    x1 = 700
    top = 74
    group_gap = 18
    available_h = 320
    total_rows = max(len(measured_benchmarks) * len(lines), 1)
    row_h = min(13, available_h / total_rows)
    bar_h = max(5, row_h - 3)
    parts = [
        rect(28, 40, 844, 380, SURFACE, "panel"),
        txt(450, 24, title, "title", "middle"),
        txt(450, 44, "Grouped by benchmark; n/a stubs mark lines without comparable accuracy.", "subtitle", "middle"),
    ]
    for tick in [0, 0.25, 0.5, 0.75, 1.0]:
        x = x0 + tick * (x1 - x0)
        parts.append(line(x, 62, x, 392, "grid"))
        parts.append(txt(x, 411, f"{tick:.2f}", "small", "middle"))
    parts.append(txt((x0 + x1) / 2, 438, "Accuracy", "axis", "middle"))

    if not measured_benchmarks:
        parts.append(txt(450, 232, "No comparable benchmark scores available in this snapshot.", "value", "middle"))

    row_idx = 0
    for benchmark in measured_benchmarks:
        group_y = top + row_idx * row_h + measured_benchmarks.index(benchmark) * group_gap
        parts.append(txt(112, group_y + 8, benchmark, "value", "end"))
        for model_line in lines:
            y = top + row_idx * row_h + measured_benchmarks.index(benchmark) * group_gap
            family = line_family.get(model_line, "")
            color = family_colors.get(family, FAMILY_PALETTE[0])
            row = lookup.get((model_line, benchmark))
            value = float(row.comparable_value) if row is not None and not pd.isna(row.comparable_value) else math.nan
            parts.append(txt(190, y + bar_h, model_line, "tiny", "end"))
            if pd.isna(value):
                parts.append(rect(x0, y, 8, bar_h, "#D1D5DB"))
                parts.append(txt(x0 + 14, y + bar_h, "n/a", "tiny"))
            else:
                width = max(2, value * (x1 - x0))
                parts.append(rect(x0, y, width, bar_h, color))
                parts.append(txt(min(x0 + width + 5, 760), y + bar_h, f"{value:.3f}", "tiny"))
            row_idx += 1

    blocked_only = [benchmark for benchmark in benchmarks if benchmark not in measured_benchmarks]
    if blocked_only:
        parts.append(txt(760, 86, "Blocked:", "small"))
        for idx, benchmark in enumerate(blocked_only[:4]):
            parts.append(txt(760, 104 + idx * 15, benchmark, "tiny"))
    parts.append(render_family_legend(family_colors, 170, 455, step=105))
    svg = svg_doc(title, "\n".join(parts))
    if not dry_run:
        atomic_write_text(path, svg)
    return str(path)


def generate_accuracy_heatmap(df: pd.DataFrame, path: Path = SVG_OUTPUTS[2], dry_run: bool = False) -> str:
    title = "Accuracy Heatmap"
    lines = ordered_lines(df)
    benchmarks = ordered_benchmarks(df)
    lookup = {(row.line, row.benchmark): row for row in df.itertuples(index=False)}
    line_family = df.drop_duplicates("line").set_index("line")["family"].to_dict()
    family_colors = family_color_map(df)
    left = 172
    top = 76
    grid_w = 560
    grid_h = 300
    cell_w = grid_w / max(len(benchmarks), 1)
    cell_h = grid_h / max(len(lines), 1)
    defs = """
        <pattern id="diagonalHatch" patternUnits="userSpaceOnUse" width="8" height="8">
            <path d="M-2,2 l4,-4 M0,8 l8,-8 M6,10 l4,-4" stroke="#9CA3AF" stroke-width="1"/>
        </pattern>
        <linearGradient id="heatLegend" x1="0%" x2="0%" y1="100%" y2="0%">
            <stop offset="0%" stop-color="#f7fbff"/>
            <stop offset="100%" stop-color="#08519c"/>
        </linearGradient>
    """
    parts = [
        rect(28, 40, 844, 380, SURFACE, "panel"),
        txt(450, 24, title, "title", "middle"),
        txt(450, 44, "Color encodes comparable accuracy; hatched cells mean official data is blocked.", "subtitle", "middle"),
    ]
    for idx, benchmark in enumerate(benchmarks):
        parts.append(txt(left + idx * cell_w + cell_w / 2, 64, benchmark, "axis", "middle"))
    for row_idx, model_line in enumerate(lines):
        y = top + row_idx * cell_h
        family = line_family.get(model_line, "")
        family_color = family_colors.get(family, MUTED)
        parts.append(rect(42, y, 8, cell_h - 1, family_color))
        parts.append(txt(left - 12, y + cell_h * 0.68, model_line, "axis", "end"))
        for col_idx, benchmark in enumerate(benchmarks):
            row = lookup.get((model_line, benchmark))
            value = float(row.comparable_value) if row is not None and not pd.isna(row.comparable_value) else math.nan
            x = left + col_idx * cell_w
            if pd.isna(value):
                parts.append(rect(x, y, cell_w - 1, cell_h - 1, "#eeeeee"))
                parts.append(rect(x, y, cell_w - 1, cell_h - 1, "url(#diagonalHatch)"))
                label = "n/a"
                label_cls = "tiny"
            else:
                parts.append(rect(x, y, cell_w - 1, cell_h - 1, heat_color(value)))
                label = f"{value:.2f}"
                label_cls = "cell-label" if value > 0.58 else "value"
            parts.append(txt(x + cell_w / 2, y + cell_h * 0.68, label, label_cls, "middle"))
    legend_x = 770
    legend_y = 112
    legend_h = 170
    parts.append(rect(legend_x, legend_y, 22, legend_h, "url(#heatLegend)", "panel"))
    for tick, label in [(1.0, "1.0"), (0.5, "0.5"), (0.0, "0.0")]:
        y = legend_y + (1.0 - tick) * legend_h
        parts.append(line(legend_x + 24, y, legend_x + 32, y, "axis-line"))
        parts.append(txt(legend_x + 38, y + 4, label, "small"))
    parts.append(txt(legend_x + 11, legend_y + legend_h + 28, "Accuracy", "axis", "middle"))
    parts.append(render_family_legend(family_colors, 170, 455, step=105))
    svg = svg_doc(title, "\n".join(parts), defs=defs)
    if not dry_run:
        atomic_write_text(path, svg)
    return str(path)


def generate_benchmark_difficulty_profile(df: pd.DataFrame, path: Path = SVG_OUTPUTS[3], dry_run: bool = False) -> str:
    title = "Benchmark Difficulty Profile"
    benchmarks = ordered_benchmarks(df)
    valid = df[df["comparable_value"].notna()]
    measured_benchmarks = [
        benchmark
        for benchmark in benchmarks
        if valid[valid["benchmark"] == benchmark].shape[0] > 0
    ]
    left = 164
    x0 = 250
    x1 = 760
    row_count = max(len(measured_benchmarks), 1)
    top = 148 if row_count == 1 else 90
    row_h = 74 if row_count > 1 else 88
    parts = [
        rect(28, 40, 844, 380, SURFACE, "panel"),
        txt(450, 24, title, "title", "middle"),
        txt(450, 44, "Mean dot plus min-max range for benchmarks with official comparable scores.", "subtitle", "middle"),
    ]
    for tick in [0, 0.25, 0.5, 0.75, 1.0]:
        x = x0 + tick * (x1 - x0)
        parts.append(line(x, 68, x, 390, "grid"))
        parts.append(txt(x, 412, f"{tick:.2f}", "small", "middle"))
    parts.append(txt((x0 + x1) / 2, 445, "Accuracy", "axis", "middle"))
    if not measured_benchmarks:
        parts.append(txt(450, 226, "No comparable benchmark scores available in this snapshot.", "value", "middle"))
    for idx, benchmark in enumerate(measured_benchmarks):
        y = top + idx * row_h
        parts.append(rect(48, y - 24, 780, 48, row_fill(idx)))
        subset = valid[valid["benchmark"] == benchmark]
        parts.append(txt(left, y + 4, benchmark, "axis", "end"))
        values = subset["comparable_value"].astype(float)
        mean = float(values.mean())
        min_val = float(values.min())
        max_val = float(values.max())
        best = subset.loc[values.idxmax()]
        worst = subset.loc[values.idxmin()]
        min_x = x0 + min_val * (x1 - x0)
        max_x = x0 + max_val * (x1 - x0)
        mean_x = x0 + mean * (x1 - x0)
        parts.append(line(min_x, y, max_x, y, "axis-line", 'stroke="#2563EB" stroke-width="4" stroke-linecap="round"'))
        parts.append(line(min_x, y - 8, min_x, y + 8, "axis-line"))
        parts.append(line(max_x, y - 8, max_x, y + 8, "axis-line"))
        parts.append(circle(mean_x, y, 5, "#FFFFFF", "#2563EB"))
        parts.append(txt(mean_x + 10, y + 4, f"mean {mean:.3f}", "value"))
        parts.append(txt(x0, y + 22, f"best {best.line} {max_val:.3f}; worst {worst.line} {min_val:.3f}", "small"))
    blocked_benchmarks = [benchmark for benchmark in benchmarks if benchmark not in measured_benchmarks]
    if blocked_benchmarks:
        parts.append(txt(450, 388, f"Blocked benchmarks omitted: {', '.join(blocked_benchmarks)}", "muted", "middle"))
    svg = svg_doc(title, "\n".join(parts))
    if not dry_run:
        atomic_write_text(path, svg)
    return str(path)


def generate_family_scaling_profile(df: pd.DataFrame, path: Path = SVG_OUTPUTS[4], dry_run: bool = False) -> str:
    title = "Family Scaling Profile"
    benchmarks = ordered_benchmarks(df)
    family_colors = family_color_map(df)
    families = list(family_colors)
    measured_benchmarks = [
        benchmark
        for benchmark in benchmarks
        if df[(df["benchmark"] == benchmark) & df["comparable_value"].notna()].shape[0] > 0
    ]
    panel_benchmarks = measured_benchmarks[:3]
    left = 96
    right = 620
    first_top = 76
    panel_gap = 18
    panel_h = 86 if len(panel_benchmarks) >= 3 else 122
    x_positions = {"S": left + 80, "M": left + 250, "L": left + 420}
    parts = [
        rect(28, 40, 844, 380, SURFACE, "panel"),
        txt(450, 24, title, "title", "middle"),
        txt(450, 44, "One small panel per benchmark with comparable scores; open circles mark missing slots.", "subtitle", "middle"),
    ]

    if not panel_benchmarks:
        parts.append(txt(450, 232, "No comparable benchmark scores available in this snapshot.", "value", "middle"))

    for panel_idx, benchmark in enumerate(panel_benchmarks):
        top = first_top + panel_idx * (panel_h + panel_gap)
        bottom = top + panel_h
        parts.append(txt(left - 18, top + 14, benchmark, "value", "end"))
        for tick in [0, 0.5, 1.0]:
            y = bottom - tick * (bottom - top)
            parts.append(line(left, y, right, y, "grid"))
            parts.append(txt(left - 10, y + 4, f"{tick:.1f}", "tiny", "end"))
        parts.append(line(left, top, left, bottom, "axis-line"))
        parts.append(line(left, bottom, right, bottom, "axis-line"))
        for size, x in x_positions.items():
            parts.append(txt(x, bottom + 12, size, "tiny", "middle"))

        for family in families:
            fam_df = df[(df["family"] == family) & (df["benchmark"] == benchmark)]
            point_coords: list[tuple[float, float]] = []
            color = family_colors[family]
            for size in SIZE_SLOTS:
                row = fam_df[fam_df["size_slot"] == size]
                x = x_positions[size]
                if row.empty or pd.isna(row.iloc[0]["comparable_value"]):
                    parts.append(circle(x, bottom - 2, 4, "#ffffff", color))
                    continue
                value = float(row.iloc[0]["comparable_value"])
                y = bottom - value * (bottom - top)
                point_coords.append((x, y))
            if len(point_coords) >= 2:
                path_d = " ".join(
                    ("M" if idx == 0 else "L") + f"{x:.1f},{y:.1f}"
                    for idx, (x, y) in enumerate(point_coords)
                )
                parts.append(
                    f'<path d="{path_d}" fill="none" stroke="{color}" stroke-width="2.2" '
                    'stroke-linecap="round" stroke-linejoin="round"/>'
                )
            for size in SIZE_SLOTS:
                row = fam_df[fam_df["size_slot"] == size]
                x = x_positions[size]
                if row.empty or pd.isna(row.iloc[0]["comparable_value"]):
                    parts.append(circle(x, bottom - 2, 4, "#ffffff", color))
                    continue
                value = float(row.iloc[0]["comparable_value"])
                y = bottom - value * (bottom - top)
                parts.append(circle(x, y, 4, color, "#ffffff"))

    if panel_benchmarks:
        last_bottom = first_top + (len(panel_benchmarks) - 1) * (panel_h + panel_gap) + panel_h
        parts.append(txt((left + right) / 2, min(last_bottom + 36, 414), "Size slot", "axis", "middle"))
        parts.append(txt(46, 220, "Accuracy", "axis", "middle", 'transform="rotate(-90 46 220)"'))

    legend_y = 88
    for idx, family in enumerate(families):
        y = legend_y + idx * 24
        parts.append(rect(635, y - 13, 15, 15, family_colors[family]))
        parts.append(txt(660, y, family, "small"))
    parts.append(rect(620, 232, 222, 48, "#F9FAFB", "panel"))
    parts.append(txt(636, 256, f"Panels: {len(panel_benchmarks)}", "value"))
    blocked_count = max(len(benchmarks) - len(measured_benchmarks), 0)
    parts.append(txt(636, 274, f"Blocked benchmarks: {blocked_count}", "small"))
    svg = svg_doc(title, "\n".join(parts))
    if not dry_run:
        atomic_write_text(path, svg)
    return str(path)


def generate_coverage_matrix(df: pd.DataFrame, path: Path = SVG_OUTPUTS[5], dry_run: bool = False) -> str:
    title = "Coverage Matrix"
    lines = ordered_lines(df)
    benchmarks = ordered_benchmarks(df)
    lookup = {(row.line, row.benchmark): row.status for row in df.itertuples(index=False)}
    family_colors = family_color_map(df)
    line_family = df.drop_duplicates("line").set_index("line")["family"].to_dict()
    line_size = df.drop_duplicates("line").set_index("line")["size_slot"].to_dict()
    left = 134
    top = 108
    cell_w = min(44, 690 / max(len(lines), 1))
    cell_h = 42
    parts = [
        rect(28, 40, 844, 380, SURFACE, "panel"),
        txt(450, 24, title, "title", "middle"),
        txt(450, 44, "Status by benchmark and model line; columns are grouped by family and S/M/L slot.", "subtitle", "middle"),
    ]

    col_lookup = {model_line: col for col, model_line in enumerate(lines)}
    for family, color in family_colors.items():
        family_lines = [model_line for model_line in lines if line_family.get(model_line) == family]
        if not family_lines:
            continue
        start_col = col_lookup[family_lines[0]]
        group_x = left + start_col * cell_w
        group_w = len(family_lines) * cell_w - 3
        parts.append(rect(group_x, 64, group_w, 9, color))
        parts.append(txt(group_x + group_w / 2, 58, family, "small", "middle"))

    for col, model_line in enumerate(lines):
        x = left + col * cell_w + cell_w / 2
        parts.append(txt(x, 92, line_size.get(model_line, ""), "axis", "middle"))

    for row_idx, benchmark in enumerate(benchmarks):
        y = top + row_idx * cell_h
        parts.append(rect(42, y - 3, 780, cell_h, row_fill(row_idx)))
        parts.append(txt(left - 8, y + 25, benchmark, "axis", "end"))
        for col, model_line in enumerate(lines):
            status = lookup.get((model_line, benchmark), "TBD")
            color = STATUS_COLORS.get(status, "#999999")
            x = left + col * cell_w
            parts.append(rect(x, y, cell_w - 3, cell_h - 6, color, "outline"))
            parts.append(txt(x + cell_w / 2 - 1, y + 23, STATUS_ABBREVIATIONS.get(status, "?"), "cell-label", "middle"))
    key_statuses = ["Done", "Partial", "Blocked", "Error", "Queue", "TBD", "Proxy"]
    parts.append(render_status_legend(95, 437, key_statuses))
    parts.append(render_family_legend(family_colors, 490, 465, step=80))
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
