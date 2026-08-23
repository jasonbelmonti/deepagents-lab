# DeepAgents Lab

DeepAgents Lab is a local-first Python repository for controlled experiments with the [DeepAgents OSS library](https://github.com/langchain-ai/deepagents). The current repository is only the bootstrap for the comparative R0 described in the [design process packet](docs/design/deepagents-lab-design-process.md).

The evaluation baseline has not been selected. Inspect AI is the provisional open-source target and LangSmith trace evaluation is the required same-case control. The R0 evidence, eight-point indifference band, and decision rule in the design packet govern the eventual choice.

## Environment

- Python 3.12, acquired and selected by `uv`
- DeepAgents `0.7.8`
- Inspect AI `0.3.260`
- LangSmith SDK `0.11.1` in the `langsmith-control` dependency group

Install the frozen environment, including the development and control groups:

```bash
uv sync --frozen --all-groups
```

No model-provider or LangSmith credentials are required for repository setup or the smoke test.

## Test

Run the local smoke suite:

```bash
uv run --frozen --all-groups pytest -q
```

The smoke test verifies only that the package scaffold is installed correctly. Agent cases, evaluator adapters, model execution, tracing, and sandbox behavior belong to the comparative R0.

## Repository workflow

The root checkout holds the stable `main` baseline. Follow-on implementation work belongs in disposable, repository-local `.worktrees/` checkouts. Local environments, credentials, evaluator logs, traces, generated results, and sandbox state are ignored and must not be committed.
