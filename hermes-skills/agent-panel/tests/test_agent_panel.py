"""
Tests for the Hermes Agent Panel DSPy system.
"""

import pytest
import os
from unittest.mock import patch, MagicMock

# Set mock env vars before imports
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("OPENAI_API_KEY", "test-key")


class TestAgentRegistry:
    """Tests for agent registry and factory."""

    def test_list_agents(self):
        from agent_panel.agents import list_agents, AGENT_REGISTRY
        agents = list_agents()
        assert isinstance(agents, list)
        assert len(agents) > 0
        assert "claude" in agents
        assert "coder" in agents
        assert "researcher" in agents

    def test_get_agent_valid(self):
        from agent_panel.agents import get_agent
        agent = get_agent("general")
        assert agent.name == "general"
        assert agent.description

    def test_get_agent_invalid(self):
        from agent_panel.agents import get_agent
        with pytest.raises(ValueError, match="Unknown agent type"):
            get_agent("nonexistent_agent")

    def test_get_agent_case_insensitive(self):
        from agent_panel.agents import get_agent
        agent = get_agent("CLAUDE")
        assert agent.name == "claude"


class TestAgentProposal:
    """Tests for AgentProposal dataclass."""

    def test_proposal_creation(self):
        from agent_panel.agents import AgentProposal
        p = AgentProposal(
            agent="claude",
            answer="The answer is 42",
            confidence=0.85
        )
        assert p.agent == "claude"
        assert p.answer == "The answer is 42"
        assert p.confidence == 0.85

    def test_proposal_to_display(self):
        from agent_panel.agents import AgentProposal
        p = AgentProposal(
            agent="coder",
            answer="Use a decorator for authentication",
            confidence=0.9
        )
        display = p.to_display()
        assert "coder" in display
        assert "conf=0.90" in display or "conf=0.9" in display


class TestBaseAgent:
    """Tests for BaseAgent and subclasses."""

    def test_base_agent_run_raises(self):
        from agent_panel.agents import BaseAgent
        agent = BaseAgent()
        # Calling run without override raises NotImplementedError
        with pytest.raises(NotImplementedError):
            agent.run("test query")

    def test_estimate_confidence_short(self):
        from agent_panel.agents import GeneralAgent
        agent = GeneralAgent(model="claude-sonnet-4-5-20250929")
        # Very short answer should have low confidence
        conf = agent._estimate_confidence("42")
        assert conf < 0.5

    def test_estimate_confidence_normal(self):
        from agent_panel.agents import GeneralAgent
        agent = GeneralAgent(model="claude-sonnet-4-5-20250929")
        # Normal length answer
        conf = agent._estimate_confidence("The answer to your question is quite detailed and explains the reasoning clearly.")
        assert conf >= 0.5

    def test_estimate_confidence_long(self):
        from agent_panel.agents import GeneralAgent
        agent = GeneralAgent(model="claude-sonnet-4-5-20250929")
        # Very long answer — penalize
        long_text = "Answer. " * 1000
        conf = agent._estimate_confidence(long_text)
        assert conf <= 0.7


class TestDSPyJudge:
    """Tests for DSPyJudge class."""

    def test_judge_init(self):
        from agent_panel.core import DSPyJudge
        judge = DSPyJudge(
            model="claude-sonnet-4-5-20250929",
            model_provider="anthropic",
            use_cot=True,
        )
        assert judge.model == "claude-sonnet-4-5-20250929"
        assert judge.model_provider == "anthropic"
        assert judge.use_cot is True
        assert judge._judge_module is None
        assert judge._optimized is False

    def test_judge_format_proposals(self):
        from agent_panel.core import DSPyJudge
        from agent_panel.agents import AgentProposal

        judge = DSPyJudge()
        proposals = [
            AgentProposal(agent="claude", answer="Claude's answer", confidence=0.8),
            AgentProposal(agent="openai", answer="OpenAI's answer", confidence=0.7),
        ]
        formatted = judge._format_proposals(proposals)
        assert "claude" in formatted
        assert "Claude's answer" in formatted
        assert "openai" in formatted
        assert "OpenAI's answer" in formatted

    def test_judge_calc_confidence(self):
        from agent_panel.core import DSPyJudge
        from agent_panel.agents import AgentProposal

        judge = DSPyJudge()

        # Good reasoning (307 chars — gets +0.1 bonus for > 200)
        good_reasoning = (
            "This answer is comprehensive, well-structured, and directly addresses "
            "the question with specific examples and clear explanations. The reasoning "
            "is thorough and demonstrates deep understanding of the topic. It covers all "
            "key aspects systematically and provides actionable insights that are "
            "clearly explained throughout."
        )
        conf = judge._calc_confidence(good_reasoning, [], "claude")
        assert conf > 0.7

        # Weak reasoning — no uncertain words, short
        weak_reasoning = "Maybe this one."
        conf = judge._calc_confidence(weak_reasoning, [], "claude")
        # "maybe" is not in uncertain_words list, so base 0.7 applies
        assert conf == 0.7

    def test_judge_calc_confidence_with_uncertainty_words(self):
        from agent_panel.core import DSPyJudge
        judge = DSPyJudge()

        reasoning = "Perhaps the answer might be unclear, possibly yes."
        conf = judge._calc_confidence(reasoning, [], "claude")
        assert conf <= 0.6  # base 0.7 minus 0.1 for uncertain words = 0.6

    def test_judge_empty_reasoning(self):
        from agent_panel.core import DSPyJudge
        judge = DSPyJudge()
        conf = judge._calc_confidence("", [], "claude")
        assert conf == 0.4


class TestAgentPanel:
    """Tests for AgentPanel orchestrator."""

    def test_panel_init_defaults(self):
        from agent_panel import AgentPanel
        panel = AgentPanel()
        assert panel.judge is not None
        assert panel.max_parallel == 5
        assert panel.timeout_per_agent == 120
        assert panel.min_proposals == 2
        assert panel.use_refinement is True
        assert panel.enable_cot is True

    def test_panel_init_custom(self):
        from agent_panel import AgentPanel
        panel = AgentPanel(
            judge_model="gpt-4o",
            judge_provider="openai",
            max_parallel=3,
            timeout_per_agent=60,
            min_proposals=3,
            use_refinement=False,
            enable_cot=False,
        )
        assert panel.judge.model == "gpt-4o"
        assert panel.judge.model_provider == "openai"
        assert panel.max_parallel == 3
        assert panel.timeout_per_agent == 60
        assert panel.min_proposals == 3
        assert panel.use_refinement is False
        assert panel.enable_cot is False

    def test_panel_feedback_creates_file(self, tmp_path, monkeypatch):
        """Test that feedback writes to ~/.hermes/agent-panel-feedback/."""
        from agent_panel import AgentPanel, AgentProposal

        # Set HOME to our temp dir so Path.home() returns it
        monkeypatch.setenv("HOME", str(tmp_path))

        panel = AgentPanel()
        proposals = [
            AgentProposal(agent="claude", answer="Answer 1", confidence=0.8),
            AgentProposal(agent="openai", answer="Answer 2", confidence=0.7),
        ]

        outfile = panel.feedback(
            query="Test question?",
            proposals=proposals,
            chosen_agent="claude",
            score=5,
        )

        assert outfile.exists()
        import json
        data = json.loads(outfile.read_text())
        assert data["query"] == "Test question?"
        assert data["chosen_agent"] == "claude"
        assert data["score"] == 5
        assert len(data["proposals"]) == 2


class TestPanelResult:
    """Tests for PanelResult dataclass."""

    def test_panel_result_creation(self):
        from agent_panel import PanelResult
        from agent_panel.agents import AgentProposal

        result = PanelResult(
            query="What is 2+2?",
            proposals=[
                AgentProposal(agent="claude", answer="4", confidence=0.9),
                AgentProposal(agent="openai", answer="4", confidence=0.8),
            ],
            best_proposal=AgentProposal(agent="claude", answer="4", confidence=0.9),
            best_answer="4",
            refined_answer="4",
            judge_reasoning="Both answers are correct but Claude explains the reasoning.",
            winner_agent="claude",
        )

        assert result.query == "What is 2+2?"
        assert result.winner_agent == "claude"
        assert result.best_answer == "4"
        assert len(result.proposals) == 2
        assert result.refined_answer == "4"


class TestPrompts:
    """Tests for DSPy signature prompts."""

    def test_judge_signature_fields(self):
        from agent_panel.prompts import JudgeSignature
        fields = dir(JudgeSignature)
        # Signatures are DSPy internal classes
        assert hasattr(JudgeSignature, "signature")

    def test_refine_signature_fields(self):
        from agent_panel.prompts import RefineSignature
        assert hasattr(RefineSignature, "signature")


class TestIntegration:
    """Integration tests (require API keys)."""

    @pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY") or
        os.environ.get("ANTHROPIC_API_KEY") == "test-key",
        reason="Requires real API keys"
    )
    def test_mock_judge_evaluate(self):
        """Test judge evaluate with mock response."""
        from agent_panel.core import DSPyJudge
        from agent_panel.agents import AgentProposal

        judge = DSPyJudge(model="claude-sonnet-4-5-20250929")
        proposals = [
            AgentProposal(agent="claude", answer="Detailed thoughtful answer", confidence=0.8),
            AgentProposal(agent="openai", answer="Short answer", confidence=0.6),
        ]

        winner, reasoning, conf = judge.evaluate("Test query", proposals)
        assert winner in ["claude", "openai"]
        assert reasoning
        assert 0 <= conf <= 1


class TestCLIArguments:
    """Tests for CLI argument parsing."""

    def test_list_agents_arg(self):
        import subprocess
        result = subprocess.run(
            ["python3", "main.py", "--list-agents"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert result.returncode == 0
        assert "claude" in result.stdout
        assert "coder" in result.stdout

    def test_no_args_shows_help(self):
        import subprocess
        result = subprocess.run(
            ["python3", "main.py"],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        assert "query" in result.stdout.lower() or "usage" in result.stdout.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
