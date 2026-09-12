# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: tags
#     formats: ipynb,py:percent
#     notebook_metadata_filter: kernelspec,jupytext
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.5
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # DeepAgents PTC + code interpreter reference
#
# This notebook demonstrates two related but separate capabilities from
# `langchain-quickjs`:
#
# 1. **Code interpreter:** the agent can call `eval` to run capability-scoped
#    JavaScript inside QuickJS. The interpreter has no host filesystem, network,
#    shell, package-manager, or clock access by default.
# 2. **Programmatic tool calling (PTC):** an explicit allowlist bridges selected
#    agent tools into that JavaScript as asynchronous functions under `tools`.
#
# The Python tool below is deliberately read-only and deterministic. Interpreter
# execution is bounded to five seconds and at most twelve PTC calls per `eval`.
#
# Cells marked **LIVE** call the configured model and incur normal provider usage.
# If LangSmith tracing is enabled in `.env`, those calls also create traces.

# %%
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from dotenv import load_dotenv
from langchain.tools import tool
from langchain_quickjs import CodeInterpreterMiddleware

from deepagents_lab.agent import DEFAULT_MODEL


def find_project_root(start: Path | None = None) -> Path:
    """Find this repository without assuming Jupyter's launch directory."""
    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    raise RuntimeError("Could not find the deepagents-lab project root.")


PROJECT_ROOT = find_project_root()
load_dotenv(PROJECT_ROOT / ".env")
MODEL = os.getenv("DEEPAGENTS_LAB_MODEL", DEFAULT_MODEL)
MODEL

# %% [markdown]
# ## Define the narrow PTC boundary
#
# Only tools included in `CodeInterpreterMiddleware(ptc=[...])` cross the
# interpreter boundary. The snake-case Python name `score_reading` is exposed to
# JavaScript as `tools.scoreReading(...)`.

# %%
@tool
def score_reading(
    sensor: str,
    observed: float,
    expected: float,
    tolerance_pct: float = 5.0,
) -> dict[str, Any]:
    """Score one sensor reading against its expected value.

    Args:
        sensor: Stable sensor identifier.
        observed: Observed numeric value.
        expected: Expected non-zero numeric value.
        tolerance_pct: Maximum acceptable absolute percentage deviation.
    """
    if expected == 0:
        raise ValueError("expected must be non-zero")

    deviation_pct = round(((observed - expected) / expected) * 100, 2)
    return {
        "sensor": sensor,
        "deviation_pct": deviation_pct,
        "status": (
            "nominal" if abs(deviation_pct) <= tolerance_pct else "investigate"
        ),
    }


# The underlying tool is easy to exercise without an LLM or interpreter.
score_reading.invoke(
    {"sensor": "thermal-a", "observed": 104, "expected": 100}
)

# %% [markdown]
# ## Construct the interpreter-enabled agent
#
# `score_reading` remains a normal agent tool, while the `ptc` allowlist also
# makes it callable from inside `eval`. `subagents=False` keeps this reference
# focused on PTC and removes the interpreter's separate `task(...)` bridge.

# %%
interpreter = CodeInterpreterMiddleware(
    ptc=[score_reading],
    subagents=False,
    mode="thread",
    timeout=5.0,
    max_ptc_calls=12,
)
interpreter

# %% tags=["live", "setup"]
if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError(
        "OPENAI_API_KEY is missing. Add it to the repository's ignored .env file."
    )

agent = create_deep_agent(
    model=MODEL,
    tools=[score_reading],
    middleware=[interpreter],
)


def show_run(result: dict[str, Any]) -> None:
    """Print the tool path plus the final answer without provider-specific code."""
    for message in result["messages"]:
        for call in getattr(message, "tool_calls", ()):
            print(f"tool call: {call['name']}")
    print("\nfinal answer:\n", result["messages"][-1].text)

# %% [markdown]
# ## LIVE 1 — capability-scoped code interpretation
#
# This prompt asks the model to use `eval` for deterministic transformation. No
# Python tool needs to cross the interpreter boundary in this run.

# %% tags=["live", "code-interpreter"]
code_interpreter_prompt = """
Use the eval tool exactly once for all computation. In one JavaScript program:

1. Store these latency samples: [42, 35, 51, 35, 47, 39].
2. Sort them numerically.
3. Compute the mean, median, minimum, maximum, and unique values.
4. Assign one JSON-compatible object containing those five results to `summary`.
5. Make `summary;` the program's final expression. Do not use a top-level return.

After eval returns, report its object verbatim and do no additional arithmetic.
""".strip()

code_interpreter_result = await agent.ainvoke(
    {"messages": [{"role": "user", "content": code_interpreter_prompt}]},
    config={"configurable": {"thread_id": "interpreter-reference"}},
)
show_run(code_interpreter_result)

# %% [markdown]
# Expected evidence: `show_run` reports an `eval` tool call, and the final answer
# contains a compact object derived by JavaScript. Inspect the corresponding
# LangSmith trace, when enabled, to see the model → `eval` → model path.

# %% [markdown]
# ## LIVE 2 — programmatic tool calling from JavaScript
#
# This run asks a single JavaScript program to call the allowlisted Python tool
# concurrently, filter intermediate results, and return only actionable rows.
# The model should call `eval`; the interpreter then calls `tools.scoreReading`.

# %% tags=["live", "ptc"]
ptc_prompt = """
Use the eval tool exactly once. Do not call score_reading as a normal agent tool.
Inside one JavaScript program:

1. Define these readings:
   - {sensor: "thermal-a", observed: 104, expected: 100}
   - {sensor: "thermal-b", observed: 119, expected: 100}
   - {sensor: "pressure-a", observed: 91, expected: 100}
   - {sensor: "pressure-b", observed: 98, expected: 100}
2. Call tools.scoreReading for all readings concurrently with Promise.all.
3. Keep only results whose status is "investigate".
4. Sort those results by absolute deviation_pct, largest first, and assign the
   sorted array to `investigate`.
5. Make `investigate;` the program's final expression. Do not use a top-level
   return statement.

After eval returns, report its array verbatim without re-running the tool.
""".strip()

ptc_result = await agent.ainvoke(
    {"messages": [{"role": "user", "content": ptc_prompt}]},
    config={"configurable": {"thread_id": "ptc-reference"}},
)
show_run(ptc_result)

# %% [markdown]
# Expected evidence: the outer agent makes one `eval` call. Within it, QuickJS
# fans out four `tools.scoreReading(...)` calls and returns only the two readings
# outside tolerance. With tracing enabled, use the run tree to compare this
# model → `eval` → PTC-tools → model shape with four ordinary tool round trips.

# %% [markdown]
# ## Suggested variations
#
# - Lower `max_ptc_calls` below the number of readings and observe the bounded
#   failure surfaced to the model.
# - Switch `mode` among `"thread"`, `"turn"`, and `"call"`, then test whether a
#   variable defined by one `eval` is visible to a later invocation.
# - Replace `score_reading` with another narrow, read-only lab tool.
# - Compare trace token counts and elapsed time against ordinary serial tool
#   calls using the same inputs.
