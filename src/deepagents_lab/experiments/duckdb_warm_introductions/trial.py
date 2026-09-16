"""Fresh matched agents, exact fixture grading and per-attempt evidence."""

import asyncio
from functools import partial
import json
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from deepagents import create_deep_agent
from langchain_core.runnables import RunnableLambda

from deepagents_lab.benchmarks.incident_metrics import ModelMeasurements

from .prompts import COMMON_SYSTEM, TRANSPORT
from .timing import MeasuredCodeInterpreterMiddleware
from .tools import NetworkTools


class TrialMeasurements(ModelMeasurements):
    """Keep generated calls even if the agent later fails and loses graph state."""

    def on_llm_end(self, response, *, run_id, **kwargs):
        super().on_llm_end(response, run_id=run_id, **kwargs)
        generation = response.generations[0][0] if response.generations and response.generations[0] else None
        message = getattr(generation, "message", None)
        if message is not None:
            with self._lock:
                self.calls[str(run_id)]["tool_requests"] = message.tool_calls


def build_agent(model, arm: str, bridge: NetworkTools):
    interpreter = None
    middleware = []
    if arm == "interpreter":
        interpreter = MeasuredCodeInterpreterMiddleware(
            ptc=bridge.tools(), subagents=False, mode="turn",
            timeout=10.0, max_ptc_calls=12, max_result_chars=8000,
        )
        middleware.append(interpreter)
    agent = create_deep_agent(
        model=model,
        tools=bridge.tools() if arm == "ordinary" else [],
        middleware=middleware,
        system_prompt=COMMON_SYSTEM + "\n\n" + TRANSPORT[arm],
    )
    return agent, interpreter


def grade(final_text: str, expected: dict, arm: str, calls: list[dict], model_calls: list[dict]) -> dict:
    try:
        # Comparing canonical JSON also rejects booleans/floats masquerading as integer fields.
        answer_correct = json.dumps(json.loads(final_text), sort_keys=True) == json.dumps(expected, sort_keys=True)
    except (ValueError, TypeError):
        answer_correct = False
    names = [name for call in model_calls for name in call.get("tool_names", [])]
    allowed = {"duckdb_schema", "query_duckdb"} if arm == "ordinary" else {"eval"}
    route_correct = bool(names) and set(names) <= allowed and any(
        call["kind"] == "query" and call.get("result", {}).get("ok") for call in calls
    )
    return {"answer_correct": answer_correct, "route_correct": route_correct}


async def run_trial(
    model, arm: str, database: Path, prompt: str, expected: dict, *,
    mode: str = "scripted", log_path: Path | None = None, timeout: float = 90,
) -> dict:
    """Time invocation only; preserve failed attempts and unknown provider usage."""
    if arm not in TRANSPORT or mode not in {"scripted", "live"}:
        raise ValueError("Use ordinary/interpreter and scripted/live")
    bridge = NetworkTools(database)
    measurements = TrialMeasurements()
    config = {"configurable": {"thread_id": str(uuid4())}, "recursion_limit": 16,
              "callbacks": [measurements]}
    interpreter = None
    messages, error = [], None
    elapsed = None
    invocation_wall_seconds = None
    interpreter_cleanup_seconds = 0.0
    try:
        agent, interpreter = build_agent(model, arm, bridge)
        started = perf_counter()
        try:
            async with asyncio.timeout(timeout):
                result = await agent.ainvoke(
                    {"messages": [{"role": "user", "content": prompt}]}, config=config,
                )
            messages = result["messages"]
        finally:
            invocation_wall_seconds = perf_counter() - started
            # QuickJS automatically evicts its REPL inside ainvoke. The explicit
            # cleanup below is only a fallback and is already outside this timer.
            interpreter_cleanup_seconds = interpreter.cleanup_seconds if interpreter else 0.0
            elapsed = invocation_wall_seconds - interpreter_cleanup_seconds
    except Exception as exc:
        error = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        if interpreter is not None:
            try:
                cleanup = RunnableLambda(partial(interpreter.aafter_agent, runtime=None))
                await cleanup.ainvoke({}, config=config)
            except Exception as exc:
                error = error or {"type": type(exc).__name__, "message": f"Cleanup: {exc}"}
    final_text = messages[-1].text if messages else ""
    model_calls = list(measurements.calls.values())
    checks = grade(final_text, expected, arm, bridge.calls, model_calls)
    totals = measurements.totals()
    if mode == "scripted":
        # Scripted runs prove execution only, even if a fake model supplies usage.
        totals.update(usage_complete=False, input_tokens=None, output_tokens=None,
                      total_tokens=None, cache_read_tokens=None, reasoning_tokens=None)
    record = {
        "arm": arm, "mode": mode, "prompt": prompt,
        "system_prompt": COMMON_SYSTEM + "\n\n" + TRANSPORT[arm],
        "expected": expected, "error": error, **checks,
        "correct": all(checks.values()) and error is None,
        "elapsed_seconds": elapsed, **totals,
        "invocation_wall_seconds": invocation_wall_seconds,
        "interpreter_cleanup_seconds": interpreter_cleanup_seconds,
        "sql_attempts": len(bridge.calls),
        "sql_errors": sum(not call.get("result", {}).get("ok", False) for call in bridge.calls),
        "sql_result_bytes": sum(call.get("result_bytes", 0) for call in bridge.calls),
        "queries": bridge.calls, "model_call_details": model_calls,
        "messages": [message.model_dump(mode="json") for message in messages],
        "final_text": final_text,
    }
    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = log_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(record, indent=2) + "\n")
        temporary.replace(log_path)
    return record
