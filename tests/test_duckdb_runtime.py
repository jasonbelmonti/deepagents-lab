"""Acceptance checks for the actual DuckDB / QuickJS notebook path."""
from pathlib import Path

import pytest

pytest.importorskip("duckdb")

from langchain_core.tools import ToolException

from deepagents_lab.experiments.duckdb_runtime.fixture import create_fixture
from deepagents_lab.experiments.duckdb_runtime.tools import DuckDBTools


@pytest.fixture
def bridge(tmp_path):
    return DuckDBTools(create_fixture(tmp_path / "sales.duckdb"))


def test_parameterized_join_and_json_types(bridge):
    result = bridge.query("""
        SELECT SUM(o.quantity * p.unit_price_cents)::BIGINT
        FROM orders o JOIN products p USING (product_id)
        WHERE o.status = ? AND o.region = ?
    """, ["paid", "West"])
    assert result["rows"] == [[50000]]
    assert bridge.query("SELECT COUNT(*) FROM orders WHERE region = ?", ["West' OR true --"])["rows"] == [[0]]
    assert bridge.query("SELECT DATE '2026-09-01', 1.25::DECIMAL(5,2), NULL")["rows"] == [
        ["2026-09-01", "1.25", None],
    ]


@pytest.mark.parametrize("sql", [
    "DELETE FROM orders",
    "SELECT 1; DROP TABLE orders",
    "SET enable_external_access = true",
    "COPY orders TO '/tmp/duckdb-export.csv'",
])
def test_rejects_non_query_statements_without_changing_data(bridge, sql):
    with pytest.raises(ToolException, match="exactly one SELECT"):
        bridge.query(sql)
    assert bridge.query("SELECT COUNT(*) FROM orders")["rows"] == [[9]]


def test_external_file_read_is_disabled(bridge, tmp_path):
    local_file = tmp_path / "private.csv"
    local_file.write_text("value\nDO_NOT_READ\n")
    with pytest.raises(ToolException, match="[Dd]isabled|[Pp]ermission"):
        bridge.query("SELECT * FROM read_csv(?)", [str(local_file)])


def test_oversized_results_fail_instead_of_returning_partial_answers(bridge):
    with pytest.raises(ToolException, match="100 rows"):
        bridge.query("SELECT * FROM range(101)")
    with pytest.raises(ToolException, match="20 KB"):
        bridge.query("SELECT repeat('a', 20001)")
    assert bridge.query("SELECT * FROM range(100)")["rows"][-1] == [99]


def test_slow_query_is_interrupted_and_next_query_succeeds(bridge):
    bridge.timeout = 0.05
    with pytest.raises(ToolException, match="[Ii]nterrupt"):
        bridge.query("SELECT SUM(sin(i)) FROM range(1000000000) t(i)")
    assert bridge.query("SELECT 42")["rows"] == [[42]]


def test_fixture_does_not_overwrite_existing_database(bridge):
    with pytest.raises(FileExistsError):
        create_fixture(bridge.path)
    assert bridge.query("SELECT COUNT(*) FROM orders")["rows"] == [[9]]


def test_full_notebook_executes_offline_from_its_own_directory(monkeypatch):
    nbformat = pytest.importorskip("nbformat")
    nbclient = pytest.importorskip("nbclient")
    pytest.importorskip("langchain_quickjs")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("LANGSMITH_TRACING", "false")
    path = Path(__file__).parents[1] / "notebooks/experiments/duckdb-code-interpreter.ipynb"
    notebook = nbformat.read(path, as_version=4)
    # Real kernel, agent, interpreter and SQL. Notebook assertions verify both
    # the initial ranking and the changed answer after a persistent host write.
    executed = nbclient.NotebookClient(notebook, timeout=60, kernel_name="python3").execute(cwd=str(path.parent))
    text = "".join(output.get("text", "") for cell in executed.cells for output in cell.get("outputs", []))
    assert "PASS: a new agent read the updated DuckDB file through eval." in text
    assert "LIVE skipped." in text
