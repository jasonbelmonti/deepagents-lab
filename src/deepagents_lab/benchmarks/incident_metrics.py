"""Per-model-call token accounting and strict benchmark correctness checks."""

from __future__ import annotations

import json
from threading import Lock
from time import perf_counter
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, LLMResult


class ModelMeasurements(BaseCallbackHandler):
    """Capture model completions, including any omitted from final graph state."""

    def __init__(self) -> None:
        self.calls: dict[str, dict[str, Any]] = {}
        self._started: dict[str, float] = {}
        self._lock = Lock()

    def on_chat_model_start(self, serialized: Any, messages: Any, *, run_id: Any, **kwargs: Any) -> None:
        with self._lock:
            key = str(run_id)
            self._started[key] = perf_counter()
            self.calls[key] = {"run_id": key, "usage": None, "completed": False}

    def on_llm_end(self, response: LLMResult, *, run_id: Any, **kwargs: Any) -> None:
        with self._lock:
            key = str(run_id)
            row = self.calls[key]
            row.update(completed=True, elapsed_seconds=perf_counter() - self._started[key])
            generation = response.generations[0][0] if response.generations and response.generations[0] else None
            if isinstance(generation, ChatGeneration) and isinstance(generation.message, AIMessage):
                message = generation.message
                row["usage"] = message.usage_metadata
                row["model"] = message.response_metadata.get("model_name")
                row["tool_names"] = [call["name"] for call in message.tool_calls]

    def on_llm_error(self, error: BaseException, *, run_id: Any, **kwargs: Any) -> None:
        with self._lock:
            key = str(run_id)
            self.calls[key].update(
                error_type=type(error).__name__,
                elapsed_seconds=perf_counter() - self._started[key],
            )

    def totals(self) -> dict[str, Any]:
        rows = list(self.calls.values())
        complete = bool(rows) and all(row["completed"] and row["usage"] is not None for row in rows)
        usage = [row["usage"] for row in rows if row["usage"] is not None]
        result: dict[str, Any] = {"model_calls": len(rows), "usage_complete": complete}
        for name in ("input_tokens", "output_tokens", "total_tokens"):
            result[name] = sum(row[name] for row in usage) if complete else None
        # Missing detail is unknown, never silently counted as zero.
        for name, group, field in (
            ("cache_read_tokens", "input_token_details", "cache_read"),
            ("reasoning_tokens", "output_token_details", "reasoning"),
        ):
            values = [row.get(group, {}).get(field) for row in usage]
            result[name] = sum(values) if complete and all(value is not None for value in values) else None
        result["model_seconds"] = sum(row.get("elapsed_seconds", 0) for row in rows)
        return result


def validate_trial(
    result: dict[str, Any], fixture: Any, measurements: ModelMeasurements, arm: str,
) -> dict[str, Any]:
    """Reject missing/extra/wrong decisions, incomplete work, and wrong tool paths."""
    final_text = result["messages"][-1].text
    try:
        answer_correct = json.loads(final_text) == fixture.expected
    except (ValueError, TypeError):
        answer_correct = False
    tool_names = [name for call in measurements.calls.values() for name in call.get("tool_names", [])]
    allowed = {tool.name for tool in fixture.tools()}
    path_correct = bool(tool_names) and (
        set(tool_names) <= allowed if arm == "ordinary" else set(tool_names) == {"eval"}
    )
    checks = {
        "answer_correct": answer_correct,
        "coverage_correct": fixture.coverage_ok(),
        "path_correct": path_correct,
        "usage_complete": measurements.totals()["usage_complete"],
    }
    return {**checks, "valid": all(checks.values()), "final_text": final_text}
