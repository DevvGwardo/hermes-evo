---
name: remove-computer-use
description: Remove Anthropic computer_use tool from hermes-agent codebase
category: software-development
---

# Remove Computer Use Integration

Removes Anthropic `computer_use` tool from hermes-agent codebase.

## Files Modified

| File | Change |
|------|--------|
| `model_tools.py` | Remove `"tools.computer_use_tool"` from `_discover_tools()` |
| `cli.py` | Remove `set_computer_approval_callback` import + 2 call sites |
| `run_agent.py` | Replace `_get_native_anthropic_tools()` body with `return None` |
| `agent/display.py` | Remove `"computer": "action"` arg map entry + 2 handling blocks |
| `agent/prompt_builder.py` | Remove `COMPUTER_USE_GUIDANCE` constant (dead code) |
| `hermes_cli/tools_config.py` | Remove tool entry + remove from `_DEFAULT_OFF_TOOLSETS` |
| `toolsets.py` | Remove entire `computer_use` toolset dict |
| `pyproject.toml` | Remove `computer-use = ["pyautogui>=0.9.54,<1"]` from extras |

## Not Removed (passive refs)

- `approval.py` regex patterns — can't fire without the tool registered
- `computer_use_tool.py` source file — stays but is never imported
- Comments in `run_agent.py`, `context_compressor.py`, `anthropic_adapter.py`

## To Revert

```bash
git checkout HEAD~1 -- <files>
```
