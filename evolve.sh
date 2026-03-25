#!/bin/bash
# OpenClaw Evo — Cron driver
# Runs one evolution cycle, saves checkpoint, exits cleanly.
# Safe to run overlapping with a daemon (daemon uses --once, this uses --cron).
#
# Usage:
#   ./evolve.sh              # normal cycle
#   TEST_FAILURES=1 ./evolve.sh   # inject synthetic Bash/Grep failures first
export AUTO_APPROVE_CONFIDENCE=${AUTO_APPROVE_CONFIDENCE:-95}
cd "$(dirname "$0")"

ARGS="--cron"
if [[ "$TEST_FAILURES" == "1" ]]; then
  ARGS="$ARGS --test-failures"
fi

npx tsx src/cli.ts $ARGS
