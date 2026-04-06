---
name: missing-script-investigation
description: Systematic approach to locate and run missing scripts or tools in a codebase when expected executables are not found. Use when a script/tool is referenced but not present, requiring methodical search and verification.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [investigation, troubleshooting, debugging, scripts, tools]
    related_skills: [systematic-debugging, agentic-coder]
---

# Missing Script Investigation

## Overview

When a script or tool is expected to exist (based on documentation, skills, or references) but cannot be found, random searching wastes time. This skill provides a systematic approach to locate missing executables, verify their purpose, and safely attempt to run them.

**Core principle:** Methodically search likely locations, gather evidence before execution, and verify safety before running unknown scripts.

## When to Use

- Documentation references a script that doesn't exist
- A skill mentions a tool that's not present
- Expected executables are missing from standard locations
- You need to verify if a script is safe to run before execution
- Searching for monitoring, maintenance, or utility scripts

## The Investigation Process

### Phase 1: Verify Expectations

**Before searching, confirm what you're looking for:**

1. **Check the source reference**
   - Where was the script mentioned? (documentation, skill, conversation)
   - What exact name or pattern was given?
   - What was it supposed to do?

2. **Check your current context**
   - Are you in the right repository/codebase?
   - Is the environment properly set up?
   - Are you looking for a user-installed vs system-wide tool?

**Actions:**
- Use `read_file` to check the original reference
- Use `terminal` to check current directory and environment
- Confirm expected script name and purpose

### Phase 2: Systematic Location Search

**Search in order of likelihood:**

1. **Check skill-specific locations first**
   - If mentioned in a specific skill (e.g., devops), check those directories
   - Common skill locations: `skill-name/`, `tools/`, `scripts/`, `bin/`

2. **Check standard executable locations**
   - `bin/`, `scripts/`, `tools/`, `cmd/`
   - `./script_name`, `./bin/script_name`

3. **Check language-specific locations**
   - Python: `scripts/`, `tools/`, `bin/`, project root
   - Node.js: `bin/` in package.json
   - Ruby: `bin/`, `script/`

4. **Expand search broadly**
   - Use `search_files` for filename patterns
   - Use `rglob` in execute_code for thorough search
   - Skip hidden directories, build artifacts, node_modules, etc.

**Actions:**
- Use `search_files(target="files", pattern="*overseer*")`
- Use `search_files(target="files", pattern="*monitor*")`
- Check directories: `cron/`, `gateway/platforms/`, `environments/`, `devops/`, `tools/`, `agent/`, `hermes_cli/`
- Use execute_code with Python's rglob for deep search

### Phase 3: Evidence Gathering

**Before running any found script, gather evidence:**

1. **Examine the script content**
   - What does it do? Is it safe to run?
   - Does it require arguments or specific environment?
   - Does it have dependencies?

2. **Check file properties**
   - Is it executable? (check permissions)
   - What type of file is it? (shell, Python, binary)
   - Size and modification time

3. **Look for documentation or comments**
   - Usage instructions
   - Safety warnings
   - Required parameters

**Actions:**
- Use `read_file` to examine script contents
- Use `terminal` to check file permissions (`ls -la`)
- Use `execute_code` to check file type and properties
- Look for shebangs, comments, usage patterns

### Phase 4: Safe Execution Attempt

**If a script is found and appears safe to run:**

1. **Prepare the environment**
   - Ensure you're in the correct working directory
   - Set any required environment variables
   - Make backup of important state if needed

2. **Make executable if needed**
   - Only change permissions if it's a script file (.sh, .py, no extension)
   - Never make binary files executable unless verified

3. **Run with appropriate interpreter**
   - `.py` files: `python3 script.py`
   - `.sh` files: `bash script.sh`
   - No extension: try direct execution or detect type

4. **Run with safety measures**
   - Use timeout to prevent hanging
   - Capture stdout/stderr for analysis
   - Run in controlled environment if possible

**Actions:**
- Use `execute_code` to make file executable: `os.chmod(script, 0o755)`
- Use `subprocess.run()` with timeout and capture_output
- Check return code and output for success/failure
- Never run as root or with elevated privileges unnecessarily

### Phase 5: Result Analysis

**After attempting to run:**

1. **Check exit code**
   - 0 = success
   - Non-zero = failure (check stderr for clues)

2. **Examine output**
   - Did it produce expected results?
   - Did it show usage/help when run incorrectly?
   - Did it error due to missing dependencies?

3. **Decide next steps**
   - If success: task complete
   - If failure due to missing deps: install dependencies or adjust approach
   - If failure due to misuse: try with correct arguments
   - If not found: consider if script should exist or if alternative approach needed

## Red Flags — STOP and Re-evaluate

If you encounter these situations:

1. **Script asks for sensitive information** (passwords, keys, etc.)
2. **Script tries to modify system files outside project scope**
3. **Script requires unclear or dangerous privileges**
4. **Multiple similar scripts with conflicting purposes**
5. **Script is obfuscated or minified without clear source**
6. **Execution hangs or consumes excessive resources**

**Action:** Stop execution, gather more information, consider if the script should be run at all.

## Hermes Agent Integration

### Tool Usage During Investigation

- **`search_files`** — Find files by name pattern
- **`read_file`** — Examine script contents safely
- **`execute_code`** — Run Python search scripts, check file properties
- **`terminal`** — Check permissions, run scripts with proper shells
- **`patch`** — Only if you need to fix a script (after investigation)

### With delegate_task

For complex searches across large codebases:

```python
delegate_task(
    goal="Search for [script_name] in the codebase and report findings",
    context="""Follow missing-script-investigation skill:
    1. Search likely locations: bin/, scripts/, tools/, skill-specific dirs
    2. Examine any found scripts for content and safety
    3. Report location, file type, and content summary
    4. DO NOT attempt to run without explicit permission
    
    Expected script: [name or pattern]
    Known references: [where it was mentioned]
    """,
    toolsets=['terminal', 'file']
)
```

## Verification Steps

After investigation, confirm:

- [ ] Searched all likely locations systematically
- [ ] Examined contents of any found scripts
- [ ] Verified file type and permissions before execution
- [ ] Used appropriate interpreter for script type
- [ ] Ran with timeout and captured output
- [ ] Analyzed results to determine success/failure
- [ ] Documented findings for future reference

## Real-World Application

This approach has been used to:
- Locate monitoring scripts in distributed systems
- Find maintenance utilities in microservice architectures
- Discover deployment tools in DevOps repositories
- Verify safety of mysterious scripts before execution
- Document missing tools for issue reporting

**Systematic investigation beats random guessing every time.**