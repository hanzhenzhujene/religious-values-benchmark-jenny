#!/usr/bin/env bash
# Provider routing for Jenny's religion benchmark sweep.
#
# Per Jenny's run policy, OpenRouter is the default route for Qwen,
# DeepSeek, Llama, and Gemma. MiniMax models use the direct MiniMax API.

resolve_provider() {
    case "$1" in
        "minimax/minimax-01") echo "minimax|MiniMax-Text-01" ;;
        "minimax/minimax-m1") echo "minimax|MiniMax-M1" ;;
        "minimax/minimax-m2.5") echo "minimax|MiniMax-M2.5" ;;
        *) return 1 ;;
    esac
}

provider_url() {
    case "$1" in
        minimax) echo "https://api.minimax.io/v1" ;;
        openrouter) echo "https://openrouter.ai/api/v1" ;;
        *) echo "https://openrouter.ai/api/v1" ;;
    esac
}

provider_key_var() {
    case "$1" in
        minimax) echo "MINIMAX_API_KEY" ;;
        openrouter) echo "OPENROUTER_API_KEY" ;;
        *) echo "OPENROUTER_API_KEY" ;;
    esac
}

setup_model_provider() {
    local model="$1"
    local entry

    if entry=$(resolve_provider "$model"); then
        local provider="${entry%%|*}"
        local provider_model="${entry#*|}"
        local key_var
        key_var=$(provider_key_var "$provider")

        EFFECTIVE_MODEL="$provider_model"
        export OPENAI_BASE_URL
        OPENAI_BASE_URL=$(provider_url "$provider")
        eval "export OPENAI_API_KEY=\"\${$key_var-}\""

        echo "  [provider] $model -> $provider ($provider_model)" >&2
    else
        EFFECTIVE_MODEL="$model"
        export OPENAI_API_KEY="${OPENROUTER_API_KEY:-}"
        export OPENAI_BASE_URL="https://openrouter.ai/api/v1"

        echo "  [provider] $model -> openrouter" >&2
    fi
}
