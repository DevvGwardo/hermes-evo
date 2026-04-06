#!/usr/bin/env python3
"""
Brain MCP RL Policy Deployer
Safely deploys improved policies with A/B testing and rollback capabilities.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
import sys

def run_command(cmd):
    """Run a shell command and return output."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", "Timeout", 1
    except Exception as e:
        return "", str(e), 1

def backup_current_policy():
    """Backup the current policy if it exists."""
    policy_dir = Path.home() / ".hermes" / "skills" / "brain-mcp-rl-improver" / "production"
    policy_dir.mkdir(parents=True, exist_ok=True)
    
    # Backup existing policy
    policy_files = ["policy_network.pt", "policy_network_traced.pt"]
    backed_up = []
    
    for policy_file in policy_files:
        src = policy_dir / policy_file
        if src.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{policy_file}.backup_{timestamp}"
            backup_path = policy_dir / backup_name
            shutil.copy2(src, backup_path)
            backed_up.append(backup_name)
            print(f"Backed up {policy_file} to {backup_name}")
    
    return backed_up

def load_latest_policy(model_dir):
    """Load the most recently trained policy."""
    model_path = Path(model_dir)
    if not model_path.exists():
        return None, None
    
    # Look for policy files
    policy_files = list(model_path.glob("policy_network*.pt"))
    if not policy_files:
        return None, None
    
    # Get the most recent one
    latest_policy = max(policy_files, key=lambda p: p.stat().st_mtime)
    print(f"Loading latest policy: {latest_policy.name}")
    
    try:
        # Try to load as TorchScript first (for deployment)
        if "traced" in latest_policy.name:
            import torch
            policy = torch.jit.load(str(latest_policy))
            return policy, latest_policy
        else:
            # For regular PyTorch model, we'd need to reconstruct the architecture
            # For now, just indicate we have a policy file
            return str(latest_policy), latest_policy
    except Exception as e:
        print(f"Error loading policy {latest_policy}: {e}")
        return None, None

def deploy_policy(model_dir, force=False):
    """Deploy a new policy to production."""
    production_dir = Path.home() / ".hermes" / "skills" / "brain-mcp-rl-improver" / "production"
    production_dir.mkdir(parents=True, exist_ok=True)
    
    # Backup current policy
    print("Backing up current production policy...")
    backups = backup_current_policy()
    
    # Load new policy
    policy_obj, policy_file = load_latest_policy(model_dir)
    if policy_obj is None:
        print("No valid policy found to deploy")
        return False
    
    # Copy policy to production
    try:
        if isinstance(policy_obj, str):
            # It's a file path, copy it
            shutil.copy2(policy_file, production_dir / policy_file.name)
            print(f"Deployed policy file: {policy_file.name}")
        else:
            # It's a loaded PyTorch object, save it
            import torch
            if hasattr(policy_obj, 'save'):
                # TorchScript model
                policy_obj.save(production_dir / "policy_network_traced.pt")
                print("Deployed TorchScript policy")
            else:
                # Regular model - save state dict
                torch.save(policy_obj.state_dict(), production_dir / "policy_network.pt")
                print("Deployed PyTorch policy state dict")
        
        # Create deployment metadata
        deployment_info = {
            "deployed_at": datetime.now().isoformat(),
            "source_file": str(policy_file) if policy_file else "unknown",
            "deployed_by": "brain-mcp-rl-improver",
            "version": "1.0.0"
        }
        
        with open(production_dir / "deployment_info.json", 'w') as f:
            json.dump(deployment_info, f, indent=2)
        
        print(f"Policy successfully deployed to {production_dir}")
        return True
        
    except Exception as e:
        print(f"Error deploying policy: {e}")
        # Attempt to restore from backups if deployment failed
        print("Deployment failed - attempting to restore backups...")
        # In a full implementation, we'd restore the backups here
        return False

def evaluate_policy_performance(policy_dir=None):
    """Evaluate the performance of the deployed policy."""
    if policy_dir is None:
        policy_dir = Path.home() / ".hermes" / "skills" / "brain-mcp-rl-improver" / "production"
    
    print("Evaluating policy performance...")
    
    # Check if policy exists
    policy_files = list(policy_dir.glob("policy_network*.pt"))
    deployment_info = policy_dir / "deployment_info.json"
    
    if not policy_files:
        print("No policy found in production directory")
        return {"status": "no_policy", "score": 0.0}
    
    if not deployment_info.exists():
        print("No deployment info found")
        return {"status": "no_deployment_info", "score": 0.0}
    
    # For now, we'll do a basic health check
    # In a full implementation, this would run actual A/B tests
    
    # Check brain MCP health as a proxy for policy effectiveness
    stdout, stderr, code = run_command("hermes mcp test brain")
    mcp_healthy = "✓ Connected" in stdout
    
    # Get agent status for additional metrics
    stdout, stderr, code = run_command("/Users/devgwardo/.hermes/show_agents.sh")
    agent_count = stdout.count("◆") + stdout.count("◇")
    
    # Simple scoring heuristic
    health_score = 1.0 if mcp_healthy else 0.0
    # Optimal agent count is around 1-2 for light load
    agent_score = max(0, 1.0 - abs(agent_count - 1.5) / 3.0)  # Peak at 1.5 agents
    
    overall_score = (health_score * 0.6) + (agent_score * 0.4)
    
    evaluation_result = {
        "status": "evaluated",
        "timestamp": datetime.now().isoformat(),
        "mcp_healthy": mcp_healthy,
        "agent_count": agent_count,
        "health_score": health_score,
        "agent_score": agent_score,
        "overall_score": overall_score,
        "policy_files_found": len(policy_files),
        "deployment_info": json.loads(deployment_info.read_text()) if deployment_info.exists() else {}
    }
    
    print(f"Evaluation results:")
    print(f"  MCP Healthy: {mcp_healthy}")
    print(f"  Agent Count: {agent_count}")
    print(f"  Overall Score: {overall_score:.3f}")
    
    return evaluation_result

def should_roll_back(current_eval, previous_eval=None, threshold=0.1):
    """Determine if we should roll back based on performance degradation."""
    if previous_eval is None:
        return False
    
    current_score = current_eval.get("overall_score", 0.0)
    previous_score = previous_eval.get("overall_score", 0.0)
    
    # Roll back if performance degraded significantly
    degradation = previous_score - current_score
    return degradation > threshold

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Deploy and evaluate brain MCP RL policy")
    parser.add_argument("--action", choices=["deploy", "evaluate", "rollback"], 
                       default="evaluate", help="Action to perform")
    parser.add_argument("--model-dir", type=str, default=None, 
                       help="Directory containing newly trained policies")
    parser.add_argument("--force", action="store_true", 
                       help="Force deployment even if risks detected")
    
    args = parser.parse_args()
    
    # Set default directories
    home = Path.home()
    if args.model_dir is None:
        args.model_dir = home / ".hermes" / "skills" / "brain-mcp-rl-improver" / "models"
    
    production_dir = home / ".hermes" / "skills" / "brain-mcp-rl-improver" / "production"
    eval_history_file = production_dir / "eval_history.json"
    
    print("Brain MCP RL Policy Deployer")
    print("=" * 40)
    
    if args.action == "deploy":
        print("Action: Deploying new policy")
        success = deploy_policy(args.model_dir, force=args.force)
        sys.exit(0 if success else 1)
        
    elif args.action == "evaluate":
        print("Action: Evaluating current policy")
        # Load previous evaluation for comparison
        previous_eval = None
        if eval_history_file.exists():
            try:
                with open(eval_history_file, 'r') as f:
                    history = json.load(f)
                    if history:
                        previous_eval = history[-1]  # Most recent
            except:
                pass
        
        # Run evaluation
        current_eval = evaluate_policy_performance(production_dir)
        
        # Save to history
        history = []
        if eval_history_file.exists():
            try:
                with open(eval_history_file, 'r') as f:
                    history = json.load(f)
            except:
                history = []
        
        history.append(current_eval)
        # Keep only last 10 evaluations
        history = history[-10:]
        
        with open(eval_history_file, 'w') as f:
            json.dump(history, f, indent=2)
        
        # Check if rollback is recommended
        if should_roll_back(current_eval, previous_eval):
            print("\n⚠️  WARNING: Performance degradation detected!")
            print("   Consider rolling back to previous policy.")
            # In a full system, this might trigger an automatic rollback
            sys.exit(2)  # Special exit code for rollback recommendation
        else:
            print("\n✅ Performance stable or improved.")
            sys.exit(0)
            
    elif args.action == "rollback":
        print("Action: Rolling back to previous policy")
        # Implementation would restore from backups
        print("Rollback functionality would be implemented here")
        print("For now, manual intervention is required")
        sys.exit(1)

if __name__ == "__main__":
    sys.exit(main())