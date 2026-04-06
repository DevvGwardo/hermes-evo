---
description: Access MCP tools directly using the MCP client library when standard Hermes MCP CLI commands fail to expose individual tools
name: mcp-direct-client-tool-access
---

# MCP Direct Client Tool Access

## When to Use This Skill
When you need to call tools on an MCP server but:
- The standard `hermes mcp call <tool>` command fails with "invalid choice" errors
- You need more control over MCP client connections
- You want to bypass CLI limitations and access MCP tools programmatically
- Standard tool access methods aren't working in your current context

## Prerequisites
- MCP server must be running and accessible
- Basic understanding of MCP protocol
- Python environment with MCP client libraries available
- Knowledge of the target MCP server's available tools

## Step-by-Step Approach

### 1. Verify MCP Server Connection
First, confirm the MCP server is running and responsive:

```bash
hermes mcp test <server-name>
# Should show: ✓ Connected and list of discovered tools
```

### 2. Set Up Python MCP Client
Use the MCP client library to create a direct connection:

```python
import asyncio
import json
from mcp.client.stdio import stdio_client
from mcp import StdioServerParameters, ClientSession

# Configure connection parameters
server_params = StdioServerParameters(
    command="<mcp-server-command>",  # e.g., "node"
    args=["<path-to-mcp-server-dist/index.js>"]  # Path to server
)

async def access_mcp_tools():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # List available tools to verify access
            tools_result = await session.list_tools()
            print(f"Available tools: {[t.name for t in tools_result.tools]}")
            
            # Call specific tool
            result = await session.call_tool(
                "<tool-name>",
                {
                    "<parameter-name>": "<parameter-value>"
                }
            )
            
            # Process result
            if hasattr(result, 'content'):
                for content_item in result.content:
                    if hasattr(content_item, 'text'):
                        try:
                            response_data = json.loads(content_item.text)
                            # Process structured response
                        except json.JSONDecodeError:
                            # Handle plain text response
                            pass
            return result

# Execute the async function
asyncio.run(access_mcp_tools())
```

### 3. Common Patterns for Brain MCP Specifically
For the Brain MCP system in Hermes:

```python
# Brain MCP specific connection
server_params = StdioServerParameters(
    command="node",
    args=["/Users/devgwardo/brain-mcp/dist/index.js"]
)

async def spawn_brain_agent(task_content, filename=None):
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Prepare task
            timestamp = int(time.time())
            if filename is None:
                filename = f'/tmp/brain_agent_{timestamp}.txt'
            
            # Spawn agent
            result = await session.call_tool(
                "brain_wake",
                {
                    "task": f"Create file {filename} in /tmp with content: {task_content}",
                    "name": f"direct-agent-{timestamp}",
                    "layout": "headless"
                }
            )
            
            # Wait for completion
            await asyncio.sleep(10)
            
            # Verify result
            import os
            if os.path.exists(filename):
                with open(filename, 'r') as f:
                    return f.read()
            return None
```

### 4. Error Handling and Troubleshooting

#### Common Issues:
- **Connection failures**: Verify server path and command are correct
- **Tool not found**: Double-check tool name spelling and case
- **Timeouts**: Increase wait time or check agent execution logs
- **Permission issues**: Ensure execute permissions on MCP server binaries

#### Debugging Tips:
1. Test connection with `hermes mcp test <server>` first
2. Use `session.list_tools()` to verify tool availability
3. Check MCP server logs for connection and execution details
4. Verify file paths are accessible from the MCP server's perspective

### 5. Verification Steps
After calling MCP tools directly:
1. Check for expected output/files in the anticipated location
2. Verify MCP server logs show successful tool execution
3. Confirm any side effects (file creation, state changes) occurred
4. Test with known good parameters before trying complex operations

### 6. When This Approach is Preferred
- Standard Hermes MCP CLI doesn't expose the needed tool
- You need to chain multiple MCP tool calls with intermediate processing
- You're working in an environment where CLI tools are limited
- You want to integrate MCP tool calls into larger Python workflows
- Debugging MCP server connectivity or tool execution issues

## Key Learnings from Experience
1. The `hermes mcp` CLI command is for server management, not tool invocation
2. Individual MCP tools must be accessed through the MCP client protocol directly
3. Python's `mcp.client.stdio` provides reliable direct access
4. Always verify tool availability with `list_tools()` before calling
5. Brain MCP specifically uses `brain_wake` for agent spawning with headless layout
6. File-based activity detection works well for verifying agent execution
7. Timeout handling is crucial - agents may take longer than expected to complete

## Related Skills
- `hermes-agent`: For spawning additional Hermes Agent instances
- `terminal`: For executing shell commands and checking results
- `execute_code`: For running Python scripts with MCP client access