"""A narrow SQL bridge: DuckDB stays in Python, JSON crosses into QuickJS."""
from datetime import date, datetime
from decimal import Decimal
import json
from pathlib import Path
from threading import Timer

import duckdb
from langchain_core.tools import ToolException, tool


SCHEMA_SQL = """
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'main'
ORDER BY table_name, ordinal_position
"""


def json_scalar(value):
    """Preserve SQL dates and exact decimals as strings at the JSON boundary."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Unsupported SQL result type: {type(value).__name__}")


class DuckDBTools:
    """Read one local fixture, with fresh connections and a visible query log.

    These are local experiment limits, not a process sandbox. Row and byte caps
    bound returned data; DuckDB's memory setting is not a hard process RAM cap.
    """

    def __init__(self, path: Path, *, max_rows: int = 100, timeout: float = 3.0):
        self.path = path.resolve(strict=True)
        if max_rows < 1 or timeout <= 0:
            raise ValueError("max_rows and timeout must be positive")
        self.max_rows = max_rows
        self.timeout = timeout
        self.queries: list[dict] = []

    def query(self, sql: str, parameters: list | None = None) -> dict:
        """Execute one SELECT, rejecting oversized results rather than truncating."""
        try:
            with duckdb.connect(str(self.path), read_only=True, config={
                "enable_external_access": "false",
                "autoload_known_extensions": "false",
                "autoinstall_known_extensions": "false",
                "threads": "1",
                "memory_limit": "128MB",
                "max_temp_directory_size": "0B",
            }) as connection:
                statements = connection.extract_statements(sql)
                if len(statements) != 1 or statements[0].type != duckdb.StatementType.SELECT:
                    raise ValueError("Use exactly one SELECT or WITH ... SELECT statement.")
                timer = Timer(self.timeout, connection.interrupt)
                timer.daemon = True
                timer.start()
                try:
                    cursor = connection.execute(sql, parameters or [])
                    rows = cursor.fetchmany(self.max_rows + 1)
                    if len(rows) > self.max_rows:
                        raise ValueError(f"Result exceeds {self.max_rows} rows; aggregate or add LIMIT.")
                    result = {"columns": [column[0] for column in cursor.description], "rows": rows}
                    payload = json.dumps(result, default=json_scalar, allow_nan=False)
                    if len(payload.encode()) > 20_000:
                        raise ValueError("Result exceeds 20 KB; select fewer or smaller values.")
                finally:
                    timer.cancel()
                    timer.join()  # The interrupt callback must finish before connection.close().
            result = json.loads(payload)
        except (duckdb.Error, ValueError, TypeError) as error:
            self.queries.append({"sql": sql, "parameters": parameters or [], "error": str(error)})
            raise ToolException(str(error)) from error
        self.queries.append({"sql": sql, "parameters": parameters or [], "rows": len(result["rows"])})
        return result

    def tools(self):
        """Return tool objects for CodeInterpreterMiddleware's PTC allowlist."""
        @tool
        def duckdb_schema() -> dict:
            """Inspect table names, column names and SQL types in the local sales database."""
            return self.query(SCHEMA_SQL)

        @tool
        def query_duckdb(
            sql: str,
            parameters: list[str | int | float | bool | None] | None = None,
        ) -> dict:
            """Run one read-only SELECT (including CTEs) against local DuckDB.

            Use ? placeholders and parameters for values. Returns columns and
            rows as JSON arrays; DATE/TIMESTAMP and DECIMAL values are strings.
            Integer money is in cents. At most 100 rows and 20 KB can be returned;
            oversized results fail, so aggregate or LIMIT explicitly. Queries
            are interrupted after three seconds. External files, network reads,
            extension installation and database mutations are disabled.
            """
            return self.query(sql, parameters)

        return [duckdb_schema, query_duckdb]
