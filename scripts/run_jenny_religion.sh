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

MAX_CONN=3
PARALLEL_MODELS=3
LIMIT_ARGS=()
START_ARGS=()
SAMPLE_IDS_ARGS=()
MODEL_FILTER=""
TASK_FILTER=""
RUN_ID="jenny-religion-$(date +%Y%m%d)"
DRY_RUN=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --limit)
            LIMIT_ARGS=("--limit" "$2")
            shift 2
            ;;
        --start)
            START_ARGS=("--start" "$2")
            shift 2
            ;;
        --sample-ids-file)
            SAMPLE_IDS_FILE="$2"
            if [[ "$SAMPLE_IDS_FILE" != /* ]]; then
                SAMPLE_IDS_FILE="$ROOT/$SAMPLE_IDS_FILE"
            fi
            SAMPLE_IDS_ARGS=("--sample_ids_file" "$SAMPLE_IDS_FILE")
            shift 2
            ;;
        --max-conn)
            MAX_CONN="$2"
            shift 2
            ;;
        --parallel-models)
            PARALLEL_MODELS="$2"
            shift 2
            ;;
        --models)
            MODEL_FILTER="$2"
            shift 2
            ;;
        --tasks)
            TASK_FILTER="$2"
            shift 2
            ;;
        --run-id)
            RUN_ID="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=1
            shift
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

TASK_LIST="${TASK_FILTER:-$("${PY_RUN[@]}" "$ROOT/scripts/check_dataset_access.py" --task-list)}"
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

write_run_metadata() {
    {
        echo "run_id=$RUN_ID"
        echo "tasks=$TASK_LIST"
        echo "models=${MODELS[*]}"
        echo "max_connections=$MAX_CONN"
        echo "parallel_models=$PARALLEL_MODELS"
        echo "limit_args=${LIMIT_ARGS[*]:-}"
        echo "start_args=${START_ARGS[*]:-}"
        echo "sample_ids_args=${SAMPLE_IDS_ARGS[*]:-}"
        echo "started=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        echo "git_commit=$(git rev-parse --short HEAD 2>/dev/null || true)"
    } > "$RUN_DIR/run-metadata.txt"
}

echo "=== Jenny religion benchmark run ==="
echo "Run id: $RUN_ID"
echo "Tasks: $TASK_LIST"
echo "Models: ${#MODELS[@]}"
echo "Max connections: $MAX_CONN"
echo "Parallel model streams: $PARALLEL_MODELS"
echo "Started: $(date)"
printf 'Selected models:\n'
printf '  %s\n' "${MODELS[@]}"
if [[ "$DRY_RUN" == "1" ]]; then
    echo "Dry run only; no model calls made."
    exit 0
fi

require_provider_credentials() {
    local needs_openrouter=0
    local needs_minimax=0
    local model

    for model in "${MODELS[@]}"; do
        case "$model" in
            minimax/*) needs_minimax=1 ;;
            *) needs_openrouter=1 ;;
        esac
    done

    if [[ "$needs_openrouter" == "1" ]]; then
        if [[ -z "${OPENROUTER_API_KEY:-}" && "${OPENAI_API_KEY:-}" != sk-or-* ]]; then
            echo "Missing OpenRouter credentials." >&2
            echo "Set OPENROUTER_API_KEY in .env/.env.local, or set OPENAI_API_KEY to an OpenRouter token that starts with sk-or-." >&2
            return 1
        fi
    fi

    if [[ "$needs_minimax" == "1" && -z "${MINIMAX_API_KEY:-}" ]]; then
        echo "Missing MiniMax credentials." >&2
        echo "Set MINIMAX_API_KEY in .env/.env.local before running MiniMax models." >&2
        return 1
    fi
}

require_provider_credentials || exit 1
write_run_metadata

min_int() {
    if [[ "$1" -lt "$2" ]]; then
        echo "$1"
    else
        echo "$2"
    fi
}

model_slug() {
    echo "$1" | tr '/:' '__'
}

setup_model_runtime_controls() {
    local model="$1"

    MODEL_MAX_CONN="$MAX_CONN"
    EXTRA_BODY_ARGS=()

    unset CEI_PROMPT_PREFIX
    case "$model" in
        minimax/*)
            export CEI_MIN_MAX_TOKENS="${CEI_MINIMAX_MAX_TOKENS:-${CEI_MIN_MAX_TOKENS:-2048}}"
            MODEL_MAX_CONN="$(min_int "$MAX_CONN" "${CEI_MINIMAX_MAX_CONN:-2}")"
            ;;
        *)
            unset CEI_MIN_MAX_TOKENS
            ;;
    esac

    if [[ "${CEI_STRICT_REASONING_OUTPUT:-1}" == "1" ]]; then
        case "$model" in
            qwen/qwen3-*|deepseek/deepseek-r1|deepseek/deepseek-r1-distill-llama-70b)
                export CEI_PROMPT_PREFIX="${CEI_PROMPT_PREFIX_OVERRIDE:-/no_think}"
                ;;
        esac
    fi

    case "$model" in
        qwen/qwen3-*|deepseek/deepseek-r1|deepseek/deepseek-r1-distill-llama-70b)
            MODEL_MAX_CONN="$(min_int "$MODEL_MAX_CONN" 1)"
            ;;
    esac

    if [[ "${CEI_OPENROUTER_REASONING_MINIMAL:-1}" == "1" ]]; then
        case "$model" in
            deepseek/deepseek-r1|deepseek/deepseek-r1-distill-llama-70b)
                EXTRA_BODY_ARGS=("--extra_body_json" '{"reasoning":{"effort":"minimal","exclude":true}}')
                ;;
        esac
    fi
}

run_model() {
    local model="$1"
    local slug
    slug="$(model_slug "$model")"
    local log="$RUN_DIR/${slug}.log"

    setup_model_provider "$model"
    setup_model_runtime_controls "$model"
    export CEI_TEMPERATURE="${CEI_TEMPERATURE:-0}"

    echo "=== $model started: $(date) ===" | tee "$log"
    echo "provider_model=$EFFECTIVE_MODEL base_url=$OPENAI_BASE_URL max_connections=$MODEL_MAX_CONN prompt_prefix=${CEI_PROMPT_PREFIX:-}" | tee -a "$log"
    (
        cd "$ROOT/src/inspect"
        "${INSPECT_RUN[@]}" run.py \
            --tasks "evals/religion.py::$TASK_LIST" \
            --model "openai/$EFFECTIVE_MODEL" \
            --model_base_url "$OPENAI_BASE_URL" \
            --temperature 0 \
            --no_sandbox \
            --max_connections "$MODEL_MAX_CONN" \
            --log_dir "$LOG_DIR/$slug" \
            ${LIMIT_ARGS[@]+"${LIMIT_ARGS[@]}"} \
            ${START_ARGS[@]+"${START_ARGS[@]}"} \
            ${SAMPLE_IDS_ARGS[@]+"${SAMPLE_IDS_ARGS[@]}"} \
            ${EXTRA_BODY_ARGS[@]+"${EXTRA_BODY_ARGS[@]}"} \
            2>&1 | tee -a "$log"
    )
    local rc=${PIPESTATUS[0]}
    echo "=== $model finished rc=$rc: $(date) ===" | tee -a "$log"
    return "$rc"
}

PIDS=()
LABELS=()
FAILURES=0

wait_current_batch() {
    local index
    local pid
    local label
    for index in "${!PIDS[@]}"; do
        pid="${PIDS[$index]}"
        label="${LABELS[$index]}"
        if ! wait "$pid"; then
            echo "Model stream failed: $label (PID $pid)" >&2
            FAILURES=$((FAILURES + 1))
        fi
    done
    PIDS=()
    LABELS=()
}

for model in "${MODELS[@]}"; do
    run_model "$model" &
    pid=$!
    PIDS+=("$pid")
    LABELS+=("$model")
    echo "Launched $model (PID $pid)"
    if [[ "${#PIDS[@]}" -ge "$PARALLEL_MODELS" ]]; then
        wait_current_batch
    fi
done

wait_current_batch

echo "=== Jenny religion benchmark run complete: $(date) ==="
echo "Failures: $FAILURES"
exit "$FAILURES"
