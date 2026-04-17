#!/bin/bash
# This script is used to run temporal reasoning experiments in parallel

# ---------------------------
# Global config
# ---------------------------
BATCH_SIZE=16
BENCHMARK_FILE="data/tr_benchmarks/politicaltr/test_complete.csv"
BENCHMARK_NAME="politr"
EXPERIMENTS=(
    "0s_question"
    "1s_question"
    "3s_question"
)

# Log folder
LOG_DIR="logs"
mkdir -p "$LOG_DIR"

# Models to run
MODELS=(
    "openai-community/gpt2-large"
    "google/gemma-3-1b-pt"
    "meta-llama/Llama-3.2-1B"
    "Qwen/Qwen3-1.7B"
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"
)

# ---------------------------
# Launch loop
# ---------------------------

# ---------------------------
# Parallel execution: 2 at a time
# ---------------------------

MAX_JOBS=2

running_jobs=0

for MODEL in "${MODELS[@]}"; do
    SAFE_NAME=$(echo "$MODEL" | tr '/:' '__')
    LOG_FILE="${LOG_DIR}/${BENCHMARK_NAME}_${SAFE_NAME}.log"

    echo "Launching: $MODEL"
    echo "  Log: $LOG_FILE"

    nohup python tr_experiment.py \
        --benchmark_file "$BENCHMARK_FILE" \
        --benchmark_name "$BENCHMARK_NAME" \
        --pretrained_model_name "$MODEL" \
        --experiments "${EXPERIMENTS[@]}" \
        --batch_size "$BATCH_SIZE" \
        > "$LOG_FILE" 2>&1 &

    running_jobs=$((running_jobs + 1))

    # If 2 process are already running: wait one to finish
    if [ "$running_jobs" -ge "$MAX_JOBS" ]; then
        echo "→ Maximum of $MAX_JOBS jobs reached, waiting..."
        wait -n   # espera a que termine *uno*
        running_jobs=$((running_jobs - 1))
    fi

    echo
done

# Wait to any other process
wait

echo "✔ All experiments finished."
