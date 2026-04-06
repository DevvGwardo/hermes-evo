---
name: brain-overseer-monitor
description: Monitor Brain MCP system health using the overseer script to check heartbeat freshness and detect responsiveness issues
category: software-development
---

# Brain Overseer Monitor Skill

## Description
Monitor the Brain MCP (Model Context Protocol) system health using the overseer script that checks heartbeat freshness and logs failure patterns. This approach goes beyond simple status checks by monitoring the timing and consistency of heartbeat updates to detect intermittent or degrading system health.

## When to Use
- When you need to monitor Brain MCP health over time (not just point-in-time checks)
- To detect intermittent connectivity issues that simple status checks might miss
- As part of routine system monitoring in cron jobs or background processes
- When troubleshooting Brain MCP responsiveness problems

## Procedure

### 1. Locate and Verify Overseer Script\nThe overseer script is typically located at:\n```bash\n~/.hermes/brain_overseer.sh\n```\n\nIf not found in the standard location, search for it:\n```bash\nfind ~/.hermes -name \"*overseer*\" -type f\nfind ~/hermes-agent -name \"*overseer*\" -type f 2>/dev/null\n```\n\nVerify it exists and is executable:\n```bash\nls -la ~/.hermes/brain_overseer.sh\n# Should show: -rwxr-xr-x ... brain_overseer.sh\n```\n
### 2. Run the Overseer Check
Execute the overseer script to perform a health check:
```bash
~/.hermes/brain_overseer.sh
```

The script returns exit code 0 regardless of findings (it logs results rather than failing on unhealthy status).

### 3. Examine Overseer Logs
Check the overseer log for detailed results:
```bash
# View recent overseer log entries
tail -20 ~/.hermes/brain_overseer.log

# Or view the full log
cat ~/.hermes/brain_overseer.log
```

### 4. Interpret Overseer Log Output

**Key Log Patterns:**
- `[TIMESTAMP] OVERSEER START: Overseer check initiated`: Script beginning
- `[TIMESTAMP] OVERSEER HEARTBEAT_FRESH: Heartbeat is being updated regularly`: Heartbeat updated within last 2 minutes (indicates healthy operation)
- `[TIMESTAMP] OVERSEER HEARTBEAT_STALE: Heartbeat has not been updated in over 2 minutes`: No recent heartbeat updates (warning sign)
- `[TIMESTAMP] OVERSEER LAST_STATUS: Last heartbeat status was: [STATUS]`: Shows what heartbeat.last reported (OK, FAIL, etc.)
- `[TIMESTAMP] OVERSEER RECOVERY_ATTEMPT: Triggering heartbeat recovery procedures`: Script detected issue and logged recovery attempt
- `[TIMESTAMP] OVERSEER RECENT_FAILURES: Found recent heartbeat failures:`: Shows actual failure patterns
- `[TIMESTAMP] OVERSEER END: Overseer check completed`: Script finished

**Important Log Interpretation Notes:**
- **HEARTBEAT_STALE with LAST_STATUS: OK**: Indicates the heartbeat mechanism is partially functional (can read status file) but not updating frequently enough - suggests the heartbeat script may be running slowly or getting stuck
- **Recurring HEARTBEAT_FAIL patterns**: Multiple failure timestamps in RECENT_FAILURES indicate intermittent connectivity issues that may require investigation
- **Overseer always returns exit code 0**: The script logs results rather than failing on unhealthy status, so check the log content, not the exit code

**Heartbeat Failure Patterns (from RECENT_FAILURES):**
- `[TIMESTAMP] HEARTBEAT_FAIL: Brain MCP is not responsive`: Direct failure to connect/communicate with Brain MCP
- Multiple timestamps show recurring or intermittent issues
- Look for patterns: clusters of failures followed by periods of recovery may indicate environmental issues or resource constraints

### 5. Health Assessment Guidelines

**Healthy System Indicators:**
- Consistent `HEARTBEAT_FRESH` messages in overseer log
- Few or no `HEARTBEAT_FAIL` entries in recent failures
- Heartbeat status file (`~/.hermes/brain_heartbeat.status`) showing \"OK\"\n- Overseer script runs without errors (exit code 0)\n\n**Warning Signs:**\n- Repeated `HEARTBEAT_STALE` messages (heartbeat not updating regularly)\n- `HEARTBEAT_FAIL` entries in recent failures section\n- **Important**: `HEARTBEAT_STALE` with Last_status showing \"OK\" indicates the heartbeat mechanism can read the status file but isn't updating frequently enough - suggests the heartbeat script may be running slowly or getting stuck\n- Clusters of failures followed by periods of apparent recovery\n\n**Critical Issues:**\n- Overseer script fails to execute (non-zero exit code, missing file)\n- Heartbeat log missing or not being written to\n- Complete lack of overseer log updates (suggests cron job not running)\n
- Overseer script runs without errors (exit code 0)

**Warning Signs:**
- Repeated `HEARTBEAT_STALE` messages (heartbeat not updating regularly)
- `HEARTBEAT_FAIL` entries in recent failures section
- Last_status showing "OK" despite stale heartbeat (indicates partial functionality)
- Clusters of failures followed by periods of apparent recovery

**Critical Issues:**
- Overseer script fails to execute (non-zero exit code, missing file)
- Heartbeat log missing or not being written to
- Complete lack of overseer log updates (suggests cron job not running)

### 6. Supplemental Checks

For additional context, check these related files:
```bash
# Check heartbeat log for raw failure data
tail -10 ~/.hermes/brain_heartbeat.log

# Check current heartbeat status
cat ~/.hermes/brain_heartbeat.status

# Check if heartbeat script itself is running
ps aux | grep brain_heartbeat
```

### 7. Automated Monitoring Tips

When running in automated contexts (cron jobs):
- The overseer script is designed to be run every 2 minutes via cron
- It logs to ~/.hermes/brain_overseer.log with timestamped entries
- Recovery attempts are logged but don't trigger automatic restarts (by design)
- For alerting, monitor the log for patterns of HEARTBEAT_STALE or recurring HEARTBEAT_FAIL

## Expected Output
Successful overseer execution produces log entries like:
```
[2026-04-04 23:14:11] OVERSEER START: Overseer check initiated
[2026-04-04 23:14:11] OVERSEER HEARTBEAT_STALE: Heartbeat has not been updated in over 2 minutes
[2026-04-04 23:14:11] OVERSEER LAST_STATUS: Last heartbeat status was: OK
[2026-04-04 23:14:11] OVERSEER RECOVERY_ATTEMPT: Triggering heartbeat recovery procedures
[2026-04-04 23:14:11] OVERSEER RECENT_FAILURES: Found recent heartbeat failures:
[2026-04-04 19:10:56] HEARTBEAT_FAIL: Brain MCP is not responsive
[2026-04-04 21:14:08] HEARTBEAT_FAIL: Brain MCP is not responsive
[2026-04-04 22:20:12] HEARTBEAT_FAIL: Brain MCP is not responsive
[2026-04-04 23:14:11] OVERSEER END: Overseer check completed
```

## Notes
- The overseer script is intentionally conservative - it logs issues but doesn't attempt automatic restarts to avoid interfering with manual troubleshooting
- Stale heartbeat with "OK" last_status often indicates the heartbeat mechanism is partially functional but not updating frequently enough
- Always correlate overseer findings with direct MCP tool checks when available for complete health picture
- This skill complements the brain-heartbeat-check skill by adding time-series monitoring capability