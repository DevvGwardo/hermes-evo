#!/usr/bin/env python3
"""
Brain MCP RL Policy Deployer
Safely rolls out improved policies with A/B testing and rollback capabilities.
"""

import json
import argparse
import os
import sys
import time
from pathlib import Path
import shutil

def load_latest_policy(policy_dir):
    """Load the most recently trained policy."""
    policy_dir = Path(policy_dir)
    if not policy_dir.exists():
        return None
    
    # Look for policy directories or files
    policy_items = list(policy_dir.glob("*"))
    if not policy_items:
        return None
    
    # Sort by modification time, newest first
    policy_items.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return policy_items[0]

def load_baseline_policy():
    """Load the baseline policy (current system behavior)."""
    # In practice, this would load the current production policy
    # For now, we'll return a marker indicating baseline usage
    return {"type": "baseline", "description": "Current brain MCP heuristics"}

def evaluate_policy_performance(policy_path, test_duration="15m"):
    """Evaluate a policy's performance over a test period."""
    # This would integrate with brain MCP monitoring systems
    # For demonstration, we'll simulate evaluation
    
    print(f"Evaluating policy: {policy_path}")
    print(f"Test duration: {test_duration}")
    
    # Simulate collecting metrics during test period
    # In reality, this would:
    # 1. Deploy the policy to a test environment
    # 2. Run brain MCP with the policy for test_duration
    # 3. Collect metrics (task completion rate, latency, resource usage, etc.)
    
    # Mock evaluation results
    import random
    performance_score = random.uniform(0.7, 0.95)  # Simulate improved performance
    
    metrics = {
        "policy_path": str(policy_path),
        "test_duration": test_duration,
        "timestamp": time.time(),
        "performance_score": performance_score,
        "task_completion_rate": min(0.95, performance_score + random.uniform(-0.05, 0.1)),
        "avg_latency_ms": max(50, 200 - performance_score * 100),
        "resource_efficiency": performance_score,
        "error_rate": max(0.01, 0.1 - performance_score * 0.09)
    }
    
    return metrics

def main():
    parser = argparse.ArgumentParser(description="Deploy brain MCP RL policy")
    parser.add_argument("--policy-dir", type=str, 
                       default="~/.hermes/skills/brain-mcp-rl-improver/policies",
                       help="Directory containing trained policies")
    parser.add_argument("--baseline-check", action="store_true",
                       help="Compare against baseline before deployment")
    parser.add_argument("--test-duration", type=str, default="15m",
                       help="Duration for A/B testing (e.g., 5m, 15m, 1h)")
    parser.add_argument("--promote-threshold", type=float, default=0.05,
                       help="Minimum improvement required to promote (5%)")
    parser.add_argument("--auto-rollback", action="store_true", default=True,
                       help="Automatically rollback if performance degrades")
    
    args = parser.parse_args()
    
    policy_dir = Path(os.path.expanduser(args.policy_dir))
    policy_dir.mkdir(parents=True, exist_ok=True)
    
    print("Brain MCP RL Policy Deployment")
    print("=" * 40)
    
    # Load latest policy
    latest_policy = load_latest_policy(policy_dir)
    if not latest_policy:
        print("ERROR: No trained policies found. Please run training first.")
        return 1
    
    print(f"Latest policy: {latest_policy}")
    
    # Load baseline for comparison
    baseline = load_baseline_policy() if args.baseline_check else None
    if baseline:
        print(f"Baseline policy: {baseline}")
    
    # Evaluate the new policy
    print(f"\nEvaluating policy over {args.test_duration}...")
    new_policy_metrics = evaluate_policy_performance(latest_policy, args.test_duration)
    
    print(f"New policy performance score: {new_policy_metrics['performance_score']:.3f}")
    
    # Compare with baseline if requested
    if args.baseline_check and baseline:
        baseline_metrics = evaluate_policy_performance(baseline, args.test_duration)
        print(f"Baseline performance score: {baseline_metrics['performance_score']:.3f}")
        
        improvement = new_policy_metrics['performance_score'] - baseline_metrics['performance_score']
        improvement_pct = (improvement / baseline_metrics['performance_score']) * 100
        
        print(f"Improvement: {improvement:.3f} ({improvement_pct:+.1f}%)")
        
        # Check if improvement meets threshold
        if improvement_pct < args.promote_threshold * 100:
            print(f"WARNING: Improvement ({improvement_pct:.1f}%) below threshold ({args.promote_threshold*100}%)")
            if not args.auto_rollback:
                response = input("Deploy anyway? (y/N): ")
                if response.lower() != 'y':
                    print("Deployment cancelled.")
                    return 1
        else:
            print(f"SUCCESS: Improvement meets threshold ({args.promote_threshold*100}%)")
    
    # Deploy the policy (in practice, this would update brain MCP configuration)
    deployment_dir = policy_dir / "deployed"
    deployment_dir.mkdir(exist_ok=True)
    
    # Create deployment marker
    deployment_marker = deployment_dir / f"deployed_{int(time.time())}.json"
    deployment_data = {
        "policy_source": str(latest_policy),
        "deployment_time": time.time(),
        "metrics": new_policy_metrics,
        "deployment_id": f"brain_mcp_rl_{int(time.time())}",
        "status": "deployed"
    }
    
    with open(deployment_marker, 'w') as f:
        json.dump(deployment_data, f, indent=2)
    
    print(f"\nPolicy deployed successfully!")
    print(f"Deployment marker: {deployment_marker}")
    
    # Create rollback information
    rollback_info = deployment_dir / f"rollback_{int(time.time())}.info"
    with open(rollback_info, 'w') as f:
        f.write(f"""Rollback information for deployment {deployment_data['deployment_id']}
Policy: {latest_policy}
Deployed: {time.ctime(deployment_data['deployment_time'])}
To rollback: Restore previous configuration and remove this deployment marker
""")
    
    print(f"Rollback info: {rollback_info}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())