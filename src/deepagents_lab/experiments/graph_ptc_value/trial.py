"""One real DeepAgents invocation; validation and accounting stay separate."""
import asyncio
import json
from contextlib import nullcontext
from time import perf_counter
from uuid import uuid4
from xml.etree import ElementTree

from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model
from langchain_core.messages import ToolMessage
from langsmith import tracing_context

from .config import ARMS, Config, Scenario
from .coverage import sufficient_reads
from .fixture import make_graph
from .measurements import GraphMeasurements, backend_snapshot
from .oracle import expected_answer
from .prompts import prompt_for
from .tools import GraphAPI


def model_settings(config):
    settings = {"timeout": config.model_timeout, "max_retries": 0}
    if config.model.startswith("openai:"):
        settings["use_responses_api"] = True
    return settings


def build_agent(model, api, arm, config):
    from langchain_quickjs import CodeInterpreterMiddleware

    if arm not in ARMS:
        raise ValueError("Unknown arm.")
    tools = api.tools()
    middleware = [] if arm == "ordinary" else [CodeInterpreterMiddleware(
        ptc=tools if arm == "ptc" else None, subagents=False, mode="turn",
        timeout=config.interpreter_timeout, max_ptc_calls=config.max_tool_calls,
        memory_limit=64 * 1024 * 1024, max_result_chars=32000,
    )]
    return create_deep_agent(model=model, tools=[] if arm == "ptc" else tools, middleware=middleware)


def exact_json(text, expected):
    try:
        # Canonical serialization also rejects bool/float impersonation of counts.
        return json.dumps(json.loads(text), sort_keys=True) == json.dumps(expected, sort_keys=True)
    except (ValueError, TypeError):
        return False


def validate(result, expected, api, measurements, arm, case):
    names = [name for row in measurements.calls.values() for name in row.get("tool_names", [])]
    allowed = {t.name for t in api.tools()} | ({"eval"} if arm == "compute" else set())
    route_ok = bool(names) and set(names) <= ({"eval"} if arm == "ptc" else allowed)
    interpreter_ok = True
    if arm == "ptc":
        outputs = [m for m in result["messages"] if isinstance(m, ToolMessage) and m.name == "eval"]
        try:
            envelope = ElementTree.fromstring(outputs[-1].text)
            interpreter_ok = outputs[-1].status != "error" and envelope.tag == "result" and exact_json(envelope.text, expected)
        except (ElementTree.ParseError, IndexError):
            interpreter_ok = False
    return {
        "answer_correct": exact_json(result["messages"][-1].text, expected),
        "route_ok": route_ok,
        "interpreter_ok": interpreter_ok,
        "sufficient_graph_evidence": sufficient_reads(api, case, expected),
    }


async def run_trial(config: Config, case: Scenario, seed: int, arm: str, *, model=None):
    """Injected models are ALWAYS scripted evidence, never live measurements."""
    live = model is None
    api = GraphAPI(make_graph(seed, case.width), max_calls=config.max_tool_calls, concurrency=config.concurrency)
    expected = expected_answer(api.data, case)
    measurements = GraphMeasurements()
    run_id = uuid4()
    row = dict(case=case.name, seed=seed, arm=arm, run_id=str(run_id),
               evidence_kind="live" if live else "scripted", correct=False, valid=False)
    started = None
    try:
        if model is None:
            model = init_chat_model(config.model, **model_settings(config))
        agent = build_agent(model, api, arm, config)
        started = perf_counter()
        with nullcontext() if live else tracing_context(enabled=False):
            async with asyncio.timeout(config.run_timeout):
                result = await agent.ainvoke(
                    {"messages": [{"role": "user", "content": prompt_for(case, api.data.root, arm, config)}]},
                    config={"callbacks": [measurements], "run_id": run_id,
                            "run_name": f"graph-ptc-value-{arm}", "tags": ["graph-ptc-value", arm],
                            "metadata": {"case": case.name, "seed": seed},
                            "configurable": {"thread_id": str(run_id)}, "recursion_limit": config.recursion_limit},
                )
        row["elapsed_seconds"] = perf_counter() - started
        row["validation"] = validate(result, expected, api, measurements, arm, case)
        row["correct"] = all(row["validation"].values())
        row["final_text"] = result["messages"][-1].text
        row["eval_calls"] = [{"status": m.status, "output": m.text} for m in result["messages"]
                             if isinstance(m, ToolMessage) and m.name == "eval"]
    except asyncio.CancelledError:
        row.update(error_type="CancelledError", interrupted=True,
                   elapsed_seconds=perf_counter() - started if started is not None else None)
    except Exception as error:
        row.update(error_type=type(error).__name__, error_status=getattr(error, "status_code", None),
                   elapsed_seconds=perf_counter() - started if started is not None else None)
    row.update(measurements.totals())
    row["model_call_details"] = list(measurements.calls.values())
    if not live:
        # Fake-model metadata is not real usage, even if a test supplies numbers.
        for field in ("input_tokens", "output_tokens", "total_tokens", "cache_read_tokens", "reasoning_tokens"):
            row[field] = None
        row["usage_complete"] = False
        for call in row["model_call_details"]:
            call["usage"] = None
    row["valid"] = row["correct"] and row["usage_complete"] and live
    row.update(backend_snapshot(api, aborted="error_type" in row))
    return row
