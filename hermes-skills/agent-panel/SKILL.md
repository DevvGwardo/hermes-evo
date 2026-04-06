---
name: hermes-agent-panel
description: Multi-agent orchestration system using DSPy — spawns parallel agent proposals, evaluates them with a DSPy-optimized judge, and returns the best response. Uses MIPRO to learn your preferences over time.
version: 1.0.0
author: DevGwardo + Hermes
tags: [multi-agent, orchestration, dspy, judge, panel, parallel-agents, prompt-optimization, agent-coordination]
required_env: []
metadata:
  hermes:
    triggers:
      - "ask all agents"
      - "which agent would be best"
      - "consult the panel"
      - "multi-agent answer"
      - "agent panel"
      - "ask the agents"
      - "best approach"
---

# Hermes Agent Panel — DSPy Multi-Agent Orchestration

Run multiple specialized agents in parallel, evaluate their proposals with a DSPy judge, and return the best answer. The judge is continuously optimized using your feedback.

## When to Use

- Query could be answered by multiple approaches or agent types
- You want a "panel" of agents to debate and vote on the best answer
- You want to learn which agent types perform best for which query categories
- You want a self-improving answer quality system

## Architecture

```
User Query
    │
    ├──► Coder Agent ──────► Proposal A
    ├──► Researcher Agent ─► Proposal B
    ├──► Creative Agent ───► Proposal C
    └──► General Agent ────► Proposal D
                                      │
                                      ▼
                              DSPy Judge (MIPRO-optimized)
                                      │
                               scores each proposal
                                      │
                                      ▼
                              Refine Agent (best)
                                      │
                                      ▼
                               Final Answer
```

## Setup

```bash
# Install dependencies
pip install dspy anthropic openai requests

# Set API keys in environment
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
```

## Usage

### Quick Start — CLI

```bash
python main.py "Best way to handle authentication in a FastAPI app?"
```

### Quick Start — Python

```python
from agent_panel import AgentPanel

panel = AgentPanel(judge_model="claude-sonnet-4-5-20250929")

result = panel.run(
    query="Explain quantum computing in simple terms",
    agent_types=["general", "creative", "coder"]
)

print(result.best_answer)
print(result.judge_reasoning)
```

### Python API

```python
from agent_panel import AgentPanel
from agent_panel.core import DSPyJudge

# Initialize with a specific judge model
panel = AgentPanel(
    judge_model="claude-sonnet-4-5-20250929",
    min_proposals=2
)

# Run with default agents
result = panel.run("How do I scale a Python web app?")

# Custom agent pool
result = panel.run(
    query="Build a REST API",
    agent_types=["coder", "architect", "devops"]
)

# Access results
for proposal in result.proposals:
    print(f"{proposal.agent}: {proposal.answer[:50]}...")
    print(f"  Score: {proposal.score}")

print(f"Best: {result.best_answer}")
```

### Collecting Feedback to Improve the Judge

```python
from agent_panel import AgentPanel

panel = AgentPanel()

# After seeing results, provide feedback
panel.feedback(
    query="Best Python async patterns?",
    chosen="coder",
    score=5  # 1-5 scale
)

# The judge improves over time with enough feedback
```

## Agent Types

| Agent | Strengths | Best For |
|---|---|---|
| `general` | Balanced, broad knowledge | General questions |
| `coder` | Code, architecture, debugging | Technical problems |
| `researcher` | Deep research, facts, citations | Factual queries |
| `creative` | Brainstorming, alternatives | Open-ended problems |
| `devops` | Infrastructure, deployment, scaling | Ops questions |

## Custom Agents

```python
from agent_panel.agents import BaseAgent, AgentProposal

class CustomAgent(BaseAgent):
    name = "custom_agent"

    def run(self, query: str) -> AgentProposal:
        answer = self.call_llm(query)
        return AgentProposal(
            agent=self.name,
            answer=answer,
            confidence=0.8
        )

panel = AgentPanel()
panel.register_agent(CustomAgent())
result = panel.run("Your query", agent_types=["custom_agent"])
```

## Judge Customization

```python
from agent_panel.core import DSPyJudge

judge = DSPyJudge(
    model="claude-sonnet-4-5-20250929",
    num_candidates=10,
    num_trials=50
)

# Optimize on your feedback data
judge.optimize(feedback_data)

# Use without optimization
judge.evaluate(proposals)
```

## Files

```
agent_panel/
  __init__.py          Package init
  core.py              DSPy pipeline: Judge, Panel, Refine
  agents.py            Agent wrappers and registry
  prompts.py           DSPy signature definitions
main.py                CLI entry point
requirements.txt        Dependencies
tests/                 Test suite
SKILL.md               This file
```

## Requirements

- Python 3.9+
- dspy
- anthropic
- openai
- requests
