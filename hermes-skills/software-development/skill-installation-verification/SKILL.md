---
name: skill-installation-verification
description: Verify Hermes skill installation completeness and troubleshoot missing components
category: software-development
version: 1.0.0
author: Hermes Agent
---

# Skill Installation Verification

A systematic approach to verify that Hermes skills are properly installed with all required components, and troubleshoot when skills appear registered but don't function as expected.

## Overview

Sometimes Hermes skills show up in `hermes skills list` but are missing critical components (scripts, templates, references) needed for execution. This skill provides a verification process to:
1. Confirm skill registration vs actual file presence
2. Check for expected directory structure and files
3. Validate that suggested usage patterns in documentation work
4. Identify common installation issues
5. Provide remediation steps

## Verification Process

### Step 1: Confirm Skill Registration
```bash
hermes skills list | grep <skill-name>
```
If the skill appears here but doesn't work, proceed to verification.

### Step 2: Check Skill Directory Structure
```bash
ls -la ~/.hermes/skills/<skill-name>/
```
Look for expected subdirectories mentioned in the skill documentation:
- `scripts/` - for executable components
- `templates/` - for configuration files
- `references/` - for documentation
- `data/` - for runtime data (may be created later)

### Step 3: Review Skill Documentation
```bash
hermes skill view <skill-name>
```
Check the "Files" section to see what components should be present.

### Step 4: Verify Expected Files Exist
Compare the file list from Step 2 with what's documented in Step 3.

### Step 5: Test Suggested Usage Patterns
Try the usage examples from the skill documentation, being prepared for:
- Command not found errors (indicating wrong command structure)
- Missing file/script errors
- Dependency issues

### Step 6: Check for Installation Scripts
Some skills may require explicit installation:
```bash
# Check if skill has install/update procedures
hermes skill view <skill-name> | grep -i install
```

## Common Issues Found

### Issue: Skill registered but directory nearly empty
- **Symptoms**: `hermes skills list` shows skill, but `~/.hermes/skills/<skill-name>/` contains only `.` and `..` or minimal files
- **Cause**: Skill registration succeeded but file deployment failed or was incomplete
- **Remediation**: 
  - Try reinstalling: `hermes skills install <skill-name>` (if available)
  - Check skill source for manual deployment
  - Look for bundled skill files in `~/.hermes/.hub/`

### Issue: Documentation suggests invalid commands
- **Symptoms**: Following usage examples results in "invalid choice" or "command not found" errors
- **Cause**: Documentation outdated or assumes different Hermes version/context
- **Remediation**:
  - Check actual available commands: `hermes --help`
  - Look for skill-specific commands in documentation
  - Verify if skill provides CLI commands vs needs to be invoked differently

### Issue: Missing dependencies
- **Symptoms**: Scripts fail with import errors or missing module messages
- **Cause**: Skill dependencies not installed
- **Remediation**:
  - Check skill documentation for installation requirements
  - Look for `pip install` or other dependency commands in SKILL.md
  - Install missing dependencies manually if needed

## Troubleshooting Commands

### List all skill directories
```bash
ls ~/.hermes/skills/
```

### Check skill source location
```bash
# For locally installed skills
ls ~/.hermes/skills/<skill-name>/

# For hub-installed skills  
ls ~/.hermes/skills/.hub/
```

### Verify skill metadata
```bash
hermes skill view <skill-name>
```

### Check for skill-specific CLI commands
Some skills add their own slash commands - check if they're available:
```bash
hermes  # Then tab complete to see available commands
```

## Remediation Approaches

### Reinstall the Skill
If the skill installation appears corrupted:
```bash
# Remove incomplete installation
rm -rf ~/.hermes/skills/<skill-name>/

# Reinstall (method depends on skill source)
# For local skills: may need to copy files manually
# For hub skills: hermes skills install <skill-name>
```

### Manual Component Deployment
If you have access to the skill source:
```bash
# Create missing directories
mkdir -p ~/.hermes/skills/<skill-name>/scripts
mkdir -p ~/.hermes/skills/<skill-name>/templates
mkdir -p ~/.hermes/skills/<skill-name>/references

# Copy required files from source
cp /path/to/skill/scripts/* ~/.hermes/skills/<skill-name>/scripts/
cp /path/to/skill/templates/* ~/.hermes/skills/<skill-name>/templates/
# etc.
```

### Validate Against Skill Source
Compare installed files with the skill's source repository:
```bash
# If skill is from git repo
diff -r ~/.hermes/skills/<skill-name>/ /path/to/skill/source/
```

## Prevention Tips

1. **After skill installation**, always verify directory structure before relying on it
2. **Check skill documentation** for any special installation steps beyond basic registration
3. **Test basic functionality** immediately after installation, not just when needed
4. **Watch for error messages** during installation that might indicate partial failures
5. **Consider creating a test trajectory/data file** to verify read/write permissions in skill directories

## Integration with Other Tools

This verification process works well with:
- `systematic-debugging` - for deeper troubleshooting when verification fails
- `internal-tool-discovery` - to understand what tools a skill should provide
- `mcp-health-check` - if the skill relates to MCP functionality
- `brain-heartbeat-check` - for skills affecting system monitoring

## Example Application

When troubleshooting the brain-mcp-rl-improver skill:
1. `hermes skills list` showed it as installed
2. `ls ~/.hermes/skills/brain-mcp-rl-improver/` revealed only a `data` directory with one trajectory file
3. `hermes skill view brain-mcp-rl-improver` documented missing `scripts/`, `templates/`, `references/` directories
4. Attempting `hermes run brain-mcp-rl-improver train` failed with invalid command error
5. Verified brain MCP connectivity was healthy via `hermes mcp test brain`
6. Checked cron job logs to see training failures due to missing components
7. Confirmed skill was incompletely installed and needed component deployment

**Key findings from this case:**
- Skills can be registered but missing executable components
- Cron jobs will fail silently if skill components are absent
- Always verify skill directory structure matches documentation
- Check both skill registration and actual file presence
- Look for skill-specific installation procedures in documentation

This approach saved time by quickly identifying the root cause as incomplete skill deployment rather than assuming user error, system issues, or MCP connectivity problems.