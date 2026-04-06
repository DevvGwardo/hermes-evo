---
name: brain-mcp-integration
description: Approach for integrating brain MCP agent execution into existing codebases by replacing simulated/stubbed functions with real brain agent invocation
category: software-development
---

# Brain MCP Integration Approach

## Overview
Systematic method for replacing simulated agent execution or stubbed functions in existing codebases with actual brain MCP agent execution. This approach enables real multi-agent collaboration instead of simulated work.

## When to Use
- When you encounter simulated agent steps (e.g., `await new Promise(r => setTimeout(r, 50))`)
- When functions return hardcoded/fake results instead of actual agent work
- When you want to replace stubbed implementations with real brain MCP agent coordination
- When integrating brain MCP capabilities into orchestration systems like OpenClaw Evo

## Preparation
- Ensure brain MCP system is operational (test with `brain_status`, `brain_agents`)
- Identify the target function/stub to replace
- Understand the expected input/output interface
- Have a clear task description for what the agent should accomplish
- Verify you can spawn agents successfully with `brain_wake`

## Steps

### 1. System Verification
```text
# Verify brain MCP is healthy
mcp_brain_brain_status
mcp_brain_brain_agents

# Test basic functionality
mcp_brain_brain_checkpoint   # Save test checkpoint
mcp_brain_brain_gate --notify false --dry_run true  # Dry run gate check
```

### 2. Target Analysis
- Locate the simulated/stubbed function (look for comments like "Placeholder", "Simulate", "Fake")
- Document the exact function signature and return type
- Identify what inputs are available (context, model, task description, etc.)
- Determine what the real agent should actually do instead of the simulation

### 3. Agent Design
- Define what specific task the brain agent should perform
- Determine appropriate model complexity (haiku for simple, sonnet/opus for complex)
- Choose layout (headless for background, windowed for visible)
- Plan what tools the agent will need access to
- Define how the agent will report results back

### 4. Implementation Strategy
Replace the stub with:
1. **Agent spawning**: Use `brain_wake` or equivalent to spawn a headless agent
2. **Context passing**: Provide the agent with necessary context (task, files, constraints)
3. **Execution waiting**: Wait for agent completion via polling or result reading
4. **Result translation**: Convert agent output to expected return format
5. **Error handling**: Manage agent failures, timeouts, and unexpected results

### 5. Example Pattern (TypeScript/Node.js)
```typescript
import { spawn } from 'child_process';
import { randomUUID } from 'crypto';

// Instead of:
// await new Promise(r => setTimeout(r, 50));
// return fakeResult;

// Use:
async function realAgentStep(context, modelInfo): Promise<ActualResultType> {
  const agentId = `agent-${randomUUID()}`;
  
  // Build prompt for the agent
  const prompt = `
    Task: [describe what needs to be done]
    Context: [relevant context information]
    Available tools: [list brain MCP tools agent can use]
    Report results via: [how agent should communicate results]
  `;
  
  // Spawn headless Claude agent (what brain_wake does internally)
  const agentProcess = spawn('claude', [
    '-p', prompt,
    '--model', getModelAlias(modelInfo),
    '--dangerously-skip-permissions'
  ], {
    env: {
      ...process.env,
      BRAIN_DB_PATH: process.env.BRAIN_DB_PATH,
      BRAIN_ROOM: process.env.BRAIN_ROOM,
      BRAIN_SESSION_ID: process.env.BRAIN_SESSION_ID,
      BRAIN_SESSION_NAME: process.env.BRAIN_SESSION_NAME
    }
  });
  
  // Wait for completion with timeout
  const result = await new Promise((resolve, reject) => {
    let output = '';
    let error = '';
    
    agentProcess.stdout.on('data', (data) => output += data.toString());
    agentProcess.stderr.on('data', (data) => error += data.toString());
    
    agentProcess.on('close', (code) => {
      if (code === 0) {
        resolve({ success: true, output: output.trim() });
      } else {
        reject(new Error(`Agent failed with code ${code}: ${error}`));
      }
    });
    
    // Timeout after 2 minutes
    setTimeout(() => {
      agentProcess.kill();
      reject(new Error('Agent execution timed out'));
    }, 120000);
  });
  
  // Translate result to expected format
  return translateToExpectedFormat(result);
}
```

### 6. Brain MCP Direct Alternative
If available in your environment, you can use direct brain MCP tool calls:
```text
# Instead of simulation:
mcp_brain_brain_wake --task "[specific task]" --name "worker-[timestamp]" --layout headless --model [appropriate] --timeout 120
# Then wait for completion and read results via brain_read or checkpoints
```

### 7. Verification
- Test the modified function in isolation if possible
- Verify it produces actual results (not simulations)
- Check that error handling works correctly
- Confirm performance characteristics are reasonable
- Ensure no regressions in existing functionality

## Key Learnings from Practice

### What Works Well
- **Headless layout**: Reliable for background agent execution without tmux dependencies
- **Clear task definition**: Agents perform best with specific, well-scoped tasks
- **Timeout management**: Essential to prevent hanging processes (2 minutes per step is reasonable)
- **Environment propagation**: Passing BRAIN_* environment variables ensures agents connect to correct MCP instance
- **Result validation**: Always verify agent output makes sense before proceeding

### Common Pitfalls
- **Overly complex tasks**: Agents struggle with vague or multi-part instructions
- **Missing context**: Agents need sufficient information to act effectively
- **Timeout too short**: Complex tasks need adequate time to complete
- **Tool access assumptions**: Don't assume agents have access to specific files/tools without granting it
- **Result parsing**: Agent output format may vary; build in flexibility

### Verification Checklist
[ ] Function compiles without errors
[ ] Function returns correct type/format
[ ] Function produces actual work (not simulation/hardcoded results)
[ ] Function handles success case appropriately
[ ] Function handles error/timeouts gracefully
[ ] No regression in existing functionality
[ ] Performance is acceptable for use case
[ ] Agents clean up properly (no zombie processes)

## Safety Considerations
- Start with simple, well-scoped tasks when testing
- Monitor agent resource usage (especially in loops/cycles)
- Implement circuit breakers for repeatedly failing agents
- Consider rate limiting if spawning many agents rapidly
- Test in isolation before deploying to production systems

## Applicable Systems
This approach works well with:
- Orchestration systems with simulated agent steps
- Multi-agent frameworks using placeholder implementations
- Any system with "fake it till you make it" agent simulations
- Codebases wanting to leverage real MCP agent capabilities
- Educational/demonstration code with stubbed implementations

## Example Applications
- Replacing `executeAgentStep` in OpenClaw Evo's ultrawork.ts
- Converting simulated coding agents to real brain MCP agents
- Turning mock testing frameworks into actual agent-driven test generation
- Converting architecture diagram generators to real agent-created designs
- Swapping fake data processors for real agent-based ETL pipelines

## Troubleshooting
If agents aren't performing as expected:
1. Verify the prompt is clear and actionable
2. Check that agents have necessary file/system access
3. Ensure sufficient timeout for task complexity
4. Validate BRAIN_* environment variables are correctly set
5. Check agent logs/output for error messages
6. Try simpler tasks to isolate the issue
7. Consider if the task needs decomposition into smaller steps

This approach transforms simulated agent systems into genuinely collaborative multi-agent environments by leveraging the brain MCP infrastructure for real agent execution and coordination.