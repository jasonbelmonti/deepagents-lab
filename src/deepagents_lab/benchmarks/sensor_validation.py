"""Run-local evidence for the introductory sensor comparison."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any
from xml.etree import ElementTree

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, LLMResult

from deepagents_lab.benchmarks.incident_metrics import ModelMeasurements


class SensorMeasurements(ModelMeasurements):
    """Capture actual tool executions, including calls bridged through QuickJS."""

    def __init__(self) -> None:
        super().__init__()
        self.tool_calls: dict[str, dict[str, Any]] = {}
        self._sequence = 0

    def on_chat_model_start(self, serialized: Any, messages: Any, *, run_id: Any, **kwargs: Any) -> None:
        super().on_chat_model_start(serialized, messages, run_id=run_id, **kwargs)
        available_specs = {}
        for message in messages[0]:
            if isinstance(message, ToolMessage) and message.name == "get_sensor_spec" and message.status == "success":
                try:
                    spec = json.loads(message.text)
                    available_specs[spec["sensor"]] = spec
                except (KeyError, TypeError, ValueError):
                    continue
        with self._lock:
            self.calls[str(run_id)]["available_specs"] = available_specs

    def on_llm_end(self, response: LLMResult, *, run_id: Any, **kwargs: Any) -> None:
        super().on_llm_end(response, run_id=run_id, **kwargs)
        generation = response.generations[0][0] if response.generations and response.generations[0] else None
        if isinstance(generation, ChatGeneration) and isinstance(generation.message, AIMessage):
            with self._lock:
                self.calls[str(run_id)]["score_sensors"] = [
                    call["args"].get("sensor") for call in generation.message.tool_calls
                    if call["name"] == "score_reading"
                ]

    def on_tool_start(
        self, serialized: dict[str, Any], input_str: str, *, run_id: Any,
        inputs: dict[str, Any] | None = None, **kwargs: Any,
    ) -> None:
        with self._lock:
            self._sequence += 1
            self.tool_calls[str(run_id)] = {
                "name": serialized.get("name"), "inputs": dict(inputs or {}),
                "started": self._sequence, "ended": None, "ok": False,
            }

    def on_tool_end(self, output: Any, *, run_id: Any, **kwargs: Any) -> None:
        with self._lock:
            self._sequence += 1
            call = self.tool_calls[str(run_id)]
            ok = not (isinstance(output, ToolMessage) and output.status == "error")
            if call["name"] == "eval":
                # QuickJS 0.3.5 wraps interpreter errors in success-status messages.
                # Its optional stdout is unescaped; only parse the final envelope.
                text = output.text if isinstance(output, ToolMessage) else str(output)
                envelope = text.rsplit("</stdout>\n", 1)[-1]
                try:
                    ok = ok and ElementTree.fromstring(envelope).tag == "result"
                except ElementTree.ParseError:
                    ok = False
            call.update(ended=self._sequence, ok=ok)

    # Errors leave ok=False and ended=None, so failed/retried work cannot pass.


def require_valid_sensor_run(
    result: dict[str, Any], measurements: SensorMeasurements,
    readings: list[dict[str, Any]], specs: dict[str, dict[str, Any]], arm: str,
) -> None:
    """Raise before comparison if answers, work, order, path or usage differ."""
    if arm not in ("ordinary", "ptc"):
        raise ValueError("arm must be 'ordinary' or 'ptc'")
    expected = []
    for reading in readings:
        spec = specs[reading["sensor"]]
        deviation = round((reading["observed"] - spec["expected"]) / spec["expected"] * 100, 2)
        if abs(deviation) > spec["tolerance_pct"]:
            expected.append({"sensor": reading["sensor"], "deviation_pct": deviation, "status": "investigate"})
    expected.sort(key=lambda row: abs(row["deviation_pct"]), reverse=True)
    try:
        answer_correct = json.loads(result["messages"][-1].text) == expected
    except (IndexError, KeyError, TypeError, ValueError):
        answer_correct = False

    calls = list(measurements.tool_calls.values())
    names = [name for call in measurements.calls.values() for name in call.get("tool_names", [])]
    allowed = {"get_sensor_spec", "score_reading"}
    path_correct = bool(names) and (
        set(names) <= allowed if arm == "ordinary" else names == ["eval"]
    )
    allowed_executions = allowed if arm == "ordinary" else allowed | {"eval"}
    path_correct = path_correct and all(call["name"] in allowed_executions for call in calls)
    path_correct = path_correct and sum(call["name"] == "eval" for call in calls) == (arm == "ptc")

    application_calls = [call for call in calls if call["name"] in allowed]
    expected_keys = Counter((name, reading["sensor"]) for name in allowed for reading in readings)
    actual_keys = Counter((call["name"], call["inputs"].get("sensor")) for call in application_calls)
    coverage_correct = actual_keys == expected_keys and all(call["ok"] for call in calls)
    arguments_correct = coverage_correct
    if coverage_correct:
        indexed = {(call["name"], call["inputs"]["sensor"]): call for call in application_calls}
        for reading in readings:
            sensor = reading["sensor"]
            spec = specs[sensor]
            lookup, score = indexed[("get_sensor_spec", sensor)], indexed[("score_reading", sensor)]
            arguments_correct = arguments_correct and lookup["inputs"] == {"sensor": sensor}
            arguments_correct = arguments_correct and score["inputs"] == {
                **reading, "expected": spec["expected"], "tolerance_pct": spec["tolerance_pct"],
            }
            arguments_correct = arguments_correct and lookup["ended"] < score["started"]

    if arm == "ordinary":
        # Tool scheduling order is not proof the model received the lookup result.
        for call in measurements.calls.values():
            sensors = call.get("score_sensors", [])
            arguments_correct = arguments_correct and len(sensors) == call.get("tool_names", []).count("score_reading")
            arguments_correct = arguments_correct and all(
                sensor in specs and call.get("available_specs", {}).get(sensor) == {"sensor": sensor, **specs[sensor]}
                for sensor in sensors
            )

    checks = {
        "answer": answer_correct, "coverage": coverage_correct,
        "arguments/dependencies": arguments_correct, "path": path_correct,
        "usage": measurements.totals()["usage_complete"],
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"{arm} sensor run invalid ({', '.join(failed)}); no efficiency comparison.")
