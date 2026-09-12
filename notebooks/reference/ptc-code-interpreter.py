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
# The Python tools below are deliberately read-only and deterministic.
# Interpreter execution is bounded to five seconds and at most twenty PTC calls
# per `eval`.
#
# The second half runs the same two-stage tool workflow with and without PTC. It
# compares end-to-end latency and the standardized token counts LangChain records
# on each model-generated `AIMessage`. One pair is useful demonstration evidence,
# not a statistically reliable benchmark; network and provider variance still
# apply.
#
# Cells marked **LIVE** call the configured model and incur normal provider usage.
# If LangSmith tracing is enabled in `.env`, those calls also create traces.

# %%
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Any
from uuid import uuid4

from deepagents import create_deep_agent
from dotenv import load_dotenv
from IPython.display import Markdown, display
from langchain.tools import tool
from langchain_core.messages import AIMessage
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
# ## Define a two-stage tool workflow
#
# Each reading must first retrieve its sensor specification and then be scored
# against that specification. This dependency forces at least two tool stages.
# Ordinary tool calling returns the first-stage payloads to the model before it
# can construct the second-stage calls. PTC keeps those intermediate values in
# JavaScript and returns only the filtered result.

# %%
SENSOR_SPECS: dict[str, dict[str, Any]] = {
    "thermal-a": {
        "expected": 100.0,
        "tolerance_pct": 5.0,
        "unit": "°C",
        "calibration_note": "Primary chamber probe; calibrated against reference T-17.",
    },
    "thermal-b": {
        "expected": 100.0,
        "tolerance_pct": 5.0,
        "unit": "°C",
        "calibration_note": "Redundant chamber probe; inspect after sustained divergence.",
    },
    "pressure-a": {
        "expected": 100.0,
        "tolerance_pct": 5.0,
        "unit": "kPa",
        "calibration_note": "Inlet transducer; zeroed before the current test window.",
    },
    "pressure-b": {
        "expected": 100.0,
        "tolerance_pct": 5.0,
        "unit": "kPa",
        "calibration_note": "Outlet transducer; compare with inlet before escalation.",
    },
    "vibration-a": {
        "expected": 50.0,
        "tolerance_pct": 10.0,
        "unit": "mm/s",
        "calibration_note": "Forward bearing channel with a wider transient envelope.",
    },
    "vibration-b": {
        "expected": 50.0,
        "tolerance_pct": 10.0,
        "unit": "mm/s",
        "calibration_note": "Aft bearing channel; investigate persistent high excursions.",
    },
    "voltage-a": {
        "expected": 28.0,
        "tolerance_pct": 3.0,
        "unit": "V",
        "calibration_note": "Primary bus sample taken downstream of regulation.",
    },
    "voltage-b": {
        "expected": 28.0,
        "tolerance_pct": 3.0,
        "unit": "V",
        "calibration_note": "Secondary bus sample; validate load before adjustment.",
    },
}

READINGS = [
    {"sensor": "thermal-a", "observed": 104.0},
    {"sensor": "thermal-b", "observed": 119.0},
    {"sensor": "pressure-a", "observed": 91.0},
    {"sensor": "pressure-b", "observed": 98.0},
    {"sensor": "vibration-a", "observed": 52.0},
    {"sensor": "vibration-b", "observed": 67.0},
    {"sensor": "voltage-a", "observed": 28.4},
    {"sensor": "voltage-b", "observed": 26.5},
]

EXPECTED_INVESTIGATIONS = (
    "vibration-b",
    "thermal-b",
    "pressure-a",
    "voltage-b",
)


@tool
def get_sensor_spec(sensor: str) -> dict[str, Any]:
    """Return the expected value and tolerance for one known sensor.

    Args:
        sensor: Stable sensor identifier.
    """
    try:
        return {"sensor": sensor, **SENSOR_SPECS[sensor]}
    except KeyError as error:
        raise ValueError(f"Unknown sensor: {sensor}") from error


@tool
def score_reading(
    sensor: str,
    observed: float,
    expected: float,
    tolerance_pct: float,
) -> dict[str, Any]:
    """Score one sensor reading against a previously retrieved specification.

    Args:
        sensor: Stable sensor identifier.
        observed: Observed numeric value.
        expected: Expected non-zero numeric value from get_sensor_spec.
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


# Exercise both tools without an LLM or interpreter.
thermal_spec = get_sensor_spec.invoke({"sensor": "thermal-a"})
score_reading.invoke(
    {
        "sensor": thermal_spec["sensor"],
        "observed": 104.0,
        "expected": thermal_spec["expected"],
        "tolerance_pct": thermal_spec["tolerance_pct"],
    }
)

# %% [markdown]
# ## Construct the interpreter boundary and metrics collector
#
# Only tools included in `CodeInterpreterMiddleware(ptc=[...])` cross the
# interpreter boundary. Python names become camel-case JavaScript functions
# (`get_sensor_spec` → `tools.getSensorSpec`), while argument names remain
# snake-case. `subagents=False` removes the separate `task(...)` bridge.
#
# Token counts come from each model-generated `AIMessage.usage_metadata` and are
# summed across the complete agent run. Elapsed time is wall-clock duration around
# `agent.ainvoke`, so it includes model and tool execution plus network latency.
# See the [LangChain message documentation](https://docs.langchain.com/oss/python/langchain/messages#token-usage)
# for the standardized usage fields.

# %%
TOOLS = [get_sensor_spec, score_reading]


def create_interpreter() -> CodeInterpreterMiddleware:
    """Create an isolated interpreter with the experiment's fixed boundaries."""
    return CodeInterpreterMiddleware(
        ptc=TOOLS,
        subagents=False,
        mode="thread",
        timeout=5.0,
        max_ptc_calls=20,
    )


interpreter = create_interpreter()


@dataclass(frozen=True)
class RunMetrics:
    elapsed_seconds: float
    model_calls: int
    input_tokens: int
    output_tokens: int
    total_tokens: int
    graph_tool_calls: int


def collect_metrics(result: dict[str, Any], elapsed_seconds: float) -> RunMetrics:
    """Aggregate standardized token usage from every model response."""
    ai_messages = [
        message
        for message in result["messages"]
        if isinstance(message, AIMessage)
    ]
    usage_rows = [
        message.usage_metadata
        for message in ai_messages
        if message.usage_metadata is not None
    ]
    if len(usage_rows) != len(ai_messages):
        raise RuntimeError("The selected model did not report complete token usage.")

    return RunMetrics(
        elapsed_seconds=round(elapsed_seconds, 3),
        model_calls=len(ai_messages),
        input_tokens=sum(row["input_tokens"] for row in usage_rows),
        output_tokens=sum(row["output_tokens"] for row in usage_rows),
        total_tokens=sum(row["total_tokens"] for row in usage_rows),
        graph_tool_calls=sum(
            len(getattr(message, "tool_calls", ()))
            for message in ai_messages
        ),
    )


async def measured_invoke(agent: Any, prompt: str, label: str):
    """Run one isolated agent thread and return its result plus metrics."""
    started = perf_counter()
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": prompt}]},
        config={
            "configurable": {
                "thread_id": f"{label}-{uuid4()}",
            }
        },
    )
    return result, collect_metrics(result, perf_counter() - started)


def show_run(label: str, result: dict[str, Any], metrics: RunMetrics) -> None:
    """Print the graph-visible tool path, final answer, and measured usage."""
    print(label)
    for message in result["messages"]:
        for call in getattr(message, "tool_calls", ()):
            print(f"tool call: {call['name']}")
    print("metrics:", json.dumps(asdict(metrics), indent=2))
    print("final answer:\n", result["messages"][-1].text)


def reduction_pct(baseline: float, candidate: float) -> str:
    """Format positive values as reductions and negative values as increases."""
    if baseline == 0:
        return "n/a"
    return f"{((baseline - candidate) / baseline) * 100:.1f}%"


def comparison_table(
    baseline: RunMetrics,
    ptc: RunMetrics,
) -> Markdown:
    """Render the measured A/B comparison as a compact notebook table."""
    rows = [
        (
            "End-to-end latency (seconds)",
            f"{baseline.elapsed_seconds:.3f}",
            f"{ptc.elapsed_seconds:.3f}",
            reduction_pct(baseline.elapsed_seconds, ptc.elapsed_seconds),
        ),
        (
            "Model calls",
            str(baseline.model_calls),
            str(ptc.model_calls),
            reduction_pct(baseline.model_calls, ptc.model_calls),
        ),
        (
            "Input tokens",
            str(baseline.input_tokens),
            str(ptc.input_tokens),
            reduction_pct(baseline.input_tokens, ptc.input_tokens),
        ),
        (
            "Output tokens",
            str(baseline.output_tokens),
            str(ptc.output_tokens),
            reduction_pct(baseline.output_tokens, ptc.output_tokens),
        ),
        (
            "Total tokens",
            str(baseline.total_tokens),
            str(ptc.total_tokens),
            reduction_pct(baseline.total_tokens, ptc.total_tokens),
        ),
        (
            "Tool calls added to graph messages",
            str(baseline.graph_tool_calls),
            str(ptc.graph_tool_calls),
            reduction_pct(baseline.graph_tool_calls, ptc.graph_tool_calls),
        ),
    ]
    body = "\n".join(
        f"| {name} | {base} | {new} | {delta} |"
        for name, base, new, delta in rows
    )
    return Markdown(
        "| Metric | Ordinary tools | PTC | PTC reduction |\n"
        "|---|---:|---:|---:|\n"
        f"{body}\n\n"
        "Positive percentages are reductions; negative percentages are increases."
    )

# %% tags=["live", "setup"]
if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError(
        "OPENAI_API_KEY is missing. Add it to the repository's ignored .env file."
    )

code_interpreter_agent = create_deep_agent(
    model=MODEL,
    tools=TOOLS,
    middleware=[create_interpreter()],
)
baseline_agent = create_deep_agent(model=MODEL, tools=TOOLS)
ptc_agent = create_deep_agent(
    model=MODEL,
    tools=TOOLS,
    middleware=[interpreter],
)

# %% [markdown]
# ## LIVE 1 — capability-scoped code interpretation
#
# This prompt asks the model to use `eval` for deterministic transformation. No
# Python tool needs to cross the interpreter boundary in this run. The metrics
# make the cost of this standalone interpreter interaction visible as well.

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

code_interpreter_result, code_interpreter_metrics = await measured_invoke(
    code_interpreter_agent,
    code_interpreter_prompt,
    "interpreter-reference",
)
show_run(
    "CODE INTERPRETER",
    code_interpreter_result,
    code_interpreter_metrics,
)

# %% [markdown]
# Expected evidence: `show_run` reports an `eval` tool call, the final answer
# contains a compact object derived by JavaScript, and the metrics include both
# model calls surrounding `eval`.

# %% [markdown]
# ## LIVE 2A — ordinary two-stage tool calling baseline
#
# The baseline has the same tools but no interpreter. It must return sensor specs
# to the model before the model can build the scoring calls. Tool calls within
# each stage may still run in parallel.

# %% tags=["live", "benchmark"]
baseline_prompt = f"""
Use only get_sensor_spec and score_reading. Do not use task, filesystem tools, or
write_todos.

For every reading below:
1. Call get_sensor_spec for its sensor.
2. Only after the specifications return, call score_reading for every reading
   with observed from the input and expected plus tolerance_pct from its spec.
3. Keep only results whose status is "investigate".
4. Sort by absolute deviation_pct, largest first.
5. Report only the sorted result array.

Readings: {json.dumps(READINGS)}
""".strip()

baseline_result, baseline_metrics = await measured_invoke(
    baseline_agent,
    baseline_prompt,
    "ordinary-tools-baseline",
)
show_run("ORDINARY TOOL CALLING", baseline_result, baseline_metrics)

# %% [markdown]
# ## LIVE 2B — the same workflow through PTC
#
# The outer agent makes one `eval` call. Inside QuickJS, the first `Promise.all`
# retrieves all specifications, the second scores all readings, and JavaScript
# filters the intermediate results before returning to the model.

# %% tags=["live", "benchmark"]
ptc_prompt = f"""
Use the eval tool exactly once. Do not call get_sensor_spec or score_reading as
normal agent tools. Do not use task, filesystem tools, or write_todos.

Inside one JavaScript program:
1. Define these readings: {json.dumps(READINGS)}
2. Call tools.getSensorSpec for every sensor concurrently with Promise.all.
3. After those calls resolve, call tools.scoreReading for every reading
   concurrently with Promise.all. Pass sensor and observed from each reading;
   pass expected and tolerance_pct from its specification. Keep argument names
   snake-case.
4. Keep only results whose status is "investigate".
5. Sort by absolute deviation_pct, largest first, and assign the array to
   `investigate`.
6. Make `investigate;` the final expression. Do not use a top-level return.

After eval returns, report its array verbatim without re-running either tool.
""".strip()

ptc_result, ptc_metrics = await measured_invoke(
    ptc_agent,
    ptc_prompt,
    "ptc-tools-candidate",
)
show_run("PROGRAMMATIC TOOL CALLING", ptc_result, ptc_metrics)

# %% [markdown]
# ## LIVE 2C — compare latency and token usage
#
# Both answers must contain the same four investigations before their efficiency
# numbers are compared. `graph_tool_calls` counts calls represented in graph
# messages: PTC's bridged calls are visible in LangSmith traces but are not added
# as synthetic graph messages, so the PTC row shows the single outer `eval` call.
# Both paths still execute the same sixteen application-tool calls.

# %% tags=["live", "benchmark"]
for sensor in EXPECTED_INVESTIGATIONS:
    assert sensor in baseline_result["messages"][-1].text
    assert sensor in ptc_result["messages"][-1].text

display(comparison_table(baseline_metrics, ptc_metrics))

# %% [markdown]
# ## Interpret the result responsibly
#
# The token totals are provider-reported usage for every model call in each
# complete run. PTC should remove a model round trip and keep specification
# payloads out of model context for this workload. Latency is noisier: connection
# setup, provider load, and run order can dominate a single pair.
#
# For decision-grade evidence, run at least five paired trials, alternate which
# path runs first, report median and tail latency, retain the exact model/config,
# and compare LangSmith traces. Do not claim a general PTC speedup from this one
# synthetic workload.

# %% [markdown]
# ## Suggested variations
#
# - Increase the number or size of intermediate specification payloads and watch
#   how input-token savings scale.
# - Lower `max_ptc_calls` below sixteen and observe the bounded failure surfaced
#   to the model.
# - Switch `mode` among `"thread"`, `"turn"`, and `"call"`, then test whether a
#   variable defined by one `eval` is visible to a later invocation.
# - Replace these read-only tools with an investigation-specific workflow, then
#   promote repeated measurements into the lab's evaluation harness.
