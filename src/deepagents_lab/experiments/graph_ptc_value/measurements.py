"""Reuse provider accounting; add inspectable context/orchestration diagnostics."""
from copy import deepcopy

from langchain_core.messages import ToolMessage
from langchain_core.outputs import ChatGeneration

from deepagents_lab.benchmarks.incident_metrics import ModelMeasurements


def backend_snapshot(api, *, aborted):
    """Freeze observed work without waiting past the invocation's time bound."""
    # Copy each row before deep-copying nested data: workers may still update it.
    calls = deepcopy([dict(call) for call in api.calls])
    complete = not aborted and all("elapsed_seconds" in call for call in calls)
    response_bytes = sum(call["response_bytes"] for call in calls)
    service_seconds = sum(call.get("elapsed_seconds", 0) for call in calls)
    return dict(application_tool_calls=calls, backend_accounting_complete=complete,
                response_bytes=response_bytes if complete else None,
                backend_service_seconds=service_seconds if complete else None,
                response_bytes_lower_bound=response_bytes,
                backend_service_seconds_lower_bound=service_seconds)


class GraphMeasurements(ModelMeasurements):
    def on_chat_model_start(self, serialized, messages, *, run_id, **kwargs):
        super().on_chat_model_start(serialized, messages, run_id=run_id, **kwargs)
        with self._lock:
            flattened = [message for batch in messages for message in batch]
            self.calls[str(run_id)].update(
                # Character diagnostics are NOT token estimates or wire bytes.
                input_text_chars=sum(len(m.text) for m in flattened),
                tool_result_text_chars=sum(len(m.text) for m in flattened if isinstance(m, ToolMessage)),
            )

    def on_llm_end(self, response, *, run_id, **kwargs):
        super().on_llm_end(response, run_id=run_id, **kwargs)
        generation = response.generations[0][0] if response.generations and response.generations[0] else None
        if isinstance(generation, ChatGeneration):
            with self._lock:
                self.calls[str(run_id)]["tool_requests"] = generation.message.tool_calls
