---
name: github-readme-extraction
description: Extract README content from GitHub repositories when standard navigation methods fail or are inefficient
category: github
---

# GitHub README Extraction Skill

## Description
Extract README content from GitHub repositories when standard navigation methods fail or are inefficient. Handles browser setup issues and provides fallbacks for content extraction.

## When to Use
- You need to extract README content from a GitHub repository
- Standard browser navigation or clicking on README links in snapshots fails
- You encounter browser setup issues (missing Playwright browsers)
- You want a reliable method to get README content for analysis

## Prerequisites
- Playwright installed (npx playwright install may be needed)
- Access to browser tools

## Steps

### 1. Handle Browser Setup
```bash
# Check if Playwright browsers are installed, install if needed
npx playwright install
```
*Note: If you see warnings about missing dependencies, run:*
```bash
npm install @playwright/test
npx playwright install
```

### 2. Navigate to Repository
```python
# Navigate to the GitHub repo
browser_navigate({"url": "https://github.com/[owner]/[repo]"})
```

### 3. Attempt Standard Extraction
Try to extract README content by:
- Taking a snapshot of the page
- Looking for README.md links in the file tree
- Attempting to click on README links

### 4. Fallback to Raw README (if standard method fails)
If clicking on README links doesn't work (element not found/visible or content extraction fails):
```python
# Extract owner and repo from URL or use known values
# Navigate directly to raw README
browser_navigate({"url": "https://raw.githubusercontent.com/[owner]/[repo]/[branch]/README.md"})
# Default branch is usually 'main' or 'master'
```

### 5. Extract and Process Content
Once you have the raw README:
- Use browser_snapshot() to get the text content
- Parse the content for needed information (use cases, installation, etc.)
- Extract key sections using pattern matching or manual review

## Example Workflow
```python
# 1. Install browsers if needed
terminal({"command": "npx playwright install"})

# 2. Navigate to repo
browser_navigate({"url": "https://github.com/DevvGwardo/hermes-agent-panel"})

# 3. Try standard method first
snapshot = browser_snapshot({})
# Look for README link and try to click...

# 4. If that fails, use fallback
browser_navigate({"url": "https://raw.githubusercontent.com/DevvGwardo/hermes-agent-panel/main/README.md"})

# 5. Get content
content_snapshot = browser_snapshot({full=True})
# Process content_snapshot to extract needed info
```

## Common Issues and Solutions

### Issue: "Executable doesn't exist" error from Playwright
**Solution:** Run `npx playwright install` to download missing browsers

### Issue: Element not found or not visible when clicking README links
**Solution:** Fallback to raw README URL approach

### Issue: Need specific branch other than main/master
**Solution:** Check the repo's branch page or try common branch names:
- main
- master
- develop
- dev

### Issue: Large README causing truncation
**Solution:** Use browser_snapshot with full=True or read specific sections

## Verification
- Confirm you have the complete README content
- Check that key sections (installation, usage, examples) are present
- Verify API key setup instructions if relevant
- Ensure code examples are extractable

## Tips
- Always try the standard method first (faster if it works)
- Keep the fallback raw README approach in mind
- For frequent use, consider creating a helper function that combines these steps
- Remember to URL-encode owner/repo names if they contain special characters