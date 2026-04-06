---
name: adaptive-discovery
description: When a specific tool/script/resource is requested but not found, use adaptive discovery to find related functionality
category: productivity
---

When a specific tool, script, or resource is requested but not found by exact name, use an adaptive discovery approach to find related functionality and provide meaningful information.

## Trigger Conditions
- User asks for a specific tool/script/resource by name
- Initial search for that exact name returns no results
- Need to provide useful information despite the missing exact match

## Approach
1. **Broaden search terms** - Look for related keywords, partial matches, or similar concepts
2. **Examine surrounding context** - Check what tools/scripts do exist in the expected area
3. **Use available diagnostic tools** - Leverage system status, logs, and health checks
4. **Pivot to related functionality** - Find and examine analogous systems that serve similar purpose
5. **Report findings clearly** - Explain what was found, how it relates to the request, and current status

## Steps
1. Search for exact match: `search_files(pattern="<exact_name>", target="files")`
2. If no results, try variations:
   - Partial matches: `search_files(pattern="*partial*", target="files")`
   - Related terms: brainstorm synonyms or related concepts
   - File extensions: search for common script/types in relevant directories
3. Examine system state:
   - Check cron jobs: `terminal(command="hermes cron list")`
   - Check logs: look for related log files in ~/.hermes/
   - Test connectivity: use appropriate test commands (e.g., `hermes mcp test <name>`)
4. Investigate discovered alternatives:
   - Read found scripts/configs to understand purpose
   - Run diagnostic tools to get current status
   - Check execution history/results
5. Synthesize response:
   - Explain what was searched for and not found
   - Describe what was discovered instead
   - Provide current status and relevant details
   - Note any limitations or differences from original request

## Example Applications
- Looking for "overseer" script -> discovered brain-heartbeat monitoring system
- Searching for specific diagnostic tool -> found related health check scripts
- Requesting unavailable utility -> identified equivalent built-in commands

## Verification
- Confirm discovered system actually serves related purpose
- Verify status information is current and accurate
- Ensure response addresses user's underlying need for monitoring/status

## Pitfalls
- Don't spend excessive time searching if multiple approaches fail
- Be clear about what was NOT found vs what was discovered
- Don't pretend the discovered item is identical to the requested item
- If no related functionality exists, state that clearly and suggest alternatives