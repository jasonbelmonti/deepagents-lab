# Notebook workspace

## State-to-correction self-steering (S → Y)

```bash
uv run --frozen --group notebooks jupyter lab \
  notebooks/experiments/state-steering.ipynb
```

Start here for the runtime experiment. S contains the observable history and
proposed final response. The captured problem X remains a retrospective
annotation; a small ridge model predicts the correction embedding Y directly
from S. A separate binary scorer learns when to intervene using reviewed positive
and negative examples. Training and runtime share one versioned state serializer.
Labels, later steering, and problem annotations never enter the state embedding.

Run All is offline with 66 authored synthetic checkpoints: 30 needing steering,
30 compliant controls, and 6 later scope changes that warrant no intervention
at the original checkpoint. Grouped holdouts compare predicted Y, state-neighbor
retrieval, direct correction similarity, and no intervention. The correction
library uses positive training examples only; validation selects regularization
and the intervention threshold. Reported false-positive rates and correction
family matches are wiring measurements, not evidence of successful task repair.

The notebook exports a reloadable JSON policy and demonstrates
`check_state(state, policy, embedder)` as the host integration point. It records
state serialization, embedding, gate, prediction and retrieval times separately.
A negative gate skips prediction/retrieval and any revision call. A positive gate
returns ranked historical advice for a bounded continuation. The experiment is
independent of the default agent. Its optional reviser produces text and has no
tools for executing missing work.

Use `EXAMPLES_JSONL` to import reviewed state/annotation records. Convert an
existing capture with `from_capture(record, needs_intervention=..., assessment=...)`;
review whether the correction was warranted given the old state. User silence
does not automatically label a checkpoint as correct. Both classes must occur
in each split, and duplicate states are rejected. Complete states over the
7,000 UTF-8 byte pilot limit fail explicitly instead of losing requirements.

LIVE embeddings are opt-in: up to 66 preparation requests for the default corpus,
then one uncached runtime embedding request and one cache-hit check. A separate
revision opt-in makes at most three chat requests across generic review and the
two gated advice arms. Actual token usage, cache behavior and timings are saved.
Credentials load from the ignored main-checkout `.env` only after opt-in; there
are no automatic provider retries. Results, manifests and policies remain under
ignored `results/state-steering/`. Helpers are in
`src/deepagents_lab/experiments/state_steering/`.

## Steering embeddings (capture-time problem descriptions)

```bash
uv run --frozen --group notebooks jupyter lab \
  notebooks/experiments/steering-embeddings.ipynb
```

At acceptance time, a model interprets the conversation and calls
`accept_steering(problem, correction)`. The backend embeds and preserves both
descriptions with their source conversation. The captured problem is X; the
requested correction is Y. This experiment compares direct correction search,
retrieval through similar problems, and a small ridge X→Y predictor.

Run All uses 36 authored synthetic events and deterministic lexical vectors,
with no credentials or provider calls. It demonstrates the pipeline; its scores
are not semantic-model or real-world efficacy evidence. Task/context groups stay
together across splits, only validation data selects regularization, and the
correction index contains training examples only. Metrics measure coarse
correction-family retrieval given a captured problem, not autonomous detection
or successful task repair.

The LIVE section is opt-in and configurable: it generates actual capture tool
arguments with the lab's OpenAI model and embeds them with
`text-embedding-3-small`. The default corpus schedules 36 capture requests and
up to 36 embedding requests, without automatic retries. A separate opt-in adds
four text-only revision calls for inspection. These calls cannot execute missing
work. Failed captures remain visible and prevent aggregate live scoring.

Import real conversations using the notebook's JSONL example and
`LIVE_EVENTS_JSONL`. Assign conversation/task `group_id` values and human
`family` relevance labels; neither is shown to the capture model. Keep transcripts
and generated records in ignored `results/steering-embeddings/`. LIVE loads the
ignored `.env` only after opt-in and disables tracing. When launched inside a
repository-local worktree, its default `ENV_FILE` points to the main checkout.
All captured text/vectors, split IDs, predictions, source hashes and observed
usage are saved locally. Helpers live in `src/deepagents_lab/experiments/steering/`.

## Conventions

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
