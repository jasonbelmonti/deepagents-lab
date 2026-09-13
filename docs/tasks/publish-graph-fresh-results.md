---
type: TaskDefinition
title: Publish the fresh graph PTC campaign results
task_id: publish-graph-fresh-results
artifact_version: "3.0"
revision: "1"
created_at: "2026-09-13T13:04:40Z"
updated_at: "2026-09-13T13:04:40Z"
validation_profile: skills/task-definition/profiles/task-definition.yaml
---

## Task Control

| Contract state | Execution route | State rationale |
| --- | --- | --- |
| READY | DIRECT | Source authority, Markdown Engine 3.5.0 structural validation, semantic proof checks and post-draft review pass; publication is bounded to preserved evidence. |

## Objective

Make the completed 60-invocation graph campaign discoverable and independently
auditable in the private repository, without publishing raw traces or changing
the experiment.

## Context / Constraints

Measured main commit: cb919679e221b39541d928358830f9b39f8d5124.
Publish fresh-case evidence separately from the historical pilot. Retain every
failure, conditional-pair counts, strict correctness semantics, small-sample
limits and preflight-overlap caveat. No new paid calls, rescoring, runtime changes,
dependency changes, historical evidence edits or merge.

## Source Authority

| Source | Authority | Status | Task implication |
| --- | --- | --- | --- |
| User request to open a PR capturing these results | Primary | Confirmed | Commit sanitized evidence and open a private-repository PR. |
| Frozen configuration and completed report under results/confirmation-20260913 | Measurement source | Read; both SHA-256 digests verified | Preserve all 60 attempts and the measured code identity. |
| Existing pilot publication and audit pattern | Repository convention | Inspected | Add separate findings, metrics and read-only arithmetic checks. |

## Task Scope

| Scope item | Classification | Approval impact | Notes |
| --- | --- | --- | --- |
| Fresh findings, complete curated metrics, frozen configuration, reproducible tables and audit tests | In scope | blocking | Publish only an explicit whitelist; raw evidence remains ignored. |
| Discovery links from repository and notebook guides | In scope | blocking | Do not replace historical results or alter executable notebook behavior. |
| New runs, runtime repair, expanded statistical or production claims | Out of scope | non-blocking | Separate authority required. |

## Materially Verifiable Success Criteria

| ID | Criterion | Proof | Required before done |
| --- | --- | --- | --- |
| TD-SC-1 | Committed metrics retain all 60 unique attempts and their failures; token totals, correctness counts and all paired comparisons reproduce the preserved report. | Exact raw projection equality; independent expected counts and arithmetic tests; mutations to metrics or tables fail the audit. | Yes |
| TD-SC-2 | Discoverable findings distinguish the fresh campaign from the pilot, disclose limitations and contain no credentials, raw prompts/programs, answers, trace identifiers or machine-local paths. | Inspect the staged whitelist, changed-file scope and links; verify original raw/config and historical-file hashes remain unchanged. | Yes |

## Incremental Value Delivery

| Slice | Value proven | Risk retired | Evidence | Stop / continue decision |
| --- | --- | --- | --- | --- |
| Auditable campaign publication | Colleagues can reproduce the reported comparisons without paid calls | Lost local results, cherry-picking or overclaiming | TD-SC-1 and TD-SC-2 | Open PR after verification; stop before merge. |

## Review Boundary

| Boundary | In scope for review | Out of scope / follow-up | Approval impact |
| --- | --- | --- | --- |
| Evidence fidelity and safe publication | All attempts, reproducible arithmetic, qualified claims, discovery and redaction | Proving general efficacy or repairing the measured harness | Blocking for misleading or unreproducible results, leaked data or scope regression. |

## Validation / Evidence

| Criterion ID | Check | Evidence | Runner / owner | Required before done |
| --- | --- | --- | --- | --- |
| TD-SC-1 | Run the publication audit against the preserved raw report and focused tests with independent expected totals | Exact 60-row projection, 37 passing attempts, 232 model calls and 1,118,867 tokens; invalid pair exclusions and audit mutation failures | Implementer | Yes |
| TD-SC-2 | Inspect published files and discovery links; compare pre/post source fingerprints | No forbidden fields or local paths; no changed historical evidence, measured harness or dependency lock; raw/config digests unchanged | Implementer | Yes |

## Execution Notes

TD0 Compact. Reuse the existing campaign worktree and branch. Read this task and
the source artifacts before resuming. Raw SHA-256:
7b84342ae0f2bb99cb35c1314080e586fe2b1516ea40aafdc61240162b1c164e.
Frozen configuration SHA-256:
1c4c4046e138e6d26777d1f63aa026ea2113247ce472f975ceb0e993c6292bf0.
READY concerns execution authority, not independent PR approval.

## Follow-up / Non-blocking Work

Additional runs, independent review, runtime failure diagnosis and broader
real-world validation are separate work; no favorable result is required.
