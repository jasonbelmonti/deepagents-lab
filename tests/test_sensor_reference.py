"""Exercise the notebook's actual tools, callbacks and comparison cell offline."""

from __future__ import annotations

import asyncio
import copy
import json
from pathlib import Path
from typing import Any

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage

from deepagents_lab.benchmarks.sensor_validation import require_valid_sensor_run


class ScriptedModel(FakeMessagesListChatModel):
    def bind_tools(self, tools: Any, **kwargs: Any) -> ScriptedModel:
        return self


EXPECTED = [
    {"sensor": "vibration-b", "deviation_pct": 34.0, "status": "investigate"},
    {"sensor": "thermal-b", "deviation_pct": 19.0, "status": "investigate"},
    {"sensor": "pressure-a", "deviation_pct": -9.0, "status": "investigate"},
    {"sensor": "voltage-b", "deviation_pct": -5.36, "status": "investigate"},
]


@pytest.fixture
def notebook(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    pytest.importorskip("langchain_quickjs")
    dotenv = pytest.importorskip("dotenv")
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: False)
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "false")
    path = Path(__file__).parents[1] / "notebooks/reference/ptc-code-interpreter.ipynb"
    document = json.loads(path.read_text())
    scope: dict[str, Any] = {"__name__": __name__}
    for cell in document["cells"]:
        source = "".join(cell["source"])
        if cell["cell_type"] == "code" and "live" not in cell.get("metadata", {}).get("tags", []):
            exec(compile(source, str(path), "exec"), scope)
        if cell["cell_type"] == "code" and source.startswith("require_valid_sensor_run("):
            scope["comparison_cell"] = source
    return scope


def run_sensor(notebook: dict[str, Any], arm: str, *, skip_tools: bool = False, answer: Any = EXPECTED):
    calls = []
    if not skip_tools and arm == "ordinary":
        calls = [[{"name": "get_sensor_spec", "args": {"sensor": r["sensor"]}} for r in notebook["READINGS"]]]
        calls.append([{"name": "score_reading", "args": {
            **r, "expected": notebook["SENSOR_SPECS"][r["sensor"]]["expected"],
            "tolerance_pct": notebook["SENSOR_SPECS"][r["sensor"]]["tolerance_pct"],
        }} for r in notebook["READINGS"]])
    elif not skip_tools:
        code = f"""
const readings = {json.dumps(notebook['READINGS'])};
const specs = await Promise.all(readings.map(r => tools.getSensorSpec({{sensor: r.sensor}})));
const scores = await Promise.all(readings.map((r, i) => tools.scoreReading({{
    ...r, expected: specs[i].expected, tolerance_pct: specs[i].tolerance_pct
}})));
JSON.stringify(scores.filter(r => r.status === 'investigate')
    .sort((a, b) => Math.abs(b.deviation_pct) - Math.abs(a.deviation_pct)));
"""
        calls = [[{"name": "eval", "args": {"code": code}}]]
    responses = [AIMessage(content="", tool_calls=[
        {**call, "id": f"{stage}-{i}", "type": "tool_call"} for i, call in enumerate(batch)
    ]) for stage, batch in enumerate(calls)]
    responses.append(AIMessage(content=json.dumps(answer)))
    for response in responses:
        response.usage_metadata = {"input_tokens": 100, "output_tokens": 10, "total_tokens": 110}
    return asyncio.run(notebook["measured_invoke"](
        ScriptedModel(responses=responses), "Run the sensor workflow.", "offline-test",
        use_interpreter=arm == "ptc",
    ))


def test_real_tool_paths_pass_the_actual_comparison_cell(notebook: dict[str, Any]) -> None:
    for arm in ("ordinary", "ptc"):
        result, metrics, evidence = run_sensor(notebook, arm)
        require_valid_sensor_run(result, evidence, notebook["READINGS"], notebook["SENSOR_SPECS"], arm)
        assert len(evidence.tool_calls) == (16 if arm == "ordinary" else 17)
        assert metrics.model_calls == (3 if arm == "ordinary" else 2)
        assert metrics.total_tokens == metrics.model_calls * 110
        prefix = "baseline" if arm == "ordinary" else "ptc"
        notebook.update({f"{prefix}_result": result, f"{prefix}_metrics": metrics, f"{prefix}_evidence": evidence})
    displayed = []
    notebook["display"] = displayed.append
    exec(notebook["comparison_cell"], notebook)
    assert len(displayed) == 1
    assert "Ordinary tools" in displayed[0].data


@pytest.mark.parametrize("answer", [EXPECTED, [dict(r, status="nominal", deviation_pct=0) for r in EXPECTED[::-1]]])
def test_actual_comparison_cell_rejects_skipped_ptc_work(notebook: dict[str, Any], answer: Any) -> None:
    notebook["baseline_result"], notebook["baseline_metrics"], notebook["baseline_evidence"] = run_sensor(notebook, "ordinary")
    notebook["ptc_result"], notebook["ptc_metrics"], notebook["ptc_evidence"] = run_sensor(notebook, "ptc", skip_tools=True, answer=answer)
    displayed = []
    notebook["display"] = displayed.append
    with pytest.raises(ValueError, match="no efficiency comparison"):
        exec(notebook["comparison_cell"], notebook)
    assert not displayed


@pytest.mark.parametrize("defect", ["wrong", "order", "extra", "missing", "arguments", "dependency", "duplicate", "failed", "path", "usage"])
def test_gate_rejects_corrupted_run_evidence(notebook: dict[str, Any], defect: str) -> None:
    result, _, evidence = run_sensor(notebook, "ordinary")
    rows = copy.deepcopy(EXPECTED)
    if defect == "wrong":
        rows[0]["deviation_pct"] = 0
    elif defect == "order":
        rows.reverse()
    elif defect == "extra":
        rows.append(dict(rows[0]))
    elif defect == "missing":
        rows.pop()
    elif defect in ("arguments", "dependency", "failed"):
        score = next(c for c in evidence.tool_calls.values() if c["name"] == "score_reading")
        if defect == "arguments":
            score["inputs"]["observed"] += 1
        elif defect == "dependency":
            score["started"] = 0
        else:
            score["ok"] = False
    elif defect == "duplicate":
        evidence.tool_calls["duplicate"] = copy.deepcopy(next(iter(evidence.tool_calls.values())))
    elif defect == "path":
        next(iter(evidence.calls.values()))["tool_names"] = ["eval"]
    else:
        next(iter(evidence.calls.values()))["usage"] = None
    result["messages"][-1] = AIMessage(content=json.dumps(rows))
    with pytest.raises(ValueError, match="no efficiency comparison"):
        require_valid_sensor_run(result, evidence, notebook["READINGS"], notebook["SENSOR_SPECS"], "ordinary")
