---
name: check-cron-job-status
description: Find and display the status of a specific cron job by its name from the Hermes cron jobs.json file.
category: devops
---
# Skill: Check Cron Job Status by Name
## Description
Find and display the status of a specific cron job by its name from the Hermes cron jobs.json file.

## When to Use
When you need to check the status, last run time, or configuration of a specific cron job in the Hermes system, particularly for brain monitoring jobs or other scheduled tasks.

## Step-by-Step

1. **Locate the cron jobs file**
   - Path: `~/.hermes/cron/jobs.json`
   - This file contains all scheduled cron jobs in JSON format

2. **Read and parse the JSON file**
   - Use `read_file` to get the contents
   - Parse the JSON to access the jobs array

3. **Find the target job by name**
   - Iterate through the jobs array
   - Match on the `name` field
   - Extract the job object when found

4. **Extract and display relevant information**
   - Key fields to report:
     - `name` and `id`
     - `last_run_at` (timestamp of last execution)
     - `last_status` (ok/error/etc)
     - `last_error` (if any)
     - `next_run_at` (when it's scheduled to run next)
     - `schedule.display` (cron expression or schedule)
     - `enabled` status
     - `state` (scheduled, paused, etc)

5. **Handle edge cases**
   - Job not found
   - Malformed JSON
   - Missing fields in job object
   - File access errors

## Example Usage
```python
# In execute_code or similar context
import json
import os
from pathlib import Path

def check_cron_job_status(job_name):
    cron_dir = Path.home() / ".hermes" / "cron"
    jobs_file = cron_dir / "jobs.json"
    
    try:
        with open(jobs_file, 'r') as f:
            data = json.load(f)
        
        for job in data.get("jobs", []):
            if job.get("name") == job_name:
                return {
                    "name": job["name"],
                    "id": job["id"],
                    "last_run": job.get("last_run_at", "Never"),
                    "status": job.get("last_status", "Unknown"),
                    "error": job.get("last_error", "None"),
                    "next_run": job.get("next_run_at", "None"),
                    "schedule": job["schedule"]["display"],
                    "enabled": job.get("enabled", False),
                    "state": job.get("state", "unknown")
                }
        return {"error": f"Job '{job_name}' not found"}
    except Exception as e:
        return {"error": f"Error reading cron jobs: {str(e)}"}
```

## Verification
- The skill should correctly identify the job by name
- Should return all relevant status fields
- Should handle missing jobs gracefully
- Should work with any valid cron job name in the system

## Related Skills
- brain-heartbeat-check: Specifically checks MCP/brain system health
- Could be extended to list all jobs or filter by status