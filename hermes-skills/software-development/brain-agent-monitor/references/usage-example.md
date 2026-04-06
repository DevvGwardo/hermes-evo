# Brain Agent Monitor - Usage Examples

## Basic Usage

1. Create the monitoring script (save as `show_agents.py`):
   ```python
   #!/usr/bin/env python3
   # ... [script content from SKILL.md] ...
   ```

2. Make it executable:
   ```bash
   chmod +x show_agents.py
   ```

3. Set up automatic updates:
   ```bash
   cronjob create agent-monitor "python3 show_agents.py" "*/5 * * * *" --deliver origin
   ```

## Advanced Usage

### Custom Status Icons

Modify the icons in the script to match your preference:
```python
status_icons = {
    'idle': '◯',      # circle
    'working': '◉',   # dotted circle
    'done': '✓',      # check
    'failed': '✖',    # multiply
    'unknown': '❓'    # question mark
}
```

### Filtering Agents

To show only working agents:
```python
# Add this filter before formatting
working_sessions = [s for s in sessions if s.get('status') == 'working']
sessions = working_sessions
```

### Detailed Progress View

For more verbose output:
```python
if progress:
    line = f"{icon} {name} ({session.get('id', 'no-id')[:8]}...) — {status}: {progress}"
else:
    line = f"{icon} {name} ({session.get('id', 'no-id')[:8]}...) — {status}"
```

## Integration Examples

### With Heartbeat System

Add to your `HEARTBEAT.md`:
```markdown
## Agent Monitoring
- Check: `python3 ~/hermes-agent/show_agents.py`
- Interval: Every manual heartbeat check
- Action: Review agent status, spawn new agents if needed
```

### With Alerting System

Create a wrapper script that sends notifications:
```bash
#!/usr/bin/env python3
import subprocess
import sys

output = subprocess.check_output([sys.executable, 'show_agents.py'], text=True)
if 'failed' in output or '✗' in output:
    # Send alert - implement your notification method here
    send_alert("Agent failure detected:\n" + output)
print(output)
```

## Troubleshooting Guide

### Common Issues

**Issue**: Script returns "Error getting agent status: [object Object]"
**Solution**: The brain tool returned a dict instead of string. Update the fallback handling.

**Issue**: No agents showing after spawning
**Solution**: 
1. Check if brain MCP server is connected: `mcp_brain_brain_status`
2. Verify agent spawned correctly: check logs
3. Agents may have completed quickly - increase task complexity

**Issue**: Cron job not running
**Solution**:
1. Check job status: `cronjob list`
2. Verify script path and permissions
3. Check Hermes agent logs for cron execution errors

## Related Skills

- `agentic-coder` - For spawning coding agents
- `hermes-agent-panel` - For multi-agent orchestration
- `subagent-driven-development` - For task-based agent spawning
- `systematic-debugging` - For debugging agent issues