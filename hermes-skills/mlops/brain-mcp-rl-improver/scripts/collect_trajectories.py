#!/usr/bin/env python3
"""
Brain MCP RL Trajectory Collector
Collects state-action-reward tuples during normal system operation
for later use in RL policy training.
"""

import json
import time
import subprocess
import os
from datetime import datetime
from pathlib import Path
import sys

def run_command(cmd):
    """Run a shell command and return output."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", "Timeout", 1
    except Exception as e:
        return "", str(e), 1

def get_brain_mcp_state():
    """Collect current brain MCP system state."""
    state = {}
    
    # Get brain MCP health status
    stdout, stderr, code = run_command("hermes mcp test brain")
    state["mcp_healthy"] = "✓ Connected" in stdout
    state["mcp_response_time"] = None
    if "response time" in stdout:
        try:
            # Extract response time like "(245ms)"
            import re
            match = re.search(r'\((\d+)ms\)', stdout)
            if match:
                state["mcp_response_time"] = int(match.group(1))
        except:
            pass
    
    # Get active sessions/agents
    stdout, stderr, code = run_command("/Users/devgwardo/.hermes/show_agents.sh")
    state["agent_display_output"] = stdout
    
    # Count active agents from display (simplified)
    state["active_agent_count"] = stdout.count("◆") + stdout.count("◇") 
    
    # Get recent tool usage (if available via logs)
    stdout, stderr, code = run_command("tail -20 /Users/devgwardo/.hermes/brain_heartbeat.log 2>/dev/null || echo 'No logs'")
    state["recent_heartbeat"] = stdout
    
    # System load
    stdout, stderr, code = run_command("uptime")
    state["system_load"] = stdout
    
    # Memory usage
    stdout, stderr, code = run_command("vm_stat 2>/dev/null | head -5 || echo 'Not available'")
    state["memory_info"] = stdout
    
    state["timestamp"] = datetime.now().isoformat()
    return state

def simulate_action_reward(state, action_taken):
    """
    Simulate reward based on action taken and resulting state.
    In a real implementation, this would observe actual outcomes.
    """
    reward_components = {
        "task_completion": 0.0,
        "resource_efficiency": 0.0,
        "latency": 0.0,
        "system_health": 0.0
    }
    
    # Base reward for taking any action
    reward_components["system_health"] = 1.0 if state.get("mcp_healthy", False) else -1.0
    
    # Reward for MCP responsiveness
    response_time = state.get("mcp_response_time")
    if response_time is not None:
        # Faster response = higher reward (inverse relationship, capped)
        latency_reward = max(0, 1.0 - (response_time / 1000.0))  # Normalize to ~1s max
        reward_components["latency"] = latency_reward
    
    # Reward for appropriate agent spawning (simplified heuristic)
    agent_count = state.get("active_agent_count", 0)
    if action_taken.get("action_type") == "spawn_agent":
        # Reward spawning when system is underutilized
        if agent_count < 2:  # Arbitrary threshold
            reward_components["task_completion"] = 0.5
        else:
            reward_components["task_completion"] = -0.2  # Penalty for over-spawning
    elif action_taken.get("action_type") == "no_op":
        # Reward doing nothing when system is busy
        if agent_count >= 3:
            reward_components["task_completion"] = 0.3
        else:
            reward_components["task_completion"] = -0.1
    
    # Resource efficiency: prefer fewer agents for same workload
    if agent_count > 0:
        reward_components["resource_efficiency"] = max(0, 1.0 - (agent_count / 5.0))  # Assume 5 is max reasonable
    
    # Total reward (weighted sum)
    total_reward = (
        0.3 * reward_components["task_completion"] +
        0.2 * reward_components["resource_efficiency"] +
        0.2 * reward_components["latency"] +
        0.3 * reward_components["system_health"]
    )
    
    return total_reward, reward_components

def collect_trajectory(duration_minutes=5):
    """Collect trajectories for specified duration."""
    print(f"Starting trajectory collection for {duration_minutes} minutes...")
    
    trajectories = []
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)
    
    last_state = get_brain_mcp_state()
    
    # Simple action space for demonstration
    action_types = ["spawn_agent_headless", "spawn_agent_tmux", "no_op", "monitor_only"]
    
    import random
    
    while time.time() < end_time:
        # In a real system, we'd observe actual actions taken
        # For this demo, we'll simulate decision making
        
        # Simple heuristic for action selection (to be replaced by RL policy)
        agent_count = last_state.get("active_agent_count", 0)
        if agent_count < 1 and random.random() < 0.3:
            action = {"action_type": "spawn_agent_headless", "details": {}}
        elif agent_count > 3 and random.random() < 0.2:
            action = {"action_type": "no_op", "details": {}}
        else:
            action = {"action_type": "monitor_only", "details": {}}
        
        # Simulate taking action and getting reward
        reward, reward_components = simulate_action_reward(last_state, action)
        
        # Record trajectory step
        trajectory_step = {
            "timestamp": datetime.now().isoformat(),
            "state": last_state,
            "action": action,
            "reward": reward,
            "reward_components": reward_components,
            "next_state": None  # Will be filled in next iteration
        }
        
        trajectories.append(trajectory_step)
        
        # Get next state
        time.sleep(30)  # Sample every 30 seconds
        new_state = get_brain_mcp_state()
        
        # Update previous step's next_state
        if trajectories:
            trajectories[-1]["next_state"] = new_state
        
        last_state = new_state
        
        print(f"Collected step {len(trajectories)} at {datetime.now().strftime('%H:%M:%S')} "
              f"- Agents: {last_state.get('active_agent_count', 0)}, "
              f"MCP Healthy: {last_state.get('mcp_healthy', False)}, "
              f"Reward: {reward:.3f}")
    
    print(f"Collection complete. Collected {len(trajectories)} trajectory steps.")
    return trajectories

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Collect brain MCP trajectories for RL training")
    parser.add_argument("--duration", type=int, default=5, help="Collection duration in minutes")
    parser.add_argument("--output", type=str, default=None, help="Output file path")
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path.home() / ".hermes" / "skills" / "brain-mcp-rl-improver" / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"trajectories_{timestamp}.json"
    else:
        output_file = Path(args.output)
    
    # Collect trajectories
    trajectories = collect_trajectory(args.duration)
    
    # Save to file
    with open(output_file, 'w') as f:
        json.dump(trajectories, f, indent=2, default=str)
    
    print(f"Trajectories saved to: {output_file}")
    print(f"File size: {output_file.stat().st_size / 1024:.1f} KB")

if __name__ == "__main__":
    main()