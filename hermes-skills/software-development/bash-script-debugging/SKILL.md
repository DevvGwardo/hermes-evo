---
name: bash-script-debugging
description: Systematic approach to debugging bash scripts, focusing on common issues like syntax errors, quote escaping, variable scope, and environment differences.
category: software-development
---
# Bash Script Debugging

## Trigger Conditions
- Bash script fails with syntax errors like "local: can only be used in a function"
- Quote escaping issues causing unexpected behavior
- Script runs manually but fails when executed via cron or other automated systems
- Need to debug environment-specific issues in bash scripts

## Approach
1. **Isolate the problem** - Run the script directly to see error output
2. **Check syntax** - Use `bash -n script.sh` to check for syntax errors without execution
3. **Enable debugging** - Add `set -x` at top of script or run with `bash -x script.sh`
4. **Check variable scope** - Remember `local` only works inside functions
5. **Verify quote handling** - Ensure proper escaping, especially when dealing with timestamps and special characters
6. **Test in target environment** - If script runs via cron, test in similar environment (same user, PATH, etc.)
7. **Check permissions** - Ensure script is executable (`chmod +x script.sh`)
8. **Log output** - Redirect both stdout and stderr to log files for analysis

## Steps
1. Run script directly: `./script.sh` or `bash script.sh`
2. If syntax error: `bash -n script.sh` to locate issues
3. If runtime error: Add `set -x` or run with `bash -x script.sh` to trace execution
4. Check for common issues:
   - `local` used outside function scope
   - Incorrect quote escaping (especially in variable assignments like `TIMESTAMP=$(date +'%Y-%m-%d %H:%M:%S')`)
   - Missing shebang or incorrect interpreter path
   - PATH issues when running via cron
5. Fix issues iteratively:
   - Move `local` declarations inside functions only
   - Use single quotes for literal strings, double quotes when variable expansion needed
   - Ensure proper escaping of special characters
6. Test fix: Run script multiple times to ensure consistent behavior
7. Verify in target environment: Test via the actual trigger mechanism (cron, service, etc.)

## Pitfalls & Fixes
- **❌ "local: can only be used in a function"** → Only use `local` inside function definitions
- **❌ Quote escaping issues** → Use `TIMESTAMP=$(date +'%Y-%m-%d %H:%M:%S')` format, avoid unnecessary escaping
- **❌ Script works manually but not via cron** → Cron has minimal environment; use full paths, source profile if needed
- **❌ Silent failures** → Always redirect output: `./script.sh >> logfile 2>&1`
- **❌ Permission denied** → Ensure executable: `chmod +x script.sh`

## Verification
- Script runs without syntax errors: `bash -n script.sh` returns 0
- Script executes successfully manual test: `./script.sh`
- Script works in target environment: Test via actual trigger mechanism
- No unexpected output or errors in logs
- Exit code is 0 for successful execution

## Example Fix
From brain overseer script:
```bash
# Before (problematic)
TIMESTAMP=$(date +\"%Y-%m-%d %H:%M:%S\")  # Incorrect escaping
local last_status  # Outside function - causes error

# After (fixed)
TIMESTAMP=$(date +'%Y-%m-%d %H:%M:%S')   # Proper quoting
# Inside function only:
# local last_status=$(check_heartbeat_status)
```