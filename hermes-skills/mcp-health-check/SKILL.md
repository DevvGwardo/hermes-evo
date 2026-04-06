---
name: mcp-health-check
description: Check the health and status of the MCP (Model Context Protocol) brain system
category: mcp
---

# MCP Health Check Skill

## Description
Check the health and status of the MCP (Model Context Protocol) brain system, including agent availability, session status, and overall system functionality. This skill provides a systematic approach to verifying that the MCP infrastructure is operational.

## When to Use
- When you need to verify MCP/brain system availability
- Before spawning agents or relying on MCP functionality
- When agents appear unresponsive or stale
- As part of routine system health monitoring
- When troubleshooting agent coordination issues

## Procedure

### 1. Check Active Sessions
First, examine what sessions are currently active in the system:
```
mcp_brain_brain_sessions
```
This returns information about all active sessions including:
- Session ID and name
- Process ID (PID)
- Current working directory
- Room/namespace
- Creation timestamp
- Last heartbeat time
- Current status (idle, working, done, failed)

### 2. Check Agent Status
Examine the status of all agents in the system:
```
mcp_brain_brain_agents
```
This provides:
- Total agent count
- Breakdown by status (working, done, failed, stale)
- For each agent: ID, name, status, progress, last heartbeat, heartbeat age, staleness flag, and any claims

### 3. Send a Health Pulse
Report your own status to the system to verify bidirectional communication:
```
mcp_brain_brain_pulse --status working --progress "Checking MCP availability and agent status"
```
This confirms you can successfully communicate with the brain system.

### 4. Interpret Results
Healthy system indicators:
- At least one session shows recent heartbeat (within last few minutes)
- Current session shows "idle" or "working" status with recent heartbeat
- Agents show appropriate statuses (stale agents from previous runs are expected)
- No widespread failures or timeouts

### 5. Troubleshooting Steps
If the system appears unhealthy:
- Check if brain processes are running
- Verify MCP server connectivity
- Look for error logs in the brain system
- Consider restarting stale agents if appropriate
- Verify network connectivity to MCP endpoints

## Expected Output
A healthy response will show:
- Active sessions with recent heartbeats
- Agent status breakdown
- Successful pulse response with "ok": true

## Notes
- Stale agents from previous swarms/leads are normal and expected
- The current session should always appear in the sessions list
- Heartbeat age is measured in seconds - newer is better
- If no sessions appear, the MCP system may be down
- This check is lightweight and safe to run frequently

## Example Usage
```bash
# Check overall system health
mcp_brain_brain_sessions
mcp_brain_brain_agents  
mcp_brain_brain_pulse --status working --progress "Routine health check"

# All commands should return quickly with structured data
```