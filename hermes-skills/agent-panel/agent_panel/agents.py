"""
Agent wrappers and registry for the panel system.
Each agent wraps an LLM provider and returns an AgentProposal.
"""

import os
import re
import time
import anthropic
import openai
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AgentProposal:
    """A proposal from a single agent."""
    agent: str
    answer: str
    confidence: float = 0.5
    reasoning: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_display(self) -> str:
        return f"[{self.agent}] (conf={self.confidence:.2f}): {self.answer[:100]}..."


class BaseAgent(ABC):
    """Base class for all panel agents."""

    name: str = "base"
    description: str = "Base agent"

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        self.model = model
        self._api_key = api_key

    @property
    def api_key(self) -> str:
        if self._api_key:
            return self._api_key
        return os.environ.get("ANTHROPIC_API_KEY", "")

    def call_llm(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.7) -> str:
        """Make an LLM call. Override for custom behavior."""
        raise NotImplementedError

    def run(self, query: str) -> AgentProposal:
        """Run this agent on the query and return a proposal."""
        answer = self.call_llm(query)
        return AgentProposal(
            agent=self.name,
            answer=answer,
            confidence=self._estimate_confidence(answer),
            metadata={"model": self.model}
        )

    def _estimate_confidence(self, answer: str) -> float:
        """Simple heuristic confidence estimation."""
        if not answer or len(answer) < 20:
            return 0.1
        # Penalize very short or very long answers
        if len(answer) < 50:
            return 0.4
        if len(answer) > 10000:
            return 0.6
        return 0.7


class ClaudeAgent(BaseAgent):
    """Agent powered by Anthropic Claude."""

    name = "claude"
    description = "Anthropic Claude — strong reasoning, nuanced answers"

    def __init__(self, model: str = "claude-sonnet-4-5-20250929", **kwargs):
        super().__init__(model=model, **kwargs)

    def call_llm(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.7) -> str:
        client = anthropic.Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=self._system_prompt(),
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    def _system_prompt(self) -> str:
        return (
            "You are a helpful, thoughtful assistant. "
            "Provide clear, accurate, well-reasoned answers. "
            "When uncertain, acknowledge limitations honestly."
        )


class OpenAIAgent(BaseAgent):
    """Agent powered by OpenAI GPT."""

    name = "openai"
    description = "OpenAI GPT — broad knowledge, creative responses"

    def __init__(self, model: str = "gpt-4o", **kwargs):
        super().__init__(model=model, **kwargs)

    def call_llm(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.7) -> str:
        client = openai.OpenAI(api_key=self._api_key or os.environ.get("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content

    def _system_prompt(self) -> str:
        return (
            "You are a helpful, thoughtful assistant. "
            "Provide clear, accurate, well-reasoned answers. "
            "When uncertain, acknowledge limitations honestly."
        )


class HermesAgent(BaseAgent):
    """Agent powered by Hermes (MiniMax)."""

    name = "hermes"
    description = "Hermes (MiniMax) — fast, efficient reasoning"

    def __init__(self, model: str = "MiniMax-M2.7-32K", base_url: str = "https://api.minimax.chat/v1", **kwargs):
        super().__init__(model=model, **kwargs)
        self.base_url = base_url

    def call_llm(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.7) -> str:
        api_key = self._api_key or os.environ.get("MINIMAX_API_KEY", "")
        if not api_key:
            raise ValueError("MINIMAX_API_KEY not set")

        client = openai.OpenAI(api_key=api_key, base_url=self.base_url)
        response = client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content

    def _system_prompt(self) -> str:
        return (
            "You are Hermes, an AI assistant. Provide clear, accurate, "
            "well-reasoned answers. Be genuinely curious and think carefully "
            "before responding. When uncertain, acknowledge limitations honestly."
        )


class GrokAgent(BaseAgent):
    """Agent powered by xAI Grok."""

    name = "grok"
    description = "xAI Grok — witty, direct, no-nonsense"

    def __init__(self, model: str = "grok-2-1212", **kwargs):
        super().__init__(model=model, **kwargs)

    def call_llm(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.7) -> str:
        api_key = self._api_key or os.environ.get("XAI_API_KEY", "")
        if not api_key:
            raise ValueError("XAI_API_KEY not set")

        client = openai.OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
        response = client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content

    def _system_prompt(self) -> str:
        return (
            "You are Grok, an AI assistant by xAI. Be witty, direct, and no-nonsense. "
            "Provide accurate answers without excessive hedging. Think for yourself."
        )


class CoderAgent(BaseAgent):
    """Specialized agent for coding tasks."""

    name = "coder"
    description = "Coding specialist — code, architecture, debugging, best practices"

    def __init__(self, model: str = "claude-sonnet-4-5-20250929", **kwargs):
        super().__init__(model=model, **kwargs)

    def call_llm(self, prompt: str, max_tokens: int = 4096, temperature: float = 0.5) -> str:
        client = anthropic.Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=(
                "You are an expert software engineer. "
                "Provide clean, well-documented code with explanations. "
                "Include trade-offs when relevant. Prefer modern patterns."
            ),
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text


class ResearcherAgent(BaseAgent):
    """Research-focused agent for factual queries."""

    name = "researcher"
    description = "Research specialist — deep facts, citations, thorough analysis"

    def __init__(self, model: str = "claude-sonnet-4-5-20250929", **kwargs):
        super().__init__(model=model, **kwargs)

    def call_llm(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.3) -> str:
        client = anthropic.Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=(
                "You are a thorough research assistant. "
                "Provide well-sourced, accurate information. "
                "Acknowledge uncertainty and distinguish facts from interpretation."
            ),
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text


class CreativeAgent(BaseAgent):
    """Creative agent for brainstorming and open-ended problems."""

    name = "creative"
    description = "Creative specialist — brainstorming, alternatives, novel ideas"

    def __init__(self, model: str = "gpt-4o", **kwargs):
        super().__init__(model=model, **kwargs)

    def call_llm(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.9) -> str:
        client = openai.OpenAI(api_key=self._api_key or os.environ.get("OPENAI_API_KEY"))
        response = client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": (
                    "You are a creative brainstorming partner. "
                    "Generate diverse alternatives, novel ideas, and fresh perspectives. "
                    "Think outside conventional frameworks. Be bold and imaginative."
                )},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content


class DevOpsAgent(BaseAgent):
    """DevOps agent for infrastructure and deployment questions."""

    name = "devops"
    description = "DevOps specialist — infrastructure, deployment, scaling, monitoring"

    def __init__(self, model: str = "claude-sonnet-4-5-20250929", **kwargs):
        super().__init__(model=model, **kwargs)

    def call_llm(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.5) -> str:
        client = anthropic.Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=(
                "You are a DevOps and infrastructure expert. "
                "Cover topics like CI/CD, containers, cloud platforms, monitoring, "
                "incident response, and scaling. Provide practical operational guidance."
            ),
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text


class GeneralAgent(BaseAgent):
    """General-purpose assistant agent."""

    name = "general"
    description = "General assistant — balanced, broad knowledge"

    def __init__(self, model: str = "claude-sonnet-4-5-20250929", **kwargs):
        super().__init__(model=model, **kwargs)

    def call_llm(self, prompt: str, max_tokens: int = 2048, temperature: float = 0.7) -> str:
        client = anthropic.Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system="You are a helpful, balanced assistant.",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text


# Agent registry — maps type names to agent classes
AGENT_REGISTRY: dict = {
    "claude": ClaudeAgent,
    "openai": OpenAIAgent,
    "hermes": HermesAgent,
    "grok": GrokAgent,
    "coder": CoderAgent,
    "researcher": ResearcherAgent,
    "creative": CreativeAgent,
    "devops": DevOpsAgent,
    "general": GeneralAgent,
}


def get_agent(agent_type: str, **kwargs) -> BaseAgent:
    """Factory to get an agent instance by type name."""
    agent_class = AGENT_REGISTRY.get(agent_type.lower())
    if agent_class is None:
        raise ValueError(
            f"Unknown agent type: {agent_type}. "
            f"Available: {list(AGENT_REGISTRY.keys())}"
        )
    return agent_class(**kwargs)


def list_agents() -> list:
    """Return list of available agent types."""
    return list(AGENT_REGISTRY.keys())
