---
name: internal-tool-discovery
description: Framework for discovering internal tools and functionality when direct searches fail
category: software-development
---

# Internal Tool Discovery

## When to Use
When you need to find a specific script, tool, or functionality but initial searches don't locate it as expected. Use this when:
- You're looking for a specific script or tool by name but can't find it
- You suspect functionality exists but isn't where you expected
- You need to discover what tools or systems are available for a task
- Initial searches come up empty but you believe the capability exists

## Approach
This skill provides a framework for discovering internal tools and functionality when direct searches fail. It emphasizes adaptability, using available exploration tools, and verifying discoveries through actual use.

## Steps

### 1. Initial Targeted Search
- Search for the exact name or expected terms
- Use multiple search strategies (filename, content, etc.)
- Check common locations where such tools might reside
- **Tools**: `search_files`, `execute_code` (for filesystem walks)

### 2. Broaden Search Scope
- If initial search fails, search for related concepts or functionality
- Look for synonyms, related terms, or partial matches
- Check documentation or comments that might reference the functionality
- **Tools**: `search_files` with broader patterns, `read_file` for documentation

### 3. Explore Available Systems/Tools
- Consider whether the functionality might be built into existing tools
- Check available MCP tools, brain tools, or Hermes-specific tools
- Use system exploration tools to see what's available
- **Tools**: `mcp_brain_brain_agents` (for MCP system), `skills_list`, tool exploration

### 4. Test Hypotheses
- When you find a candidate that might provide the functionality, test it
- Use the tool or system to see if it provides what you need
- Verify by examining outputs or results
- **Tools**: Direct use of candidate tools, `execute_code` for testing

### 5. Adapt Based on Findings
- Modify your search strategy based on what you discover
- If you find related functionality, explore its surroundings
- Use discovered information to refine your search
- **Tools**: All discovery tools, guided by what you've learned

### 6. Verify and Report
- Confirm your discovery by using the functionality to accomplish the original goal
- Document what you found and how it relates to what was sought
- Report findings with context about the discovery process
- **Tools**: Whatever was discovered to accomplish the task

## Key Principles
- **Adaptability**: Change your approach based on what you find
- **Exploration over assumption**: Don't assume where functionality should be; discover where it actually is
- **Verification through use**: The best way to confirm you've found the right tool is to use it
- **Leverage existing systems**: Often functionality is built into existing tools rather than being separate

## Example: Finding the "Overseer Script"
Looking for an overseer script to monitor heartbeats:
1. Searched for "overseer" in filenames and content - found only references in our own search scripts
2. Searched for "heartbeat monitor" - found references in platform code but no standalone script
3. Considered that the functionality might be built into existing systems
4. Explored the MCP/brain system using `mcp_brain_brain_agents` 
5. Discovered this tool provides agent status, heartbeats, and monitoring capabilities
6. Verified by using it to get the actual heartbeat information needed
7. Reported that the overseer functionality IS the brain_agents tool

## Pitfalls to Avoid
- Assuming the tool must exist as a separate file/script with the exact name
- Giving up too quickly when initial searches fail
- Not verifying that discovered functionality actually solves the original problem
- Forgetting to check if functionality is built into existing tools/systems
- Not adapting search strategy based on intermediate findings

## Related Skills
- `adaptive-web-research`: Similar adaptive approach but for web information gathering
- `mcp-health-check`: Specific to MCP system health checking
- `systematic-debugging`: For root cause investigation when things don't work as expected