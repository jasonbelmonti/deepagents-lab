---
type: TaskDefinition
title: Test the incremental value of PTC on graph investigations
task_id: graph-ptc-value-experiment
artifact_version: "3.0"
revision: "3"
created_at: "2026-09-12T12:00:00-05:00"
updated_at: "2026-09-12T21:10:09Z"
validation_profile: skills/task-definition/profiles/task-definition.yaml
---

## Task Control

| Contract state | Execution route | State rationale |
| --- | --- | --- |
| SUPERSEDED | BLOCKED | The user approved a three-PR decomposition on 2026-09-12. Successors: graph-ptc-workload.md, graph-ptc-benchmark.md and graph-ptc-notebook.md in this directory. Only PR 1 execution begins now; this historical combined contract grants no further execution authority. |

## Objective

This document preserves the original combined experiment contract and its
historical evidence. The replacement stack below is now the delivery boundary;
review each PR against its own successor contract, not every historical criterion.

Deliver a separate runnable notebook that can test, rather than assume, whether
PTC reduces real-model turns, tokens and latency on correct social-graph
investigations compared with ordinary tools and ordinary tools plus computation.
Keep graph-workspace as exploratory materialization/persistence research.

## Context / Constraints

This is a bounded synthetic experiment representing warm introductions, not a
production graph platform. All arms share seeded read-only graph data, batch
APIs, backend filters and work/concurrency limits. No canned answer tool or
handwritten solution is supplied to the live agent. Default Run All is keyless;
paid measurements require an explicit notebook switch or separately authorized
runner invocation. The user authorized one fresh 24-invocation development pilot
after correcting model-visible API documentation parity. Use the configured
model and existing credentials without displaying secrets. Preserve the first,
confounded pilot separately; no favorable result is required. Existing
dependencies, default agent, server and UI stay unchanged.

## Source Authority

| Source | Authority | Status | Task implication |
| --- | --- | --- | --- |
| User-approved three-PR decomposition and instruction to begin PR 1, 2026-09-12 | Primary, latest | Confirmed | Replace the single delivery boundary with the three successor contracts; begin only the workload PR. |
| User clarification after the pilot | Primary | Confirmed | No-interpreter versus interpreter with PTC is primary; compute-only is secondary. Preserve raw measurements and qualify any later reframing. |
| User request in this task, 2026-09-12 | Primary | Confirmed | Create a new hypothesis-testing graph notebook; retain the previous one as exploration. |
| User confirmation after the first pilot, 2026-09-12 | Primary, latest scope | Confirmed | Correct tool-documentation parity, add regression coverage, and run a fresh 24-invocation pilot; retain the first as inconclusive evidence. |
| First pilot assessment at results/graph-ptc-value/pilot-20260912/11a22e78-6709-460b-9022-e9d57abaf160/pilot-assessment.md and installed QuickJS renderer | Diagnostic evidence | Inspected | PTC received only the first description line, missing return fields and contact absence semantics; test actual model-visible documentation. |
| Preceding agreed comparison | Supporting user-approved direction | Confirmed | Ordinary, compute-only and PTC arms; correctness, actual usage, latency and negative control. |
| Repository origin/main at 03b738c | Implementation baseline | Inspected | Reuse notebook conventions and ModelMeasurements without changing prior experiments. |
| DeepAgents interpreter documentation, consulted 2026-09-12 | Capability reference | Inspected | PTC bridges tools into code; compute-only code has no such bridge. Pinned installed behavior takes precedence. |

## Task Scope

| Scope item | Classification | Approval impact | Notes |
| --- | --- | --- | --- |
| Notebook, focused helpers, graph fixtures/oracle, three arms and report | In scope | blocking | Real-model-ready experiment with offline verification. |
| Controls for depth, neighborhood size and simple lookup | In scope | blocking | Factor labels distinguish graph-work effects from model orchestration. |
| Documentation and substantive tests | In scope | blocking | Clear limits and no premature benefit claim. |
| Fresh parity-corrected 24-invocation development pilot | In scope | blocking | Preserve all attempts and separate provenance; stop on existing safety/request-failure gates or a systemic fairness defect. Report failures or an incomplete campaign honestly. |
| Held-out campaign and statistical confirmation | Follow-up | non-blocking | Do not treat reused development seeds as confirmatory evidence. |
| Production graph engines, private social data, writes, UI and services | Out of scope | non-blocking | No architecture or dependency expansion. |

## Materially Verifiable Success Criteria

| ID | Criterion | Proof | Required before done |
| --- | --- | --- | --- |
| TD-SC-1 | Three configurations expose equivalent graph APIs/data/limits and complete model-visible input/output descriptions; compute-only eval cannot invoke tools and PTC can. | Actual DeepAgents/QuickJS tests, captured first model messages/tool declarations and source inspection. | Yes |
| TD-SC-2 | Seeded warm-introduction investigations have independently checked exact results, directed/date filtering, contact exclusions, connector ranking and path evidence; lookup and separate depth/width controls are available. | Known-answer, randomized cross-check and mutation tests. | Yes |
| TD-SC-3 | Live runner rotates matched arms, preserves every completed attempt and known failed-call usage, records provenance/prompts/settings and enforces bounded work and time. | Persistence, accounting, scheduling, failure and real-runtime tests. | Yes |
| TD-SC-4 | Reports separate correctness from usage completeness, show matched efficiency plus all-attempt costs, and cannot label scripted or absent runs as live PTC evidence. | Deterministic report arithmetic and missing/failed/scripted-data tests. | Yes |
| TD-SC-5 | New synchronized/output-free notebook executes offline without keys, explains opt-in paid calls and interpretation, and clearly distinguishes prior exploratory work. | Key-cleared nbconvert execution and pairing/documentation inspection. | Yes |
| TD-SC-6 | Existing suite remains passing with notebook dependencies installed; no secrets/generated outputs or unrelated agent/server/UI/dependency changes enter the diff. | Full frozen pytest suite, compatibility and diff/ignore checks. | Yes |
| TD-SC-7 | A fresh pilot attempts the fixed 24-run configuration or records a justified early stop, retains all accounting/provenance separately from the first pilot, and reports correctness, token use and latency without a predetermined benefit claim. | Raw live report and assessment, including development-sample and incomplete-usage caveats where applicable. | Yes |

## Incremental Value Delivery

| Slice | Value proven | Risk retired | Evidence | Stop / continue decision |
| --- | --- | --- | --- | --- |
| Comparable graph workload | Exact task and equivalent capabilities | Confounded or trivial PTC comparison | TD-SC-1 and TD-SC-2 tests | Continue when oracle and runtime boundaries pass. |
| Evidence-producing notebook | Repeatable opt-in live comparison with honest offline validation | Missing costs, cherry-picked successes, premature claims | TD-SC-3 through TD-SC-6 | Continue to the authorized pilot when parity and offline verification pass. |
| Parity-corrected pilot | Observed development evidence for or against PTC value | Confounded documentation and untested model behavior | TD-SC-7 raw report and assessment | Stop at one campaign and report the result; further tuning or held-out execution needs separate direction. |

## Review Boundary

| Boundary | In scope for review | Out of scope / follow-up | Approval impact |
| --- | --- | --- | --- |
| Scientific validity | Comparable capabilities, correct answers, measurable hypothesis and failure-aware accounting | Proving universal speedup or production p95 | blocking for misleading current conclusions |
| Implementation | Scoped runtime, tests, opt-in behavior and durable reports | Broader benchmark framework and existing experiment refactors | blocking for regressions or unsafe behavior |
| Evidence | Offline real-runtime and report tests plus the authorized pilot with full accounting | Favorable PTC result, statistical confirmation or another campaign | blocking for missing authorized execution, unsupported claims or non-runnable experiment |

## Validation / Evidence

| Criterion ID | Check | Evidence | Runner / owner | Required before done |
| --- | --- | --- | --- | --- |
| TD-SC-1 | Exercise all arms, denied bridge and actual model-visible API descriptions | Pytest real DeepAgents/QuickJS results and parity regression that fails before correction | Implementer | Yes |
| TD-SC-2 | Known graph, changed graph, seeds and controls | Oracle/tool tests and notebook inspection | Implementer | Yes |
| TD-SC-3 | Interrupted/failed runs, usage, order and provenance | Runner tests and saved offline smoke report | Implementer | Yes |
| TD-SC-4 | Recompute comparisons on crafted trials | Report tests, including PTC losses and unknown totals | Implementer | Yes |
| TD-SC-5 | Execute default notebook with provider keys absent | nbconvert exit 0, no error cells, synchronized source | Implementer | Yes |
| TD-SC-6 | Run all tests and inspect complete diff | Frozen pytest output, uv pip check, git diff --check | Implementer | Yes |
| TD-SC-7 | Run the authorized campaign and inspect every attempt | Fresh report.json and pilot assessment; prior raw report unchanged | Implementer | Yes |

## Execution Notes

TD1 Standard; DIRECT is appropriate after readiness gates because this is an
isolated notebook experiment using established runtime and measurement patterns.
Research hypothesis: PTC may reduce model turns and intermediate context at
equivalent correctness, particularly for dependent multi-stage investigations.
No direction or minimum magnitude of observed improvement is required.

Revision 2 records the documentation-parity defect found in the first pilot and
the user's authorization to correct it and rerun. Keep model, seeds, workloads,
scheduling and limits fixed for this comparison; do not change them mid-campaign.

### Replacement stack

| Position | Contract to read first | PR base | Review question | Current authorization |
| --- | --- | --- | --- | --- |
| 1 | [Graph workload](graph-ptc-workload.md) | main | Are the graph workload, answers and read-evidence checks correct? | Execute now in codex/graph-ptc-workload. |
| 2 | [Agent benchmark](graph-ptc-benchmark.md) | PR 1 branch while stacked | Are agent capabilities, measurement and failure accounting fair? | Recorded for later execution; primary framing must be corrected. |
| 3 | [Notebook and findings](graph-ptc-notebook.md) | PR 2 branch while stacked | Is the workflow understandable and are conclusions supported? | Recorded for later execution; no new paid runs. |

Tests remain with their implementing slice. The source notebook pair stays
together in PR 3. Keep the full prototype in .worktrees/graph-ptc-value until
the entire stack is safely delivered; do not drop its uncommitted files or
ignored results. PRs 2 and 3 should use predecessor code plus only their own
incremental changes. Resolve merge strategy and the resulting main commit
before retargeting a dependent PR; do not blindly rewrite branch history.

### Historical evidence

Revision 2's complete prototype passed 117 tests and key-cleared notebook
execution, with all 14 measured source hashes verified. Its corrected pilot
completed 24 invocations, 19 correct, with 404,846 tokens across 86 requests.
These observations do not prove any isolated stack checkpoint or general speedup.
Details remain under .worktrees/graph-ptc-value/results/graph-ptc-value/:
parity-verification.md and
pilot-parity-corrected-20260912/4a0a6d15-8e7d-43a6-a072-506848caa846/pilot-assessment.md.
The first pilot remains separate and inconclusive. Raw report SHA-256 values:
first c102c9bd0b8202afd98bad196d06e419374acdf3d157eaa296f00fc1ebc81e0b;
corrected c1c0705ceb4d9f0e2233411a95294c87b30821d85e1cd801fe21ca620ed97900.

## Follow-up / Non-blocking Work

Freeze model/prompts before a separately authorized held-out campaign on new seeds,
expand to representative authorized data and workloads, and quantify statistical
uncertainty before making product or production claims. Consider a specialized
database query as a separate engineering alternative, not a hidden advantage
given to one of the three compared agents.
