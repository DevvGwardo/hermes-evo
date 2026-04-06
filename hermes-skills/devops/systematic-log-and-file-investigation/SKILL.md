---
name: systematic-log-and-file-investigation
category: devops
description: A methodical approach to investigating system behavior by following clues from logs, scripts, and file system evidence
---

# Systematic Log and File Investigation

## When to Use
When you need to understand a system's behavior, troubleshoot an issue, or investigate cron jobs/scripts where you don't have direct documentation but can examine logs, scripts, and file system clues.

## Approach
Instead of guessing or making assumptions, follow a systematic trail of evidence by:
1. Finding relevant files through targeted searches
2. Reading scripts to understand their purpose and logic
3. Examining log files for historical patterns and current status
4. Checking status files or checkpoints for real-time state
5. Running the actual scripts to observe behavior
6. Correlating information from multiple sources

## Steps

### 1. Identify What You're Looking For
- Start with any identifiers you have (job IDs, script names, process names)
- Use these as search terms to find related files

### 2. Find Related Files Through Systematic Search
```bash
# Search for files by name pattern
find . -name "*overseer*" -type f
find . -name "*brain*" -type f

# Search in specific directories likely to contain relevant files
find ./cron -name "*" -type f
find ./agent -name "*monitor*" -type f
```

### 3. Examine Scripts to Understand Logic
- Read any discovered scripts to understand their purpose
- Look for configuration variables, file paths, and logic flow
- Identify what files they read/write and what they monitor

### 4. Check Log Files for Historical Patterns
```bash
# Look for log files referenced in scripts
cat /path/to/script.log

# Check for patterns, frequencies, and trends
grep -i "error\|fail\|ok\|status" /path/to/logfile | tail -20
```

### 5. Examine Status/State Files
- Look for status files, checkpoints, or state indicators
- These often contain current operational state
- Common patterns: .status, .state, .pid files

### 6. Run Scripts to Observe Current Behavior
- Execute discovery scripts in safe mode first
- Observe output and any side effects
- Check if they produce expected results or errors

### 7. Correlate Information Across Sources
- Cross-reference timestamps between logs and status files
- Verify that script behavior matches log entries
- Look for consistency in reported states

### 8. Document Your Findings
- Create a summary of what you discovered
- Note any patterns, anomalies, or concerns
- Document the evidence trail you followed

## Key Insights from This Approach
- **Logs tell the real story**: Even when status files say "OK", logs may reveal intermittent issues
- **Scripts reveal intent**: Reading the actual monitoring script shows exactly what it's checking
- **Multiple evidence sources**: Combining script logic, log history, and current status gives complete picture
- **Pattern recognition**: Regular intervals in logs often reveal cron schedules or monitoring frequencies
- **Self-healing systems**: Many systems attempt automatic recovery - look for these patterns

## Verification
- Does the observed behavior match what the script claims to do?
- Are log timestamps consistent with expected frequencies?
- Do status changes in logs correlate with external events you know about?
- Can you reproduce the script's logic by tracing through the code?

## Common Pitfalls to Avoid
- Assuming current status file is always accurate (check logs for recency)
- Missing relevant files because search terms were too specific/not specific enough
- Not checking file permissions when scripts fail to read/write expected files
- Overlooking environment-specific paths in scripts
- Missing rotated or archived logs that contain older history

## Example Application: Brain Overseer Investigation\nIn investigating the brain overseer system:\n1. Started with known job ID from cron: `d39c727d6fa4`\n2. Searched for overseer-related files, found brain_overseer.sh\n3. Read the script to understand it checks heartbeat freshness every 2 minutes (max age 150 seconds)\n4. Examined brain_heartbeat.log to see failure/recovery patterns\n5. Checked brain_heartbeat.status for current state\n6. Ran the overseer script to observe current behavior\n7. Performed direct MCP connectivity test with `hermes mcp test brain`\n8. Correlated overseer log entries with heartbeat log to verify logic\n9. Discovered the system experiences intermittent failures but self-recovers\n10. Identified timing issue: overseer's 2.5-minute freshness check can false-positive when heartbeat execution and status file update have slight timing variance\n\nThis approach is particularly valuable for:\n- Understanding undocumented monitoring systems\n- Troubleshooting intermittent issues\n- Verifying that automated systems are working as intended\n- Investigating cron job behavior when direct observation isn't possible\n- Distinguishing genuine failures from timing artifacts in monitoring systems