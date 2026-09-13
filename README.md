# DeepAgents Lab

DeepAgents Lab is a local-first workbench for controlled experiments with the [DeepAgents OSS library](https://github.com/langchain-ai/deepagents). It includes a Python Agent Server and an exact-pinned, unmodified upstream Agent Chat UI submodule for browser-based experiments. The comparative evaluation baseline remains governed by the [design process packet](docs/design/deepagents-lab-design-process.md).

## Quick start

### Prerequisites

- Git
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/)
- Node.js `22.20.0` with Corepack available
- An OpenAI API key

`uv` installs and selects the repository's required Python 3.12 runtime. The
upstream Agent Chat UI pins its own pnpm version, which Corepack supplies.

### 1. Install the project

Clone the private repository if needed, then enter it:

```bash
git clone git@github.com:jasonbelmonti/deepagents-lab.git
cd deepagents-lab
```

Install the frozen server, UI, and test environment. Notebook dependencies stay
out of this default workflow:

```bash
uv sync --frozen --group langsmith-control
```

### 2. Configure local credentials

Create the ignored local environment file:

```bash
cp .env.example .env
```

Open `.env` and add your OpenAI API key:

```dotenv
OPENAI_API_KEY=your-key-here
DEEPAGENTS_LAB_MODEL=openai:gpt-5.6-luna

LANGSMITH_TRACING=false
LANGSMITH_API_KEY=
LANGSMITH_PROJECT=deepagents-lab
```

Only `OPENAI_API_KEY` is required for an agent run. Leave LangSmith tracing
disabled unless you want to upload traces.

### 3. Start the Agent Server

In terminal 1, from the repository root:

```bash
uv run --frozen deepagents-server
```

Wait for the server to report that it is listening on `127.0.0.1:2024`.

### 4. Start Agent Chat UI

In terminal 2, from the same repository root:

```bash
uv run --frozen deepagents-ui
```

The first launch takes longer because this command initializes the exact-pinned
UI submodule and installs its frozen JavaScript dependencies. Later launches
still verify the frozen install but reuse the local dependency store.

### 5. Try the agent

Open [http://127.0.0.1:3000](http://127.0.0.1:3000), submit a message, and then
send a follow-up in the same thread. Use the **New thread** button in the Agent
Chat header to start an isolated chat.

The local services are:

- Agent Chat UI: `http://127.0.0.1:3000`
- Agent Server: `http://127.0.0.1:2024`
- Agent Server API documentation: `http://127.0.0.1:2024/docs`
- Graph ID: `deepagents_lab`

Stop each process with `Ctrl-C` in its terminal.

## Optional LangSmith tracing

To send server-side traces to LangSmith, update `.env`:

```dotenv
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your-key-here
LANGSMITH_PROJECT=deepagents-lab
```

Restart the Agent Server after changing `.env`. Model and tracing credentials
remain in the Python server process and are not passed to the browser UI.

## Test

Run the local smoke suite:

```bash
uv run --frozen --all-groups pytest -q
```

The tests verify the package scaffold and live-invocation boundary without making
network calls. Evaluator adapters, tracing, and sandbox behavior belong to the
comparative R0.

No OpenAI or LangSmith credentials are required for installation or the offline
test suite.

## Live model smoke

Supply your OpenAI API key through the current shell or a secret manager. Do not
put it in `.env.example` or another tracked file.

```bash
export OPENAI_API_KEY="..."
uv run --frozen deepagents-live \
  "Reply with exactly DEEPAGENTS_LIVE_OK and nothing else."
```

The command uses `openai:gpt-5.6-luna` by default. Override it through the
command line or the `DEEPAGENTS_LAB_MODEL` environment variable documented in
`.env.example`:

```bash
uv run --frozen deepagents-live --model openai:gpt-5.6-luna \
  "Reply with exactly DEEPAGENTS_LIVE_OK and nothing else."
```

A successful run prints the model's final assistant response. This is an opt-in
provider call that incurs normal API usage; it is not yet an evaluation case.

## Notebook experiments

Install the optional notebook environment and open the tracked PTC/code
interpreter reference with one command:

```bash
uv run --frozen --group notebooks jupyter lab \
  notebooks/reference/ptc-code-interpreter.ipynb
```

The reference demonstrates two distinct interpreter paths:

- capability-scoped JavaScript execution through the QuickJS-backed `eval` tool;
- programmatic tool calling (PTC), where that JavaScript calls explicitly
  allowlisted, read-only Python tools through the `tools.*` namespace.

It also runs the same two-stage workload through ordinary tool calling and PTC,
then compares end-to-end latency, model-call count, and provider-reported input,
output, and total token usage. The single comparison is explanatory rather than
decision-grade benchmark evidence; the notebook documents the repeated-trial
controls needed for that claim.

For the repeated four-stage incident-triage benchmark (20 records, five
alternating pairs, latency p50/p95 and token usage), open:

```bash
uv run --frozen --group notebooks jupyter lab \
  notebooks/reference/incident-triage-benchmark.ipynb
```

It makes ten paid agent runs and saves every trial under ignored
`results/incident-triage/`. Comparisons require correct answers and complete
record coverage from both arms; failed runs stay visible. With five pairs,
reported p95 is the observed maximum and remains exploratory.

In these two references, run the cells marked **LIVE** to make OpenAI API calls
using the same
`OPENAI_API_KEY` and `DEEPAGENTS_LAB_MODEL` values as the rest of the lab. The
notebook loads the repository's ignored `.env` file, so no manual export is
required. Those calls incur normal provider usage and optionally emit LangSmith
traces under the existing `.env` configuration.

For a separate, **offline-first graph experiment**, open:

```bash
uv run --frozen --group notebooks jupyter lab \
  notebooks/experiments/graph-workspace.ipynb
```

Run All works without credentials. It compares full graph loading, bounded
neighborhood loading, and backend-side path queries through real QuickJS. It
also demonstrates interpreter snapshot sizes, SQLite-backed investigation
records, explicit graph updates, stale-revision rejection, and work budgets.
Its scripted-model timings are local infrastructure measurements, not live
model performance or production scaling evidence. An optional `RUN_LIVE=True`
section makes three paid invocations and records real token usage; only that
section loads `.env`. All databases and measurements stay under ignored
`results/graph-workspace/` directories. No new dependency or service is required.

For the **no-interpreter vs PTC agent comparison**, open:

```bash
uv run --frozen --group notebooks jupyter lab \
  notebooks/experiments/graph-ptc-value.ipynb
```

This tests whether adding an interpreter with PTC helps warm-introduction
investigations. Ordinary (no interpreter) vs PTC is primary; compute-only vs PTC
is a secondary control. Graph workspace above remains exploratory research.
Default Run All requires no keys: it runs three scripted checks and displays
separate historical pilot findings. It makes no new model measurements.
Only changing `RUN_LIVE = False` to `True` enables paid runs (24 agent invocations
by default, potentially many more API requests). That section loads the ignored
`.env`; see [the notebook guide](notebooks/README.md#graph-ptc-value-agent-comparison)
for configuration and a smaller first run.

[Historical findings and auditable metrics](docs/experiments/graph-ptc-value/pilot-findings.md)
show mixed latency results and conditional token savings, not a general speedup.

[Fresh-case results from 60 live invocations](docs/experiments/graph-ptc-value/fresh-20260913/findings.md)
capture four new seeds and a reserved question variant on the merged harness.
PTC saved tokens on multi-step cases and passed more harder cases; latency
benefits remain limited. All failures and missing matched comparisons are retained.

Each `.ipynb` is paired with a review-friendly Jupytext `py:percent` source file.
Keep both files synchronized and output-free before committing:

```bash
uv run --frozen --group notebooks jupytext --sync \
  notebooks/reference/ptc-code-interpreter.ipynb
uv run --frozen --group notebooks jupyter nbconvert --clear-output --inplace \
  notebooks/reference/ptc-code-interpreter.ipynb
```

See [the notebook workspace guide](notebooks/README.md) for the isolation and
commit conventions.

## Local Agent Server

The repository exposes the same DeepAgents construction used by
`deepagents-live` through a loopback-only local Agent Server. Its stable client
coordinates are:

- Server URL: `http://127.0.0.1:2024`
- Graph ID: `deepagents_lab`
- API documentation: `http://127.0.0.1:2024/docs`

After completing the quick-start configuration, start the fixed loopback server
with one command:

```bash
uv run --frozen deepagents-server
```

`deepagents-server` loads `.env` through `langgraph.json`, binds to
`127.0.0.1:2024`, and suppresses automatic browser launch. No manual exports
are required.

The server starts and exposes basic discovery without either an OpenAI or
LangSmith credential. `OPENAI_API_KEY` is required when the server materializes
the configured `openai:gpt-5.6-luna` graph for schema inspection or a run. The key
stays in the server environment and is never sent to a local UI client. No
LangSmith account, API key, Studio session, or trace upload is required for this
workflow.

While the server is running, verify the registered graph from another shell:

```bash
curl -fsS -X POST -H 'Content-Type: application/json' \
  -d '{"limit":10,"offset":0}' \
  http://127.0.0.1:2024/assistants/search
```

Stop the server with `Ctrl-C`. Development thread state is written beneath the
ignored `.langgraph_api/` directory and is not evaluation evidence.

The exact `langgraph-cli[inmem]==0.4.31` development dependency resolves
`langgraph-api==0.13.0`. The CLI is MIT-licensed; the Agent Server runtime uses
the [Elastic License 2.0](https://pypi.org/project/langgraph-api/) and is kept at
this local development boundary. It is not represented here as an OSI
open-source or production deployment component.

## Local Agent Chat UI

`apps/agent-chat-ui` is a Git submodule pointing directly to LangChain's
[Agent Chat UI repository](https://github.com/langchain-ai/agent-chat-ui) at an
exact commit. The lab does not copy, patch, or maintain upstream UI source.

`deepagents-ui` initializes the exact-pinned submodule, installs from its frozen
pnpm lock, and runs the unchanged upstream application on
`http://127.0.0.1:3000`. It supplies the upstream-supported deployment URL
`http://127.0.0.1:2024` and graph ID `deepagents_lab`, so no setup form or UI
environment file is needed for the lab workflow.

The launcher removes inherited OpenAI, LangSmith, deployment-proxy, UI-auth,
and AI-agent detection variables before starting the UI process. Model and
optional tracing credentials remain in the Python server process, while the
detection cleanup prevents Next.js from generating untracked agent-instruction
files inside the submodule. Agent Chat UI itself remains unmodified and retains
all capabilities provided by upstream.

Submodule dependencies, Next.js build output, local environment files, browser
evidence, and Agent Server runtime state are ignored. This application is a
local development surface, not evaluation evidence or a production deployment.

## Evaluation status

The evaluation baseline has not been selected. Inspect AI is the provisional
open-source target and LangSmith trace evaluation is the required same-case
control. The R0 evidence, eight-point indifference band, and decision rule in
the design packet govern the eventual choice.

## Repository workflow

The root checkout holds the stable `main` baseline. Follow-on implementation work belongs in disposable, repository-local `.worktrees/` checkouts. Local environments, credentials, evaluator logs, traces, generated results, and sandbox state are ignored and must not be committed.
