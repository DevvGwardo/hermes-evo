#!/usr/bin/env bash
# spawn-worker.sh — spawn a tmux-backed Hermes worker agent
# Usage: spawn-worker.sh <profile> <session_id> <task> <output_path>
# Example: spawn-worker.sh coder 20260225_143052 "Write X" "/path/to/output.py"

set -e

PROFILE="${1:?Usage: $0 <profile> <session_id> <task> <output_path>}"
SESSION_ID="${2:?}"
TASK="${3:?}"
OUTPUT_PATH="${4:-}"

if ! tmux has-session -t "pool-$PROFILE-$SESSION_ID" 2>/dev/null; then
    tmux new-session -d -s "pool-$PROFILE-$SESSION_ID" "hermes --profile $PROFILE"
    sleep 8
fi

FULL_TASK="$TASK"
if [[ -n "$OUTPUT_PATH" ]]; then
    FULL_TASK="$TASK. Write output to: $OUTPUT_PATH"
fi

tmux send-keys -t "pool-$PROFILE-$SESSION_ID" "$FULL_TASK" Enter

echo "Worker spawned: pool-$PROFILE-$SESSION_ID"
echo "Output path: $OUTPUT_PATH"
