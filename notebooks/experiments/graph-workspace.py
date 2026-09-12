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
# # Graph workspace: materialization, updates and persistence
#
# **Run All is offline by default.** No credentials, external graph service or
# extra dependencies are needed. This experiment uses real DeepAgents + QuickJS
# with a scripted model to isolate local infrastructure behavior. It does not
# report simulated token counts as model usage. An explicitly enabled LIVE
# section lets a real model write the PTC program.
#
# Question: find up to five people interested in graphs, reachable from Maya
# (p000000) along recent, directed collaboration paths of at most three hops.
# Rank by fewest hops, then person ID. Keep each person's shortest path; break
# path ties lexicographically. A follows edge is not a collaboration.
#
# Compare:
#
# - **eager:** copy the full graph, including irrelevant profile data, into JS;
# - **bounded:** ask the backend for a filtered neighborhood, then traverse in JS;
# - **backend:** execute the path query in indexed SQLite and return only answers.
#
# These vary **where work happens and what crosses the boundary**, not just PTC.
# There is no ordinary-tool baseline here; use the reference notebooks for that.
# This is not a graph-database product comparison or production scaling proof.

# %%
import hashlib
import json
import os
import sqlite3
import sys
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path
from statistics import median
from time import perf_counter
from uuid import uuid4

from IPython.display import Markdown, display

import deepagents_lab.experiments.graph_workspace as graph_workspace
from deepagents_lab.experiments.graph_workspace.fixture import create_fixture
from deepagents_lab.experiments.graph_workspace.runner import PROGRAM, compare, run_probe
from deepagents_lab.experiments.graph_workspace.store import GraphStore, Query, StaleRevision
from deepagents_lab.experiments.graph_workspace.tools import ARMS

ROOT = next(p for p in (Path.cwd(), *Path.cwd().parents) if (p / "pyproject.toml").exists())
RUN_DIR = ROOT / "results" / "graph-workspace" / str(uuid4())
PEOPLE, PROFILE_BYTES, HUB_EDGES = 1000, 256, 0
query = Query()
store = create_fixture(RUN_DIR / "graph.sqlite", people=PEOPLE, payload_bytes=PROFILE_BYTES, hub_edges=HUB_EDGES)
manifest = {
    "fixture": {"people": PEOPLE, "payload_bytes": PROFILE_BYTES, "hub_edges": HUB_EDGES},
    "query": asdict(query), "python": sys.version, "sqlite": sqlite3.sqlite_version,
    "versions": {name: version(name) for name in ("deepagents", "langchain-quickjs", "quickjs-rs")},
    "source_sha256": {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(Path(graph_workspace.__file__).parent.glob("*.py"))
    },
}
print("Durable graph:", store.path)
print("Maya's expected matches:", store.answer(query, store.revision))

# %% [markdown]
# ## 1. Inspect the program and run the three materialization paths
#
# The offline recipe performs actual tool calls and executes actual JavaScript.
# Every result is checked against the SQL answer, with known-path tests providing
# an independent check of that oracle. Missing work, wrong results, tool errors,
# interpreter errors and revision changes invalidate a trial.
#
# The graph is loaded once into a file-backed database during setup. Each tool
# opens a short read transaction; no database connection crosses into QuickJS.
# The allowlist is read-only and bound to this query, database and revision.

# %%
print(PROGRAM)

# %%
rows = await compare(store, query, repeats=3)
(RUN_DIR / "materialization.json").write_text(json.dumps({**manifest, "trials": rows}, indent=2))
display(Markdown(
    "| Arm | Valid trials | Median run ms | Median tool ms | JSON response bytes |\n"
    "|---|---:|---:|---:|---:|\n" +
    "\n".join(
        f"| {arm} | {sum(r['valid'] for r in rows if r['arm'] == arm)}/3 | "
        + (f"{median(r['elapsed_ms'] for r in rows if r['arm'] == arm):.2f} | "
           f"{median(r['backend_ms'] for r in rows if r['arm'] == arm):.2f} | "
           f"{median(r['response_bytes'] for r in rows if r['arm'] == arm):,.0f} |"
           if all(r['valid'] for r in rows if r['arm'] == arm) else "invalid | invalid | invalid |")
        for arm in ARMS
    )
))
assert all(r["valid"] for r in rows), "Inspect materialization.json; do not interpret invalid runs as savings."

# %% [markdown]
# **Read these measurements carefully.** Run time spans agent invocation with
# scripted model responses, tool work and interpreter lifecycle; it excludes
# graph/model construction and the correctness oracle. Tool time includes a
# SQLite connection, query/materialization and JSON-size measurement. It is
# nested inside run time: do not add them. JSON bytes estimate the logical tool
# payload, not exact wire bytes, heap memory or tokens. The oracle and prior
# repetitions warm caches; this is not a cold-start benchmark. Arm order rotates.
# Three repeats are explanatory, not enough for a production p95 claim.

# %% [markdown]
# ## 2. Observe graph-size versus neighborhood-size effects
#
# These fixtures add **disconnected communities** while Maya's neighborhood stays
# fixed. This specifically tests whether unrelated graph growth increases data
# transfer. It does not establish constant-time queries for an arbitrary graph.
# Change HUB_EDGES above to connect Maya to more communities and observe fan-out.

# %%
growth = []
for size in (100, 10_000):
    sample = create_fixture(RUN_DIR / f"growth-{size}-{uuid4()}.sqlite", people=size, payload_bytes=PROFILE_BYTES)
    for arm in ARMS:
        row = await run_probe(sample, query, arm)
        growth.append({"people": size, "payload_bytes": PROFILE_BYTES, "hub_edges": 0, **row})
(RUN_DIR / "growth.json").write_text(json.dumps({**manifest, "trials": growth}, indent=2))
display(Markdown(
    "| People | Arm | Valid | JSON bytes | Run ms |\n|---:|---|---|---:|---:|\n" +
    "\n".join(f"| {r['people']} | {r['arm']} | {r['valid']} | {r['response_bytes']:,} | "
              f"{r['elapsed_ms']:.2f} |" if r["elapsed_ms"] is not None else
              f"| {r['people']} | {r['arm']} | false | n/a | not run |" for r in growth)
))

# %% [markdown]
# ## 3. Measure the cost of retaining interpreter state
#
# Turn mode discards scratch state. Thread mode snapshots it into agent state.
# Below, each independent probe deliberately retains its view in a JS variable.
# An in-memory checkpointer lets us inspect the middleware's private snapshot;
# it is a diagnostic, **not durable session storage**.
#
# Snapshot bytes are the fully materialized snapshot, including runtime overhead,
# not incremental checkpoint storage or peak heap usage. These runs do not
# isolate snapshot CPU time or measure restore latency.

# %%
snapshots = [await run_probe(store, query, arm, mode="thread") for arm in ARMS]
(RUN_DIR / "snapshots.json").write_text(json.dumps({**manifest, "trials": snapshots}, indent=2))
assert all(r["valid"] for r in snapshots), snapshots
display(Markdown(
    "| Arm | Materialized snapshot bytes |\n|---|---:|\n" +
    "\n".join(f"| {r['arm']} | {r['snapshot_bytes']:,} |" for r in snapshots)
))

# %% [markdown]
# ## 4. Persist the investigation, not a graph copy
#
# Save query parameters and their observed revision. Reopening this file works
# after a kernel/process restart; tests also verify this in a fresh subprocess.
# Keep the printed database path to resume later: construct GraphStore(Path(...))
# and call load_investigation with the printed ID. Re-running setup creates a
# new isolated database; it never overwrites a previous run.
#
# This small record is not a historical graph snapshot or cached result handle.
# Here, resuming reruns the query. Server-side result caches, cross-machine
# handles, access control and TTL policies are intentionally not implemented.

# %%
investigation_id = str(uuid4())
store.save_investigation(investigation_id, query, store.revision)
started = perf_counter()
reopened = GraphStore(store.path)
saved_query, saved_revision = reopened.load_investigation(investigation_id)
resume_ms = (perf_counter() - started) * 1000
record = {"id": investigation_id, "query": asdict(saved_query), "revision": saved_revision}
print("Investigation ID:", investigation_id)
print("Logical record bytes:", len(json.dumps(record).encode()), "Record reload ms:", round(resume_ms, 3))
print("Resumed answers:", reopened.answer(saved_query, saved_revision))

# %% [markdown]
# ## 5. Make an explicit update; reject stale work
#
# This host-side edit removes one synthetic collaboration. Writes are NOT exposed
# to the interpreter. The transaction checks the expected revision; reusing the
# same operation ID with the same request cannot apply it twice.
#
# A global revision is intentionally simple for this single-user fixture. It
# rejects any graph change, including unrelated updates. It is not a proposed
# high-throughput distributed concurrency scheme or historical snapshot service.

# %%
before = reopened.answer(saved_query, saved_revision)
operation_id = str(uuid4())
new_revision = reopened.remove_edge(
    "p000000", "p000001", expected_revision=saved_revision, operation_id=operation_id,
)
assert reopened.remove_edge(
    "p000000", "p000001", expected_revision=saved_revision, operation_id=operation_id,
) == new_revision
try:
    reopened.answer(saved_query, saved_revision)
except StaleRevision as error:
    print("Expected stale-read rejection:", error)
else:
    raise AssertionError("Stale query unexpectedly succeeded.")
refreshed = reopened.answer(saved_query, reopened.revision)
assert refreshed != before
print("Explicitly refreshed answers:", refreshed)

# %% [markdown]
# ## 6. Demonstrate a transfer budget
#
# A budget failure means **incomplete**, not “nobody is reachable.” The backend
# also caps rows and SQLite VM instructions. JSON transfer is checked before it
# crosses into QuickJS, but after Python materializes it; this is not a peak-RAM
# guard. Defaults are lab safety limits, not production capacity targets.

# %%
limited = await run_probe(reopened, saved_query, "eager", byte_budget=1024)
assert not limited["valid"]
print(limited["error_type"], limited["tool_calls"])

# %% [markdown]
# ## 7. LIVE — let a real model write the PTC program (optional)
#
# Set RUN_LIVE=True to make three paid agent invocations. Only this section reads
# .env. ENV_FILE may point to your existing checkout's ignored .env; no secrets
# are copied automatically into this worktree. Existing LangSmith settings apply.
# The live run uses the current, updated graph. It records actual model calls and
# input/output/total tokens; missing usage invalidates the attempt.
# Accounting is retained even when the program or final answer fails. Inspect
# model_call_details for each observed call's usage and completion/error status.
# If usage_complete is false, aggregate token totals remain null; known per-call
# usage is still retained and must not be mistaken for the complete run cost.
#
# These are single trials, not a statistically controlled model comparison.
# Agent-generated code may fail the workload; failures remain visible.

# %% tags=["live"]
RUN_LIVE = False
ENV_FILE = ROOT / ".env"
if RUN_LIVE:
    from dotenv import load_dotenv
    from langchain.chat_models import init_chat_model
    from deepagents_lab.agent import DEFAULT_MODEL

    load_dotenv(ENV_FILE, override=False)
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY in ENV_FILE or your environment.")
    model_name = os.getenv("DEEPAGENTS_LAB_MODEL", DEFAULT_MODEL)
    if not model_name.startswith("openai:"):
        raise ValueError("This notebook's LIVE client is configured for openai: models.")
    live_rows = []
    for arm in ARMS:
        model = init_chat_model(model_name, timeout=60, max_retries=0, use_responses_api=True)
        live_rows.append(await run_probe(reopened, saved_query, arm, model=model))
        (RUN_DIR / "live.json").write_text(json.dumps(
            {**manifest, "model": model_name, "trials": live_rows}, indent=2,
        ))
    display(live_rows)
else:
    print("LIVE skipped. Set RUN_LIVE=True when ready for paid calls.")

# %% [markdown]
# ## What this establishes—and what remains unmeasured
#
# You can observe graph materialization, controlled PTC execution, payload
# reduction, thread snapshot size, persistent investigation records, optimistic
# stale-read rejection, retry-safe updates and explicit budget failures.
#
# Next scaling measurements would need concurrent clients, varied degree
# distributions, cache-cold runs, write contention, database restarts, real
# network latency, snapshot restore timings and representative graph engines.
# SQLite is a local teaching backend, not a claim about multi-tenant production
# capacity. The graph algorithm and supported query are deliberately narrow.
# Do not infer universal PTC speedups, cheap queries from small answers, or
# constant working sets when local degree grows.
#
# Outputs and SQLite files stay under ignored results/graph-workspace/.
# The default Agent Server, Agent Chat UI and prior reference notebooks are unchanged.
#
# Sources: [DeepAgents interpreters](https://docs.langchain.com/oss/python/deepagents/interpreters),
# [SQLite recursive queries](https://www.sqlite.org/lang_with.html),
# [Python SQLite progress handler](https://docs.python.org/3.12/library/sqlite3.html#sqlite3.Connection.set_progress_handler).
