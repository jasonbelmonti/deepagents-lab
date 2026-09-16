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
# # Self-steering from observable state: S → Y
#
# Can a cheap predictor select useful corrections from the information available
# **before** a user intervenes? This extends `steering-embeddings.ipynb`:
#
# - **S:** a frozen history plus the proposed final response.
# - **X:** the retrospective description of what needed steering; an annotation.
# - **Y:** the captured corrective instruction, used as a training target.
#
# `S → embedding → intervention gate → predicted Y → stored correction text`
#
# The runtime function accepts only S. X, user steering, relevance labels, and
# group IDs are excluded from the embedding input. Both training and runtime
# use the same versioned serializer; assembling S makes no language-model call.
#
# **Run All is offline:** 66 authored synthetic checkpoints and lexical vectors.
# Scores demonstrate wiring only. LIVE embeddings and revisions are separate
# opt-ins. This experiment checks proposed final responses; it does not install
# middleware in the lab's default agent or execute tools to repair tasks.

# %%
import json
import os
from pathlib import Path
from uuid import uuid4

from IPython.display import HTML, display

from deepagents_lab.agent import DEFAULT_MODEL
from deepagents_lab.experiments.steering.embeddings import LexicalEmbedder
from deepagents_lab.experiments.steering.report import table
from deepagents_lab.experiments.state_steering.artifacts import load_policy, save_experiment
from deepagents_lab.experiments.state_steering.dataset import embed_examples, load_examples
from deepagents_lab.experiments.state_steering.evaluation import evaluate
from deepagents_lab.experiments.state_steering.fixture import make_state_fixtures
from deepagents_lab.experiments.state_steering.revision import revision_messages
from deepagents_lab.experiments.state_steering.runtime import check_state
from deepagents_lab.experiments.state_steering.state import build_state, state_text

ROOT = next(p for p in (Path.cwd(), *Path.cwd().parents) if (p / "pyproject.toml").exists())
RUN_DIR = ROOT / "results" / "state-steering" / str(uuid4())
RUN_DIR.mkdir(parents=True)
SEED = 42
MAX_VALIDATION_FALSE_POSITIVE_RATE = 0.10
examples = make_state_fixtures()
embedder = LexicalEmbedder(dimensions=512)
print("Results:", RUN_DIR)
print("Examples:", len(examples), "| Intervention:", sum(e.needs_intervention for e in examples))

# %% [markdown]
# ## 1. Inspect the input and annotation boundary
#
# The history contains the original requirements and observable evidence. The
# proposed response is the response we are about to release. A missing result
# and a result that was never produced are different situations.
#
# No summary model is used. The complete serialized state has a conservative
# 7,000 UTF-8 byte limit for this pilot. Oversized inputs fail explicitly;
# requirements are never silently dropped. Larger histories require a separately
# evaluated state-selection strategy used identically in training and serving.

# %%
example = examples[0]
print("Actual embedding input S:\n", state_text(example.state))
display(HTML(table([{
    "problem_X_annotation": example.problem, "correction_Y_target": example.correction,
    "needs_intervention_label": example.needs_intervention, "assessment": example.assessment,
}])))

# %% [markdown]
# ## 2. Include independently judged no-intervention cases
#
# The fixture has 30 unmet-requirement cases, 30 matched compliant controls, and
# 6 cases where the user introduced new scope afterward. The last group retains
# its captured problem/correction annotation but is labeled **no intervention at
# the earlier checkpoint**. Predicting an unannounced new requirement is outside
# this experiment. Absence of user feedback is never automatically a negative.
#
# All cases from a context, including positive/control pairs, share one group.
# Six groups and repeated templates are too small for reliable efficacy claims.

# %%
display(HTML(table([{
    "sample_id": e.sample_id, "group": e.group_id, "needs_intervention": e.needs_intervention,
    "assessment": e.assessment,
} for e in examples[:11]])))
records = embed_examples(examples, embedder)
print("Embedded S for every row; embedded Y only for positive rows. X remains text annotation.")

# %% [markdown]
# ## 3. Train, tune on validation, then evaluate held-out states
#
# A binary ridge scorer learns whether to intervene. Its score is not a
# calibrated probability. The threshold maximizes validation recall subject to
# the chosen validation false-positive limit; this is not a guaranteed runtime
# false-positive bound. The mapping fits S→Y on positive training rows only.
#
# Compare the same gate with three selectors:
# - **direct_correction:** compare S with stored correction embeddings.
# - **state_neighbors:** find similar historical S and return its paired Y text.
# - **ridge_prediction:** predict Y from S and retrieve correction text near Y.
#
# **no_intervention** leaves every draft alone. The library contains training
# corrections only. Mapping regularization and the gate threshold never use
# test labels or test Y vectors. Group IDs and family labels are not features.

# %%
report, policy, splits = evaluate(
    records, seed=SEED, max_validation_false_positive_rate=MAX_VALIDATION_FALSE_POSITIVE_RATE,
)
display(HTML(table([{"split": name, "groups": report["split_group_ids"][name], "rows": len(rows)}
                    for name, rows in splits.items()])))
display(HTML(table(report["mapping_tuning"])))
display(HTML(table([report["selected_gate"]])))
display(HTML(table(report["summary"])))
save_experiment(RUN_DIR / "offline", report, records, policy)

# %% [markdown]
# **Read the metrics separately:** intervention recall measures detected positive
# cases; false-positive rate measures unnecessary interventions on negatives.
# Positive family hit@1/MRR measures correction selection before the gate.
# Useful selection precision counts interventions that select the labeled family.
# Selection accuracy credits correct family interventions and correct abstentions.
# No accepted interventions gives undefined precision, not perfect precision.
# A family match does not establish that applying the instruction repairs a task.

# %%
display(HTML(table(report["trials"]["ridge_prediction"], [
    "sample_id", "needs_intervention", "intervene", "gate_score", "expected_family",
    "predicted_family", "family_hit", "correction",
])))

# %% [markdown]
# ## 4. Reload the policy and check a runtime state
#
# `check_state(state, policy, embedder)` is the host integration point. It embeds
# S once, scores the intervention gate, and only predicts/retrieves when needed.
# A host can check a proposed response before publishing it, then pass returned
# advice into a bounded continuation. The serialized policy contains weights,
# embedding identity, state format, threshold, and the training correction library.
# No historical problem description or researcher label is required at runtime.

# %%
loaded_policy = load_policy(RUN_DIR / "offline" / "policy.json")
QUERY_INDEX = 0
runtime_state = splits["test"][QUERY_INDEX].example.state
decision = check_state(runtime_state, loaded_policy, embedder)
display(HTML(table([{key: decision[key] for key in
                     ("intervene", "gate_score", "threshold", "advice", "state_bytes", "provider_requests")}])))
display(HTML(table(decision["candidates"])))
display(HTML(table([decision["timings"]])))
if decision["intervene"]:
    print("Payload for a text-only revision:\n", revision_messages(runtime_state, decision["advice"])[-1].content)
else:
    print("Continue with the existing response; no revision call.")

# %% [markdown]
# The host can supply a new state directly. Include the relevant original
# instructions and actual observed tool results in history. No issue summary is
# requested. Every serialized state gets the same preprocessing as training.

# %%
custom_state = build_state(
    history=[
        {"role": "user", "content": "Implement STAR-1234, run its experiment, and report the measured results."},
        {"role": "tool", "content": "Experiment finished: p95 latency fell from 120 ms to 105 ms."},
    ],
    proposed_response="I finished implementing STAR-1234.",
)
custom_decision = check_state(custom_state, loaded_policy, embedder)
display(HTML(table([{key: custom_decision[key] for key in ("intervene", "gate_score", "advice")}])))
print("This is a prediction to inspect, not a verified correction.")

# %% [markdown]
# ## 5. Inspect runtime overhead
#
# Timings separate serialization, embedding, gate, Y prediction and retrieval.
# `provider_requests` and `provider_calls` distinguish actual requests from cache
# hits. Offline timings use lexical vectors and say nothing about API latency.
# Array bytes exclude Python object overhead, correction text and service costs.
# Capture/annotation cost is offline; an agent revision is additional runtime work.

# %%
checks = [check_state(r.example.state, loaded_policy, embedder) for r in splits["test"]]
display(HTML(table([{"sample_id": record.example.sample_id, "intervene": check["intervene"],
                    **check["timings"]} for record, check in zip(splits["test"], checks)])))
(RUN_DIR / "offline" / "runtime-checks.json").write_text(json.dumps(checks, indent=2))
print("Policy numerical array bytes:", report["policy_array_bytes"])

# %% [markdown]
# ## 6. Import reviewed real examples
#
# Exported JSONL has `state`, `needs_intervention`, `assessment`, and optional
# `problem`, `correction`, `family`, `source_event_id`. Positives require all
# three annotations. Use one original task/conversation per `group_id`, keeping
# controls, paraphrases and related checkpoints in the same group.
#
# Convert an existing `CapturedExample` with
# `from_capture(record, needs_intervention=True, assessment="...")` from
# `state_steering.dataset`. The label and assessment require review: an observed
# steering event may introduce new scope. Preserve the original capture separately.
# For controls, author a `StateExample` from a reviewed checkpoint; user silence
# alone does not establish that the response was correct.
#
# Set `EXAMPLES_JSONL` below to use this format with semantic embeddings. Both
# label classes must be present in every split. Duplicate states are rejected.

# %%
example_path = RUN_DIR / "example-states.jsonl"
example_path.write_text("\n".join(e.model_dump_json() for e in examples) + "\n")
assert len(load_examples(example_path)) == len(examples)
print("Reviewed-state JSONL example:", example_path)

# %% [markdown]
# ## 7. LIVE: semantic S/Y embeddings and runtime measurement
#
# Default corpus: up to **66 embedding requests**, each containing S and, for
# positive rows, Y. Exact cached inputs reuse vectors. No capture or chat model
# is needed here because problem/correction annotations already exist.
# At most 120 examples per live run. No automatic provider retries.
#
# One held-out runtime check uses a separate empty cache: **one additional
# embedding request**, then a second check demonstrates the warm cache. Actual
# tokens and latency are saved. This measures one example, not a latency SLA.
# Input texts go to the configured provider only after opt-in. Credentials load
# only in this cell. A failed run preserves usage logs and raises, withholding
# aggregate results instead of silently dropping failures.

# %% tags=["live"]
RUN_LIVE_EMBEDDINGS = False
EXAMPLES_JSONL = None
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 256
MAIN_CHECKOUT = ROOT.parent.parent if ROOT.parent.name == ".worktrees" else ROOT
ENV_FILE = MAIN_CHECKOUT / ".env"
live_report, live_policy, live_splits = None, None, None

if RUN_LIVE_EMBEDDINGS:
    from dotenv import load_dotenv
    from openai import OpenAI
    from deepagents_lab.experiments.steering.embeddings import OpenAIEmbedder

    load_dotenv(ENV_FILE, override=False)
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY in the environment or ENV_FILE before LIVE.")
    live_examples = load_examples(Path(EXAMPLES_JSONL)) if EXAMPLES_JSONL else examples
    if not 1 <= len(live_examples) <= 120:
        raise ValueError("Select 1–120 reviewed examples for this live pilot.")
    LIVE_DIR = RUN_DIR / "live" / str(uuid4())
    client = OpenAI(timeout=60, max_retries=0)
    live_embedder = OpenAIEmbedder(client, LIVE_DIR / "training-cache", EMBEDDING_MODEL, EMBEDDING_DIMENSIONS)
    runtime_embedder = OpenAIEmbedder(client, LIVE_DIR / "runtime-cache", EMBEDDING_MODEL, EMBEDDING_DIMENSIONS)
    try:
        live_records = embed_examples(live_examples, live_embedder)
        live_report, live_policy, live_splits = evaluate(
            live_records, seed=SEED, max_validation_false_positive_rate=MAX_VALIDATION_FALSE_POSITIVE_RATE,
        )
        save_experiment(LIVE_DIR, live_report, live_records, live_policy)
        display(HTML(table(live_report["summary"])))
        live_state = live_splits["test"][QUERY_INDEX].example.state
        live_checks = [check_state(live_state, live_policy, runtime_embedder) for _ in range(2)]
        (LIVE_DIR / "runtime-checks.json").write_text(json.dumps(live_checks, indent=2))
        display(HTML(table([{"cache": label, "provider_requests": check["provider_requests"], **check["timings"]}
                            for label, check in zip(("cold", "warm"), live_checks)])))
    finally:
        (LIVE_DIR / "embedding-calls.json").write_text(json.dumps({
            "preparation": live_embedder.calls, "runtime": runtime_embedder.calls,
        }, indent=2))
else:
    print("LIVE embeddings skipped; no credentials loaded or provider calls made.")

# %% [markdown]
# ## 8. LIVE: apply guidance to the same draft
#
# Separate opt-in compares the original draft, generic review, gated state-neighbor
# guidance and gated predicted-Y guidance. At most **three chat model requests**;
# a negative gate returns the original draft without invoking the reviser.
# All arms start from the same observable state, with no later steering or X.
#
# Revisions are text-only, bounded to one attempt per arm, with tracing disabled.
# They can improve a report or acknowledge missing work; they cannot run missing
# tests. Inspect text, unnecessary changes, token usage and elapsed time together.
# The checkpoint hash prevents applying a decision to a different state.

# %% tags=["live"]
RUN_LIVE_REVISIONS = False
REVISION_MODEL = None
if RUN_LIVE_REVISIONS:
    if live_policy is None:
        raise RuntimeError("Run LIVE embeddings successfully before enabling revisions.")
    from langchain_openai import ChatOpenAI
    from deepagents_lab.experiments.state_steering.revision import compare_revisions

    model_name = REVISION_MODEL or os.environ.get("DEEPAGENTS_LAB_MODEL", DEFAULT_MODEL)
    revision_model = ChatOpenAI(model=model_name.removeprefix("openai:"), timeout=60, max_retries=0)
    revision_rows = compare_revisions(live_state, live_policy, runtime_embedder, revision_model,
                                      LIVE_DIR / "revisions" / str(uuid4()))
    display(HTML(table(revision_rows, ["arm", "advice", "revised", "ok", "text", "usage", "revision_ms"])))
else:
    print("LIVE revisions skipped.")

# %% [markdown]
# ## What would count as useful evidence?
#
# Use independently reviewed real conversations and compliant controls, held out
# by task and preferably later time periods. Compare the S→Y mapping with paired
# state retrieval at the same intervention threshold. Measure unnecessary
# interventions, selected guidance, actual task improvement and total inference
# cost. A good synthetic family score alone answers none of those questions.
#
# Problem X remains useful for diagnosing failure families and labeling examples.
# Future user preferences must be observable in S if they should condition the
# result. A single pooled vector and linear model are experimental choices;
# matching train/runtime schemas does not guarantee arbitrary-state generalization.
#
# References: [MemPrompt](https://aclanthology.org/2022.emnlp-main.183/),
# [learning to predict critiques](https://arxiv.org/abs/2602.16066), and
# [official embedding documentation](https://developers.openai.com/api/docs/guides/embeddings).
# Reports, vectors, source checksums, portable policies and provider usage are
# saved under ignored `results/state-steering/`. Source notebooks remain output-free.
