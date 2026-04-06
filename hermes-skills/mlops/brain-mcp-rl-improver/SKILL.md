---
name: brain-mcp-rl-improver
description: Apply reinforcement learning to improve brain MCP system performance through automated overnight training cycles
category: mlops
version: 1.0.0
author: Hermes Agent
---

# Brain MCP RL Improver

A skill for applying reinforcement learning to improve brain MCP system performance through automated overnight training cycles.

## Overview

This skill implements a continuous improvement loop for the brain MCP multi-agent system, incorporating lessons learned from system troubleshooting:
1. **Daytime Data Collection**: Trajectory logging of agent spawning, task routing, and state management decisions
2. **Overnight Training**: RL policy optimization using collected trajectories  
3. **Deployment & Evaluation**: A/B testing of improved policies against baseline heuristics
4. **System Health Integration**: Leverages verified direct MCP client connections for reliable tool access when Hermes MCP CLI limitations are encountered

## Components

### Data Collector (`collect_trajectories.py`)
Logs state-action-reward tuples during normal brain MCP operations:
- System state (load, active agents, queue depth)
- Actions taken (spawn agent, assign task, manage shared state)
- Immediate rewards (task completion, latency, resource usage)
- Long-term rewards (system health, conflict reduction)

### Policy Trainer (`train_policy.py`)
Uses TRL/GRPO to optimize policies:
- Input: Collected trajectories
- Output: Improved spawning/routing policies
- Algorithms: PPO for spawning policy, GRPO for task routing

### Policy Deployer (`deploy_policy.py`)
Safely rolls out improved policies:
- A/B testing framework
- Performance monitoring
- Rollback on degradation

### Evaluator (`evaluate_improvement.py`)
Measures impact of policy changes:
- Before/after comparison
- Statistical significance testing
- Alert on significant improvements/degradations

## Installation

1. Install required dependencies:
   ```bash
   pip install trl peft transformers datasets accelerate
   ```

2. Ensure brain MCP is accessible and healthy

3. Deploy the skill components to `~/.hermes/skills/brain-mcp-rl-improver/`

## Usage

### Manual Operation
```bash
# Collect trajectories during peak usage
hermes run brain-mcp-rl-improver collect --duration 4h

# Train policies overnight
hermes run brain-mcp-rl-improver train --timesteps 100000

# Evaluate improvements
hermes run brain-mcp-rl-improver evaluate
```

### Automated Cron Jobs
The skill sets up three cron jobs:
1. **Data Collection** (every 4 hours during active periods)
2. **Policy Training** (2:00 AM daily - optimal low-usage time)
3. **Evaluation & Deployment** (4:00 AM daily)

## Files

- `SKILL.md` - This file
- `scripts/collect_trajectories.py` - Daytime data collection
- `scripts/train_policy.py` - Overnight RL training
- `scripts/deploy_policy.py` - Safe policy deployment
- `scripts/evaluate_improvement.py` - Impact measurement
- `templates/policy_config.yaml` - Policy hyperparameters
- `references/rl_approach.md` - Detailed methodology

## Safety Features

- **Conservative Updates**: Small policy changes, gradual rollout
- **Performance Guards**: Automatic rollback if metrics degrade
- **Fallback Policies**: Always maintains working baseline
- **Audit Logging**: Full trace of all policy changes
- **Human Oversight**: Requires approval for major changes

## Troubleshooting & Lessons Learned

Based on practical implementation experience:

1. **MCP Connectivity Verification**: Always verify brain MCP connectivity before assuming it works. Node.js module mismatches (like better_sqlite3 version issues) can be resolved with `npm rebuild` in the brain-mcp directory.

2. **Sandbox Execution Limitations**: Direct terminal execution in Hermes sandbox environments may encounter TTY/issues. File-based approaches and script verification are often more reliable than relying on terminal output alone.

3. **Cron Job Management**: Use `hermes cron list` rather than standalone `cronjob` commands for reliable cron job inspection and management within the Hermes environment.

4. **Layered Verification Approach**: When troubleshooting, verify in this order:
   - Brain MCP connectivity (`hermes mcp test brain`)
   - Status display functionality (`/Users/devgwardo/.hermes/show_agents.sh`)
   - Monitoring system logs (heartbeat and overseer)
   - Skill component verification
   - Cron job scheduling status

5. **System Priming**: Initialize the RL pipeline with an initial trajectory file to ensure data directories are populated before the first scheduled collection runs.

6. **File-Based Verification**: When direct MCP tool access is challenging, verify agent spawning success through detectable file creation in `/tmp` (specifically `/tmp/agent_demo_*.txt` files for status display integration).

7. **Heartbeat Log Interpretation**: Heartbeat logs may show status information embedded within status display output. Check logs directly for definitive HEARTBEAT_OK/HEARTBEAT_FAIL status.

8. **Overseer Recovery Procedures**: The brain overseer automatically attempts recovery when heartbeats fail, which can be seen in overseer logs as "OVERSEER RECOVERY_ATTEMPT" followed by recovery procedures.

## Optimal Timing

Based on typical usage patterns:
- **Data Collection**: 9 AM - 9 PM (active hours)
- **Policy Training**: 2:00 AM - 4:00 AM (lowest system usage)
- **Evaluation**: 4:00 AM - 5:00 AM (post-training validation)

This ensures training doesn't interfere with production workloads while leveraging overnight idle time for computation.

## Integration Points

- Uses existing brain MCP health monitoring (heartbeat/overseer)
- Leverages Hermes agent spawning capabilities
- Integrates with status display for visibility
- Compatible with current cron job infrastructure