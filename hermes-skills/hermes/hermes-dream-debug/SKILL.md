---
name: hermes-dream-debug
category: hermes
description: Debug session for dream_service.py — prune truncation fix, dry-run verification, and terminal redaction gotchas.
---

# hermes-dream-debug

## Context
`dream_service.py` at `~/.hermes/cron/dream_service.py` (standalone: `~/hermes-dream/dream_service.py`)

## Prune phase truncation fix

**Problem:** prune phase hit `max_tokens` (default 2048) on first run — output truncated before all `FILE:` directives parsed.

**Fix:** in `_run_phase()` call, set `max_tokens=3072` for prune phase:
```python
elif phase == 'prune':
    response = _llm_complete(prompt, phase=phase, api_key=api_key,
                             base_url=base_url, model=model,
                             max_tokens=3072)  # ← was 2048
```

Orient, gather, and consolidate phases are unaffected.

**Verification:**
```bash
python3 ~/.hermes/cron/dream_service.py --dry-run
```
Prune should output ~3200+ bytes with no truncation warning.

## Dry-run gating

`--dry-run` runs all phases without writing files. Gates require `--force` or sufficient time elapsed. Use `--force` to bypass.

## Terminal redaction gotcha

Terminal output can display `***` redaction for variable names (e.g. `max_tokens=***`) — display artifacts, not actual file content. The actual file is correct and `py_compile` passes. Verify with raw byte reads if in doubt.

## Repo
github.com/DevvGwardo/hermes-dream
