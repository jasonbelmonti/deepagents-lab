"""Cancellation through the real agent while an actual graph worker is unfinished."""
import asyncio
import json
import os
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from threading import Event, enumerate as active_threads, local
from time import perf_counter

import pytest

from deepagents_lab.experiments.graph_ptc_value import tools
from deepagents_lab.experiments.graph_ptc_value.config import CASES, Config
from deepagents_lab.experiments.graph_ptc_value.smoke import scripted_model
from deepagents_lab.experiments.graph_ptc_value.trial import run_trial


def _shutdown_probe(arm, mode):
    """Exercise real middleware in a fresh process, including Python teardown."""
    from deepagents_lab.experiments.graph_ptc_value import trial
    from deepagents_lab.experiments.graph_ptc_value.smoke import ScriptedModel, message

    config = replace(Config(), run_timeout=3, interpreter_timeout=1)
    case = CASES[0]
    responses = scripted_model(config, case, 7, arm).responses
    if arm == "compute":
        responses.insert(0, message([("eval", {"code": "1 + 1"})], "compute"))
    if mode == "graph_error":
        responses.insert(0, message([
            ("eval", {"code": "await tools.getProfiles({person_ids:[]})"}),
        ], "bad"))
    for response in responses:
        response.usage_metadata = {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120}

    async def run():
        second_started = asyncio.Event()

        class FailureModel(ScriptedModel):
            async def _agenerate(self, *args, **kwargs):
                if self.i and mode in ("provider_error", "timeout", "cancel"):
                    second_started.set()
                    if mode == "provider_error":
                        raise RuntimeError("synthetic provider failure after eval")
                    await asyncio.Event().wait()
                return await super()._agenerate(*args, **kwargs)

        # Substitute only the provider boundary so real partial usage is retained.
        trial.init_chat_model = lambda *args, **kwargs: FailureModel(responses=responses)
        task = asyncio.create_task(run_trial(config, case, 7, arm))
        if mode == "cancel":
            await asyncio.wait_for(second_started.wait(), 10)
            task.cancel()
        row = await task
        if mode == "success":
            assert row["correct"] and row["valid"], row
        else:
            expected = {"provider_error": "RuntimeError", "timeout": "TimeoutError",
                        "cancel": "CancelledError", "graph_error": "ValueError"}[mode]
            assert row["error_type"] == expected and not row["valid"], row
            assert row["model_call_details"][0]["usage"]["total_tokens"] == 120, row
            if mode == "cancel":
                assert row["interrupted"]
        return row

    row = asyncio.run(run())
    assert not any(thread.name.startswith("quickjs-worker-") for thread in active_threads())
    print(json.dumps({"arm": arm, "mode": mode, "error_type": row.get("error_type")}), flush=True)


@pytest.mark.parametrize("arm,mode", [
    (arm, mode) for arm in ("compute", "ptc")
    for mode in ("success", "provider_error", "timeout", "cancel")
] + [("ptc", "graph_error")])
def test_interpreter_trial_exits_after_success_or_failure(arm, mode):
    child_env = {key: value for key, value in os.environ.items()
                 if key not in {"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY",
                                "LANGSMITH_API_KEY", "LANGCHAIN_API_KEY"}}
    child_env.update(LANGSMITH_TRACING="false", LANGCHAIN_TRACING_V2="false")
    result = subprocess.run([sys.executable, str(Path(__file__).resolve()), arm, mode],
                            env=child_env, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout.splitlines()[-1])["mode"] == mode


@pytest.mark.parametrize("arm", ["ordinary", "ptc"])
def test_cancelled_trial_keeps_an_immutable_partial_backend_snapshot(monkeypatch, arm):
    paused, release = Event(), Event()
    clock_state = local()

    def gated_clock():
        if getattr(clock_state, "started", False):
            paused.set()  # Real backend work is recorded; its duration is not yet final.
            assert release.wait(10), "Test did not release the graph worker."
        clock_state.started = True
        return perf_counter()

    monkeypatch.setattr(tools, "perf_counter", gated_clock)
    config, case = Config(), CASES[0]

    async def run():
        task = asyncio.create_task(run_trial(
            config, case, 7, arm, model=scripted_model(config, case, 7, arm)))
        try:
            assert await asyncio.to_thread(paused.wait, 10), "Graph worker did not start."
            task.cancel()
            row = await asyncio.wait_for(task, 5)
            serialized = json.dumps(row, sort_keys=True)
        finally:
            release.set()
            await asyncio.gather(task, return_exceptions=True)
            await asyncio.get_running_loop().shutdown_default_executor()
        assert json.dumps(row, sort_keys=True) == serialized
        return row

    row = asyncio.run(run())
    assert row["interrupted"] and not row["correct"] and not row["valid"]
    assert row["backend_accounting_complete"] is False
    assert row["response_bytes"] is None and row["backend_service_seconds"] is None
    assert row["response_bytes_lower_bound"] > 0
    assert row["backend_service_seconds_lower_bound"] == 0
    assert len(row["application_tool_calls"]) == 1
    call = row["application_tool_calls"][0]
    assert call["ok"] and not call["delivered"]
    assert "elapsed_seconds" not in call


if __name__ == "__main__":
    _shutdown_probe(*sys.argv[1:])
