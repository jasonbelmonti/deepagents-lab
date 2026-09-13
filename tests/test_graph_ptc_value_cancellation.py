"""Cancellation through the real agent while an actual graph worker is unfinished."""
import asyncio
import json
from threading import Event, local
from time import perf_counter

import pytest

from deepagents_lab.experiments.graph_ptc_value import tools
from deepagents_lab.experiments.graph_ptc_value.config import CASES, Config
from deepagents_lab.experiments.graph_ptc_value.smoke import scripted_model
from deepagents_lab.experiments.graph_ptc_value.trial import run_trial


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
