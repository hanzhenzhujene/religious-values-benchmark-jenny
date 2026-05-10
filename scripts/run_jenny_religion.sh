#!/usr/bin/env bash
# Run Jenny's religion benchmarks across the selected model matrix.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.env" ]]; then
    set -a
    source "$ROOT/.env"
    set +a
fi
if [[ -f "$ROOT/.env.local" ]]; then
    set -a
    source "$ROOT/.env.local"
    set +a
fi
source "$ROOT/provider_config.sh"

ALL_MODELS=(
    "qwen/qwen3-8b"
    "qwen/qwen3-32b"
    "qwen/qwen3-235b-a22b"
    "deepseek/deepseek-r1-distill-llama-70b"
    "deepseek/deepseek-chat-v3.1"
    "deepseek/deepseek-r1"
    "meta-llama/llama-3.2-3b-instruct"
    "meta-llama/llama-3.1-8b-instruct"
    "meta-llama/llama-3.3-70b-instruct"
    "google/gemma-3-4b-it"
    "google/gemma-3-12b-it"
    "google/gemma-3-27b-it"
    "minimax/minimax-01"
    "minimax/minimax-m1"
    "minimax/minimax-m2.5"
)

MAX_CONN=8
LIMIT_ARGS=()
MODEL_FILTER=""
RUN_ID="jenny-religion-$(date +%Y%m%d)"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --limit)
            LIMIT_ARGS=("--limit" "$2")
            shift 2
            ;;
        --max-conn)
            MAX_CONN="$2"
            shift 2
            ;;
        --models)
            MODEL_FILTER="$2"
            shift 2
            ;;
        --run-id)
            RUN_ID="$2"
            shift 2
            ;;
        *)
            echo "Unknown arg: $1" >&2
            exit 1
            ;;
    esac
done

if command -v uv >/dev/null 2>&1; then
    UV_BIN="$(command -v uv)"
    PY_RUN=("$UV_BIN" run python)
    INSPECT_RUN=("$UV_BIN" run --package cei-inspect python)
elif [[ -x "$HOME/Library/Python/3.9/bin/uv" ]]; then
    UV_BIN="$HOME/Library/Python/3.9/bin/uv"
    PY_RUN=("$UV_BIN" run python)
    INSPECT_RUN=("$UV_BIN" run --package cei-inspect python)
elif [[ -x "$ROOT/.venv/bin/python" ]]; then
    PY_RUN=("$ROOT/.venv/bin/python")
    INSPECT_RUN=("$ROOT/.venv/bin/python")
else
    echo "Could not resolve uv or .venv/bin/python. Run make setup first." >&2
    exit 1
fi

TASK_LIST="$("${PY_RUN[@]}" "$ROOT/scripts/check_dataset_access.py" --task-list)"
if [[ -z "$TASK_LIST" ]]; then
    echo "No official Jenny religion tasks are currently accessible." >&2
    exit 1
fi

MODELS=()
if [[ -n "$MODEL_FILTER" ]]; then
    IFS=',' read -ra INDICES <<< "$MODEL_FILTER"
    for i in "${INDICES[@]}"; do
        idx=$((i - 1))
        if [[ $idx -ge 0 && $idx -lt ${#ALL_MODELS[@]} ]]; then
            MODELS+=("${ALL_MODELS[$idx]}")
        else
            echo "Warning: model index $i out of range (1-${#ALL_MODELS[@]})" >&2
        fi
    done
else
    MODELS=("${ALL_MODELS[@]}")
fi

RUN_DIR="$ROOT/results/inspect/full-runs/$RUN_ID"
LOG_DIR="$ROOT/results/inspect/logs/$RUN_ID"
mkdir -p "$RUN_DIR" "$LOG_DIR"

echo "=== Jenny religion benchmark run ==="
echo "Run id: $RUN_ID"
echo "Tasks: $TASK_LIST"
echo "Models: ${#MODELS[@]}"
echo "Max connections: $MAX_CONN"
echo "Started: $(date)"

run_model() {
    local model="$1"
    local slug
    slug="$(echo "$model" | tr '/:' '__')"
    local log="$RUN_DIR/${slug}.log"

    setup_model_provider "$model"
    export CEI_TEMPERATURE="${CEI_TEMPERATURE:-0}"
    export CEI_MIN_MAX_TOKENS="${CEI_MIN_MAX_TOKENS:-2048}"

    echo "=== $model started: $(date) ===" | tee "$log"
    (
        cd "$ROOT/src/inspect"
        "${INSPECT_RUN[@]}" run.py \
            --tasks "evals/religion.py::$TASK_LIST" \
            --model "openai/$EFFECTIVE_MODEL" \
            --model_base_url "$OPENAI_BASE_URL" \
            --temperature 0 \
            --no_sandbox \
            --max_connections "$MAX_CONN" \
            --log_dir "$LOG_DIR/$slug" \
            ${LIMIT_ARGS[@]+"${LIMIT_ARGS[@]}"} \
            2>&1 | tee -a "$log"
    )
    local rc=${PIPESTATUS[0]}
    echo "=== $model finished rc=$rc: $(date) ===" | tee -a "$log"
    return "$rc"
}

PIDS=()
for model in "${MODELS[@]}"; do
    run_model "$model" &
    pid=$!
    PIDS+=("$pid")
    echo "Launched $model (PID $pid)"
done

FAILURES=0
for pid in "${PIDS[@]}"; do
    if ! wait "$pid"; then
        FAILURES=$((FAILURES + 1))
    fi
done

echo "=== Jenny religion benchmark run complete: $(date) ==="
echo "Failures: $FAILURES"
exit "$FAILURES"
