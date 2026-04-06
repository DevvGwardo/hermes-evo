#!/usr/bin/env python3
"""
Brain MCP RL Policy Trainer
Trains reinforcement learning policies using collected trajectories.
"""

import json
import os
import torch
import numpy as np
from pathlib import Path
from datetime import datetime
import argparse
import sys

def load_trajectories(data_dir):
    """Load all trajectory files from data directory."""
    trajectories = []
    data_path = Path(data_dir)
    
    if not data_path.exists():
        print(f"No data directory found at {data_path}")
        return trajectories
    
    trajectory_files = list(data_path.glob("trajectories_*.json"))
    print(f"Found {len(trajectory_files)} trajectory files")
    
    for file_path in trajectory_files:
        try:
            with open(file_path, 'r') as f:
                file_trajectories = json.load(f)
                trajectories.extend(file_trajectories)
                print(f"Loaded {len(file_trajectories)} trajectories from {file_path.name}")
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
    
    return trajectories

def preprocess_trajectories(trajectories):
    """Convert trajectories to training format."""
    print(f"Preprocessing {len(trajectories)} trajectory steps...")
    
    # For simplicity, we'll create a basic state-action-reward dataset
    # In a full implementation, you'd use proper RL libraries like TRL
    
    processed_data = []
    
    for step in trajectories:
        state = step.get("state", {})
        action = step.get("action", {})
        reward = step.get("reward", 0.0)
        
        # Extract features from state (simplified)
        features = {
            "mcp_healthy": float(state.get("mcp_healthy", False)),
            "mcp_response_time": state.get("mcp_response_time", 1000) / 1000.0,  # Normalize to seconds
            "active_agent_count": min(state.get("active_agent_count", 0) / 5.0, 1.0),  # Normalize to 0-1
            "system_load_indicator": 0.5,  # Placeholder - would parse uptime output
            "time_of_day": (datetime.now().hour / 24.0),  # Cyclical feature
        }
        
        # Action encoding (simplified)
        action_type = action.get("action_type", "no_op")
        action_encoded = {
            "spawn_agent_headless": [1.0, 0.0, 0.0, 0.0],
            "spawn_agent_tmux": [0.0, 1.0, 0.0, 0.0],
            "no_op": [0.0, 0.0, 1.0, 0.0],
            "monitor_only": [0.0, 0.0, 0.0, 1.0]
        }.get(action_type, [0.0, 0.0, 0.0, 1.0])  # Default to monitor_only
        
        processed_data.append({
            "state_features": list(features.values()),
            "action": action_encoded,
            "reward": reward,
            "reward_components": step.get("reward_components", {}),
            "feature_names": list(features.keys())
        })
    
    return processed_data

def train_simple_policy(processed_data, output_dir):
    """Train a simple policy network (placeholder for full RL implementation)."""
    print("Training simple policy network...")
    
    if len(processed_data) < 10:
        print("Insufficient data for training. Need at least 10 samples.")
        return False
    
    # Prepare data
    states = torch.FloatTensor([item["state_features"] for item in processed_data])
    actions = torch.FloatTensor([item["action"] for item in processed_data])
    rewards = torch.FloatTensor([item["reward"] for item in processed_data])
    
    # Simple neural network policy (for demonstration)
    input_dim = states.shape[1]
    hidden_dim = 64
    output_dim = actions.shape[1]  # 4 action types
    
    policy_net = torch.nn.Sequential(
        torch.nn.Linear(input_dim, hidden_dim),
        torch.nn.ReLU(),
        torch.nn.Linear(hidden_dim, hidden_dim),
        torch.nn.ReLU(),
        torch.nn.Linear(hidden_dim, output_dim),
        torch.nn.Softmax(dim=-1)
    )
    
    optimizer = torch.optim.Adam(policy_net.parameters(), lr=0.001)
    loss_fn = torch.nn.MSELoss()
    
    # Training loop
    epochs = 100
    batch_size = min(32, len(processed_data))
    
    print(f"Training for {epochs} epochs with batch size {batch_size}")
    
    for epoch in range(epochs):
        # Shuffle data
        indices = torch.randperm(len(states))
        states_shuffled = states[indices]
        actions_shuffled = actions[indices]
        rewards_shuffled = rewards[indices]
        
        epoch_loss = 0.0
        num_batches = 0
        
        for i in range(0, len(states), batch_size):
            batch_states = states_shuffled[i:i+batch_size]
            batch_actions = actions_shuffled[i:i+batch_size]
            batch_rewards = rewards_shuffled[i:i+batch_size]
            
            # Predict action probabilities
            pred_actions = policy_net(batch_states)
            
            # Loss: encourage high probability on actions that led to high rewards
            # Weighted MSE where weights are normalized rewards
            reward_weights = (batch_rewards - batch_rewards.min()) / (batch_rewards.max() - batch_rewards.min() + 1e-8)
            reward_weights = reward_weights.unsqueeze(1)  # Shape: [batch_size, 1]
            
            loss = loss_fn(pred_actions * reward_weights, batch_actions * reward_weights)
            
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            epoch_loss += loss.item()
            num_batches += 1
        
        if epoch % 20 == 0:
            avg_loss = epoch_loss / max(num_batches, 1)
            print(f"Epoch {epoch}/{epochs}, Average Loss: {avg_loss:.4f}")
    
    # Save policy
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    policy_path = output_dir / "policy_network.pt"
    torch.save({
        'policy_net_state_dict': policy_net.state_dict(),
        'optimizer_state_dict': optimizer.state_dict(),
        'feature_names': processed_data[0]['feature_names'] if processed_data else [],
        'training_samples': len(processed_data),
        'training_date': datetime.now().isoformat()
    }, policy_path)
    
    print(f"Policy saved to: {policy_path}")
    
    # Also save as TorchScript for easier deployment
    try:
        example_input = torch.randn(1, len(processed_data[0]['state_features']))
        traced_script_module = torch.jit.trace(policy_net, example_input)
        torchscript_path = output_dir / "policy_network_traced.pt"
        traced_script_module.save(torchscript_path)
        print(f"TorchScript policy saved to: {torchscript_path}")
    except Exception as e:
        print(f"Could not create TorchScript version: {e}")
    
    return True

def main():
    parser = argparse.ArgumentParser(description="Train brain MCP RL policy")
    parser.add_argument("--data-dir", type=str, default=None, help="Directory containing trajectory data")
    parser.add_argument("--output-dir", type=str, default=None, help="Directory to save trained policy")
    parser.add_argument("--timesteps", type=int, default=10000, help="Number of training timesteps (for compatibility)")
    
    args = parser.parse_args()
    
    # Set default directories
    home = Path.home()
    if args.data_dir is None:
        args.data_dir = home / ".hermes" / "skills" / "brain-mcp-rl-improver" / "data"
    if args.output_dir is None:
        args.output_dir = home / ".hermes" / "skills" / "brain-mcp-rl-improver" / "models"
    
    print("Brain MCP RL Policy Trainer")
    print("=" * 40)
    print(f"Data directory: {args.data_dir}")
    print(f"Output directory: {args.output_dir}")
    print(f"Timesteps: {args.timesteps}")
    print()
    
    # Load trajectories
    trajectories = load_trajectories(args.data_dir)
    
    if len(trajectories) == 0:
        print("No trajectory data found. Please run data collection first.")
        return 1
    
    # Preprocess data
    processed_data = preprocess_trajectories(trajectories)
    
    # Train policy
    success = train_simple_policy(processed_data, args.output_dir)
    
    if success:
        print("\nTraining completed successfully!")
        print(f"Policy saved to: {args.output_dir}")
        return 0
    else:
        print("\nTraining failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())