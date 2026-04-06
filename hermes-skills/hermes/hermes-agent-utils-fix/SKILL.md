---
name: hermes-agent-utils-fix
description: Fix import error for env_var_enabled in hermes-agent utils.py
category: hermes
---

# hermes-agent Utils Import Error

## Issue
```
ImportError: cannot import name 'env_var_enabled' from 'utils'
```
Location: `/Users/devgwardo/.hermes/hermes-agent/utils.py`

## Context
This error causes Hermes to fail on startup. The `env_var_enabled` function is missing from utils.py.

## Fix
Check what `env_var_enabled` is supposed to do (likely checks if an env var is enabled via truthy/falsy value) and add it to utils.py, OR find where it's defined and ensure proper import.

## Investigation Steps
1. Search for `env_var_enabled` in the codebase to see where it's defined or used
2. Check git history if it was recently removed
3. Look at similar env helper functions in utils.py for pattern
