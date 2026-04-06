---
name: hermes-agent-status-check
category: devops
description: Check Hermes Agent component status using multiple fallback methods
---

# Hermes Agent Status Check

## Trigger Conditions
When you need to check the status of Hermes Agent components including environment, API keys, auth providers, messaging platforms, gateway service, scheduled jobs, and active sessions.

## Approach
This skill provides a reusable method to check Hermes agent status by trying multiple approaches in order of effectiveness:

1. **Primary method**: Use `hermes status` command (most comprehensive)
2. **Fallback method**: Run `show_agents.py` script directly
3. **Alternative**: Use MCP brain tools via execute_code (if available)

## Steps

### Method 1: Use hermes status command (Recommended)
```bash
hermes status
```
This provides the most complete status information including:
- Environment details (project path, Python version, .env file)
- API keys status (redacted by default)
- Auth providers (Nous Portal, OpenAI Codex)
- API-key providers configuration
- Terminal backend info
- Messaging platforms status
- Gateway service status
- Scheduled jobs count
- Active sessions count

### Method 2: Direct script execution (Fallback)
If the hermes CLI is not available or not working:
```bash
python3 show_agents.py
```
This shows active brain agents with status indicators using direct MCP brain tool calls.

### Method 3: Programmatic check via hermes_cli.status (Alternative)
For programmatic access to the full status display:
```python
# In execute_code context or Python script
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.resolve()  # Adjust as needed
sys.path.insert(0, str(project_root))

from hermes_cli.status import show_status

class Args:
    def __init__(self):
        self.all = False   # Set to True to show unredacted API keys
        self.deep = False  # Set to True for connectivity checks

args = Args()
show_status(args)
```

### Method 4: Programmatic MCP brain tools check (Alternative)
For programmatic access or when other methods fail:
```python
# In execute_code context
try:
    result = mcp_brain_brain_sessions()
    # Process and format the result\nexcept Exception as e:
    # Handle error and try alternative approaches
    pass
```

## Key Findings from Experience
- The `hermes status` command is the most reliable and comprehensive method
- Direct MCP tool access via `execute_code` can be unreliable due to tool availability
- The `show_agents.py` script provides basic agent status but lacks the full system overview
- Always check for the existence of required files/scripts before attempting to run them
- Error handling is crucial - have fallback methods ready when primary approaches fail

## Verification
After running the status check, verify that:
- Output shows proper formatting with section headers
- No critical error messages appear in the output
- At minimum, environment and API keys sections are populated
- Gateway service status shows as loaded/running if expected

## Notes
- The `hermes status` command respects the `--all` flag to show unredacted API keys
- Use `hermes doctor` for more detailed diagnostics if needed
- Regular status checks can help identify configuration issues early
- The status output format may vary slightly between Hermes agent versions