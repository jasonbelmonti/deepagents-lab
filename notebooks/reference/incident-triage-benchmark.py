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
# # Four-stage incident triage: latency and token benchmark
#
# Follow the [PTC introduction](ptc-code-interpreter.ipynb) with a deeper workload:
# 20 incidents pass through **incident lookup → evidence → service context →
# classification**. Each of the first three stages returns 1,536 bytes of
# synthetic diagnostic data **per incident**. Only references and the final
# classification matter for the requested answer.
#
# Both agents use the same four batch APIs. The ordinary agent can batch all
# incidents per stage; the PTC agent writes a JavaScript program that follows
# references inside `eval`. This tests the effect of eliminating model turns
# between stages and filtering intermediate payloads. It does not impose serial
# per-record calls on the ordinary agent or insert artificial tool delays.
#
# This notebook makes **ten paid agent runs** by default: five pairs, alternating
# which arm runs first. Existing `.env` model and LangSmith settings apply.
# A single run can be interrupted; completed trial data is saved as it finishes.

# %%
import os
from pathlib import Path

from dotenv import load_dotenv
from IPython.display import Markdown, display

from deepagents_lab.agent import DEFAULT_MODEL
from deepagents_lab.benchmarks.incident_fixture import IncidentFixture
from deepagents_lab.benchmarks.incident_report import render_report
from deepagents_lab.benchmarks.incident_triage import BenchmarkConfig, run_benchmark

PROJECT_ROOT = next(
    path for path in (Path.cwd(), *Path.cwd().parents)
    if (path / "pyproject.toml").is_file()
)
load_dotenv(PROJECT_ROOT / ".env", override=False)
config = BenchmarkConfig(
    model=os.getenv("DEEPAGENTS_LAB_MODEL", DEFAULT_MODEL),
    pairs=5,
    records=20,
    payload_bytes=1536,
    first_arm="ordinary",
)
config

# %% [markdown]
# ## Inspect the fixture and expected result (offline)
#
# The tools simulate incident-management batch APIs. Every reference depends on
# a prior lookup and is checked by the fixture. Successful runs must process all
# 20 records exactly once at each of the four stages and return the exact sorted
# P1/P2 decisions, including the correct owner. Partial answers and skipped
# stages fail validation even if they look plausible.

# %%
fixture = IncidentFixture(config.records, config.payload_bytes)
print("Records:", len(fixture.ids))
print("Stages: 4; record-stage operations per successful run:", 4 * len(fixture.ids))
print("Expected escalations:")
fixture.expected

# %% [markdown]
# ## LIVE — run five alternating pairs
#
# Each trial constructs a fresh agent and client before timing `ainvoke`, and
# uses a fresh thread and fixture. The outer runs are sequential. Pair 1 runs
# ordinary then PTC; pair 2 reverses this order, and so on. Set `first_arm="ptc"`
# for the complementary schedule. No warm-up requests are made. Remote prompt
# caching can still vary; the report exposes cached input tokens where available.
#
# The same model settings apply to both arms. SDK retries are disabled, and each
# agent run has a 180-second deadline. Interpreter code uses the narrow tool
# allowlist with a five-second execution timeout and a 100-call budget. These
# settings and installed dependency versions are recorded with the results.
# OpenAI clients use Responses, matching the lab's DeepAgents configuration.
# Two consecutive provider request/access failures stop the run and retain the
# partial report so you can correct the configuration before retrying.

# %% tags=["live", "benchmark"]
if not os.getenv("OPENAI_API_KEY"):
    raise RuntimeError("Add OPENAI_API_KEY to the repository's ignored .env file.")

report = await run_benchmark(
    config,
    output_dir=PROJECT_ROOT / "results" / "incident-triage",
)

# %% [markdown]
# ## LIVE — inspect every trial and the paired comparison
#
# The report shows latency p50/p95, model calls, and input/output/total tokens.
# Token counts come from completed model responses via LangChain callbacks,
# including nested model activity. Missing usage is reported as unknown and
# invalidates that pair. Cached and reasoning counts are subsets of the input
# and output totals; do not add them again.
#
# Invalid runs remain in the raw report and trial table. Efficiency comparisons
# use only pairs where **both arms** pass all correctness and usage checks.
# Check that the report contains five valid pairs before interpreting reductions.

# %% tags=["live", "benchmark"]
display(Markdown(render_report(report)))
print("Raw JSON:", report["report_path"])

# %% [markdown]
# ## Read the result within its limits
#
# p50 is the median; p95 uses nearest rank. With five observations per arm, p95
# equals the observed maximum. It is an exploratory tail measurement, not a
# stable estimate of production p95. Repeat with more pairs and the reverse
# starting order for stronger evidence. A reduction may be negative: the report
# does not assume PTC wins.
#
# The workload uses deterministic local batch tools and controlled synthetic
# payloads. Real network tools introduce other bottlenecks. Depth and payload
# reduction are varied together here; this is not an attribution of speedup to
# one mechanism alone, nor a selection of the lab's evaluation framework.
#
# Reports are saved under the ignored `results/incident-triage/` directory with
# unique names. They include every trial, exact prompts/configuration, source
# and fixture hashes, usage details and root run IDs for matching LangSmith
# traces. Keep this notebook and its Jupytext pair output-free when committing.
#
# References: [DeepAgents interpreters](https://docs.langchain.com/oss/python/deepagents/interpreters)
# and [LangChain token usage](https://docs.langchain.com/oss/python/langchain/messages#token-usage).
