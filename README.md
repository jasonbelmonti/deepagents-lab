# DeepAgents Lab

DeepAgents Lab is a local-first Python repository for controlled experiments with the [DeepAgents OSS library](https://github.com/langchain-ai/deepagents). The current repository is only the bootstrap for the comparative R0 described in the [design process packet](docs/design/deepagents-lab-design-process.md).

The evaluation baseline has not been selected. Inspect AI is the provisional open-source target and LangSmith trace evaluation is the required same-case control. The R0 evidence, eight-point indifference band, and decision rule in the design packet govern the eventual choice.

## Environment

- Python 3.12, acquired and selected by `uv`
- DeepAgents `0.7.8`
- Inspect AI `0.3.260`
- LangChain's OpenAI integration for live model calls
- LangSmith SDK `0.11.1` in the `langsmith-control` dependency group

Install the frozen environment, including the development and control groups:

```bash
uv sync --frozen --all-groups
```

No model-provider or LangSmith credentials are required for repository setup or the
offline test suite.

## Test

Run the local smoke suite:

```bash
uv run --frozen --all-groups pytest -q
```

The tests verify the package scaffold and live-invocation boundary without making
network calls. Evaluator adapters, tracing, and sandbox behavior belong to the
comparative R0.

## Live model smoke

Supply your OpenAI API key through the current shell or a secret manager. Do not
put it in `.env.example` or another tracked file.

```bash
export OPENAI_API_KEY="..."
uv run --frozen deepagents-live \
  "Reply with exactly DEEPAGENTS_LIVE_OK and nothing else."
```

The command uses `openai:gpt-5.4` by default. Override it through the command line
or the `DEEPAGENTS_LAB_MODEL` environment variable documented in `.env.example`:

```bash
uv run --frozen deepagents-live --model openai:gpt-5.4 \
  "Reply with exactly DEEPAGENTS_LIVE_OK and nothing else."
```

A successful run prints the model's final assistant response. This is an opt-in
provider call that incurs normal API usage; it is not yet an evaluation case.

## Repository workflow

The root checkout holds the stable `main` baseline. Follow-on implementation work belongs in disposable, repository-local `.worktrees/` checkouts. Local environments, credentials, evaluator logs, traces, generated results, and sandbox state are ignored and must not be committed.
