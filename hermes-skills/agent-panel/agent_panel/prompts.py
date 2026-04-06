"""
DSPy signature definitions for agent panel evaluation.
These define the input/output structure for each stage of the pipeline.
"""

import dspy


class JudgeSignature(dspy.Signature):
    """
    Evaluate and score multiple agent proposals for a given user query.
    Return a score and reasoning for which proposal best answers the query.
    """
    query = dspy.InputField(desc="The original user question or task")
    proposals = dspy.InputField(
        desc="List of agent proposals, each with an agent name and their answer"
    )
    winner = dspy.OutputField(desc="The name of the agent with the best answer")
    reasoning = dspy.OutputField(
        desc="Detailed reasoning for why this proposal is best, citing specific strengths"
    )


class RefineSignature(dspy.Signature):
    """
    Take the best proposal and refine it into a final polished answer.
    Keep what works, improve clarity and correctness.
    """
    query = dspy.InputField(desc="The original user question")
    best_proposal = dspy.InputField(desc="The winning agent proposal")
    final_answer = dspy.OutputField(desc="The refined final answer")


class CritiqueSignature(dspy.Signature):
    """
    Provide constructive critique of an agent proposal.
    Identify weaknesses and suggest specific improvements.
    """
    proposal = dspy.InputField(desc="The agent proposal to critique")
    query = dspy.InputField(desc="The original user query")
    critique = dspy.OutputField(desc="Specific critique with actionable suggestions")
    weaknesses = dspy.OutputField(desc="List of specific weaknesses in the proposal")


class AggregateSignature(dspy.Signature):
    """
    Synthesize multiple partial answers into a comprehensive response.
    Used when no single agent has the full picture.
    """
    partial_answers = dspy.InputField(desc="Multiple partial answers from different agents")
    query = dspy.InputField(desc="The original comprehensive question")
    synthesis = dspy.OutputField(
        desc="A complete synthesized answer drawing from all partial answers"
    )
