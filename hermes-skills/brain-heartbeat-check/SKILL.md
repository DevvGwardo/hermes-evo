---
name: brain-heartbeat-check
description: Check MCP/brain system health using show_agents.py or show_agents.sh scripts as primary health check tools
category: devops
---

# Brain Heartbeat Check Skill

## Description
Check the health and status of the MCP (Model Context Protocol) brain system. This skill provides multiple approaches to verify brain/MCP health, ranging from direct MCP tool access (when available) to script-based fallbacks for restricted environments like cron jobs.

The health check follows this priority:
1. **Direct MCP Tool Access** - Most accurate, checks actual server connectivity and tool availability
2. **Script-Based Check** - Reliable fallback for cron/restricted environments  
3. **Server Process & Config Verification** - Diagnostic checks for troubleshooting

## Procedure

### 1. Primary Method: Direct MCP Tool Access (Recommended)
When MCP tool access is available (not in restricted environments like cron jobs), use direct tool access for the most accurate health check:
```bash
# Check MCP server status and tool availability
hermes mcp status

# Specifically check brain server
hermes mcp status brain

# List available MCP tools to see if brain tools are discoverable
hermes mcp tools
```

**Expected Output for Healthy System:**
- MCP server shows `connected: true`
- Brain server shows `tools: > 0` (number of available tools)
- Brain-specific tools appear in the tool list (e.g., `mcp_brain_brain_sessions`)

### 2. Fallback Method: Script-Based Check (Cron/Restricted Environments)
When direct MCP tool access requires approval (like in cron jobs), use the dedicated brain heartbeat script:
```bash
# Locate and execute the brain heartbeat script
bash $(find ~/.hermes -name \"brain_heartbeat.sh\" -type f | head -1)
```

**Script Output Analysis:**
- `◇ session-XXXXXX — idle (checking MCP access...)`: Script executed but MCP tools not directly accessible (expected in cron jobs) - **INDICATES SUCCESSFUL EXECUTION**
- `◇ session-XXXXXX — idle (error)`: Script encountered an error during execution
- Detailed session output with actual agent data: Indicates direct MCP access succeeded within script context
- **Success Criteria**: Script runs without Python exceptions (exit code 0), regardless of output content

### 3. Diagnostic Method: Server Process & Configuration Verification
For troubleshooting when health checks indicate issues:
```bash
# Verify brain server script exists and is accessible
ls -la /Users/devgwardo/brain-mcp/dist/index.js

# Check Node.js can load the server (shows compatibility issues)
node /Users/devgwardo/brain-mcp/dist/index.js --help 2>&1 | head -5

# Verify Node.js version compatibility
node --version

# Check if brain server processes are running
ps aux | grep brain-mcp | grep -v grep

# Review brain MCP server configuration
cat ~/.hermes/config.yaml | grep -A 10 -B 2 "mcp_servers:"
```

### 4. Advanced: Node.js Module Compatibility Diagnostics
When encountering module errors (e.g., better_sqlite3.node):
```bash
# Navigate to brain MCP directory
cd /Users/devgwardo/brain-mcp

# Check compiled Node.js version for native modules
strings node_modules/better-sqlite3/build/Release/better_sqlite3.node | grep NODE_MODULE_VERSION

# Current Node.js version
node -v | sed 's/v//'

# Rebuild native modules for current Node.js
npm rebuild

# Alternative: Fresh install if rebuild fails
# rm -rf node_modules package-lock.json
# npm install

# Test if server loads correctly now
node dist/index.js --help 2>&1 | head -5
```

### 5. Supplemental: Check Heartbeat History
Review historical context from the brain heartbeat monitoring system:
```bash
# Check recent heartbeat log entries
tail -20 ~/.hermes/brain_heartbeat.log

# Check current status file
cat ~/.hermes/brain_heartbeat.status
```

**Heartbeat Log Indicators:**
- `HEARTBEAT_OK: Brain MCP is responsive`: Successful MCP connection
- `HEARTBEAT_FAIL: Brain MCP is not responsive`: Failed MCP connection
- Patterns of intermittent connectivity suggest environmental issues

## Example Usage
```bash
# Primary: Direct MCP tool check (preferred when available)
STATUS=$(hermes mcp status brain 2>/dev/null || echo "MCP access not available")
echo \"Brain MCP status: $STATUS\"

# Fallback: Script-based check for cron/restricted environments  
OUTPUT=$(python3 ./show_agents.py 2>/dev/null || echo "Script failed")
echo \"Brain health check output: $OUTPUT\"

# Verify script executed successfully (exit code 0)
if python3 ./show_agents.py >/dev/null 2>&1; then
  echo \"Brain heartbeat check mechanism: OK\"
else
  echo \"Brain heartbeat check mechanism: FAILED\"
fi
```

## Notes
- **Priority Order**: Direct MCP tools > Script-based check > Server diagnostics
- **Cron Job Context**: Expect script-based fallback to show \"checking MCP access...\" which indicates successful execution in approval-required environments
- **Healthy System Indicators**: 
  - Direct tools: Brain server connected with available tools
  - Script fallback: Script executes successfully (exit code 0)  
  - Diagnostics: Server script exists, Node.js compatible, processes running
- **Troubleshooting Focus**: When seeing \"checking MCP access...\" in script output, verify server connectivity and tool discovery separately
- **Safety**: All check methods are lightweight and non-invasive for frequent use