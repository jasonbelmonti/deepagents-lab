# Notebook workspace

Use `notebooks/reference/` for small, executable examples of reusable
DeepAgents techniques. Each tracked notebook has a paired Jupytext
`py:percent` source file so code review does not depend on notebook JSON.

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
