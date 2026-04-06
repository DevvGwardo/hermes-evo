#!/usr/bin/env python3
"""
Brain MCP RL Improvement Evaluator
Measures the impact of RL policy changes on system performance.
"""

import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
import sys

def run_command(cmd):
    """Run a shell command and return output."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", "Timeout", 1
    except Exception as e:
        return "", str(e), 1

def get_system_metrics():
    """Collect comprehensive system metrics for evaluation."""
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "mcp_health": {},
        "agent_activity": {},
        "system_performance": {},
        "recent_errors": {}
    }
    
    # 1. Brain MCP Health Check
    stdout, stderr, code = run_command("hermes mcp test brain")
    metrics["mcp_health"]["connected"] = "✓ Connected" in stdout
    metrics["mcp_health"]["tools_discovered"] = 0
    metrics["mcp_health"]["response_times"] = []
    
    # Extract response times if available
    if "response time" in stdout:
        import re
        matches = re.findall(r'\((\d+)ms\)', stdout)
        metrics["mcp_health"]["response_times"] = [int(x) for x in matches]
        if matches:
            metrics["mcp_health"]["avg_response_time"] = sum(metrics["mcp_health"]["response_times"]) / len(metrics["mcp_health"]["response_times"])
    
    # 2. Agent Activity and Status
    stdout, stderr, code = run_command("/Users/devgwardo/.hermes/show_agents.sh")
    metrics["agent_activity"]["display_output"] = stdout
    metrics["agent_activity"]["active_agents"] = stdout.count("◆")  # Working agents
    metrics["agent_activity"]["idle_agents"] = stdout.count("◇")   # Idle agents
    metrics["agent_activity"]["done_agents"] = stdout.count("✓")   # Done agents
    metrics["agent_activity"]["failed_agents"] = stdout.count("✗") # Failed agents
    
    # Check for recent agent-created files (indicates productive work)
    stdout, stderr, code = run_command("find /tmp -name 'agent_demo_*.txt' -type f -mmin -5 2>/dev/null | wc -l")
    try:
        metrics["agent_activity"]["recent_demo_files"] = int(stdout.strip()) if stdout.strip().isdigit() else 0
    except:
        metrics["agent_activity"]["recent_demo_files"] = 0
    
    # 3. System Performance
    stdout, stderr, code = run_command("uptime")
    metrics["system_performance"]["load_average"] = stdout
    
    stdout, stderr, code = run_command("vm_stat 2>/dev/null | grep -E 'Pages free|Pages active'" || echo "Not available")
    metrics["system_performance"]["memory_info"] = stdout
    
    # 4. Recent System Health (from logs)
    log_files = [
        "/Users/devgwardo/.hermes/brain_heartbeat.log",
        "/Users/devgwardo/.hermes/brain_overseer.log"
    ]
    
    metrics["recent_errors"]["heartbeat_failures"] = 0
    metrics["recent_errors"]["overseer_alerts"] = 0
    
    for log_file in log_files:
        if Path(log_file).exists():
            stdout, stderr, code = run_command(f"grep -c 'HEARTBEAT_FAIL' {log_file} 2>/dev/null || echo 0")
            try:
                if "heartbeat" in log_file:
                    metrics["recent_errors"]["heartbeat_failures"] = int(stdout.strip()) if stdout.strip().isdigit() else 0
                else:
                    metrics["recent_errors"]["overseer_alerts"] = int(stdout.strip()) if stdout.strip().isdigit() else 0
            except:
                pass
    
    # 5. Data Collection Status (if applicable)
    data_dir = Path.home() / ".hermes" / "skills" / "brain-mcp-rl-improver" / "data"
    if data_dir.exists():
        trajectory_files = list(data_dir.glob("trajectories_*.json"))
        metrics["data_collection"]["files_collected"] = len(trajectory_files)
        if trajectory_files:
            latest_file = max(trajectory_files, key=lambda f: f.stat().st_mtime)
            metrics["data_collection"]["last_collection"] = datetime.fromtimestamp(latest_file.stat().st_mtime).isoformat()
    
    return metrics

def calculate_performance_score(metrics):
    """Calculate a composite performance score from metrics."""
    score_components = {
        "mcp_health": 0.0,
        "agent_efficiency": 0.0,
        "system_stability": 0.0,
        "resource_utilization": 0.0
    }
    
    # 1. MCP Health Score (0-1)
    if metrics["mcp_health"]["connected"]:
        score_components["mcp_health"] = 1.0
        # Bonus for fast response times
        avg_response = metrics["mcp_health"].get("avg_response_time", 1000)
        if avg_response < 500:  # Less than 500ms
            score_components["mcp_health"] = min(1.0, score_components["mcp_health"] + 0.2)
    else:
        score_components["mcp_health"] = 0.0
    
    # 2. Agent Efficiency Score (0-1)
    active = metrics["agent_activity"]["active_agents"]
    idle = metrics["agent_activity"]["idle_agents"]
    total_agents = active + idle
    
    if total_agents > 0:
        # Ideal ratio: some agents working, some idle for responsiveness
        ideal_active_ratio = 0.4  # 40% active, 60% idle/ready
        actual_ratio = active / total_agents if total_agents > 0 else 0
        efficiency = 1.0 - abs(actual_ratio - ideal_active_ratio)
        score_components["agent_efficiency"] = max(0.0, efficiency)
        
        # Bonus for recent productive work (demo files)
        if metrics["agent_activity"]["recent_demo_files"] > 0:
            score_components["agent_efficiency"] = min(1.0, score_components["agent_efficiency"] + 0.2)
    else:
        # No agents - check if this is appropriate (system idle)
        score_components["agent_efficiency"] = 0.5  # Neutral - depends on workload
    
    # 3. System Stability Score (0-1)
    heartbeat_fails = metrics["recent_errors"]["heartbeat_failures"]
    overseer_alerts = metrics["recent_errors"]["overseer_alerts"]
    
    # Start with perfect score, deduct for issues
    stability_score = 1.0
    stability_score -= min(0.5, heartbeat_fails * 0.1)  # Max 0.5 penalty for heartbeat fails
    stability_score -= min(0.3, overseer_alerts * 0.05)  # Max 0.3 penalty for overseer alerts
    score_components["system_stability"] = max(0.0, stability_score)
    
    # 4. Resource Utilization Score (0-1)
    # This would be more sophisticated in practice - for now, basic check
    # Penalize extreme resource usage (would need actual CPU/memory metrics)
    score_components["resource_utilization"] = 0.8  # Assume reasonable utilization
    
    # Weighted composite score
    weights = {
        "mcp_health": 0.3,
        "agent_efficiency": 0.25,
        "system_stability": 0.25,
        "resource_utilization": 0.2
    }
    
    composite_score = sum(score_components[key] * weights[key] for key in score_components)
    
    return {
        "composite_score": composite_score,
        "components": score_components,
        "raw_metrics": metrics
    }

def load_baseline_performance():
    """Load baseline performance for comparison."""
    baseline_file = Path.home() / ".hermes" / "skills" / "brain-mcp-rl-improver" / "baseline_performance.json"
    if baseline_file.exists():
        try:
            with open(baseline_file, 'r') as f:
                return json.load(f)
        except:
            pass
    return None

def save_baseline_performance(performance_data):
    """Save current performance as baseline for future comparisons."""
    baseline_file = Path.home() / ".hermes" / "skills" / "brain-mcp-rl-improver" / "baseline_performance.json"
    baseline_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(baseline_file, 'w') as f:
        json.dump(performance_data, f, indent=2, default=str)
    
    print(f"Baseline performance saved to {baseline_file}")

def compare_performance(current, baseline):
    """Compare current performance against baseline."""
    if baseline is None:
        return {
            "status": "no_baseline",
            "message": "No baseline performance available for comparison",
            "improvement": None
        }
    
    current_score = current["composite_score"]
    baseline_score = baseline["composite_score"]
    
    improvement = current_score - baseline_score
    improvement_percent = (improvement / baseline_score * 100) if baseline_score != 0 else 0
    
    # Component-wise comparison
    component_changes = {}
    for key in current["components"]:
        if key in baseline["components"]:
            change = current["components"][key] - baseline["components"][key]
            component_changes[key] = {
                "current": current["components"][key],
                "baseline": baseline["components"][key],
                "change": change,
                "change_percent": (change / baseline["components"][key] * 100) if baseline["components"][key] != 0 else 0
            }
    
    return {
        "status": "compared",
        "baseline_score": baseline_score,
        "current_score": current_score,
        "improvement": improvement,
        "improvement_percent": improvement_percent,
        "component_changes": component_changes,
        "significant_improvement": improvement > 0.05,  # 5% threshold
        "significant_degradation": improvement < -0.05  # 5% threshold
    }

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Evaluate brain MCP RL improvement impact")
    parser.add_argument("--action", choices=["evaluate", "baseline", "compare"], 
                       default="evaluate", help="Action to perform")
    parser.add_argument("--save-baseline", action="store_true", 
                       help="Save current performance as baseline")
    parser.addetailed-output", action="store_true", 
                       help="Show detailed output")
    
    args = parser.parse_args()
    
    print("Brain MCP RL Improvement Evaluator")
    print("=" * 40)
    
    if args.action == "baseline" or args.save_baseline:
        print("Collecting baseline performance metrics...")
        metrics = get_system_metrics()
        performance = calculate_performance_score(metrics)
        save_baseline_performance(performance)
        print("Baseline performance saved successfully!")
        if args.detailed_output:
            print(json.dumps(performance, indent=2, default=str))
        return 0
    
    elif args.action == "compare":
        print("Loading baseline performance...")
        baseline = load_baseline_performance()
        if baseline is None:
            print("No baseline found. Use --save-baseline to create one first.")
            return 1
        
        print("Collecting current performance metrics...")
        metrics = get_system_metrics()
        current = calculate_performance_score(metrics)
        
        comparison = compare_performance(current, baseline)
        
        print(f"\nPerformance Comparison:")
        print(f"Baseline Score: {comparison['baseline_score']:.3f}")
        print(f"Current Score:  {comparison['current_score']:.3f}")
        print(f"Improvement:    {comparison['improvement']:+.3f} ({comparison['improvement_percent']:+.1f}%)")
        
        if comparison["significant_improvement"]:
            print("✅ SIGNIFICANT IMPROVEMENT DETECTED (>5%)")
        elif comparison["significant_degradation"]:
            print("❌ SIGNIFICANT DEGRADATION DETECTED (<-5%)")
        else:
            print("➡️  Performance change within normal variance (±5%)")
        
        if args.detailed_output:
            print("\nComponent-wise Changes:")
            for component, changes in comparison["component_changes"].items():
                print(f"  {component}: {changes['baseline']:.3f} → {changes['current']:.3f} "
                      f"({changes['change']:+.3f}, {changes['change_percent']:+.1f}%)")
            
            print("\nFull Comparison Data:")
            print(json.dumps(comparison, indent=2, default=str))
        
        # Return appropriate exit code
        if comparison["significant_improvement"]:
            return 0  # Success
        elif comparison["significant_degradation"]:
            return 2  # Failure - degradation
        else:
            return 1  # Neutral - no significant change
    
    else:  # evaluate action
        print("Collecting current performance metrics...")
        metrics = get_system_metrics()
        performance = calculate_performance_score(metrics)
        
        print(f"\nCurrent Performance Score: {performance['composite_score']:.3f}")
        print("Component Breakdown:")
        for component, score in performance["components"].items():
            print(f"  {component}: {score:.3f}")
        
        # Check against baseline if available
        baseline = load_baseline_performance()
        if baseline:
            comparison = compare_performance(performance, baseline)
            print(f"\nVs Baseline ({baseline['composite_score']:.3f}):")
            print(f"  Change: {comparison['improvement']:+.3f} ({comparison['improvement_percent']:+.1f}%)")
            
            if comparison["significant_improvement"]:
                print("  ✅ Significant improvement")
            elif comparison["significant_degradation"]:
                print("  ❌ Significant degradation")
            else:
                print("  ➡️  Within normal variance")
        
        if args.detailed_output:
            print("\nDetailed Metrics:")
            print(json.dumps(performance["raw_metrics"], indent=2, default=str))
        
        return 0

if __name__ == "__main__":
    sys.exit(main())