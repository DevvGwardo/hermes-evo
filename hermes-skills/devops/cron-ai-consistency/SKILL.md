---
name: cron-ai-consistency
description: Diagnose and fix inconsistent behavior in Hermes cron jobs where AI agent interpretation leads to unreliable execution
version: 1.0.0
author: Hermes Agent
---
# Cron Job AI Consistency Fix

When Hermes cron jobs use AI agents to interpret prompts (rather than direct script execution), the agent's behavior can be inconsistent - sometimes executing the intended action, sometimes giving generic responses. This leads to unreliable system health monitoring and false alerts.

## Problem Symptoms

- Cron job outputs alternate between executing actual scripts and giving generic responses
- System health indicators show intermittent staleness despite underlying systems being healthy
- Overseer/monitoring tools detect false failures due to lack of status file updates
- Job logs show pattern: some runs show script execution, others show AI-generated summaries

## Diagnostic Approach

1. **Correlate job outputs with system state**
   - Check if status file/timestamp updates match job execution patterns
   - Look for correlation between "script execution" jobs and fresh system indicators
   - Look for correlation between "generic response" jobs and stale system indicators

2. **Analyze job output patterns**
   - Collect recent job outputs for the problematic cron job
   - Categorize each job as: script execution, generic response, or other
   - Calculate percentage of jobs that actually perform the intended action

3. **Verify root cause**
   - Manually run the expected script/command to confirm it works
   - Check that manual execution produces the expected system updates
   - Confirm that the AI agent's generic responses don't produce system updates

## Solution: Make Prompts More Explicit

Instead of relying on AI agent interpretation of vague prompts, make cron job prompts explicitly directive:

### Before (problematic):
```
"Run the brain heartbeat script to check MCP availability"
```

### After (fixed):
```
"Execute the brain heartbeat script at /Users/devgwardo/.hermes/brain_heartbeat.sh and report the results. Include whether the script ran successfully, what it output, and the current status of the MCP/brain system."
```

### Key improvements:
- Specifies exact script path to execute
- Requires reporting of execution results (success/failure, output)
- Asks for system status reporting to confirm check worked
- Reduces ambiguity in AI agent interpretation

## Validation Steps

1. After updating the cron job prompt:
   - Monitor job outputs for increased consistency in script execution
   - Check that status file updates occur more regularly
   - Verify overseer/monitoring tools show fewer false alerts

2. Expected outcomes:
   - Higher percentage of jobs showing actual script execution
   - More regular status file timestamp updates
   - Reduced oscillating FRESH/STALE patterns in overseer logs
   - More reliable system health reporting

## Prevention

For new cron jobs that execute scripts:
- Use explicit prompts that specify exact execution requirements
- Consider adding skills that encapsulate script execution logic
- Test job behavior manually before enabling
- Monitor early outputs for consistency

## Related Tools

- `hermes cronjob list` - View cron job definitions
- `hermes cronjob update` - Modify cron job prompts
- Session search - Review past cron job outputs for pattern analysis
- File tools - Examine cron job definitions and outputs