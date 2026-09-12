---
type: TaskDefinition
title: Define the graph investigation workload and correctness checks
task_id: graph-ptc-workload
artifact_version: "3.0"
revision: "1"
created_at: "2026-09-12T21:10:09Z"
updated_at: "2026-09-12T21:52:07Z"
validation_profile: skills/task-definition/profiles/task-definition.yaml
---

## Task Control

| Contract state | Execution route | State rationale |
| --- | --- | --- |
| READY | DIRECT | Source authority, Markdown Engine 3.5.0 validation, semantic gate and post-draft review pass; the isolated first PR may proceed. |

## Objective

Ship the independently testable graph workload that defines a correct
warm-introduction investigation before adding agent execution or a notebook.
This is PR 1 of the graph interpreter experiment stack.

## Context / Constraints

Reuse the existing prototype without changing its measured workload. These are
small synthetic, read-only graphs, not a production graph service. Use a clean
worktree, retain the original experiment and both raw pilot reports, and keep
tests with the code they validate. No paid calls, new dependencies or UI/server
changes. The eventual primary comparison is no interpreter versus interpreter
with PTC; the compute-only arm is a secondary control, implemented in PR 2.

## Source Authority

| Source | Authority | Status | Task implication |
| --- | --- | --- | --- |
| User-approved three-PR decomposition and request to execute PR 1 | Primary | Confirmed | Record the stack, isolate and verify only its first implementation slice. |
| User clarification: compare agents with and without an interpreter | Primary | Confirmed | No-interpreter is the primary baseline; do not require performance proof in this PR. |
| main at 03b738c and prototype in .worktrees/graph-ptc-value | Implementation source | Inspected | Preserve workload semantics and existing imports while extracting the first slice. |

## Task Scope

| Scope item | Classification | Approval impact | Notes |
| --- | --- | --- | --- |
| Scenario/config definitions, seeded fixtures, batch tools, oracle and sufficient-read checks | In scope | blocking | Package files: __init__, config, fixture, tools, oracle and coverage under src/deepagents_lab/experiments/graph_ptc_value. |
| Data/API tests and durable decomposition contracts | In scope | blocking | tests/test_graph_ptc_value_data.py stays with the implementation. |
| Agent runner, interpreter integration, measurements, reports, notebook and findings | Follow-up | non-blocking | Owned by PRs 2 and 3; absent code must not block this PR. |
| Provider calls, private graph data, service changes and library forks | Out of scope | non-blocking | No scope or dependency expansion. |

## Materially Verifiable Success Criteria

| ID | Criterion | Proof | Required before done |
| --- | --- | --- | --- |
| TD-SC-1 | Reproducible graphs and exact expected answers cover bounded directed/date-filtered paths, contact exclusions, distinct connectors, canonical paths, ranking and lookup/depth/width cases. | Known-answer, mutation and fixture tests plus source inspection. | Yes |
| TD-SC-2 | Batch reads expose complete input/output descriptions, enforce ID/call/concurrency limits, filter/project data and record failures; sufficient-read checks reject incomplete investigations and allow justified pruning. | Data/API tests and tool/coverage source inspection. | Yes |
| TD-SC-3 | The slice works from main without later stack files; its tests and the existing full suite pass with pinned notebook dependencies, and the diff contains no secrets, results, unrelated changes or dependency modifications. | Clean-worktree pytest, uv pip check, diff inspection and preservation hashes. | Yes |

## Incremental Value Delivery

| Slice | Value proven | Risk retired | Evidence | Stop / continue decision |
| --- | --- | --- | --- | --- |
| Independently verifiable graph workload | A precise investigation and answer boundary | Benchmarking an incorrect or answer-shaped workload | TD-SC-1 through TD-SC-3 | Stop at a verified PR against main; do not execute the remaining stack automatically. |

## Review Boundary

| Boundary | In scope for review | Out of scope / follow-up | Approval impact |
| --- | --- | --- | --- |
| Workload correctness and isolation | Declared graph semantics, bounded reads, oracle, evidence checks and independent tests | Model-visible middleware rendering, measured benefits, live execution and notebook usability | blocking only for defects or regressions inside this slice |

## Validation / Evidence

| Criterion ID | Check | Evidence | Runner / owner | Required before done |
| --- | --- | --- | --- | --- |
| TD-SC-1 | Run tests/test_graph_ptc_value_data.py | Passing known-answer and scenario tests | Implementer | Yes |
| TD-SC-2 | Exercise API failures, concurrency and read coverage | Passing data/API tests; complete source descriptions | Implementer | Yes |
| TD-SC-3 | Verify only this slice in its own worktree | Full frozen pytest, package compatibility, bounded diff and unchanged original evidence | Implementer | Yes |

## Execution Notes

TD1 Standard; DIRECT is appropriate once readiness gates pass because the
prototype already has a clean file-level boundary. No partial-file staging or
preparatory refactor is required. The branch is codex/graph-ptc-workload, based
on main. Read this file first when resuming or reviewing PR 1. The successor
contracts are graph-ptc-benchmark.md and graph-ptc-notebook.md in this directory.
The complete stack and historical evidence are recorded in
graph-ptc-value-experiment.md; its superseded criteria do not govern this PR.

### Execution Checkpoint

| Execution status | Current proving slice | Evidence admitted | Next action | Blockers / stop condition |
| --- | --- | --- | --- | --- |
| review-ready | Isolated TD-SC-1 through TD-SC-3 after review remediation | TD-SC-1/TD-SC-2: 17 focused tests pass, including regressions for BLK-1 through BLK-4 that failed before the fixes. TD-SC-3: 89 full tests pass; 217 packages compatible; all 23 original source/notebook/pilot hashes unchanged; eleven-file diff remains bounded. Evidence: results/convergent-review/pr10-graph-workload/round2/verification.md. | Independently review the remediation delta and required gates in Round 2 against the unchanged frozen contract. | Not independently approved. Stop after PR 1; no paid calls or automatic PR 2 execution. |

## Follow-up / Non-blocking Work

PR 2 adds the agent benchmark and actual middleware documentation-parity tests.
PR 3 delivers the notebook and bounded interpretation of the existing pilot.
Neither is required to approve this first workload PR.
