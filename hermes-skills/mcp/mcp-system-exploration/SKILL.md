---
name: mcp-system-exploration
description: Skill for exploring and testing the Hermes Brain MCP (Model Context Protocol) system
category: mcp
---

# MCP System Exploration

## Overview
Skill for exploring and testing the Hermes Brain MCP (Model Context Protocol) system. Provides a systematic approach to understanding MCP capabilities, testing agent spawning, communication, and coordination features.

## When to Use
- When you need to understand or debug the brain MCP system
- When testing agent spawning and coordination capabilities
- When exploring MCP features for the first time
- When verifying MCP functionality after system changes

## Preparation
- Ensure Hermes is running and brain MCP server is active
- Have terminal access to execute MCP commands
- Know your current working directory (the brain room)
- Optional: Have a specific test task in mind

## Steps

### 1. Check System Status
```text
mcp_brain_brain_status
```
- Shows current session info, room details, and agent count
- Verify you're in the expected brain room
- Check total vs in-room agent counts

### 2. Spawn a Test Agent
```text
mcp_brain_brain_wake \
  --task "Simple test task (e.g., echo hello)" \
  --name "test-agent-[timestamp]" \
  --layout headless \
  --model haiku \
  --timeout 30
```
- Use headless mode for background agents without tmux
- Start with haiku model for simple, fast tasks
- Set reasonable timeout (30-60 seconds)
- Note the agent ID and session ID for tracking

### 3. Monitor Agent Status
```text
mcp_brain_brain_sessions
mcp_brain_brain_agents --include_stale true
```
- Check if agent is spawned, working, done, or failed
- Watch heartbeat age to detect stale agents (>60 seconds typically indicates issues)
- Look at progress messages to understand agent state

### 4. Communicate with Agents
```text
# Send direct message
mcp_brain_brain_dm \
  --to "[agent-id]" \
  --content "Your instructions here"

# Check agent inbox
mcp_brain_brain_inbox

# Post to general channel (all agents can read)
mcp_brain_brain_post \
  --content "Message for all agents"
```

### 5. Test Context and State Features
```text
# Push context ledger entry
mcp_brain_brain_context_push \
  --entry_type "discovery" \
  --summary "What you learned" \
  --detail "Full details of your discovery" \
  --file_path "/path/to/relevant/file" \
  --tags '["test", "mcp", "feature-name"]'

# Get context summary
mcp_brain_brain_context_summary

# Test shared state
mcp_brain_brain_set --key "test-key" --value "test-value"
mcp_brain_brain_get --key "test-key"
```

### 6. Test Resource Claims
```text
# Claim a resource (prevents conflicts)
mcp_brain_brain_claim \
  --resource "unique-resource-name" \
  --ttl 60  # Auto-release after 60 seconds

# Release when done
mcp_brain_brain_release \
  --resource "unique-resource-name"

# List all active claims
mcp_brain_brain_claims
```

### 7. Handle Stale Agents
```text
# Check for stale agents
mcp_brain_brain_agents --include_stale true

# Respawn a failed/stale agent
mcp_brain_brain_respawn \
  --agent_name "[stale-agent-name]"

# The respawn command will give you:
# - replacement_name
# - replacement_task  
# - suggested_layout and model
# Use these to wake the replacement agent
```

### 8. Verify Integration (Before Marking Work Complete)
```text
# Check contract compliance
mcp_brain_brain_contract_check

# If mismatches found, fix them then re-check
```

### 9. Clean Up
```text
# Ensure agents complete their tasks and exit
# Resources auto-release based on TTL or manual release
# Stale agents will eventually be cleaned up by system
```

## Key MCP Concepts Learned

### Agent Lifecycle
- **Spawning**: Use `brain_wake` with task, name, layout, model, timeout
- **Monitoring**: Track via `brain_sessions` and `brain_agents`
- **Communication**: `brain_pulse` (heartbeat), `brain_dm` (direct), `brain_post` (channel)
- **Recovery**: `brain_respawn` for failed/stale agents
- **Testing Note**: Stale agents (heartbeat_age > 1 hour) are normal leftovers from prior sessions and not indicative of system issues unless accumulating rapidly

### Coordination Features
- **Claims**: `brain_claim`/`brain_release` prevent file/resource conflicts
- **Contracts**: `brain_contract_set`/`brain_contract_get`/`brain_contract_check` prevent integration bugs
- **Context**: `brain_context_push` builds external memory ledger
- **State**: `brain_set`/`brain_get` for shared ephemeral state

### Best Practices Discovered
1. **Always pulse regularly**: Send `brain_pulse` every 2-3 tool calls with status and progress
2. **Read DMs**: `brain_pulse` returns pending direct messages - always check and respond
3. **Claim before editing**: Use `brain_claim` on files before modifying, `brain_release` after
4. **Context is critical**: Use `brain_context_push` after every significant action to prevent losing track during context compression
5. **Start simple**: For first tests, use headless layout and haiku model for fast feedback
6. **Watch for staleness**: Agents with heartbeat_age > 60s are likely stuck and need attention
7. **Use recovery**: Don't just kill stale agents - use `brain_respawn` to continue their work

## Common Issues and Solutions

### Issue: Agent immediately exits with "invalid choice" error
**Cause**: Agent trying to interpret MCP instructions as hermes CLI commands
**Solution**: In DMs, be explicit that agents should NOT run hermes commands - they should just produce output and use brain pulses

### Issue: Agent appears stuck in "spawned by lead; initializing"
**Cause**: Agent waiting for instructions or blocked
**Solution**: Send clear DM instructions about what to do (often just output text and pulse done)

### Issue: Cannot find list_resources method
**Cause**: Not all MCP methods are implemented in brain server
**Solution**: Focus on implemented methods: status, sessions, agents, wake, pulse, DM, post, context, get/set, claim/release

### Issue: Losing track of what agents are doing
**Solution**: Regular `brain_context_push` entries with clear summaries and file paths

## Verification
After completing MCP exploration tasks:
- [ ] Verified brain status shows expected room and session info
- [ ] Successfully spawned at least one test agent
- [ ] Monitored agent status through sessions/agents commands
- [ ] Sent and received direct messages with agents
- [ ] Posted to general channel and confirmed visibility
- [ ] Tested context push and retrieval
- [ ] Tested shared state set/get operations
- [ ] Experimented with resource claims and releases
- [ ] Handled at least one stale agent scenario (observe or respawn)
- [ ] Checked contract compliance before considering work complete

## Safety Notes
- Brain MCP is designed for safe experimentation - agents run isolated
- Resources auto-claim with TTL to prevent permanent locks
- Context ledger persists across sessions and survives brain clears
- Always clean up claims when done to avoid blocking others
- Headless mode agents don't require tmux and work in any environment

## References
- Hermes brain MCP implementation in ~/.hermes/
- Brain tool definitions in MCP server
- Session logs in ~/.hermes/logs/ for debugging
- Agent output in /var/folders/*/brain-agent-*.log files