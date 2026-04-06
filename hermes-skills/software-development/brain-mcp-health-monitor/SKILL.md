---
name: brain-mcp-health-monitor
description: Monitor and maintain brain MCP system health including overseer scripts, heartbeat checks, and Node.js module compatibility
category: software-development
---

# Brain MCP Health Monitor Skill

## Description
Monitor and maintain the health of the brain MCP (Model Context Protocol) system. This skill provides procedures for checking system health, diagnosing common issues (particularly Node.js module compatibility), and maintaining the overseer/heartbeat monitoring infrastructure.

## When to Use
- When agents appear unresponsive or stale
- When overseer logs show heartbeat failures
- Before relying on brain MCP functionality for agent spawning
- As part of routine system health monitoring
- When encountering `ERR_DLOPEN_FAILED` or `NODE_MODULE_VERSION` errors

## Procedure

### 1. Check Overseer Logs
First, examine the brain overseer logs to understand recent health status:
```bash
cat ~/.hermes/brain_overseer.log
```
Look for:
- HEARTBEAT_STALE vs HEARTBEAT_FRESH status
- RECENT_FAILURES sections
- Recovery attempt logs

### 2. Verify Heartbeat Status
Check the current heartbeat status file:
```bash
cat ~/.hermes/brain_heartbeat.status
```
Should contain "OK" for healthy state or "FAIL" for issues.

### 3. Examine Heartbeat Log
Review recent heartbeat checks:
```bash
tail -20 ~/.hermes/brain_heartbeat.log
```
Look for patterns of HEARTBEAT_OK vs HEARTBEAT_FAIL.

### 4. Test Brain MCP Connectivity
Directly test the brain MCP connection:
```bash
hermes mcp test brain
```
Watch for:
- Successful connection messages (✓ Connected)
- Node.js compatibility errors (ERR_DLOPEN_FAILED, NODE_MODULE_VERSION mismatches)
- Connection timeouts or closures

### 5. Enable and Test Brain MCP Tools
If the MCP connection is successful but you need to use brain tools:
```bash
# Enable all brain MCP tools (if not already enabled)
hermes tools enable brain:*

# List available brain tools to verify they're accessible
hermes tools list | grep brain

# Call specific brain MCP tools using the tools call command
hermes tools call brain:sessions          # List active sessions
hermes tools call brain:pulse             # Report progress and stay alive
hermes tools call brain:status            # Show session info
hermes tools call brain:agents            # Check health of all agents
```

### 6. Diagnose Node.js Issues (If Applicable)
If you see Node.js version errors:
```bash
# Check current Node.js version
node --version

# Navigate to brain-mcp directory
cd ~/.hermes/brain-mcp || cd /path/to/brain-mcp

# Rebuild native modules
npm rebuild better-sqlite3

# Alternative: full reinstall
# npm install
```

### 7. Run Overseer Check
Manually trigger the overseer script:
```bash
~/.hermes/brain_overseer.sh
```
Then check updated logs:
```bash
tail -10 ~/.hermes/brain_overseer.log
```

### 8. Verify Cron Jobs
Ensure the monitoring cron jobs are active:
```bash
crontab -l | grep -E "(brain_|overseer|heartbeat)"
```
Should show entries for both heartbeat (every minute) and overseer (every 2 minutes).
Should show entries for both heartbeat (every minute) and overseer (every 2 minutes).

## Expected Output
Healthy system indicators:
- Overseer log shows HEARTBEAT_FRESH status
- Heartbeat status file contains "OK"
- Recent heartbeat logs show HEARTBEAT_OK entries
- `hermes mcp test brain` returns successful connection
- No Node.js compatibility errors in test output
- Overseer script runs without errors

## Troubleshooting Steps
If the system appears unhealthy:
1. **Node.js module issues**: Rebuild better-sqlite3 in brain-mcp directory
2. **Stale processes**: Check if brain MCP server is running
3. **Cron not running**: Verify cron daemon is active and jobs are scheduled
4. **Permission issues**: Ensure scripts are executable (`chmod +x *.sh`)
5. **Path issues**: Verify brain-mcp directory exists and is accessible

## Notes
- The heartbeat script runs every minute via cron
- The overseer script runs every 2 minutes via cron
- Stale agent entries in logs are normal from previous runs
- Node.js version mismatches can cause the test command to run but fail to actually connect
- Self-healing attempts are logged but actual restart depends on MCP management setup

## Example Usage
```bash
# Quick health check
cat ~/.hermes/brain_heartbeat.status
hermes mcp test brain

# Detailed diagnosis
tail -20 ~/.hermes/brain_overseer.log
tail -10 ~/.hermes/brain_heartbeat.log

# Fix Node.js issues
cd ~/.hermes/brain-mcp && npm rebuild better-sqlite3

# Manual oversight check
~/.hermes/brain_overseer.sh
```

## Related Files
- `~/.hermes/brain_overseer.sh` - Overseer monitoring script
- `~/.hermes/brain_heartbeat.sh` - Heartbeat checking script  
- `~/.hermes/brain_overseer.log` - Overseer activity log
- `~/.hermes/brain_heartbeat.log` - Heartbeat activity log
- `~/.hermes/brain_heartbeat.status` - Current status file
- `~/.hermes/brain-mcp/` - Brain MCP server directory