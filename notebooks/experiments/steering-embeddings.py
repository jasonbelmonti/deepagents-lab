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
# # Steering embeddings: capture, predict, retrieve, apply
#
# At the moment an agent accepts steering, a model reads the conversation and
# describes **what needed steering** and **the correction requested**. Embed
# those two descriptions as X and Y. Can a small learned X→Y mapping retrieve
# useful corrective guidance for another captured problem?
#
# **The captured problem description is X.** The capture model intentionally
# sees the user's steering. This notebook tests correction recommendation given
# that description. Detecting a problem before the user intervenes is a separate
# experiment. We do not substitute the last assistant message for X.
# See `state-steering.ipynb` for the companion S→Y experiment, which keeps X as
# an annotation and predicts from the observable state before steering.
#
# **Run All is offline.** It uses 36 authored synthetic conversations, authored
# capture arguments, and deterministic lexical vectors. These are wiring checks,
# not measured model extraction or evidence of semantic prediction quality.
# The LIVE section performs actual model capture and semantic embedding calls.
#
# Experiment flow:
#
# `conversation + steering → model → accept_steering(problem, correction)`
#
# `stored X/Y pairs → train/validation/test → predicted Y → correction text`

# %%
import json
import os
from pathlib import Path
from uuid import uuid4

from IPython.display import HTML, display
from langsmith import tracing_context

from deepagents_lab.agent import DEFAULT_MODEL
from deepagents_lab.experiments.steering.capture import CaptureStore, load_events
from deepagents_lab.experiments.steering.embeddings import LexicalEmbedder
from deepagents_lab.experiments.steering.evaluation import evaluate, margin_sweep
from deepagents_lab.experiments.steering.fixture import make_fixtures
from deepagents_lab.experiments.steering.report import metric_bars, save_report, table

ROOT = next(p for p in (Path.cwd(), *Path.cwd().parents) if (p / "pyproject.toml").exists())
RUN_DIR = ROOT / "results" / "steering-embeddings" / str(uuid4())
SEED = 42
fixtures = make_fixtures()
embedder = LexicalEmbedder(dimensions=512)
store = CaptureStore(RUN_DIR / "offline" / "captures", embedder)
print("Local results:", RUN_DIR)
print("Conversations:", len(fixtures), "| Backend:", embedder.identity)

# %% [markdown]
# ## 1. Inspect a steering event and the capture tool
#
# The host binds the original conversation, group ID, and relevance label to
# the tool. The model supplies only `problem` and `correction`. Labels and
# authored fixture answers are excluded from the LIVE model's prompt.
#
# Preserve the distinction between missing work and missing reporting, and
# between a violated requirement and newly added scope. The corpus includes
# each of those cases. Keep raw transcripts so captures can be reviewed later.

# %%
example = fixtures[0]
display(HTML(table([message.model_dump() for message in example.event.messages])))
capture_tool = store.tool_for(example.event, origin="authored_fixture", capture_model="human-authored-demo")
print(json.dumps(capture_tool.args, indent=2))
with tracing_context(enabled=False):
    accepted = capture_tool.invoke(example.pair.model_dump())
display(HTML(table([accepted], ["problem", "correction", "embedding_id"])))
print("Stored dimensions:", len(store.read(example.event.event_id).x))

# %% [markdown]
# ## 2. Capture the illustrative corpus
#
# This calls the actual tool/backend with authored arguments. No model generated
# these descriptions. The offline vectors count hashed words and word pairs;
# they intentionally require no downloaded models, credentials, or provider calls.
#
# Six wording/context groups contain six steering families. Related examples
# stay in one split. Families recur across splits because we are testing reuse
# of known correction types. The correction wording is deliberately repetitive:
# high scores on this fixture are expected and cannot establish generalization.

# %%
with tracing_context(enabled=False):
    records = [store.accept(f.event, f.pair, origin="authored_fixture", capture_model="human-authored-demo")
               for f in fixtures]
display(HTML(table([
    {"family": record.event.family, "problem_X": record.pair.problem, "correction_Y": record.pair.correction}
    for record in records[:6]
])))

# %% [markdown]
# ## 3. Compare three ways to retrieve a correction
#
# - **direct_correction:** compare X directly with stored Y vectors.
# - **problem_neighbors:** find similar historical X vectors and return their paired corrections.
# - **ridge_prediction:** fit a regularized linear mapping from X to Y, then
#   search the correction vectors using the predicted Y.
#
# Ridge is a small, inspectable starting model. It uses a dual solve appropriate
# to a small corpus. Regularization is chosen using validation retrieval MRR;
# the test split never selects hyperparameters. The correction library contains
# training examples only. No held-out Y vector is a retrieval candidate.
#
# A match means the retrieved correction has the same researcher-assigned
# **family**. This is a coarse relevance proxy, not proof the instruction fits
# every detail or that an agent successfully repaired the work.

# %%
report, index, splits = evaluate(records, seed=SEED)
display(HTML(table([
    {"split": name, "rows": len(values), "groups": sorted({r.event.group_id for r in values})}
    for name, values in splits.items()
])))
display(HTML(table(report["tuning"], ["alpha", "hit_at_1", "reciprocal_rank"])))
print("Selected alpha:", report["chosen_alpha"], "| Predictor bytes:", report["predictor_bytes"])

# %%
display(HTML(metric_bars(report["summary"])))
display(HTML(table(report["summary"])))
print("Majority-family baseline hit@1:", report["majority_family_hit_at_1"])
save_report(RUN_DIR / "offline", report, records)

# %% [markdown]
# `hit_at_1` / `hit_at_3`: first / first three retrieved examples contain a matching
# family. `reciprocal_rank` (MRR): average reciprocal rank of the first matching
# example. `supported_family`: fraction of queries whose family exists in training.
# Unsupported families count as misses. `batch_predict_ms` covers local vector
# prediction/search only; it excludes capture, embedding, model revision, and IO.
# It is a single small warm-process measurement, not a service latency benchmark.

# %% [markdown]
# ## 4. Inspect the actual guidance, including wrong neighbors
#
# Change `QUERY_INDEX` to inspect another held-out problem. A useful prediction
# selects correction text; the numeric vector itself is not an agent instruction.
# Cosine scores and margins are not calibrated probabilities.

# %%
QUERY_INDEX = 0
query = splits["test"][QUERY_INDEX]
print("Captured problem:", query.pair.problem)
print("Held-out reference correction:", query.pair.correction)
neighbors = []
for arm in ("direct_correction", "problem_neighbors", "ridge_prediction"):
    neighbors.extend({"arm": arm, **row} for row in index.recommend([query.x], arm, limit=3))
display(HTML(table(neighbors, ["arm", "score", "family", "correction"])))

# %% [markdown]
# ## 5. Explore abstention on validation data
#
# The margin compares the top result with the best result from a different
# correction family. Repeated entries from one family do not create artificial
# ambiguity. Inspect coverage and family precision together. No accepted query
# gives undefined precision, not perfect precision. Choose thresholds before a
# future held-out evaluation; this table makes no calibrated-confidence claim.
#
# This corpus contains recognized steering events only. It cannot measure how
# often the system unnecessarily intervenes when no steering is needed.

# %%
display(HTML(table(margin_sweep(index, splits["validation"]))))

# %% [markdown]
# ## 6. Bring real steering conversations
#
# JSONL: one object per event with `event_id`, `group_id`, `family`, `messages`,
# and `synthetic: false`. End the messages at the user steering instruction.
# `family` is a human relevance label shared by substitutable corrections.
# `group_id` is the original task/conversation; put paraphrases and repeated
# steering from the same task together. Use at least five groups for evaluation.
# Neither field is shown to the capturing model or embedded.
#
# The exported synthetic JSONL below is a format example. Copy it to an ignored
# location and replace the conversations and labels with your own data. Set
# `LIVE_EVENTS_JSONL` in the next cell to import that file. Imported transcripts
# are sent to the configured provider only when LIVE capture is enabled.

# %%
example_path = RUN_DIR / "example-events.jsonl"
example_path.parent.mkdir(parents=True, exist_ok=True)
example_path.write_text("\n".join(f.event.model_dump_json() for f in fixtures) + "\n")
print("JSONL format example:", example_path)
assert len(load_events(example_path)) == len(fixtures)

# %% [markdown]
# ## 7. LIVE: model-authored capture + semantic embeddings
#
# Set `RUN_LIVE_CAPTURE = True` to run. The default synthetic corpus schedules
# **36 capture calls and up to 36 embedding requests**, with two inputs per
# embedding request. No automatic retries; individual failures are recorded.
# Capture and embedding usage are saved separately. This is a call bound, not
# a dollar budget. Rerunning this section creates a new run and costs again.
#
# Credentials are loaded only here after opt-in. Existing environment values
# take precedence. Tracing is disabled for these transcript experiments.
# A short smoke run can use `live_events[:2]`, but it cannot support evaluation.
# Model/embedding names are configurable; account access is not assumed.

# %% tags=["live"]
RUN_LIVE_CAPTURE = False
LIVE_EVENTS_JSONL = None  # Example: ROOT / "results" / "my-steering-events.jsonl"
MAIN_CHECKOUT = ROOT.parent.parent if ROOT.parent.name == ".worktrees" else ROOT
ENV_FILE = MAIN_CHECKOUT / ".env"
CAPTURE_MODEL = None  # None uses DEEPAGENTS_LAB_MODEL after loading .env, then the lab default.
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 256
live_records, live_failures, live_report, live_index, live_splits = [], [], None, None, None

if RUN_LIVE_CAPTURE:
    from dotenv import load_dotenv
    from langchain_openai import ChatOpenAI
    from openai import OpenAI
    from deepagents_lab.experiments.steering.embeddings import OpenAIEmbedder
    from deepagents_lab.experiments.steering.live import capture_batch

    load_dotenv(ENV_FILE, override=False)
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY in the environment or ENV_FILE before LIVE.")
    capture_model_name = CAPTURE_MODEL or os.environ.get("DEEPAGENTS_LAB_MODEL", DEFAULT_MODEL)
    live_events = load_events(Path(LIVE_EVENTS_JSONL)) if LIVE_EVENTS_JSONL else [f.event for f in fixtures]
    LIVE_DIR = RUN_DIR / "live" / str(uuid4())
    live_embedder = OpenAIEmbedder(OpenAI(timeout=60, max_retries=0), LIVE_DIR / "embedding-cache",
                                  model=EMBEDDING_MODEL, dimensions=EMBEDDING_DIMENSIONS)
    live_store = CaptureStore(LIVE_DIR / "captures", live_embedder)
    capture_model = ChatOpenAI(model=capture_model_name.removeprefix("openai:"), timeout=60, max_retries=0)
    live_records, live_failures = capture_batch(live_events, live_store, capture_model, capture_model_name)
    print("Captured:", len(live_records), "| Failures:", live_failures, "| Results:", LIVE_DIR)
    display(HTML(table([{**r.pair.model_dump(), "family": r.event.family} for r in live_records])))
else:
    print("LIVE capture skipped. No provider calls or credential loading.")

# %% [markdown]
# ## 8. Evaluate live captures after inspection
#
# Read the extracted pairs above: do they faithfully describe the actual steering
# and preserve applicability? Family labels alone do not validate extraction.
# Any failed capture prevents aggregate scoring here, avoiding survivor bias.
# A synthetic LIVE run measures this synthetic corpus only. Real-world benefit
# requires independently labeled conversations and actual correction outcomes.

# %%
if RUN_LIVE_CAPTURE:
    if live_failures:
        print("Evaluation withheld: inspect failed attempts and rerun a complete campaign.")
    elif len({r.event.group_id for r in live_records}) < 5:
        print("Capture smoke complete; use at least five groups for held-out evaluation.")
    else:
        live_report, live_index, live_splits = evaluate(live_records, seed=SEED)
        display(HTML(table(live_report["summary"])))
        display(HTML(metric_bars(live_report["summary"])))
        display(HTML(table(margin_sweep(live_index, live_splits["validation"]))))
        save_report(LIVE_DIR, live_report, live_records)

# %% [markdown]
# ## 9. LIVE: give retrieved guidance to a revising model
#
# A separate opt-in runs four text-only revisions of one held-out conversation:
# no advice, a generic checklist, problem-neighbor guidance, and predicted-Y
# guidance. Each receives the same earlier transcript, ending before the user's
# actual steering. The query X is still a retrospective captured problem: this
# demonstrates **using** a recommendation, not independently detecting a problem.
#
# These revisions have no tools. They may improve a handoff or acknowledge missing
# work; they cannot run an experiment or fabricate results. Inspect whether each
# response addresses the problem, preserves facts, and introduces unnecessary
# changes. No model-judged or keyword-based repair score is claimed.

# %% tags=["live"]
RUN_LIVE_REVISIONS = False
if RUN_LIVE_REVISIONS:
    if live_index is None:
        raise RuntimeError("Complete LIVE capture and evaluation first.")
    from deepagents_lab.experiments.steering.live import compare_revisions

    live_query = live_splits["test"][QUERY_INDEX]
    revision_rows = compare_revisions(live_query.event, live_index, [live_query.x], capture_model,
                                      LIVE_DIR / "revisions" / str(uuid4()))
    display(HTML(table(revision_rows, ["arm", "advice", "ok", "text", "elapsed_ms"])))
else:
    print("LIVE revisions skipped.")

# %% [markdown]
# ## Interpretation and research context
#
# This prototype isolates the user's proposal: model-authored descriptions at
# capture time become X, and the requested correction becomes Y. A learned map
# must earn its place against straightforward retrieval. Real gains require
# useful corrections with fewer repeat interventions and acceptable total cost.
#
# - [MemPrompt](https://aclanthology.org/2022.emnlp-main.183/): storing and retrieving corrective feedback.
# - [Predicting teacher critiques](https://arxiv.org/abs/2602.16066): learning a feedback model for self-correction.
# - [CTRL](https://arxiv.org/abs/2502.03492): optimizing critiques for successful revisions.
# - [Context/feedback embeddings](https://arxiv.org/abs/2406.07291): contrastive ranking in a different dialogue domain.
# - [OpenAI embedding API](https://developers.openai.com/api/docs/guides/embeddings): optional semantic vectors.
#
# All transcripts, vectors, trial predictions, split IDs, tuning scores, source
# checksums and observed provider usage remain in ignored `results/`. Committed
# notebook/source pairs contain no execution outputs or credentials.
