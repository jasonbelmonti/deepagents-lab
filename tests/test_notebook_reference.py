from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).parents[1]
NOTEBOOK = PROJECT_ROOT / "notebooks/reference/ptc-code-interpreter.ipynb"
JUPYTEXT_SOURCE = PROJECT_ROOT / "notebooks/reference/ptc-code-interpreter.py"


def test_ptc_reference_notebook_is_paired_and_output_free() -> None:
    document = json.loads(NOTEBOOK.read_text())

    assert document["metadata"]["jupytext"]["formats"] == "ipynb,py:percent"
    assert JUPYTEXT_SOURCE.is_file()
    assert all(cell.get("execution_count") is None for cell in document["cells"])
    assert all(not cell.get("outputs") for cell in document["cells"])


def test_ptc_reference_notebook_covers_both_interpreter_paths() -> None:
    document = json.loads(NOTEBOOK.read_text())
    source = "".join(
        part
        for cell in document["cells"]
        for part in cell.get("source", ())
    )

    assert "CodeInterpreterMiddleware" in source
    assert "ptc=TOOLS" in source
    assert "tools.getSensorSpec" in source
    assert "tools.scoreReading" in source
    assert "max_ptc_calls=20" in source
    assert "usage_metadata" in source
    assert "perf_counter" in source
    assert "comparison_table" in source
    assert "baseline_agent" in source
    live_cells = [
        cell
        for cell in document["cells"]
        if "live" in cell.get("metadata", {}).get("tags", ())
    ]
    assert len(live_cells) == 5
