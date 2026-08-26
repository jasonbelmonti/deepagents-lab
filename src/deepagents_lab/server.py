"""Agent Server graph export.

The server imports this factory without constructing the provider client. That
keeps startup and basic API discovery credential-free; the graph is compiled
only when the server needs the executable graph.
"""

from __future__ import annotations

from langgraph.pregel import Pregel

from deepagents_lab.agent import create_agent


def graph() -> Pregel:
    """Create the fixed graph registered with the local Agent Server."""
    return create_agent()
