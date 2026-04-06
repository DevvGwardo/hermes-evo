"""
DSPy-powered agent panel core.
Runs multiple agents in parallel, evaluates with a DSPy judge, returns the best answer.
"""

import os
import time
import concurrent.futures
from dataclasses import dataclass, field
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import dspy

from .agents import (
    BaseAgent, AgentProposal, get_agent,
    list_agents, AGENT_REGISTRY
)
from .prompts import JudgeSignature, RefineSignature


@dataclass
class PanelResult:
    """Result from a full panel run."""
    query: str
    proposals: list[AgentProposal]
    best_proposal: AgentProposal
    best_answer: str
    refined_answer: Optional[str]
    judge_reasoning: str
    winner_agent: str
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ"))
    metadata: dict = field(default_factory=dict)


class DSPyJudge:
    """
    DSPy-powered judge that scores agent proposals.
    Uses ChainOfThought to generate reasoning before scoring.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        model_provider: str = "anthropic",
        use_cot: bool = True,
        num_candidates: int = 10,
        num_trials: int = 50,
    ):
        self.model = model
        self.model_provider = model_provider
        self.use_cot = use_cot
        self.num_candidates = num_candidates
        self.num_trials = num_trials
        self._lm = None
        self._judge_module = None
        self._optimized = False

    def _get_lm(self):
        """Get or create the language model."""
        if self._lm is not None:
            return self._lm

        if self.model_provider == "anthropic":
            import anthropic
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            self._lm = dspy.Claude(
                model=self.model or "claude-sonnet-4-5-20250929",
                api_key=api_key,
            )
        elif self.model_provider == "openai":
            self._lm = dspy.OpenAI(
                model=self.model or "gpt-4o",
                api_key=os.environ.get("OPENAI_API_KEY", ""),
            )
        else:
            raise ValueError(f"Unknown provider: {self.model_provider}")

        dspy.settings.configure(lm=self._lm)
        return self._lm

    def _build_module(self):
        """Build the judge module based on settings."""
        if self.use_cot:
            return dspy.ChainOfThought(JudgeSignature)
        return dspy.Predict(JudgeSignature)

    def evaluate(
        self,
        query: str,
        proposals: list[AgentProposal],
    ) -> tuple[str, str, float]:
        """
        Evaluate proposals and return (winner_name, reasoning, confidence).

        Args:
            query: The original user query
            proposals: List of agent proposals to evaluate

        Returns:
            Tuple of (winner_agent_name, reasoning, confidence_score)
        """
        lm = self._get_lm()

        if not self._judge_module:
            self._judge_module = self._build_module()

        # Format proposals for the judge
        proposals_text = self._format_proposals(proposals)

        try:
            # Run the judge
            result = self._judge_module(query=query, proposals=proposals_text)

            winner = result.winner.strip()
            reasoning = result.reasoning.strip() if hasattr(result, 'reasoning') else ""

            # Validate winner is in proposals
            winner_names = [p.agent for p in proposals]
            if winner not in winner_names:
                # Try fuzzy match
                for p in proposals:
                    if winner.lower() in p.agent.lower() or p.agent.lower() in winner.lower():
                        winner = p.agent
                        break
                else:
                    # Default to highest confidence
                    best = max(proposals, key=lambda p: p.confidence)
                    winner = best.agent
                    reasoning = f"(Judge output invalid, defaulted to highest confidence) {reasoning}"

            # Calculate confidence from reasoning length and structure
            confidence = self._calc_confidence(reasoning, proposals, winner)

            # Update winner proposal confidence
            for p in proposals:
                if p.agent == winner:
                    p.confidence = confidence
                    p.reasoning = reasoning

            return winner, reasoning, confidence

        except Exception as e:
            # Fallback: return highest confidence proposal
            best = max(proposals, key=lambda p: p.confidence) if proposals else None
            if best:
                return (
                    best.agent,
                    f"[Judge error: {str(e)}, defaulted to {best.agent}]",
                    best.confidence * 0.5
                )
            raise

    def _format_proposals(self, proposals: list[AgentProposal]) -> str:
        """Format proposals into a readable string for the judge."""
        lines = []
        for i, p in enumerate(proposals, 1):
            lines.append(
                f"\n--- Proposal {i}: {p.agent} ---\n"
                f"Answer: {p.answer[:2000]}"
                f"{'...' if len(p.answer) > 2000 else ''}\n"
            )
        return "\n".join(lines)

    def _calc_confidence(
        self,
        reasoning: str,
        proposals: list[AgentProposal],
        winner: str
    ) -> float:
        """Estimate confidence from reasoning quality."""
        base = 0.7
        if not reasoning:
            return 0.4

        # Longer reasoning typically means more careful evaluation
        if len(reasoning) > 200:
            base += 0.1

        # Penalize if judge output looks uncertain
        uncertain_words = ["might", "perhaps", "possibly", "unclear", "difficult"]
        if any(w in reasoning.lower() for w in uncertain_words):
            base -= 0.1

        return max(0.3, min(0.95, base))

    def optimize(self, feedback_data: list[dict], save_path: Optional[str] = None):
        """
        Optimize the judge using MIPRO on feedback data.

        Args:
            feedback_data: List of dicts with keys: query, proposals, chosen_agent, score
            save_path: Optional path to save optimized state
        """
        try:
            from dspy.teleprompt import MIPRO

            # Build trainset from feedback
            trainset = []
            for item in feedback_data:
                proposal_str = self._format_proposals(item["proposals"])
                trainset.append(
                    dspy.Example(
                        query=item["query"],
                        proposals=proposal_str,
                        winner=item["chosen_agent"],
                    ).with_inputs("query", "proposals")
                )

            if len(trainset) < 3:
                print(f"Warning: need at least 3 examples to optimize, got {len(trainset)}")
                return

            # Metric
            def judge_metric(example, pred, trace=None):
                return pred.winner.strip().lower() == example.winner.strip().lower()

            self._judge_module = self._build_module()

            optimizer = MIPRO(
                metric=judge_metric,
                num_candidates=self.num_candidates,
                init_temperature=1.0,
                verbose=True,
            )

            optimized = optimizer.compile(
                self._judge_module,
                trainset=trainset,
                num_trials=self.num_trials,
            )

            self._judge_module = optimized
            self._optimized = True

            if save_path:
                import json
                with open(save_path, "w") as f:
                    json.dump({"optimized": True, "num_examples": len(trainset)}, f)

            print(f"Optimized judge on {len(trainset)} examples.")

        except ImportError:
            print("MIPRO optimizer not available. Install: pip install dspy[anthropic]")


class AgentPanel:
    """
    Main panel orchestrator.
    Runs multiple agents in parallel, evaluates with DSPy judge, returns best answer.
    """

    def __init__(
        self,
        judge_model: Optional[str] = None,
        judge_provider: str = "anthropic",
        max_parallel: int = 5,
        timeout_per_agent: int = 120,
        min_proposals: int = 2,
        use_refinement: bool = True,
        enable_cot: bool = True,
    ):
        """
        Initialize the agent panel.

        Args:
            judge_model: Model name for the judge (e.g. "claude-sonnet-4-5-20250929")
            judge_provider: "anthropic" or "openai"
            max_parallel: Max parallel agent calls
            timeout_per_agent: Timeout per agent in seconds
            min_proposals: Minimum number of proposals needed
            use_refinement: Whether to refine the best answer after selection
            enable_cot: Use ChainOfThought in the judge
        """
        self.enable_cot = enable_cot
        self.judge = DSPyJudge(
            model=judge_model,
            model_provider=judge_provider,
            use_cot=self.enable_cot,
        )
        self.max_parallel = max_parallel
        self.timeout_per_agent = timeout_per_agent
        self.min_proposals = min_proposals
        self.use_refinement = use_refinement

    def run(
        self,
        query: str,
        agent_types: Optional[list[str]] = None,
        agents: Optional[list[BaseAgent]] = None,
        verbose: bool = True,
    ) -> PanelResult:
        """
        Run the full panel pipeline.

        Args:
            query: The user query to answer
            agent_types: List of agent type names to use (from AGENT_REGISTRY)
            agents: Optional list of pre-configured agent instances
            verbose: Print progress

        Returns:
            PanelResult with all proposals, best answer, and judge reasoning
        """
        if agents is None:
            agent_types = agent_types or ["general", "coder", "researcher"]
            agents = [get_agent(t) for t in agent_types]

        if verbose:
            print(f"\nPanel: running {len(agents)} agents on query: {query[:60]}...")

        # Phase 1: Collect proposals in parallel
        proposals = self._run_agents_parallel(agents, query, verbose)

        if len(proposals) < self.min_proposals:
            raise ValueError(
                f"Need at least {self.min_proposals} proposals, got {len(proposals)}"
            )

        # Phase 2: Judge evaluation
        if verbose:
            print(f"Panel: evaluating {len(proposals)} proposals with DSPy judge...")

        winner_agent, reasoning, confidence = self.judge.evaluate(query, proposals)

        # Find the winning proposal
        best_proposal = next((p for p in proposals if p.agent == winner_agent), proposals[0])

        # Phase 3: Optional refinement
        refined_answer = None
        if self.use_refinement and best_proposal.answer:
            if verbose:
                print(f"Panel: refining best answer from {winner_agent}...")
            refined_answer = self._refine(query, best_proposal.answer)

        final_answer = refined_answer or best_proposal.answer

        return PanelResult(
            query=query,
            proposals=proposals,
            best_proposal=best_proposal,
            best_answer=final_answer,
            refined_answer=refined_answer,
            judge_reasoning=reasoning,
            winner_agent=winner_agent,
            metadata={
                "num_agents": len(agents),
                "refinement_used": refined_answer is not None,
            }
        )

    def _run_agents_parallel(
        self,
        agents: list[BaseAgent],
        query: str,
        verbose: bool,
    ) -> list[AgentProposal]:
        """Run agents in parallel and collect proposals."""
        proposals = []

        def run_single(agent: BaseAgent) -> tuple[str, AgentProposal]:
            try:
                proposal = agent.run(query)
                return (agent.name, proposal)
            except Exception as e:
                return (agent.name, AgentProposal(
                    agent=agent.name,
                    answer=f"[Error: {str(e)}]",
                    confidence=0.0,
                    metadata={"error": str(e)}
                ))

        with ThreadPoolExecutor(max_workers=self.max_parallel) as executor:
            futures = {executor.submit(run_single, agent): agent for agent in agents}

            for future in as_completed(futures, timeout=self.timeout_per_agent):
                agent_name, proposal = future.result()
                proposals.append(proposal)
                if verbose:
                    print(f"  [{agent_name}] {proposal.to_display()}")

        return proposals

    def _refine(self, query: str, best_answer: str) -> Optional[str]:
        """Refine the best answer using DSPy."""
        try:
            lm = self.judge._get_lm()
            if not self.judge._optimized:
                # Skip refinement if judge isn't optimized (to save API calls)
                return None

            refine_module = dspy.Predict(RefineSignature)
            result = refine_module(query=query, best_proposal=best_answer)
            return result.final_answer.strip()

        except Exception as e:
            print(f"Refinement error: {e}")
            return None

    def feedback(
        self,
        query: str,
        proposals: list[AgentProposal],
        chosen_agent: str,
        score: float,
    ):
        """
        Record feedback to improve future judge performance.
        Store locally; call panel.judge.optimize() when ready.
        """
        import json
        from pathlib import Path

        feedback_dir = Path.home() / ".hermes" / "agent-panel-feedback"
        feedback_dir.mkdir(parents=True, exist_ok=True)

        record = {
            "query": query,
            "proposals": [
                {"agent": p.agent, "answer": p.answer, "confidence": p.confidence}
                for p in proposals
            ],
            "chosen_agent": chosen_agent,
            "score": score,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        outfile = feedback_dir / f"feedback_{int(time.time())}.json"
        with open(outfile, "w") as f:
            json.dump(record, f, indent=2)

        return outfile

    def load_feedback(self, limit: int = 100) -> list[dict]:
        """Load recorded feedback for judge optimization."""
        import json
        from pathlib import Path

        feedback_dir = Path.home() / ".hermes" / "agent-panel-feedback"
        if not feedback_dir.exists():
            return []

        files = sorted(feedback_dir.glob("feedback_*.json"), reverse=True)[:limit]
        records = []
        for f in files:
            try:
                with open(f) as fp:
                    records.append(json.load(fp))
            except Exception:
                continue
        return records

    def optimize_judge(self, save_path: Optional[str] = None):
        """Optimize the judge on collected feedback."""
        feedback = self.load_feedback()
        if not feedback:
            print("No feedback data found. Use panel.feedback() to record interactions.")
            return

        proposals = []
        for item in feedback:
            props = [
                AgentProposal(
                    agent=p["agent"],
                    answer=p["answer"],
                    confidence=p.get("confidence", 0.5),
                )
                for p in item.get("proposals", [])
            ]
            item["proposals"] = props

        self.judge.optimize(feedback, save_path=save_path)
