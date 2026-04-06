---
name: dream-consolidation-engine
description: Standalone Dream subagent for Hermes — 4-phase session consolidation via MiniMax-M2.7
---

# Dream Consolidation Engine

Standalone Dream subagent for Hermes — runs as a cron job, consolidates session logs into durable long-term memory.

## Trigger conditions (all must pass)
- 24h since last successful dream (`lastDreamDate` in `dream-state.json`)
- 5+ sessions counted (`sessionCount` in `dream-state.json`)
- No lock file exists (`~/.hermes/cron/dream.lock`)

## State file
`~/.hermes/memories/dream-state.json`:
```json
{ "lastDreamMs": 0, "lastDreamDate": "", "sessionCount": 0, "totalDreams": 0 }
```

## 4 phases

**1. Orient** — assess existing memory structure
**2. Gather Signal** — extract facts from recent sessions
**3. Consolidate** — write/update memory files
**4. Prune** — trim stale entries, enforce size limits

Each phase: `_run_phase(name, system, user)` → string
- `system`: phase instructions + directory description
- `user`: "What was learned or decided?" for that phase

## LLM calls
- Model: `MiniMax-M2.7` (NOT MiniMax-M2.7-highspeed — account doesn't support it)
- Endpoint: direct to MiniMax CN API (`https://api.minimax.io/v1/chat/properties_v2`)
- Auth: Bearer token from `~/.hermes/.env` (key `MINIMAX_API_KEY`)
- Max tokens: 3072 for prune, 2560 for consolidate, 2048 otherwise

## FILE: directive
LLM outputs `FILE:path` lines to write. Parsed in consolidate/prune, stripped before counting token usage.

## Integration

**Session counting** (every Hermes message):
```python
subprocess.Popen([str(HERMES_ROOT / "cron/dream.sh"), "--bump-session"],
                 env={...}, cwd=str(HERMES_ROOT))
```
Fires in `flush_memories()` in `gateway/run.py` after every completed turn. Never blocks.

**Cron registration**:
```
every 4h → ~/.hermes/cron/dream.sh
```

## Common issues
- MiniMax 500: transient, retry with backoff handles it
- Prune truncates FILE: directives: bump max_tokens to 3072
- Lock file left behind after crash: manually remove `~/.hermes/cron/dream.lock`