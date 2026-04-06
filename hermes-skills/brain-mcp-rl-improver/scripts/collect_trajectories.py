#!/usr/bin/env python3
"""
Brain MCP RL Trajectory Data Collector
Logs state-action-reward tuples during normal brain MCP operations for RL training.
"""

import json
import time
import argparse
import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path

def get_brain_mcp_status():
    """Get brain MCP system status."""
    try:
        # Try to get agent status using available tools
        result = subprocess.run([
            sys.executable, '-m', 'hermes', 'status'
        ], capture_output=True, text=True, timeout=10)
        return result.stdout if result.returncode == 0 else "status_check_failed"
    except Exception as e:
        return f"status_error: {str(e)}"

def get_system_state():
    """Collect current system state."""
    state = {
        "timestamp": datetime.now().isoformat(),
        "load_avg": os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0],
        "active_agents": 0,  # Would need to parse from brain MCP
        "queue_depth": 0,    # Would need to parse from brain MCP
        "mcp_status": get_brain_mcp_status()
    }
    return state

def record_action(action_type, action_details):
    """Record an action taken by the system."""
    return {
        "type": action_type,
        "details": action_details,
        "timestamp": datetime.now().isoformat()
    }

def calculate_reward(state_before, action, state_after):
    """Calculate immediate reward for state-action transition."""
    # Simple reward function - in practice this would be more sophisticated
    reward = 0.0
    
    # Reward for successful actions
    if action.get("type") == "spawn_agent" and action.get("details", {}).get("success"):
        reward += 1.0
    elif action.get("type") == "assign_task" and action.get("details", {}).get("success"):
        reward += 0.5
    
    # Penalty for errors or failures
    if "error" in str(state_after.get("mcp_status", "")):
        reward -= 1.0
        
    return reward

def main():
    parser = argparse.ArgumentParser(description="Collect brain MCP RL trajectory data")
    parser.add_argument("--duration", type=str, default="1h", 
                       help="Duration to collect data (e.g., 1h, 30m, 4h)")
    parser.add_argument("--output-dir", type=str, 
                       default="~/.hermes/skills/brain-mcp-rl-improver/data",
                       help="Directory to save trajectory files")
    
    args = parser.parse_args()
    
    # Parse duration
    duration_map = {"h": 3600, "m": 60, "s": 1}
    unit = args.duration[-1]
    value = int(args.duration[:-1]) if len(args.duration) > 1 else 1
    total_seconds = value * duration_map.get(unit, 60)
    
    output_dir = Path(os.path.expanduser(args.output_dir))
    output_dir.mkdir(parents=True, exist_ok=True)
    
    start_time = time.time()
    trajectory_data = []
    
    print(f"Starting trajectory collection for {args.duration}")
    print(f"Saving to: {output_dir}")
    
    last_state = get_system_state()
    
    try:
        while time.time() - start_time < total_seconds:
            # In a real implementation, we would monitor for actual actions
            # For now, we'll sample state periodically and infer actions
            
            time.sleep(30)  # Sample every 30 seconds
            
            current_state = get_system_state()
            
            # Infer action based on state changes (simplified)
            action = {
                "type": "monitor",
                "details": {
                    "sample_interval": 30,
                    "trigger": "periodic_check"
                }
            }
            
            reward = calculate_reward(last_state, action, current_state)
            
            # Record trajectory step
            trajectory_step = {
                "state": last_state,
                "action": action,
                "reward": reward,
                "next_state": current_state,
                "timestamp": datetime.now().isoformat()
            }
            
            trajectory_data.append(trajectory_step)
            last_state = current_state
            
            # Print progress every 5 minutes
            if len(trajectory_data) % 10 == 0:
                elapsed = time.time() - start_time
                remaining = total_seconds - elapsed
                print(f"Collected {len(trajectory_data)} steps, "
                      f"elapsed: {elapsed/60:.1f}m, remaining: {remaining/60:.1f}m")
    
    except KeyboardInterrupt:
        print("\nCollection interrupted by user")
    except Exception as e:
        print(f"Error during collection: {e}")
    finally:
        # Save trajectory data
        if trajectory_data:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = output_dir / f"trajectories_{timestamp}.json"
            
            with open(output_file, 'w') as f:
                json.dump({
                    "metadata": {
                        "collection_start": datetime.fromtimestamp(start_time).isoformat(),
                        "collection_end": datetime.now().isoformat(),
                        "total_steps": len(trajectory_data),
                        "duration_seconds": time.time() - start_time
                    },
                    "trajectories": trajectory_data
                }, f, indent=2)
            
            print(f"Saved {len(trajectory_data)} trajectory steps to {output_file}")
        else:
            print("No trajectory data collected")

if __name__ == "__main__":
    main()