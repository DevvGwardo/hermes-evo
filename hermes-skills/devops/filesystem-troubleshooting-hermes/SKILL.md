---
name: filesystem-troubleshooting-hermes
description: Troubleshooting filesystem access issues in Hermes environment where standard Python os functions fail but terminal/Hermes tools work
category: devops
---

# Filesystem Troubleshooting in Hermes Environment

## When to Use
When standard Python filesystem functions (os.path.exists, os.listdir, etc.) return unexpected results or fail to find files/directories that are visible via terminal commands.

## Symptoms
- os.path.exists() returns False for files/directories visible in `ls` output
- FileNotFoundError when trying to open files that terminal commands can access
- Inconsistent behavior between Python os functions and terminal/file tools

## Approach
1. **Verify with terminal first**: Use `terminal("ls -la <path>")` to confirm what's actually visible
2. **Use Hermes file tools**: When Python os functions fail, rely on:
   - `read_file()` for reading file contents
   - `search_files()` for finding files
   - `terminal()` for filesystem operations
3. **Check execution context**: Remember that the Hermes tools may have different filesystem access than standard Python functions
4. **Test file accessibility**: Try to read a file with `read_file()` before assuming it doesn't exist

## Why This Works
The Hermes agent operates in an environment where:
- Standard Python os functions may be restricted or operate in a different namespace
- Hermes-provided tools (read_file, terminal, search_files) have been configured with appropriate filesystem access
- These tools bypass certain restrictions or work through different access mechanisms

## Steps
1. When os.path.exists(path) returns False unexpectedly:
   ```python
   # Verify with terminal
   terminal_result = terminal(f"ls -la {path}")
   
   # If terminal shows the file/directory exists:
   # Use Hermes tools instead
   file_content = read_file(path)  # For files
   search_result = search_files("*", target="files", path=path)  # For directories
   ```

2. For checking if a file is readable:
   ```python
   try:
       content = read_file("path/to/file")
       # File is accessible via Hermes tools
   except Exception as e:
       # Handle the error appropriately
   ```

3. For directory listing when os.listdir fails:
   ```python
   # Use terminal or search_files
   terminal_result = terminal(f"ls -la {directory}")
   # OR
   search_result = search_files("*", target="files", path=directory)
   ```

## Verification
After using Hermes tools to access files/directories:
- Confirm you can read expected content
- Verify file operations work as needed
- Note that terminal commands provide the ground truth for what exists

## Important Notes
- This discrepancy appears to be environment-specific to the Hermes agent runtime
- The issue is not universal - some Python os functions may work correctly
- When in doubt, trust terminal output and Hermes file tools over os.path functions
- This approach has been validated for finding and executing scripts like show_agents.py when standard discovery methods fail