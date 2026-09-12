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

## Graph workspace (offline-first)

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
