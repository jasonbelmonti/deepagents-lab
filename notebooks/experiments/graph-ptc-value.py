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
# # Does PTC add value to a graph investigation?
#
# **Hypothesis, not conclusion:** letting an agent call graph tools from code can
# reduce model round trips and intermediate model context, lowering tokens and
# latency **without losing correct answers** on multi-stage social-graph work.
#
# [Graph workspace](graph-workspace.ipynb) is exploratory research into graph
# loading, persistence and updates. This is a separate controlled comparison of
# **ordinary tools**, **ordinary tools + compute-only interpreter**, and **PTC**.
# All three read the same graph with the same batch APIs, filters and limits.
# **Primary: no interpreter (ordinary) vs interpreter with PTC.** This tests
# adding an interpreter-backed agent configuration. **Secondary: compute-only
# interpreter vs PTC** isolates access to graph tools from code more closely.
# The ordinary arm has no eval; the compute arm may choose not to use eval.
#
# Default Run All is offline and requires no credentials. It verifies the
# experiment, not the hypothesis. Only the opt-in LIVE section produces real
# model evidence for a new run. Section 6 loads a separate, historical development
# pilot from committed non-secret metrics; reading it makes no provider calls.
# No speedup is assumed or required.

# %%
from dataclasses import asdict, replace
from pathlib import Path

from IPython.display import Markdown, display

from deepagents_lab.experiments.graph_ptc_value.config import CASES, VARIANT, Config
from deepagents_lab.experiments.graph_ptc_value.fixture import make_graph
from deepagents_lab.experiments.graph_ptc_value.oracle import expected_answer
from deepagents_lab.experiments.graph_ptc_value.prompts import prompt_for
from deepagents_lab.experiments.graph_ptc_value.report import render_report
from deepagents_lab.experiments.graph_ptc_value.runner import run_benchmark
from deepagents_lab.experiments.graph_ptc_value.smoke import scripted_model
from deepagents_lab.experiments.graph_ptc_value.tools import GraphAPI

ROOT = next(p for p in (Path.cwd(), *Path.cwd().parents) if (p / "pyproject.toml").exists())
config = Config()
print("Planned LIVE agent invocations:", config.planned_runs)
print("Each invocation may make multiple paid model requests. Default LIVE is disabled.")

# %% [markdown]
# ## 1. A concrete warm-introduction question
#
# Find up to five graph engineers reachable through recent collaborations,
# excluding direct contacts and people contacted recently. Rank by the number
# of distinct first-hop connectors, then shortest path length, then person ID.
# Include a canonical supporting path for each connector. Paths are directed,
# date-filtered, bounded and cycle-free. The printed prompt gives exact rules.
#
# The generic tools only return relationships, selected profile fields and
# contact history. None knows the final answer. The model writes its own live
# program; no handwritten graph solver is included in its prompt.
# Validation also checks sufficient read evidence: all needed neighborhoods and
# enough profile/contact checks to establish the ranking. It allows different
# batching, repeated/repaired calls and pruning below an established top five;
# merely guessing an oracle-matching answer does not pass.
#
# This synthetic graph contains shared connections, alternate paths, cycles,
# stale relationships and irrelevant edge kinds. It models an introduction
# workflow, not arbitrary graph analytics or a real social network's capacity.

# %%
example_case, example_seed = CASES[2], 7  # Development example, not a live evaluation seed.
example_graph = make_graph(example_seed, example_case.width)
print(prompt_for(example_case, example_graph.root, "ptc", config))
print("Offline oracle (not supplied to the live agent):")
display(expected_answer(example_graph, example_case))
display([{"name": t.name, "description": t.description} for t in GraphAPI(example_graph).tools()])

# %% [markdown]
# ## 2. Predictions for a future run
#
# These are hypotheses to challenge, not preregistered claims about the historical
# pilot shown later. Our primary comparison was clarified after that pilot.
#
# - **Depth:** depth-2 vs depth-3 uses the same graph, changing only the allowed
#   path depth. We predict fewer additional model turns for PTC as dependent
#   discovery grows. More depth also exposes more records; this is not a pure
#   isolation of token volume from task complexity.
# - **Width:** depth-3 vs width-12 holds the question depth fixed while increasing
#   neighborhood size. We predict less growth in model input for PTC, because
#   code can discard intermediate edges/profiles before returning an answer.
# - **Negative control:** lookup asks for one person's topic. PTC may have no
#   advantage or be slower because code generation/execution adds work.
#
# The prediction is challenged if PTC costs more, fails more often, or does not
# reduce the expected model-turn/context burden. A favorable result on correct
# pairs alone does not establish value if PTC's overall success rate deteriorates.
#
# Each case gets fresh agents over identical data for each seed. Batches and
# independent parallel calls are allowed in every arm. The compute arm may
# choose not to use eval. PTC can repair its code; those extra calls count.
# No artificial tool delays or padded profile blobs favor one arm.
# Every arm receives the complete API input/output descriptions, including
# edge fields, defaults and contact-history absence semantics. A regression test
# inspects actual model messages/tool declarations: QuickJS's PTC renderer keeps
# only the first description line, so these descriptions are single-line values.

# %%
display([asdict(case) for case in config.cases])
print("Evaluation seeds:", config.seeds)
print("Optional question variant:", asdict(VARIANT))

# %% [markdown]
# ## 3. Verify the instrument, offline
#
# These three scripted runs execute actual DeepAgents tools and QuickJS. They
# check the runtime wiring and compare executed graph results against a Python
# oracle. The ordinary script uses batched expansion and parallel profile/contact
# calls; the PTC script does the same reads inside JavaScript.
#
# **The scripts are test fixtures, not evidence of model ability or savings.**
# Their prescribed model-call counts and timings must not be reported as live
# benefits. The report labels them scripted and leaves token usage unknown,
# even if a fake model supplies usage metadata. Unit tests additionally compare
# an independent JS solver on multiple seeds and test incorrect/missing work.

# %%
offline_config = replace(config, cases=(example_case,), seeds=(example_seed,))
offline_report = await run_benchmark(
    offline_config, ROOT / "results/graph-ptc-value/offline", model_factory=scripted_model,
)
assert all(row["correct"] for row in offline_report["trials"]), offline_report["report_path"]
assert all(row["total_tokens"] is None and not row["valid"] for row in offline_report["trials"])
display(Markdown(render_report(offline_report)))
print("Offline diagnostic artifact:", offline_report["report_path"])

# %% [markdown]
# ## 4. LIVE — let the model choose and execute the investigation
#
# Set RUN_LIVE=True below and run this cell. It loads your ignored `.env` using
# the same OPENAI_API_KEY and DEEPAGENTS_LAB_MODEL as the lab. ENV_FILE can point
# to another checkout's ignored file; no secrets are copied. Existing LangSmith
# settings apply, and each trial records its root run ID for trace lookup.
#
# Defaults: **24 paid agent invocations**, four cases × two seeds × three arms.
# This is a small pilot, not 24 individual API requests. Each invocation may make
# several requests; config bounds deadlines and tool work, not dollar spend.
# To start smaller, replace config.cases/seeds explicitly before enabling LIVE.
#
# Runs are sequential, with arm order rotating through six permutations. Model
# settings are identical across arms; SDK retries are off. No warm-up calls or
# artificial network delays are used. Provider load and prompt caching can still
# vary. Two consecutive provider request/access failures stop the campaign; a
# caller interruption also saves observed evidence and stops. Saved reports
# retain completed attempts, observed failed-call usage and unfinished-run markers.

# %% tags=["live", "benchmark"]
RUN_LIVE = False
ENV_FILE = ROOT / ".env"
live_report = None
if RUN_LIVE:
    import os
    from dotenv import load_dotenv

    load_dotenv(ENV_FILE, override=False)
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY in ENV_FILE or the environment.")
    live_config = replace(config, model=os.getenv("DEEPAGENTS_LAB_MODEL", config.model))
    if not live_config.model.startswith("openai:"):
        raise ValueError("This notebook's LIVE setup expects an openai: model.")
    live_report = await run_benchmark(live_config, ROOT / "results/graph-ptc-value/live")
else:
    print("LIVE skipped. No new model measurements; historical evidence is separate below.")

# %% [markdown]
# ## 5. Interpret the result without cherry-picking
#
# Start with correctness and all-attempt tokens, including errors and repairs.
# Missing usage makes complete cost unknown; the known lower bound is not the
# total. Cost per correct answer charges failed attempts to that arm. Correctness
# and complete usage are separate: missing provider metadata is not a wrong
# graph answer, but it excludes the attempt from token/latency comparisons.
#
# Then inspect matched ordinary→PTC results per case (primary), followed by
# compute→PTC (secondary). Only pairs where both runs
# pass answer, route, work and usage checks enter those comparisons. Positive
# percent reductions favor PTC; negative ones favor the baseline. This is
# explicitly conditional evidence, shown alongside unfiltered success rates.
# Model-call records include generated programs and the amount of tool-result
# text presented at each model call, to inspect the proposed mechanism.
#
# Two observations per arm/case cannot establish reliable statistical confidence
# or production p95. Freeze prompts/model/configuration after the development
# pilot, then repeat on **new seeds and new query variants** (for example VARIANT)
# without tuning on their answers. Do not pool the lookup and graph-search cases
# or report only whichever arm/case wins. If conclusions remain mixed, say so.

# %%
if live_report is not None:
    display(Markdown(render_report(live_report)))
    print("Replayable live evidence:", live_report["report_path"])
else:
    display(Markdown("**No new live results in this session.** Offline checks are not efficacy evidence."))

# %% [markdown]
# ## 6. Inspect the existing development pilot — no calls
#
# The pilot ran before the stack's later validation, framing and cleanup fixes.
# Its recorded correctness uses its historical scorer, not the current harness.
# The primary framing below is **post-hoc**; no measurements have been rerun or
# silently relabeled. The first, documentation-confounded pilot is excluded.
#
# [Curated findings](../../docs/experiments/graph-ptc-value/pilot-findings.md)
# explain every workload, the failures, controls and limitations.
# [Supporting tables](../../docs/experiments/graph-ptc-value/pilot-tables.md)
# include every attempt and both comparisons. The JSON is a whitelisted metric
# extract, not the original programs, prompts or full traces. Its raw-report
# digest binds it to the preserved local evidence; the audit command in the
# findings verifies that extract when the original raw report is available.

# %%
import json

EVIDENCE = ROOT / "docs/experiments/graph-ptc-value"
historical_metrics = json.loads((EVIDENCE / "pilot-metrics.json").read_text())
assert historical_metrics["sample_kind"] == "historical-development"
display(Markdown((EVIDENCE / "pilot-findings.md").read_text().split("## Audit")[0]))
display(Markdown((EVIDENCE / "pilot-tables.md").read_text()))

# %% [markdown]
# ## Scope of any eventual claim
#
# An honest finding would name the model, workload family, sample count,
# correctness rates and measured reductions. This tests whether programmable
# orchestration helps on these changing investigations, not whether PTC beats a
# purpose-built database query for a fixed question.
#
# Latency spans agent invocation, including model/code generation, tool work and
# interpreter lifecycle; agent construction and the correctness oracle are outside
# timing. A narrow upstream cancellation-during-cleanup race can leave a daemon
# worker; cancellation still returns evidence and processes exit normally. Restart
# the notebook kernel after interrupting a campaign. This is not a production
# lifecycle guarantee. Backend service times may overlap and are nested within invocation
# time. No exclusive interpreter-overhead or real network-service benchmark is
# claimed. JSON response bytes and context text characters are not tokens, heap
# size or wire traffic. Token counts come only from real provider responses;
# cached and reasoning details are subsets, not additional totals.
#
# Fixtures, exact prompts/settings, versions, source hashes, expected answers,
# tool requests and trial accounting are written to unique ignored directories
# under results/graph-ptc-value. Notebook sources remain output-free. No new
# dependency, service, UI fork or default-agent change is required.
#
# Reference: [DeepAgents interpreters](https://docs.langchain.com/oss/python/deepagents/interpreters).
