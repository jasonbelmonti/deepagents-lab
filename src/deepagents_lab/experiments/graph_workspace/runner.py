"""Real graph/QuickJS infrastructure probes; optional agent-written live runs."""
from __future__ import annotations

import asyncio
import json
from contextlib import nullcontext
from time import perf_counter
from uuid import uuid4
from xml.etree import ElementTree

from deepagents import create_deep_agent
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langsmith import tracing_context

from deepagents_lab.benchmarks.incident_metrics import ModelMeasurements
from .store import GraphStore, Query
from .tools import ARMS, GraphTools

# Deliberately keep view in a top-level variable so thread snapshot size reflects
# materialization. This is a controlled recipe, not agent-generated code.
PROGRAM = """
var view = await tools.readGraph({});
var q = view.query;
var answers;
if (view.answers) {
    answers = view.answers;
} else {
    var people = new Map(view.people.map(p => [p.id, p]));
    var adjacency = new Map();
    for (var e of view.edges) {
        if (e.kind !== 'collaborated' || e.last_seen < q.since) continue;
        if (!adjacency.has(e.source)) adjacency.set(e.source, []);
        adjacency.get(e.source).push(e.target);
    }
    for (var neighbors of adjacency.values()) neighbors.sort();
    var queue = [[q.root]];
    var seen = new Set([q.root]);
    var found = [];
    for (var index = 0; index < queue.length; index++) {
        var path = queue[index], id = path[path.length - 1];
        if (path.length > 1 && people.get(id)?.topic === q.topic)
            found.push({person_id: id, path});
        if (path.length - 1 >= q.max_hops) continue;
        for (var next of adjacency.get(id) || []) {
            if (!seen.has(next)) { seen.add(next); queue.push([...path, next]); }
        }
    }
    found.sort((a,b) => a.path.length - b.path.length || a.person_id.localeCompare(b.person_id));
    answers = found.slice(0, q.limit);
}
JSON.stringify(answers);
"""


class RecipeModel(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


async def run_probe(
    store: GraphStore, query: Query, arm: str, *, mode: str = "turn",
    model=None, byte_budget: int = 8_000_000, program: str = PROGRAM,
) -> dict:
    """Live when model is supplied; otherwise no provider call or token claims."""
    from langchain_quickjs import CodeInterpreterMiddleware

    if arm not in ARMS or mode not in ("turn", "thread"):
        raise ValueError("Unknown materialization arm or persistence mode.")
    live = model is not None
    revision = store.revision
    try:
        expected = store.answer(query, revision)  # correctness oracle, outside timing
    except Exception as error:
        return {
            "arm": arm, "mode": mode, "live": live, "revision": revision, "valid": False,
            "error_type": type(error).__name__, "error": str(error), "phase": "oracle",
            "elapsed_ms": None, "tool_calls": [], "response_bytes": 0, "backend_ms": 0,
        }
    boundary = GraphTools(store, query, revision, arm, byte_budget=byte_budget)
    measurements = ModelMeasurements()
    if not live:
        model = RecipeModel(responses=[
            AIMessage(content="", tool_calls=[{"name": "eval", "args": {"code": program}, "id": "recipe", "type": "tool_call"}]),
            AIMessage(content="Infrastructure probe complete."),
        ])
    agent = create_deep_agent(
        model=model, tools=[],
        checkpointer=InMemorySaver() if mode == "thread" else None,
        middleware=[CodeInterpreterMiddleware(
            ptc=boundary.tools(), subagents=False, mode=mode, timeout=5,
            memory_limit=64 * 1024 * 1024, max_ptc_calls=8, max_result_chars=16000,
        )],
    )
    prompt = (
        "Use eval and tools.readGraph({}) to answer this fixed investigation. "
        "The tool returns query and revision. For people/edges, find people with the query topic "
        "reachable from root along directed collaborated edges with last_seen >= since, within max_hops. "
        "Exclude root. Choose each person's shortest path, breaking path ties lexicographically. "
        "Rank by hop count then person_id, retain query.limit people. Return objects {person_id, path}. "
        "If the tool returns answers, use them unchanged. Return JSON.stringify(answerArray) from eval "
        "and only the resulting JSON as your final answer. No other tools or logging."
    )
    row = {"arm": arm, "mode": mode, "live": live, "revision": revision, "valid": False}
    run_config = {
        "callbacks": [measurements], "recursion_limit": 20,
        "configurable": {"thread_id": str(uuid4())},
    }
    started = perf_counter()
    try:
        with nullcontext() if live else tracing_context(enabled=False):
            async with asyncio.timeout(120):
                result = await agent.ainvoke({"messages": [{"role": "user", "content": prompt}]}, config=run_config)
                row["elapsed_ms"] = (perf_counter() - started) * 1000
                # Private middleware state is omitted from normal graph output.
                state = (await agent.aget_state(run_config)).values if mode == "thread" else {}
        outputs = [m for m in result["messages"] if isinstance(m, ToolMessage)]
        names = [name for call in measurements.calls.values() for name in call.get("tool_names", [])]
        # No masked interpreter errors, missing work, stale reads or partial answers.
        parsed = []
        for output in outputs:
            envelope = ElementTree.fromstring(output.text)
            if output.name != "eval" or output.status == "error" or envelope.tag != "result":
                raise ValueError("Unsuccessful or unexpected tool execution.")
            parsed.append(json.loads(envelope.text or "null"))
        usage = measurements.totals()
        final_ok = not live or json.loads(result["messages"][-1].text) == expected
        row["validation"] = {
            "interpreter_answer": bool(parsed) and parsed[-1] == expected,
            "final_answer": final_ok,
            "path": bool(names) and set(names) == {"eval"},
            "work": bool(boundary.calls) and all(call["ok"] for call in boundary.calls),
            "usage": not live or usage["usage_complete"],
            "revision": store.revision == revision,
        }
        row["valid"] = all(row["validation"].values())
        row["answers"] = parsed[-1] if parsed else None
        row["snapshot_bytes"] = len(state.get("_quickjs_snapshot_payload") or b"")
        if mode == "thread" and not row["snapshot_bytes"]:
            raise ValueError("Thread snapshot was unavailable; persistence measurement invalid.")
        row["model_calls"] = usage["model_calls"] if live else None
        row["input_tokens"] = usage["input_tokens"] if live else None
        row["output_tokens"] = usage["output_tokens"] if live else None
        row["total_tokens"] = usage["total_tokens"] if live else None
    except Exception as error:
        row.update(valid=False, error_type=type(error).__name__, error=str(error), elapsed_ms=(perf_counter() - started) * 1000)
    row["tool_calls"] = boundary.calls
    row["response_bytes"] = sum(call["response_bytes"] for call in boundary.calls)
    row["backend_ms"] = sum(call["backend_ms"] for call in boundary.calls)
    return row


async def compare(store: GraphStore, query: Query, *, repeats: int = 3) -> list[dict]:
    """Rotate arm order; preserve every trial, including invalid attempts."""
    if not 1 <= repeats <= 20:
        raise ValueError("Use 1–20 repeats.")
    rows = []
    for repeat in range(repeats):
        for arm in ARMS[repeat % 3:] + ARMS[:repeat % 3]:
            rows.append({**await run_probe(store, query, arm), "repeat": repeat + 1})
    return rows
