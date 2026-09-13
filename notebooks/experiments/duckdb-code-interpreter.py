# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: tags
#     formats: ipynb,py:percent
#     notebook_metadata_filter: kernelspec,jupytext
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.5
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # DuckDB at runtime: Deep Agent + code interpreter
#
# Explore a local sales database from agent-written code. **Run All is offline
# by default:** a scripted model exercises real DeepAgents, QuickJS and DuckDB.
# The optional LIVE section lets a real model write its own JavaScript and SQL.
#
# ```text
# Deep Agent → eval(JavaScript) → tools.queryDuckdb({sql, parameters})
#                              → Python → DuckDB → JSON rows → JavaScript
# ```
#
# The existing code interpreter runs **JavaScript in QuickJS**. DuckDB runs in
# the host Python process; its connection is never copied into the interpreter.
# Programmatic tool calling (PTC) bridges two allowlisted Python tools. There is
# no Python REPL or `import duckdb` inside `eval`, and no database server to start.
#
# Launch from this checkout with:
# `uv run --frozen --group notebooks jupyter lab notebooks/experiments/duckdb-code-interpreter.ipynb`

# %%
import asyncio
import json
import os
from functools import partial
from importlib.metadata import version
from pathlib import Path
from uuid import uuid4
from xml.etree import ElementTree

import duckdb
from deepagents import create_deep_agent
from IPython.display import Markdown, display
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableLambda
from langchain_quickjs import CodeInterpreterMiddleware
from langsmith import tracing_context

from deepagents_lab.agent import DEFAULT_MODEL
from deepagents_lab.experiments.duckdb_runtime.fixture import create_fixture
from deepagents_lab.experiments.duckdb_runtime.tools import DuckDBTools

ROOT = next(p for p in (Path.cwd(), *Path.cwd().parents) if (p / "pyproject.toml").is_file())
RUN_DIR = ROOT / "results" / "duckdb-code-interpreter" / str(uuid4())
DATABASE = create_fixture(RUN_DIR / "sales.duckdb")
bridge = DuckDBTools(DATABASE)
print("Database:", DATABASE)
print({name: version(name) for name in ("deepagents", "langchain-quickjs", "duckdb")})

# %% [markdown]
# ## 1. Inspect the fixture and query it directly
#
# Nine synthetic orders join three products. Prices are integer cents, and only
# `status = 'paid'` counts as revenue. Each setup run creates a separate database
# under ignored `results/`; it never overwrites a previous run.
#
# This Python call checks the database before adding the agent/interpreter path.
# The same tool returns `{columns, rows}` inside JavaScript. Dates and exact
# SQL decimals cross the JSON boundary as strings.

# %%
print(json.dumps(bridge.query("SELECT * FROM products ORDER BY product_id"), indent=2))
print(json.dumps(bridge.query("SELECT * FROM orders ORDER BY order_id"), indent=2))

# %% [markdown]
# ## 2. Build the Deep Agent with a DuckDB-enabled interpreter
#
# Passing **tool objects** in `ptc=[...]` exposes them only inside the interpreter.
# Python `query_duckdb` becomes JavaScript `tools.queryDuckdb`; argument names stay
# unchanged. The outer agent has `eval` plus the standard DeepAgents tools.
# Its instructions route database work through `eval`.
#
# Turn mode keeps JavaScript globals across eval calls within one invocation and
# releases them afterward. DuckDB persists separately in the printed database
# file. Each invocation below uses a fresh agent and a unique thread ID.

# %%
SYSTEM_PROMPT = """
You are exploring a local DuckDB sales database. Use eval for all database work.
First inspect the schema with await tools.duckdbSchema({}). Then write SQL with
await tools.queryDuckdb({sql: 'SELECT ...', parameters: []}). Both return objects
with columns and rows arrays; do not JSON.parse them. Use ? for parameter values.
Join orders to products on product_id. Count only paid orders as revenue, unless
asked otherwise; quantity * unit_price_cents is revenue in integer cents.
Use SQL for joins and aggregation, JavaScript for shaping the compact result.
Return your value as the program's final expression, preferably JSON.stringify.
If a query errors, correct it. Never treat failed or oversized results as empty.
Do not use task, filesystem tools, or write_todos for this experiment. Report
only conclusions supported by successful queries, including units and filters.
""".strip()


async def run_agent(model, prompt, database_tools):
    interpreter = CodeInterpreterMiddleware(
        ptc=database_tools.tools(),
        subagents=False,
        mode="turn",
        timeout=10.0,
        max_ptc_calls=12,
        max_result_chars=8000,
    )
    config = {"configurable": {"thread_id": str(uuid4())}, "recursion_limit": 12}
    try:
        agent = create_deep_agent(
            model=model, tools=[], middleware=[interpreter], system_prompt=SYSTEM_PROMPT,
        )
        async with asyncio.timeout(90):
            return await agent.ainvoke(
                {"messages": [{"role": "user", "content": prompt}]}, config=config,
            )
    finally:
        # Also release the interpreter if a model error skips its normal hook.
        cleanup = RunnableLambda(partial(interpreter.aafter_agent, runtime=None))
        await cleanup.ainvoke({}, config=config)

# %% [markdown]
# ## 3. Run a real interpreter program without a provider
#
# The scripted model supplies the program below. DuckDB executes the join and
# aggregation at runtime; JavaScript converts positional SQL rows into named
# objects. Schema inspection and the query happen inside one `eval` call.
#
# This verifies plumbing, not a model's ability to generate correct SQL. The
# check reads the **actual interpreter ToolMessage**, not the scripted final text.

# %%
PROGRAM = """
var schema = await tools.duckdbSchema({});
var sales = await tools.queryDuckdb({
  sql: `SELECT o.region, SUM(o.quantity * p.unit_price_cents)::BIGINT AS revenue_cents
        FROM orders o JOIN products p USING (product_id)
        WHERE o.status = ?
        GROUP BY o.region ORDER BY revenue_cents DESC, o.region`,
  parameters: ['paid']
});
var ranking = sales.rows.map(row => Object.fromEntries(
  sales.columns.map((name, i) => [name, row[i]])
));
JSON.stringify({tables: [...new Set(schema.rows.map(row => row[0]))], ranking});
""".strip()
print(PROGRAM)


class ScriptedModel(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


def scripted_model():
    return ScriptedModel(responses=[
        AIMessage(content="", tool_calls=[{
            "name": "eval", "args": {"code": PROGRAM}, "id": "duckdb-probe", "type": "tool_call",
        }]),
        AIMessage(content="Offline recipe complete; inspect the actual eval output below."),
    ])


def interpreter_results(result):
    outputs = []
    for message in result["messages"]:
        if isinstance(message, ToolMessage) and message.name == "eval":
            envelope = ElementTree.fromstring(message.text)
            assert message.status != "error" and envelope.tag == "result", message.text
            outputs.append(json.loads(envelope.text))
    assert outputs, "The agent did not execute eval."
    return outputs

# %%
with tracing_context(enabled=False):
    offline_result = await run_agent(scripted_model(), "Rank paid revenue by region.", bridge)
offline_answer = interpreter_results(offline_result)[-1]
assert offline_answer == {
    "tables": ["orders", "products"],
    "ranking": [
        {"region": "West", "revenue_cents": 50000},
        {"region": "Central", "revenue_cents": 35000},
        {"region": "East", "revenue_cents": 25000},
    ],
}, offline_answer
print(json.dumps(offline_answer, indent=2))
print("Queries actually executed inside eval:")
print(json.dumps(bridge.queries[-2:], indent=2))

# %% [markdown]
# ## 4. Prove the next invocation reads current database contents
#
# Add a paid East order on the **host**, after the first agent has finished.
# Re-run exactly the same interpreter program through a new bridge/agent. East
# must now lead at 85,000 cents. This demonstrates runtime data access and file
# persistence independent of JavaScript globals or model text.
#
# The upsert makes this cell safe to rerun. Restart from setup for the original
# nine-order fixture. The optional LIVE run uses the updated ten-order database.

# %%
with duckdb.connect(str(DATABASE)) as connection:
    connection.execute("""
        INSERT OR REPLACE INTO orders VALUES
        (10, '2026-09-06', 'East', 3, 2, 'paid')
    """)
reopened = DuckDBTools(DATABASE)
with tracing_context(enabled=False):
    updated_result = await run_agent(scripted_model(), "Rank paid revenue by region.", reopened)
updated_answer = interpreter_results(updated_result)[-1]
assert updated_answer["ranking"] == [
    {"region": "East", "revenue_cents": 85000},
    {"region": "West", "revenue_cents": 50000},
    {"region": "Central", "revenue_cents": 35000},
], updated_answer
print(json.dumps(updated_answer, indent=2))
print("PASS: a new agent read the updated DuckDB file through eval.")

# %% [markdown]
# ## 5. LIVE — let the model write JavaScript and SQL
#
# Change `RUN_LIVE` to `True`, then run this section. Each run invokes the real
# model and can make several paid API requests. Only this section loads `.env`;
# existing environment values win. In a worktree, set `ENV_FILE` to the ignored
# `.env` in your original checkout if needed. LangSmith settings apply if enabled.
#
# Edit `QUESTION` to explore products, regions, daily totals, or window functions.
# The handwritten `PROGRAM` and expected answers are not supplied to the model.
# The messages below show the generated JavaScript, interpreter outputs and final
# response so you can inspect what actually ran.

# %% tags=["live", "configuration"]
RUN_LIVE = False
ENV_FILE = ROOT / ".env"  # Or an absolute path to your existing checkout's .env.
QUESTION = """
Inspect the schema, then rank regions by paid revenue in cents.
Include paid order counts and each region's percentage of total paid revenue.
Explain which statuses were excluded. Use DuckDB SQL for the aggregation.
""".strip()

# %% tags=["live"]
if RUN_LIVE:
    from dotenv import load_dotenv
    from langchain.chat_models import init_chat_model

    load_dotenv(ENV_FILE, override=False)
    model_name = os.getenv("DEEPAGENTS_LAB_MODEL", DEFAULT_MODEL)
    if model_name.startswith("openai:") and not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(f"Set OPENAI_API_KEY in the environment or {ENV_FILE}.")
    settings = {"timeout": 45, "max_retries": 0}
    if model_name.startswith("openai:"):
        settings["use_responses_api"] = True
    model = init_chat_model(model_name, **settings)
    live_bridge = DuckDBTools(DATABASE)
    live_result = await run_agent(model, QUESTION, live_bridge)
    for message in live_result["messages"]:
        for call in getattr(message, "tool_calls", ()):
            print(call["name"], json.dumps(call["args"], indent=2))
        if isinstance(message, ToolMessage):
            print(message.name, message.text)
    assert any("rows" in query for query in live_bridge.queries), "No successful DuckDB query occurred."
    display(Markdown(live_result["messages"][-1].text))
    print("DuckDB query log:", json.dumps(live_bridge.queries, indent=2))
else:
    print("LIVE skipped. Set RUN_LIVE=True to ask the model to write the program.")

# %% [markdown]
# ## Experiment boundaries and next edits
#
# - **SQL:** one SELECT/CTE per call, read-only database, no external file/network
#   reads or extension loading. Load your own CSV/Parquet into tables from host
#   Python, close that write connection, then pass its database path to DuckDBTools.
# - **Limits:** 100 rows / 20 KB per SQL result (oversized results fail), a
#   three-second DuckDB interrupt timer, 12 PTC calls / ten seconds per eval,
#   and 12 graph steps / a 90-second invocation timeout. These are experiment
#   controls, not a process sandbox or a guaranteed hard deadline under native
#   library stalls. The DuckDB memory setting is not a hard process RAM cap.
# - **Persistence:** keep the printed file path; reconnect with DuckDBTools after
#   a kernel restart. A new setup cell creates a new fixture. Do not keep a host
#   write connection open while agent reads use read-only connections.
# - **Exploration:** change QUESTION, try a window-function query, or load a larger
#   local dataset. Database writes currently happen in host cells only.
#
# References: [QuickJS interpreter](https://docs.langchain.com/oss/python/deepagents/interpreters),
# [DuckDB Python API](https://duckdb.org/docs/current/clients/python/dbapi),
# [DuckDB configuration](https://duckdb.org/docs/current/configuration/overview).
