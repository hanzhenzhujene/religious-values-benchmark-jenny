#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/../../../.."

FAILURES=0
run_rebound() {
    local label="$1"
    shift
    echo "=== Rebound started: $label :: $(date) ==="
    "$@"
    local rc=$?
    echo "=== Rebound finished: $label rc=$rc :: $(date) ==="
    if [[ "$rc" -ne 0 ]]; then
        FAILURES=$((FAILURES + 1))
    fi
}

run_rebound 'deepseek/deepseek-r1 bibleqa_sentence_selection missing-after-runtime-error (762 samples)' ./scripts/run_jenny_religion.sh --run-id jenny-religion-20260510-rebound-deepseek_deepseek-r1-missing_after_runtime_error --models 6 --tasks bibleqa_sentence_selection --sample-ids-file results/inspect/rebounds/jenny-religion-20260510/deepseek_deepseek-r1__bibleqa_sentence_selection__missing_after_runtime_error.ids --max-conn 1 --parallel-models 1
run_rebound 'deepseek/deepseek-r1-distill-llama-70b bibleqa_sentence_selection parse-failure-rerun (886 samples)' ./scripts/run_jenny_religion.sh --run-id jenny-religion-20260510-rebound-deepseek_deepseek-r1-distill-llama-70b-parse_failure_rerun --models 4 --tasks bibleqa_sentence_selection --sample-ids-file results/inspect/rebounds/jenny-religion-20260510/deepseek_deepseek-r1-distill-llama-70b__bibleqa_sentence_selection__parse_failure_rerun.ids --max-conn 2 --parallel-models 1
run_rebound 'qwen/qwen3-32b bibleqa_sentence_selection parse-failure-rerun (591 samples)' ./scripts/run_jenny_religion.sh --run-id jenny-religion-20260510-rebound-qwen_qwen3-32b-parse_failure_rerun --models 2 --tasks bibleqa_sentence_selection --sample-ids-file results/inspect/rebounds/jenny-religion-20260510/qwen_qwen3-32b__bibleqa_sentence_selection__parse_failure_rerun.ids --max-conn 2 --parallel-models 1
run_rebound 'qwen/qwen3-8b bibleqa_sentence_selection missing-after-runtime-error (561 samples)' ./scripts/run_jenny_religion.sh --run-id jenny-religion-20260510-rebound-qwen_qwen3-8b-missing_after_runtime_error --models 1 --tasks bibleqa_sentence_selection --sample-ids-file results/inspect/rebounds/jenny-religion-20260510/qwen_qwen3-8b__bibleqa_sentence_selection__missing_after_runtime_error.ids --max-conn 1 --parallel-models 1

echo "=== Rebound batch complete; failures=$FAILURES :: $(date) ==="
exit "$FAILURES"
