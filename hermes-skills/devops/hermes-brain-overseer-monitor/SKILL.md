---
name: hermes-brain-overseer-monitor
description: Monitor the health of the Hermes Brain MCP system using the overseer script
category: devops
---
## Overview
Monitor the health of the Hermes Brain MCP system using the brain overseer monitoring approach. This skill provides a systematic approach to locate, execute, and interpret the brain overseer heartbeat monitoring by examining log files, status files, and the overseer script logic. Based on actual system inspection, the overseer monitoring is implemented via check_brain_heartbeat.py which executes the brain_heartbeat.sh script and analyzes job status. When standard scripts are not found, direct MCP tool calls (mcp_brain_brain_agents) can be used to check agent status and heartbeat freshness.

## When to Use
- Checking if the Brain MCP system is responsive
- Investigating system health alerts
- Verifying cron job execution for brain MCP monitoring
- Standard overseer scripts are not available or not executing
## Overview
Monitor the health of the Hermes Brain MCP system using the brain overseer script and associated heartbeat monitoring tools. This skill provides a systematic approach to locate, execute, and interpret the brain overseer heartbeat monitoring by examining log files, status files, and the overseer script logic.

## Steps

### 1. Locate the brain overseer cron job and related files
```bash
# Check the overseer cron job configuration
hermes cron list | grep overseer

# Or check the jobs file directly
cat $HOME/.hermes/cron/jobs.json | grep -A 20 overseer

# Locate the heartbeat monitoring files
find $HOME/.hermes -name '*heartbeat*' -type f
```

Expected output includes:
- Cron job with ID matching "brain-overseer" (or similar name) that runs every 2 minutes
- `$HOME/.hermes/brain_heartbeat.sh` - The heartbeat execution script (runs every minute)
- `$HOME/.hermes/brain_heartbeat.log` - Heartbeat logging
- `$HOME/.hermes/brain_heartbeat.status` - Current heartbeat status
- Output files in `$HOME/.hermes/cron/output/[job_id]/`

### 2. Check the overseer cron job execution
```bash
# View the most recent overseer job output
OVERSEER_JOB_ID=$(hermes cron list | grep overseer | head -1 | awk '{print $1}')
hermes cron output $OVERSEER_JOB_ID

# Or check the latest output file directly
ls -t $HOME/.hermes/cron/output/*/ | head -1 | xargs ls -t | head -1
cat [latest_output_file]

# The overseer job output contains the heartbeat monitoring results
```

### 3. Review overseer output and history
```bash
# View recent overseer activity (output from last execution)
# Find the overseer job ID and get its latest output
OVERSEER_JOB_ID=$(hermes cron list | grep overseer | head -1 | awk '{print $1}')
hermes cron output $OVERSEER_JOB_ID

# Check overseer execution history
ls -t $HOME/.hermes/cron/output/$OVERSEER_JOB_ID/ | head -5
```

The overseer job output shows:
- Job execution details including prompt and schedule
- Whether the script ran successfully
- What it output
- Current status of the MCP/brain system

### 4. Check current heartbeat status
```bash
# View the current heartbeat status
cat $HOME/.hermes/brain_heartbeat.status

# View recent heartbeat activity
tail -20 $HOME/.hermes/brain_heartbeat.log
```

### 5. Interpret the output from logs and status files
Look for these key indicators:

**In the overseer log (`brain_overseer.log`):**
- `OVERSEER HEARTBEAT_FRESH`: Heartbeat is being updated regularly (healthy)
- `OVERSEER HEARTBEAT_STALE`: Heartbeat has not been updated in over 2 minutes (needs attention)
- `OVERSEER RECENT_FAILURES`: Shows recent heartbeat failures from the heartbeat log
- `OVERSEER RECOVERY_ATTEMPT`: Indicates the overseer is attempting recovery procedures

**In the heartbeat log (`brain_heartbeat.log`):**
- `HEARTBEAT_OK`: Brain MCP is responsive (healthy)
- `HEARTBEAT_FAIL`: Brain MCP is not responsive (unhealthy)
- `SELF_HEAL`: Indicates self-healing procedures were attempted
- Timestamped entries show when checks occurred

**In the heartbeat status file (`brain_heartbeat.status`):**
- `OK`: Indicates the last known good state (may be stale if not updated recently)
- Other values indicate specific error conditions

## Example Healthy Overseer Log Output
```
[2026-04-05 07:54:49] OVERSEER START: Overseer check initiated
[2026-04-05 07:54:49] OVERSEER HEARTBEAT_FRESH: Heartbeat is being updated regularly
[2026-04-05 07:54:49] OVERSEER END: Overseer check completed
```

## Example Stale Heartbeat Overseer Log Output
```
[2026-04-05 07:54:49] OVERSEER START: Overseer check initiated
[2026-04-05 07:54:49] OVERSEER HEARTBEAT_STALE: Heartbeat has not been updated in over 2 minutes
[2026-04-05 07:54:49] OVERSEER LAST_STATUS: Last heartbeat status was: OK
[2026-04-05 07:54:49] OVERSEER RECOVERY_ATTEMPT: Triggering heartbeat recovery procedures
[2026-04-05 07:54:49] OVERSEER RECENT_FAILURES: Found recent heartbeat failures:
[2026-04-04 19:10:56] HEARTBEAT_FAIL: Brain MCP is not responsive
[2026-04-05 07:54:49] OVERSEER END: Overseer check completed
```

## Troubleshooting\\nIf the overseer cron job is not found or not executing:\\n1. Check if `$HOME/.hermes` directory exists\\n2. Verify the hermes agent is properly installed\\n3. Check cron jobs with `hermes cron list`\\n4. Look for overseer-related jobs in the output\\n5. Ensure the cron daemon is running\\n\\nIf the heartbeat shows issues despite overseer running:\\n- Check the heartbeat status file: `cat $HOME/.hermes/brain_heartbeat.status`\\n- Review recent heartbeat activity: `tail -20 $HOME/.hermes/brain_heartbeat.log`\\n- Check overseer output for execution details\\n\\nPattern recognition from monitoring:\\n- Overseer runs every 2 minutes via cron to check heartbeat freshness\\n- Heartbeat script runs every minute via cron to check Brain MCP responsiveness\\n- Heartbeat log shows alternating HEARTBEAT_OK and HEARTBEAT_FAIL during intermittent issues\\n- Status file shows the last known state (may be stale if not updated recently)\\n- Failures trigger self-heal logging in the heartbeat script\\n- Overseer output includes whether the script ran successfully and what it output\\n\\nAdditional insights from execution:\\n- The overseer approach uses cron job inspection rather than direct script execution\\n- When running via cron, monitoring provides historical trend data\\n- Heartbeat failures often appear as clusters showing when Brain MCP became unresponsive\\n- Recovery attempts are logged in the evangel but don't fix underlying issues\\n- The overseer log (via cron output) provides valuable trend data for diagnosing intermittent problems\\n- Both overse report and heartbeat monitoring are needed for complete picture

## Notes\n- The brain overseer runs every 2 minutes via cron to monitor heartbeat freshness\n- It executes the check_brain_heartbeat.py script which runs the heartbeat script and reports results\n- The overseer determines freshness by checking job execution and output\n- Historical tracking is available through cron output files\n- This approach complements direct MCP tool calls by providing trend analysis\n- The overseer monitoring is part of the hermes agent cron job system for brain system monitoring

## Example Healthy Output
```
◇ session-97520 — idle
◆ session-97521 — working: processing request
✓ session-97522 — done: completed analysis
```

## Example Output Showing MCP Connectivity Check
```
◇ session-97520 — idle (checking MCP access...)
```

## Example Unhealthy Output
```
Error getting agent status: MCP connection timeout
◇ session-97520 — idle (error)
```

## Troubleshooting
If show_agents.py is not found:
1. Check if `$HOME/.hermes` directory exists
2. Verify the hermes agent is properly installed
3. Look for the script in alternative locations as shown in step 1
4. The script may also be located in the agent/ directory as part of the hermes agent codebase

If the output shows persistent error messages:
- This indicates the Brain MCP system may be down or unresponsive
- Check network connectivity to MCP services
- Review MCP server logs for errors
- Consider restarting the hermes agent or MCP services
- Verify that the brain mcp tools are properly registered and accessible

Pattern recognition from monitoring:
- "(checking MCP access...)" indicates the script is attempting to establish MCP connectivity
- Consistent idle status with no errors suggests healthy but inactive system
- Working status indicates active processing
- Error messages require investigation of MCP connectivity or service availability

## Notes
- The show_agents.py script uses direct MCP brain tool calls to get agent status
- Provides real-time health check without requiring log file inspection
- Output includes visual status indicators (◇, ◆, ✓, ✗) for quick assessment
- Can be run manually for on-demand health checking or automated via cron
- The script is part of the hermes agent toolset for brain system monitoring