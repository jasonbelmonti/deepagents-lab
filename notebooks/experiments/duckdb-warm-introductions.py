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
# # DuckDB + Deep Agents: warm introductions into a job
#
# Forked from `duckdb-code-interpreter`. This experiment asks:
# **Who can I approach for an introduction into Atlas's Infrastructure team?**
# We query a synthetic network, rank routes with evidence for every edge, and
# compare two Deep Agents using the **same DuckDB schema/query tools**:
#
# | Arm | What the model controls |
# | --- | --- |
# | Ordinary | Calls SQL tools directly; one SQL query may solve the whole task. |
# | Interpreter | Writes JavaScript in `eval`, calls those SQL tools, returns compact results. |
#
# Start Jupyter from this worktree with `uv run --frozen --group notebooks jupyter lab`.
# Run all cells with `RUN_LIVE=False` for an offline demonstration. Only the final
# opt-in section invokes a provider. No real people or private network data are used.

# %%
from dataclasses import asdict, replace
import hashlib
from importlib.metadata import version
import inspect
import json
import os
from pathlib import Path
from uuid import uuid4

import duckdb
from IPython.display import Code, Markdown, display
from langsmith import tracing_context

from deepagents_lab.agent import DEFAULT_MODEL
from deepagents_lab.experiments.duckdb_warm_introductions.domain import Question
from deepagents_lab.experiments.duckdb_warm_introductions.fixture import create_fixture, make_network
from deepagents_lab.experiments.duckdb_warm_introductions.oracle import expected_routes
from deepagents_lab.experiments.duckdb_warm_introductions.prompts import task_prompt
from deepagents_lab.experiments.duckdb_warm_introductions.reference import REFERENCE_SQL, named_rows, reference_parameters
from deepagents_lab.experiments.duckdb_warm_introductions.smoke import executed_answer, program, scripted_model
from deepagents_lab.experiments.duckdb_warm_introductions.tools import NetworkTools
from deepagents_lab.experiments.duckdb_warm_introductions.trial import build_agent, run_trial

ROOT = next(p for p in (Path.cwd(), *Path.cwd().parents) if (p / "pyproject.toml").is_file())
RUN_DIR = ROOT / "results" / "duckdb-warm-introductions" / str(uuid4())
VERSIONS = {name: version(name) for name in ("deepagents", "langchain-quickjs", "duckdb", "langchain-openai")}
print(VERSIONS)

# %% [markdown]
# ## 1. Create a network with useful and misleading paths
#
# Vera is a direct contact on the target team. Maya knows two people there, but
# represents one first connector. Chris and Ari provide independent alternatives.
# A hub knows many employees but has weak evidence on the first edge. Other
# distractors include former/future employees, another team, a stale relationship,
# reverse-only evidence, shared affiliation, a future-dated edge and a cycle.
#
# Change `HUB_SIZE`, recency, hop limit or number of connectors, then rerun from
# this cell. Increase fanout to test whether the agent keeps computation in SQL.
# Each setup creates a fresh database; it does not overwrite a previous run.

# %% tags=["configuration"]
HUB_SIZE = 30  # 1–1000 synthetic target-team employees behind the weak hub edge.
QUESTION = Question(max_hops=3, top_k=4, cutoff="2025-09-13", as_of="2026-09-13")
NETWORK = make_network(HUB_SIZE)
DATABASE = create_fixture(RUN_DIR / str(uuid4()) / "network.duckdb", NETWORK)
EXPECTED = expected_routes(NETWORK, QUESTION)  # Python DFS; no SQL or model calls.
PROMPT = task_prompt(QUESTION)
print("Database:", DATABASE)
print(f"{len(NETWORK.people)} people; {len(NETWORK.relationships)} directed relationships")
display(Markdown(PROMPT))

# %% [markdown]
# Strength is an ordinal fixture score from 1 to 5. The ranking uses the weakest
# edge, then fewer hops, then the oldest evidence date (newer wins), then stable
# ID tie-breakers. Paths contain no repeated people and stop at three hops.
# Targets must currently work at the job's company and exact team. Direct contacts
# are eligible; repeated routes through the same first connector do not add options.
#
# These rules test mechanical correctness. They do not establish willingness to
# introduce someone or the probability that an introduction leads to employment.

# %%
names = dict(NETWORK.people)
rows = ["| Connector | Route | Weakest edge | Oldest evidence |", "| --- | --- | --- | --- |"]
for route in EXPECTED["routes"]:
    path_names = " → ".join(names[p] for p in route["path"])
    rows.append(f"| {names[route['connector_id']]} | {path_names} | {route['bottleneck_strength']} | {route['oldest_evidence_at']} |")
display(Markdown("\n".join(rows)))
print(json.dumps(EXPECTED, indent=2))  # Includes ordered edge IDs and employment evidence.

# %% [markdown]
# ## 2. Verify the query without a model
#
# This reference recipe uses a bounded recursive CTE, rejects cycles and ranks
# one best path per connector. The independent Python traversal above supplies
# the expected answer. Both agents have permission to write SQL like this.
# **Neither this SQL nor the expected answer is sent to live agents.**

# %%
display(Code(REFERENCE_SQL, language="sql"))
reference_bridge = NetworkTools(DATABASE)
reference_result = reference_bridge.query(REFERENCE_SQL, reference_parameters(QUESTION))
assert reference_result["ok"], reference_result
assert {"routes": named_rows(reference_result)} == EXPECTED
print("PASS: executed SQL matches the independent Python traversal.")

# %% [markdown]
# ## 3. Inspect the agent wiring and interpreter program
#
# Both arms use the same tool definitions, data, task rules and 12-call SQL budget.
# The interpreter receives tool objects through `ptc`; the ordinary arm receives
# them through `tools`. The shared helper below constructs a fresh Deep Agent for
# each attempt. Its source is displayed so the integration remains visible.
#
# Python `query_duckdb` becomes JavaScript `tools.queryDuckdb`. Results are native
# objects with `ok`, `columns` and `rows`; failures return `ok: false` with an error.
# QuickJS can keep intermediate values between eval calls within one invocation.
# DuckDB persists in its own file, independently of the interpreter.

# %%
display(Code(inspect.getsource(build_agent), language="python"))
display(Code(program(QUESTION), language="javascript"))

# %% [markdown]
# ## 4. Run both agents offline and verify actual tool outputs
#
# Scripted models supply known calls and a canned final answer. Verification reads
# the **actual SQL ToolMessage or eval result**, so canned text alone cannot pass.
# The ordinary script batches schema inspection and the query in one model turn;
# the interpreter script runs them in one eval. These are plumbing checks, not
# evidence that either approach uses fewer provider tokens or achieves lower latency.

# %%
offline = []
with tracing_context(enabled=False):
    for arm in ("ordinary", "interpreter"):
        record = await run_trial(
            scripted_model(arm, QUESTION, EXPECTED), arm, DATABASE, PROMPT, EXPECTED,
            log_path=RUN_DIR / f"offline-{arm}-{uuid4()}.json",
        )
        assert record["correct"], record["error"] or record["final_text"]
        assert executed_answer(record) == EXPECTED
        assert record["total_tokens"] is None
        offline.append(record)
        print(f"PASS {arm}: {record['sql_attempts']} SQL/schema calls; actual returned paths match.")
print("Evidence files:", RUN_DIR)

# %% [markdown]
# ## 5. Prove SQL errors are recoverable
#
# These recipes first query a nonexistent column, check the error and then execute
# the valid query. Errors count toward the shared budget. Failed or oversized
# results must never be interpreted as an empty network.

# %%
with tracing_context(enabled=False):
    for arm in ("ordinary", "interpreter"):
        record = await run_trial(
            scripted_model(arm, QUESTION, EXPECTED, inject_error=True),
            arm, DATABASE, PROMPT, EXPECTED,
            log_path=RUN_DIR / f"recovery-{arm}-{uuid4()}.json",
        )
        assert record["correct"] and record["sql_errors"] == 1, record["error"]
        assert executed_answer(record) == EXPECTED
        print(f"PASS {arm}: error followed by a correct result; {record['sql_attempts']} attempts logged.")

# %% [markdown]
# ## 6. A new invocation reads updated employment evidence
#
# Mark Vera's employment as ended on the host. Run the same SQL recipe through
# a fresh interpreter; the route must disappear if it was eligible before.
# Restore the fixture afterward so the LIVE comparison uses the original data.
# Close host write connections before agent reads. This cell is safe to rerun.

# %%
changed_network = replace(NETWORK, employment=tuple(
    replace(e, ends_at=QUESTION.as_of) if e.person_id == "vera" else e for e in NETWORK.employment
))
changed_expected = expected_routes(changed_network, QUESTION)
with duckdb.connect(str(DATABASE)) as connection:
    connection.execute("UPDATE employment SET ends_at = ? WHERE person_id = 'vera'", [QUESTION.as_of])
try:
    with tracing_context(enabled=False):
        changed = await run_trial(
            scripted_model("interpreter", QUESTION, changed_expected),
            "interpreter", DATABASE, PROMPT, changed_expected,
            log_path=RUN_DIR / f"updated-employment-{uuid4()}.json",
        )
    assert changed["correct"], changed["error"]
    assert executed_answer(changed) == changed_expected
    assert all(route["target_id"] != "vera" for route in changed_expected["routes"])
    print("PASS: a fresh interpreter read the updated file.")
    print(json.dumps(changed_expected, indent=2))
finally:
    with duckdb.connect(str(DATABASE)) as connection:
        connection.execute("UPDATE employment SET ends_at = NULL WHERE person_id = 'vera'")

# %% [markdown]
# ## 7. LIVE: let the model write its own SQL and JavaScript
#
# Set `RUN_LIVE=True` to run matched pairs. One pair makes two agent invocations,
# each potentially containing several paid requests. Only this section loads `.env`.
# In a worktree, `ENV_FILE` may point to your original checkout's ignored `.env`.
# Existing environment values win; configured LangSmith tracing applies to live runs.
#
# Both arms get fresh agents and the same model settings. Order alternates across
# pairs. Every completed/failed attempt is saved, with generated calls, query results,
# final answer, exact fixture grading and per-model-call usage when reported.
# Missing usage stays unknown; partial usage remains visible in the call details.
# Invocation latency includes model/tool execution and excludes agent construction,
# fixture generation, oracle computation and interpreter cleanup. Automatic cleanup
# inside `ainvoke` is timed separately and subtracted; the log retains both raw
# `invocation_wall_seconds` and `interpreter_cleanup_seconds`. A single pair is
# exploratory evidence; use repeated matched trials before claiming an improvement.

# %% tags=["live", "configuration"]
RUN_LIVE = False
LIVE_PAIRS = 1  # 1–5; each pair runs ordinary and interpreter once.
ENV_FILE = ROOT / ".env"

# %% tags=["live"]
live_records = []
if RUN_LIVE:
    from dotenv import load_dotenv
    from langchain.chat_models import init_chat_model

    if not 1 <= LIVE_PAIRS <= 5:
        raise ValueError("LIVE_PAIRS must be between 1 and 5")
    load_dotenv(ENV_FILE, override=False)
    model_name = os.getenv("DEEPAGENTS_LAB_MODEL", DEFAULT_MODEL)
    if model_name.startswith("openai:") and not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(f"Set OPENAI_API_KEY in the environment or {ENV_FILE}.")
    settings = {"timeout": 45, "max_retries": 0}
    if model_name.startswith("openai:"):
        settings["use_responses_api"] = True
    live_dir = RUN_DIR / f"live-{uuid4()}"
    live_dir.mkdir()
    source_dir = ROOT / "src/deepagents_lab/experiments/duckdb_warm_introductions"
    manifest = {
        "model": model_name, "model_settings": settings, "versions": VERSIONS,
        "question": asdict(QUESTION), "hub_size": HUB_SIZE, "pairs": LIVE_PAIRS,
        "database": str(DATABASE), "database_sha256": hashlib.sha256(DATABASE.read_bytes()).hexdigest(),
        "fixture": asdict(NETWORK), "expected": EXPECTED,
        "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source_dir.glob("*.py")},
    }
    (live_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    for pair in range(LIVE_PAIRS):
        arms = ("ordinary", "interpreter") if pair % 2 == 0 else ("interpreter", "ordinary")
        for arm in arms:
            model = init_chat_model(model_name, **settings)
            record = await run_trial(
                model, arm, DATABASE, PROMPT, EXPECTED, mode="live",
                log_path=live_dir / f"pair-{pair + 1}-{arm}.json",
            )
            live_records.append(record)
            print(arm, "correct:", record["correct"], "error:", record["error"])
    columns = ("arm", "correct", "elapsed_seconds", "model_calls", "total_tokens", "sql_attempts", "sql_errors")
    display(Markdown("\n".join([
        "| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |",
        *("| " + " | ".join(str(r[c]) if r[c] is not None else "unknown" for c in columns) + " |" for r in live_records),
    ])))
    print("Complete attempt logs and manifest:", live_dir)
else:
    print("LIVE skipped. Offline execution makes no provider calls.")

# %% [markdown]
# ## What to investigate next
#
# | Scenario | Hypothesis to measure |
# | --- | --- |
# | More edges and distracting profiles | Keeping joins/ranking in DuckDB should reduce row text sent to the model compared with returning raw profiles. Both arms can benefit. |
# | A single well-formed SQL query | The ordinary arm may match or beat PTC; interpreter overhead may add no value. |
# | Adaptive queries and several job/team variants | JavaScript may combine tool calls and retain intermediate results with fewer model round trips. |
# | Stale evidence and ambiguous identities | SQL can enforce explicit rules; neither transport fixes missing or incorrectly linked source data. |
#
# Compare total tokens, invocation latency, model calls and exact fixture correctness
# together. Include failed attempts and inspect generated SQL. The independent oracle
# proves adherence to these rules, not usefulness of a recommendation in the real world.
#
# Limits: 100 rows / 20 KB per SQL result; 12 shared schema/query attempts (errors
# included); three-second SQL interrupt timer; 16 graph steps / 90 seconds per
# invocation. PTC additionally allows 12 calls / ten seconds / 8,000 output characters
# per eval. These are local experiment controls, not a process sandbox or guaranteed
# hard native-code deadline. External reads, extensions and agent database writes
# are disabled by the reused bridge. Host Python owns fixture loading and updates.
#
# References: [Deep Agents interpreter](https://docs.langchain.com/oss/python/deepagents/interpreters),
# [DuckDB recursive CTEs](https://duckdb.org/docs/current/sql/query_syntax/with).
