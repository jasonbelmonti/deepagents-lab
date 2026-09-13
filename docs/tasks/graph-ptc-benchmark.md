---
type: TaskDefinition
title: Compare graph agents with and without an interpreter
task_id: graph-ptc-benchmark
artifact_version: "3.0"
revision: "3"
created_at: "2026-09-12T21:10:09Z"
updated_at: "2026-09-13T04:27:25Z"
validation_profile: skills/task-definition/profiles/task-definition.yaml
---

## Task Control

| Contract state | Execution route | State rationale |
| --- | --- | --- |
| READY | DIRECT | Current execution authority and merged baseline are verified; Markdown Engine 3.5.0, semantic and post-draft gates pass. The bounded second PR can proceed directly. |

## Objective

Deliver a failure-aware, reproducible agent comparison over PR 1's graph
workload. Primary: no interpreter versus interpreter with PTC. Secondary:
compute-only interpreter versus PTC, to investigate the tool bridge separately.

## Context / Constraints

PR 2 depends on graph-ptc-workload.md, merged in PR #10, and targets main.
Retain all three arms and the existing workload, model settings and limits.
Changing which comparison is emphasized must not relabel historical raw results
or imply new measurements. Use existing dependencies. No new paid campaign,
production service, notebook or graph mutation is authorized by this contract.
The user authorized this second delivery slice after confirming PR #10 merged.

## Source Authority

| Source | Authority | Status | Task implication |
| --- | --- | --- | --- |
| User request to begin the next PR after PR #10 merged | Primary, latest | Confirmed | Execute only PR 2, verify it offline and open its PR; do not begin PR 3 or a paid campaign. |
| User-approved stack and no-interpreter baseline clarification | Primary | Confirmed | Isolate the execution/measurement machinery and correct the primary framing. |
| graph-ptc-workload.md | Predecessor contract | Inspected | Reuse identical graph access and expected-answer semantics. |
| PR #10 merge commit e78210c98dda92cdde37750931e76e0edbbb20ee | Implementation baseline | Merge verified through GitHub and fetched Git objects | Branch from this main commit and retain all five reviewed workload fixes. |
| Existing prototype in .worktrees/graph-ptc-value | Implementation source | Inspected | Reuse runtime, accounting and tests; preserve prior evidence. |

## Task Scope

| Scope item | Classification | Approval impact | Notes |
| --- | --- | --- | --- |
| Agent construction, prompts, trial validation, measurements, runner, reports and offline scripts | In scope | blocking | Focused helpers and their runtime, documentation-parity and report tests. |
| Notebook, README walkthrough and published findings | Follow-up | non-blocking | PR 3 owns the user-facing workflow and interpretation. |
| Extra live runs, workload redesign and library forks | Out of scope | non-blocking | No added spend or changed experiment. |

## Materially Verifiable Success Criteria

| ID | Criterion | Proof | Required before done |
| --- | --- | --- | --- |
| TD-SC-1 | All arms share complete model-visible graph contracts and limits; ordinary has no interpreter, compute has no tool bridge, and PTC can execute graph reads through code. | Real DeepAgents/QuickJS tests and captured model-boundary documentation. | Yes |
| TD-SC-2 | Runner preserves all attempts and partial usage, bounds work/time, records reproducible provenance, rotates matched order and prevents scripted fallback to paid calls. | Runtime, cancellation, scheduling and persistence tests. | Yes |
| TD-SC-3 | Reports identify ordinary versus PTC as primary, retain the secondary control, separate scripted/live evidence, and show failures, all-attempt costs and correct-pair comparisons without benefit claims from missing data. | Arithmetic and framing tests plus a passing full offline suite. | Yes |

## Incremental Value Delivery

| Slice | Value proven | Risk retired | Evidence | Stop / continue decision |
| --- | --- | --- | --- | --- |
| Runnable comparison instrument | Trustworthy measurements can be produced on the fixed workload | Confounded capabilities, lost failures or fabricated savings | TD-SC-1 through TD-SC-3 | Stop at verified PR 2; no paid execution is required. |

## Review Boundary

| Boundary | In scope for review | Out of scope / follow-up | Approval impact |
| --- | --- | --- | --- |
| Fair execution and accounting | Equivalent information, real interpreter behavior, validation, bounded execution and honest reports | Notebook delivery, held-out confirmation and favorable results | blocking for scientific-validity, safety or regression defects in the harness |

## Validation / Evidence

| Criterion ID | Check | Evidence | Runner / owner | Required before done |
| --- | --- | --- | --- | --- |
| TD-SC-1 | Run runtime and model-visible documentation tests | Actual middleware/QuickJS results without provider calls | Implementer | Yes |
| TD-SC-2 | Run failure, usage and persistence cases | Saved offline artifacts and passing tests | Implementer | Yes |
| TD-SC-3 | Recompute crafted report cases and run full suite | Exact arithmetic, primary/secondary labels and frozen pytest output | Implementer | Yes |

## Execution Notes

TD1 Standard. DIRECT after readiness gates. The selected predecessor is main at
e78210c98dda92cdde37750931e76e0edbbb20ee. Read this file first before implementing or reviewing PR 2. Reuse the
prototype's remaining harness files; do not cherry-pick the entire experiment.
Worktree: .worktrees/graph-ptc-benchmark; branch: codex/graph-ptc-benchmark.
Revision 3 records authorized BLK-1 remediation after convergent-review Round 1;
the success criteria and review boundary are unchanged.

### Execution Checkpoint

| Execution status | Current proving slice | Evidence admitted | Next action | Blockers / stop condition |
| --- | --- | --- | --- | --- |
| review-ready | TD-SC-1 through TD-SC-3, with BLK-1 interpreter cleanup remediated. | TD-SC-1: real capability and model-visible contract tests pass. TD-SC-2: nine subprocess exit regressions pass, and the original provider-error, campaign-error and timeout reproductions exit normally with accounting retained; all 24 scripted attempts are correct. TD-SC-3: 50 focused and all 143 offline tests pass; no live benefit claims. All 23 preserved hashes match. Evidence: results/convergent-review/pr11-graph-benchmark/round2/pre-commit-validation.json. | Publish the remediation commit to PR 11 and perform independent convergent-review Round 2 against the unchanged contract. | Closure of BLK-1 requires independent review. Stop before merge, paid calls, dependency forks or PR 3 implementation. |

## Follow-up / Non-blocking Work

graph-ptc-notebook.md owns PR 3. Held-out trials, additional models and mandatory
compute baselines require separate direction and are not approval conditions.
