"""Identical bounded SQL tools and error envelopes for both agent arms."""

import json
from pathlib import Path
from threading import Lock
from time import perf_counter

from langchain_core.tools import ToolException, tool

from deepagents_lab.experiments.duckdb_runtime.tools import DuckDBTools, SCHEMA_SQL


class NetworkTools:
    def __init__(self, path: Path, *, max_calls: int = 12):
        if max_calls < 1:
            raise ValueError("max_calls must be positive")
        self.database = DuckDBTools(path)
        self.max_calls = max_calls
        self.calls: list[dict] = []
        self._lock = Lock()

    def query(self, sql: str, parameters: list | None = None, *, kind: str = "query") -> dict:
        started = perf_counter()
        with self._lock:
            exhausted = len(self.calls) >= self.max_calls
            record = {"kind": kind, "sql": sql, "parameters": parameters or []}
            self.calls.append(record)
        try:
            if exhausted:
                raise ToolException(f"The {self.max_calls}-call SQL budget is exhausted.")
            result = {"ok": True, **self.database.query(sql, parameters)}
        except ToolException as error:
            # QuickJS sees a normal object, so one bad SQL statement need not end
            # the invocation. The ordinary tool exposes exactly the same object.
            result = {"ok": False, "error": str(error)[:2000]}
        record.update(result=result, elapsed_seconds=perf_counter() - started,
                      result_bytes=len(json.dumps(result).encode()))
        return result

    def tools(self):
        @tool
        def duckdb_schema() -> dict:
            """Inspect table/column names and SQL types in the local social-network database.

            Returns {ok: true, columns: [...], rows: [...]} or {ok: false, error: ...}.
            This counts toward the same 12-call budget as query_duckdb.
            """
            return self.query(SCHEMA_SQL, kind="schema")

        @tool
        def query_duckdb(
            sql: str, parameters: list[str | int | float | bool | None] | None = None,
        ) -> dict:
            """Run one read-only DuckDB SELECT, including recursive CTEs and window functions.

            Use ? placeholders with parameters. Returns {ok: true, columns: [...],
            rows: [...]} or {ok: false, error: ...}; dates are ISO strings.
            Check ok before using rows; errors are not empty answers. At most 100
            rows and 20 KB per SQL result; aggregate or LIMIT rather than dumping
            tables. Queries have a three-second interrupt timer. At most 12 total
            schema/query attempts per invocation, including errors. External file
            and network access, extensions and writes are disabled.
            """
            return self.query(sql, parameters)

        return [duckdb_schema, query_duckdb]
