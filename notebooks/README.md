# Notebook workspace

Use `notebooks/reference/` for small, executable examples of reusable
DeepAgents techniques. Each tracked notebook has a paired Jupytext
`py:percent` source file so code review does not depend on notebook JSON.

Use `notebooks/experiments/` for discrete, tracked investigations. Their helpers
live under `src/deepagents_lab/experiments/<experiment>/`, independently of the
default agent and the reusable reference notebooks.

## Working agreement

- Keep experiment-specific tools and prompts close to their reference notebook.
- Import shared lab construction only when the experiment uses it unchanged.
- Treat cells marked **LIVE** as opt-in provider calls with normal API cost.
- Keep API keys in the repository's ignored `.env` file.
- Commit notebooks without cell outputs or execution counts.
- Put disposable investigations under `notebooks/scratch/`; that directory is
  ignored and is not durable evaluation evidence.

Launch a reference from the repository root:

```bash
uv run --frozen --group notebooks jupyter lab \
  notebooks/reference/ptc-code-interpreter.ipynb
```

For repeated latency/token measurements over a deeper four-stage workload:

```bash
uv run --frozen --group notebooks jupyter lab \
  notebooks/reference/incident-triage-benchmark.ipynb
```

The incident-triage benchmark runs five alternating pairs over 20 records. It
records every trial, validates complete work and exact answers, and displays
latency p50/p95 and token comparisons. Five samples make p95 exploratory.
Reports are saved under ignored `results/incident-triage/` directories. The
fixture, measurement, runner and report helpers live under
`src/deepagents_lab/benchmarks/` so the notebook stays focused on the experiment.

## Graph workspace (exploratory research, offline-first)

```bash
uv run --frozen --group notebooks jupyter lab \
  notebooks/experiments/graph-workspace.ipynb
```

Run All needs no API key. The notebook compares eager, bounded-neighborhood and
backend-side materialization on an indexed synthetic SQLite graph. It exercises
actual PTC, inspects thread snapshot sizes, persists small investigation records,
reopens them, applies a retry-safe host-side edit and rejects stale reads.
Increasing disconnected graph size and increasing local hub degree are distinct
knobs; neither alone establishes production scaling. Scripted-model timings and
logical JSON bytes are not provider latency, tokens, heap size or network bytes.

To let a real model write the program, set `RUN_LIVE=True` in the final section.
Set `ENV_FILE` to your ignored `.env` if it is in another checkout. Three paid
agent runs are made; failures and real usage are recorded. The default remains
offline, and offline probes suppress tracing. SQLite files and JSON measurements
are isolated under `results/graph-workspace/<run-id>/` and never committed.

Graph persistence is independent of PTC memory. Saved records contain query
parameters and the observed revision, not historical graph copies. Restore them
using the printed database path and investigation ID. This local experiment has
no distributed result-handle cache, tenant authorization, or production database
selection. The default Agent Server and UI are unchanged.

## Graph PTC value (agent comparison)

```bash
uv run --frozen --group notebooks jupyter lab \
  notebooks/experiments/graph-ptc-value.ipynb
```

1. Run all cells as committed. No key is needed: three scripted invocations
   exercise real DeepAgents/QuickJS without provider calls.
2. Read the separate historical pilot section. It loads committed metrics;
   it does not run a model. The first, confounded campaign is excluded.
3. Only when ready to spend, configure the LIVE cell, then change
   `RUN_LIVE = False` to `True`. Defaults are 24 paid agent invocations,
   not 24 API requests. Deadlines and work limits are not a dollar budget.

**Primary: ordinary (no interpreter) vs PTC.** **Secondary: compute-only
interpreter vs PTC.** Every arm shares graph data, batch APIs and limits.
Depth/width cases and a lookup control expose both benefits and overhead.
This is separate from graph workspace's exploratory loading/persistence work.

LIVE loads `ENV_FILE = ROOT / ".env"` only after opt-in. Use:

```dotenv
OPENAI_API_KEY=your-key
DEEPAGENTS_LAB_MODEL=openai:gpt-5.6-luna
```

Existing environment values win over `.env`. Set `ENV_FILE` to an absolute path
if your file lives in another checkout. LangSmith is optional; existing tracing
settings apply. No Agent Server or Agent Chat UI is required for this notebook.

For a smaller first run, change the configuration cell to
`config = replace(Config(), cases=(CASES[0],), seeds=(1103,))` before enabling
LIVE. That schedules three paid agent invocations, one per arm. Keep the default
offline checks unchanged. New campaigns go to unique ignored directories under
`results/graph-ptc-value/live/`; rerunning LIVE incurs additional calls.
After interrupting a campaign, restart the kernel: a narrow upstream cleanup
race can leave a daemon worker, although observed evidence is saved.

[Historical findings](../docs/experiments/graph-ptc-value/pilot-findings.md) and
[all-attempt tables](../docs/experiments/graph-ptc-value/pilot-tables.md) preserve
recorded failures, pair counts, tokens and latency. They predate current harness
fixes and are not current-code validation or held-out evidence. Scripted timings
are not live benefits. Keep all notebook outputs local and commit only the
synchronized source pair.

The separate [fresh-case campaign findings](../docs/experiments/graph-ptc-value/fresh-20260913/findings.md)
capture 60 later live invocations on the merged harness: four fresh seeds,
five workloads and all three arms. The committed extract includes every failure
and supports keyless arithmetic checks. It is not pooled with the earlier
pilot displayed by the notebook; no notebook rerun is needed to read these results.

## DuckDB code interpreter

```bash
uv run --frozen --group notebooks jupyter lab \
  notebooks/experiments/duckdb-code-interpreter.ipynb
```

DuckDB is included in the optional `notebooks` dependency group. No database
server or additional service is required. Run All needs no credentials: a
scripted model drives real DeepAgents + QuickJS + DuckDB, and checks the actual
interpreter results before and after a database update.

The interpreter runs JavaScript. `tools.duckdbSchema({})` and
`tools.queryDuckdb({sql, parameters})` bridge to Python's DuckDB package at
runtime. The notebook shows the agent construction, allowlist, SQL, generated
messages and query log. Helpers live in
`src/deepagents_lab/experiments/duckdb_runtime/`. Database files live in unique,
ignored `results/duckdb-code-interpreter/` directories.

For a real model, set `RUN_LIVE = True` and edit `QUESTION`. That section loads
`ENV_FILE = ROOT / ".env"`; point it at an absolute `.env` path when working in
a separate checkout. Existing environment values take precedence. The default
model follows `DEEPAGENTS_LAB_MODEL` or the lab default and uses `OPENAI_API_KEY`.
Each live invocation may incur multiple provider requests; rerunning it makes
new calls. The offline recipe is never included in the live prompt.

The agent can run one SELECT/CTE per query, with parameters, joins, aggregation
and window functions. The bridge rejects writes, external reads and oversized
results. Host cells create and update the fixture; keep write connections closed
while the agent reads. To explore your own CSV/Parquet, load it into tables from
host Python first. The notebook documents query, output and interpreter limits;
this remains a local experiment, not a process sandbox.

## DuckDB warm introductions

```bash
uv run --frozen --group notebooks jupyter lab \
  notebooks/experiments/duckdb-warm-introductions.ipynb
```

Forked from the basic DuckDB notebook. Find ranked, evidence-backed routes into
a synthetic job's team through direct contacts or up to three directed hops.
The fixture includes duplicate connectors, a weak high-degree hub, stale and
reverse-only edges, former employees and other distractors. Each answer includes
ordered relationship evidence and current-employment evidence. An independent
Python traversal checks the SQL results. The ranking is a fixture heuristic,
not a calibrated prediction of introduction success.

Run All with `RUN_LIVE=False` executes five provider-free agent invocations:
both tool transports, error recovery in each, and an employment-update probe.
Checks read actual SQL/eval outputs. `HUB_SIZE` (1–1000), `Question.max_hops`
(1–3), recency and `Question.top_k` (1–10) are exploration knobs. Rerun from
fixture setup after changing them. The update probe restores the original data.

Set `RUN_LIVE=True` for one matched pair by default: two paid agent invocations,
potentially several provider calls each. `LIVE_PAIRS` supports 1–5 pairs and
alternates arm order. Only LIVE loads `ENV_FILE`; use an absolute path to your
existing checkout's ignored `.env` if needed. Both arms receive identical SQL
capabilities and may solve the task with one query. The reference SQL and oracle
answer are never sent to live agents. An interpreter speedup is not assumed.

Unique ignored `results/duckdb-warm-introductions/` directories hold the DuckDB
file, per-attempt JSON and live manifests. Inspect generated calls, results,
errors, correctness, model calls, tokens and invocation latency together.
Missing usage stays unknown, with partial reported usage retained in call details.
Scripted runs are plumbing evidence; they do not measure provider performance.
Helpers live in `src/deepagents_lab/experiments/duckdb_warm_introductions/` and
reuse the basic notebook's read-only bridge. SQL errors return recoverable objects
and count toward the same 12-call budget in both arms.
