"""Shared DeepAgents construction for every lab entry point."""

from __future__ import annotations

from deepagents import create_deep_agent
from langgraph.pregel import Pregel

DEFAULT_MODEL = "openai:gpt-5.6-luna"


def create_agent(model: str = DEFAULT_MODEL) -> Pregel:
    """Create the lab's compiled DeepAgents graph for ``model``."""
    return create_deep_agent(model=model)
