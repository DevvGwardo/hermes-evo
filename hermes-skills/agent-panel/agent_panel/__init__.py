"""
Hermes Agent Panel — DSPy Multi-Agent Orchestration System
Multi-agent proposal → DSPy judge → best answer
"""

from .core import AgentPanel, PanelResult, DSPyJudge
from .agents import BaseAgent, AgentProposal

__version__ = "1.0.0"

__all__ = [
    "AgentPanel",
    "PanelResult",
    "DSPyJudge",
    "BaseAgent",
    "AgentProposal",
]
