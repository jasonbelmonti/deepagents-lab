"""Run repeatable paired incident-triage experiments from a notebook."""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from time import perf_counter
from typing import Any, Callable
from uuid import uuid4

from deepagents import create_deep_agent
from langchain.chat_models import init_chat_model

from deepagents_lab.agent import DEFAULT_MODEL
from deepagents_lab.benchmarks.incident_fixture import IncidentFixture
from deepagents_lab.benchmarks.incident_metrics import ModelMeasurements, validate_trial
from deepagents_lab.benchmarks.incident_report import render_report, summarize


@dataclass(frozen=True)
class BenchmarkConfig:
    model: str = DEFAULT_MODEL
    pairs: int = 5
    records: int = 20
    payload_bytes: int = 1536
    first_arm: str = "ordinary"
    run_timeout_seconds: float = 180
    model_timeout_seconds: float = 90
    max_retries: int = 0
    recursion_limit: int = 32
    interpreter_timeout_seconds: float = 5
    max_ptc_calls: int = 100

    def __post_init__(self) -> None:
        IncidentFixture(self.records, self.payload_bytes)
        if not 1 <= self.pairs <= 50 or self.first_arm not in ("ordinary", "ptc"):
            raise ValueError("Use 1–50 pairs and first_arm='ordinary' or 'ptc'.")
        if min(self.run_timeout_seconds, self.model_timeout_seconds, self.interpreter_timeout_seconds) <= 0:
            raise ValueError("Timeouts must be positive.")
        if self.max_retries != 0 or self.max_ptc_calls < 4 or self.recursion_limit < 12:
            raise ValueError("Use no SDK retries, at least four PTC calls and recursion_limit >= 12.")


def trial_order(config: BenchmarkConfig, pair: int) -> tuple[str, str]:
    arms = (config.first_arm, "ptc" if config.first_arm == "ordinary" else "ordinary")
    return arms if pair % 2 else arms[::-1]


def prompt_for(arm: str, ids: list[str]) -> str:
    common = f"""Triage all of these incidents: {json.dumps(ids)}.
Use the four batch APIs in dependency order:
1. fetch_incidents(incident_ids) -> records with evidence_ref.
2. fetch_evidence(evidence_refs) -> records with context_ref.
3. fetch_service_context(context_refs) -> records with decision_ref.
4. classify_incidents(decision_refs) -> records with incident_id, priority, owner.
Process every incident once at every stage. Batch all records together at each
stage; follow returned references exactly. Diagnostic history is audit context
and does not need to appear in your answer. Retain P1 and P2 decisions only.
Sort by priority ascending, then incident_id ascending. The final answer must be
only valid JSON: an array of objects with incident_id, priority and owner.
Do not use planning, subagents, filesystem tools or any other unrelated tool.
"""
    if arm == "ordinary":
        return common + "Call the four batch tools directly using normal tool calls."
    return common + """Use eval for the entire workflow, calling the allowlisted tools
from JavaScript as tools.fetchIncidents, tools.fetchEvidence,
tools.fetchServiceContext and tools.classifyIncidents. Arguments remain
snake_case. Tool results are native arrays; use await and map to pass the
references to the next batch. Do not call these tools outside eval.
Make JSON.stringify(filteredAndSortedDecisions) the last expression; do not use
a top-level return statement. Do not log intermediate payloads. Return the
resulting JSON unchanged as your final answer."""


def model_settings(config: BenchmarkConfig) -> dict[str, Any]:
    settings: dict[str, Any] = {"timeout": config.model_timeout_seconds, "max_retries": config.max_retries}
    if config.model.startswith("openai:"):
        # Match DeepAgents' provider default when supplying an explicit client.
        settings["use_responses_api"] = True
    return settings


async def run_trial(config: BenchmarkConfig, arm: str, pair: int, position: int) -> dict[str, Any]:
    from langchain_quickjs import CodeInterpreterMiddleware

    fixture = IncidentFixture(config.records, config.payload_bytes)
    tools = fixture.tools()
    middleware = [] if arm == "ordinary" else [CodeInterpreterMiddleware(
        ptc=tools, subagents=False, mode="call", timeout=config.interpreter_timeout_seconds,
        max_ptc_calls=config.max_ptc_calls, max_result_chars=16000,
    )]
    model = init_chat_model(config.model, **model_settings(config))
    agent = create_deep_agent(model=model, tools=tools, middleware=middleware)
    measurements = ModelMeasurements()
    run_id = uuid4()
    row: dict[str, Any] = {
        "pair": pair, "position": position, "arm": arm, "run_id": str(run_id), "valid": False,
    }
    started = perf_counter()
    try:
        async with asyncio.timeout(config.run_timeout_seconds):
            result = await agent.ainvoke(
                {"messages": [{"role": "user", "content": prompt_for(arm, fixture.ids)}]},
                config={
                    "callbacks": [measurements], "run_id": run_id,
                    "run_name": f"incident-triage-{arm}",
                    "tags": ["incident-triage", arm], "metadata": {"pair": pair, "position": position},
                    "configurable": {"thread_id": str(run_id)},
                    "recursion_limit": config.recursion_limit,
                },
            )
        row["elapsed_seconds"] = perf_counter() - started
        row.update(validate_trial(result, fixture, measurements, arm))
    except Exception as error:
        row["elapsed_seconds"] = perf_counter() - started
        row["error_type"] = type(error).__name__
        row["error_status"] = getattr(error, "status_code", None)
        row["error_code"] = getattr(error, "code", None)
        row["error_param"] = getattr(error, "param", None)
    row.update(measurements.totals())
    row["model_call_details"] = list(measurements.calls.values())
    row["application_tool_calls"] = fixture.calls
    return row


def _manifest(config: BenchmarkConfig) -> dict[str, Any]:
    fixture = IncidentFixture(config.records, config.payload_bytes)
    dataset = [[fixture._record(stage, incident) for incident in fixture.ids] for stage in range(4)]
    return {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "config": asdict(config),
        "model_settings": model_settings(config),
        "versions": {name: version(name) for name in (
            "deepagents", "langchain", "langchain-core", "langchain-openai", "langchain-quickjs", "quickjs-rs",
        )},
        "source_sha256": {
            source.name: hashlib.sha256(source.read_bytes()).hexdigest()
            for source in sorted(Path(__file__).parent.glob("incident_*.py"))
        },
        "fixture_sha256": hashlib.sha256(json.dumps(dataset, sort_keys=True).encode()).hexdigest(),
        "expected": fixture.expected,
        "prompts": {arm: prompt_for(arm, fixture.ids) for arm in ("ordinary", "ptc")},
        "trials": [],
    }


async def run_benchmark(
    config: BenchmarkConfig,
    output_dir: Path,
    progress: Callable[[str], None] = print,
) -> dict[str, Any]:
    """Save each trial immediately; interruptions preserve all completed trials."""
    report = _manifest(config)
    destination = output_dir / f"incident-triage-{uuid4()}"
    destination.mkdir(parents=True, exist_ok=False)
    report["report_path"] = str((destination / "report.json").resolve())

    def save() -> None:
        report["summary"] = summarize(report["trials"])
        temporary = destination / "report.json.tmp"
        temporary.write_text(json.dumps(report, indent=2) + "\n")
        temporary.replace(destination / "report.json")
        (destination / "report.md").write_text(render_report(report))

    save()
    progress(f"Results: {destination}")
    for pair in range(1, config.pairs + 1):
        for position, arm in enumerate(trial_order(config, pair), start=1):
            progress(f"Pair {pair}/{config.pairs}, position {position}: {arm} running")
            row = await run_trial(config, arm, pair, position)
            report["trials"].append(row)
            save()
            progress(
                f"{arm}: valid={row['valid']}, {row['elapsed_seconds']:.2f}s, "
                f"model_calls={row['model_calls']}, total_tokens={row['total_tokens']}"
            )
            last_two = report["trials"][-2:]
            if len(last_two) == 2 and all(
                trial.get("error_type") == row.get("error_type")
                and trial.get("error_status") in (400, 401, 403, 404, 429)
                for trial in last_two
            ):
                report["stop_reason"] = "Repeated provider request failures; fix configuration/access before rerunning."
                save()
                progress(report["stop_reason"])
                return report
    return report
