---
name: agent-pool-coordinator
description: Spawn and coordinate specialized agent profiles that work in parallel and report back. Coordinator pattern for multi-agent task delegation.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [Agent, Multi-Agent, Coordinator, Profile, Pool, Orchestration]
    related_skills: [hermes-agent-spawning, subagent-driven-development]
---

# Agent Pool Coordinator

Spawn specialized worker agents from profiles, delegate tasks, collect results, and synthesize final output.

## Architecture

```
Coordinator (you)
  │
  ├─ spawns worker-1 ──► profile: coder
  ├─ spawns worker-2 ──► profile: researcher
  └─ spawns worker-3 ──► profile: writer
         │
         │ all write to
         ▼
  ~/.hermes/agent-pool/results/<session_id>/
         │
         │ coordinator reads + synthesizes
         ▼
      Final Answer
```

## Workflow

### 1. Create output directory for this delegation session

```bash
SESSION_ID=$(date +%Y%m%d_%H%M%S)
POOL_DIR="$HOME/.hermes/agent-pool/results/$SESSION_ID"
mkdir -p "$POOL_DIR"
```

### 2. Spawn workers

Each worker gets:
- A profile (defining its role/personality)
- A task (what to do)
- An output file path (where to write results)

#### Pattern A: tmux PTY (interactive, recommended for steering)

```bash
PROFILE="coder"
TASK="Write a FastAPI users CRUD endpoint. Write the complete file to $POOL_DIR/api.py"
tmux new-session -d -s "worker-$PROFILE-$$" "hermes --profile $PROFILE"
sleep 8
tmux send-keys -t "worker-$PROFILE-$$" "$TASK" Enter
```

#### Pattern B: one-shot -q (fire and forget)

```bash
hermes --profile researcher chat -q "Research KV cache compression techniques. Write a summary to $POOL_DIR/kv-cache-research.md" 2>&1
```

### 3. Monitor workers

```bash
# List all worker sessions
tmux list-sessions -F '#{session_name}'

# Check a worker's latest output
tmux capture-pane -t "worker-coder-$$" -p | tail -30

# Wait for completion (check every 30s)
for i in {1..20}; do
  if tmux has-session -t "worker-$PROFILE-$$" 2>/dev/null; then
    echo "Still running..."
    sleep 30
  else
    echo "Done!"
    break
  fi
done
```

### 4. Collect and aggregate

```bash
# Read all result files
cat "$POOL_DIR"/*.md "$POOL_DIR"/*.py 2>/dev/null

# Use the aggregator script
~/.hermes/skills/agent-pool-coordinator/scripts/aggregate.py "$POOL_DIR"
```

### 5. Cleanup

```bash
# Kill remaining sessions
tmux kill-session -t "worker-coder-$$" 2>/dev/null
tmux kill-session -t "worker-researcher-$$" 2>/dev/null
```

## Available Profile Templates

| Profile | Purpose | Best for |
|---------|---------|----------|
| `coder` | Write, refactor, debug code | Implementing features, writing tests |
| `researcher` | Investigate, compare, analyze | Paper review, market research, tech analysis |
| `writer` | Draft, edit, polish prose | Documentation, reports, blog posts |
| `reviewer` | Critique, find issues, suggest improvements | Code review, design review, security audit |

## spawn-worker script

```bash
# Usage: spawn-worker.sh <profile> <session_id> <task> <output_path>
~/.hermes/skills/agent-pool-coordinator/scripts/spawn-worker.sh coder "$SESSION_ID" "Write X to Y" "/path/to/output.py"
```

## Profile templates

Located in `references/profiles/`. Each is a complete profile directory that can be copied to `~/.hermes/profiles/`.

- `coder/` — focused on implementation, minimal fluff
- `researcher/` — thorough investigation, cites sources
- `writer/` — clear prose, structured output
- `reviewer/` — critical eye, finds edge cases

## Key conventions

1. **One session per worker** — don't reuse tmux sessions across delegation cycles
2. **Write to POOL_DIR** — workers output to shared result directory
3. **Unique SESSION_ID** — date-based groups results cleanly
4. **Check before kill** — verify worker finished before cleanup
5. **Profile must exist** — `hermes --profile <name>` fails if profile isn't in `~/.hermes/profiles/`

## Adding a new profile

```bash
# Copy template
cp -r ~/.hermes/skills/agent-pool-coordinator/references/profiles/coder ~/.hermes/profiles/my-coder

# Edit the profile's SOUL.md to customize
nano ~/.hermes/profiles/my-coder/SOUL.md

# Verify
hermes --profile my-coder --version
```
