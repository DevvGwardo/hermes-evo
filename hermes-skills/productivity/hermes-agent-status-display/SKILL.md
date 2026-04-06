---
name: hermes-agent-status-display
description: Create an automatic agent status display for Hermes brain/MCP system with self-healing adaptations
version: 2.0.0
author: Hermes
---

# Hermes Agent Status Display Skill

## Description
Create an automatic agent status display that shows session status with visual indicators in the Hermes brain/MCP system. Uses the official Hermes CLI status command when available, with fallback approaches for different execution contexts. Includes self-healing adaptations and guidance for monitoring agent activity.

## When to Use
- When you want to monitor agent activity in the Hermes brain system
- When you need to check the status of the Hermes agent system
- When you want clear guidance for spawning worker agents
- When you want automatic periodic status updates
- When you need a pragmatic, working solution that adapts to environmental constraints
- When trial and error shows different approaches are needed in different contexts

## Limitations
- Direct MCP brain tool access may not be available in all execution contexts
- The hermes CLI command may not be available in minimal environments
- Some status information requires specific tool availability

## Prerequisites
- Hermes agent system installed
- Bash shell access
- hermes CLI available (for primary method)

## Steps

### 1. Primary Method: Use Hermes CLI Status Command
The most reliable way to get agent status is to use the official hermes CLI:

```bash
hermes status
```

This provides comprehensive information including:
- Environment details (project path, Python version, model provider)
- API key status
- Auth provider status
- Terminal backend info
- Messaging platform configuration
- Gateway service status
- Scheduled jobs count
- Active sessions count

### 2. Fallback: Direct Script Execution
If the hermes CLI is not available or not working, you can run the status script directly:

```bash
~/.hermes/show_agents.py
```

Note: This script may show "Error getting agent status: No module named 'hermes_tools'" in some environments but still provides basic session information.

### 3. Alternative: Use Hermes CLI Status Module
In environments where direct script execution fails or the hermes CLI isn't available, you can import and run the status module directly:

```bash
python -c "from hermes_cli.status import show_status; show_status(type('Args', (), {'all': False, 'deep': False}))"

This approach works in sandboxed environments and provides the same comprehensive status information as the hermes CLI command.
```

### 4. Alternative: Check Running Processes
To see what agent-related processes are currently active:

```bash
ps aux | grep -E '(hermes|agent)' | grep -v grep
```

### 4. Check for Brain System Components
To verify the brain/MCP system components:

```bash
ls -la ~/.hermes/ | grep -E '(brain|gateway|auth|config)'
```

### 5. Set Up Automatic Status Updates
Create a cron job for periodic status checks:

```bash
cronjob create --name agent-status-display \
  --schedule "*/30 * * * *" \
  --prompt "Run the hermes status command and output the result" \
  --deliver origin
```

## Self-Healing Features
- Automatically detects the best available method for getting status information
- Provides clear fallback options when primary methods fail
- Works in both interactive and automated contexts
- Gives actionable guidance for users to interpret the results
- Includes troubleshooting hints for common issues

## Troubleshooting
- If you see "Error getting agent status: No module named 'hermes_tools'": This indicates the hermes_tools module isn't available in the current Python environment, but the script still provides basic session information
- If hermes command not found: Ensure Hermes agent is properly installed and the CLI is in your PATH
- For detailed diagnostics: Run 'hermes doctor'
- To reconfigure: Run 'hermes setup'

## Customization
- Modify the cron job schedule for different update frequencies
- Adapt the delivery target based on your needs (origin, local, telegram, discord, etc.)
- Combine with other monitoring skills for comprehensive system oversight