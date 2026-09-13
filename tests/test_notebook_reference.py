from __future__ import annotations

import json
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).parents[1]
NOTEBOOKS = [
    "reference/ptc-code-interpreter",
    "reference/incident-triage-benchmark",
    "experiments/graph-workspace",
    "experiments/graph-ptc-value",
    "experiments/duckdb-code-interpreter",
]


@pytest.mark.parametrize("name", NOTEBOOKS)
def test_reference_notebook_is_paired_and_output_free(name: str) -> None:
    notebook = PROJECT_ROOT / f"notebooks/{name}.ipynb"
    document = json.loads(notebook.read_text())

    assert document["metadata"]["jupytext"]["formats"] == "ipynb,py:percent"
    assert notebook.with_suffix(".py").is_file()
    assert all(cell.get("execution_count") is None for cell in document["cells"])
    assert all(not cell.get("outputs") for cell in document["cells"])


@pytest.mark.parametrize("name", NOTEBOOKS)
def test_notebook_source_pair_is_synchronized(name: str) -> None:
    jupytext = pytest.importorskip("jupytext")
    path = PROJECT_ROOT / f"notebooks/{name}"
    notebook, source = [jupytext.read(path.with_suffix(suffix)) for suffix in (".ipynb", ".py")]
    assert [(c.cell_type, c.source, c.metadata.get("tags")) for c in notebook.cells] == [
        (c.cell_type, c.source, c.metadata.get("tags")) for c in source.cells
    ]
