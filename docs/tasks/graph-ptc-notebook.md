---
type: TaskDefinition
title: Deliver the graph interpreter notebook and pilot findings
task_id: graph-ptc-notebook
artifact_version: "3.0"
revision: "2"
created_at: "2026-09-12T21:10:09Z"
updated_at: "2026-09-13T11:51:37Z"
validation_profile: skills/task-definition/profiles/task-definition.yaml
---

## Task Control

| Contract state | Execution route | State rationale |
| --- | --- | --- |
| READY | DIRECT | Current authority and merged baseline are verified; Markdown Engine 3.5.0, semantic and post-draft gates pass. The bounded notebook and evidence slice can proceed directly. |

## Objective

Make the no-interpreter versus interpreter-with-PTC graph comparison easy to
run and scrutinize through an offline-first notebook and a curated account of
the existing pilot. Keep the compute-only arm as a clearly secondary control.

## Context / Constraints

PR 3 depends on graph-ptc-benchmark.md, merged in PR #11, and targets main.
Retain synchronized, output-free notebook sources and keyless default execution.
The full prototype and local pilot artifacts remain in .worktrees/graph-ptc-value.
The first campaign is confounded and separate; the corrected campaign contains
24 invocations and complete usage. Do not rerun either or rewrite their raw JSON.
The user now authorizes the final PR. Reuse the merged harness unchanged; the
historical pilot predates subsequent validation and lifecycle fixes, so its
recorded correctness and timings must not be presented as current-head measurements.

## Source Authority

| Source | Authority | Status | Task implication |
| --- | --- | --- | --- |
| User request to move onto the last PR, 2026-09-13 | Primary, latest | Confirmed | Execute and open only this final notebook/findings slice; no new paid runs. |
| User-approved stack and interpreter/no-interpreter comparison | Primary | Confirmed | Deliver the notebook and findings after the benchmark, with the correct emphasis. |
| PR #11 merge commit 7d4bd90457d0a51fda773cd6e72c15d859d47e40 | Implementation baseline | GitHub merge verified and fetched | Preserve the reviewed harness and its scoped cleanup fix. |
| graph-ptc-benchmark.md | Predecessor contract | Inspected | Consume the verified runner and retain all three arms. |
| Existing notebook and pilot evidence in .worktrees/graph-ptc-value/results/graph-ptc-value | Evidence source | Both raw digests and all 23 preserved prototype/pilot hashes verified | Curate only whitelisted metrics; retain historical scorer identity and avoid held-out claims. |

## Task Scope

| Scope item | Classification | Approval impact | Notes |
| --- | --- | --- | --- |
| Notebook pair, discovery/readme guidance and pairing tests | In scope | blocking | Default Run All stays offline; LIVE remains explicit and paid. |
| Curated pilot findings and auditable non-secret supporting metrics | In scope | blocking | Distinguish observations from hypotheses; keep raw local artifacts unchanged. |
| New campaign, runtime redesign, graph scale/persistence claims and UI | Out of scope | non-blocking | No additional execution or architecture expansion. |

## Materially Verifiable Success Criteria

| ID | Criterion | Proof | Required before done |
| --- | --- | --- | --- |
| TD-SC-1 | Notebook and paired source execute keylessly with no errors, stay synchronized/output-free, distinguish scripts from live evidence and document explicit paid opt-in. | Key-cleared nbconvert, pairing checks and full tests. | Yes |
| TD-SC-2 | Notebook and READMEs make no-interpreter versus PTC primary, explain the secondary compute arm, and distinguish this experiment from graph materialization research. | Documentation and workflow inspection. | Yes |
| TD-SC-3 | Curated findings cover every workload, failed attempts, paired-sample counts, usage and latency; supporting metrics reproduce reported numbers and preserve the first pilot's inconclusive status. | Source/hash checks and arithmetic verification against saved reports. | Yes |

## Incremental Value Delivery

| Slice | Value proven | Risk retired | Evidence | Stop / continue decision |
| --- | --- | --- | --- | --- |
| Reviewable investigation notebook | Colleagues can run the instrument and inspect its limited evidence | Opaque setup, wrong baseline or overstated findings | TD-SC-1 through TD-SC-3 | Stop after verified PR 3; no new paid campaign. |

## Review Boundary

| Boundary | In scope for review | Out of scope / follow-up | Approval impact |
| --- | --- | --- | --- |
| Usability and evidence integrity | Reproducible offline workflow, explicit spend boundary and traceable qualified conclusions | Proving universal speedup, production scale or statistical significance | blocking for misleading claims, secret leakage or a broken notebook |

## Validation / Evidence

| Criterion ID | Check | Evidence | Runner / owner | Required before done |
| --- | --- | --- | --- | --- |
| TD-SC-1 | Execute notebook with keys absent | Successful nbconvert and synchronized/output-free tracked pair | Implementer | Yes |
| TD-SC-2 | Inspect all primary/secondary comparison labels | Consistent README, notebook and report framing | Implementer | Yes |
| TD-SC-3 | Verify hashes and recompute every published metric | Auditable supporting data; no omitted failures or rewritten raw runs | Implementer | Yes |

## Execution Notes

TD1 Standard. DIRECT after readiness gates and selection of the PR 2 baseline.
Read this file first before implementation or review. The corrected raw report is
pilot-parity-corrected-20260912/4a0a6d15-8e7d-43a6-a072-506848caa846/report.json
under the local evidence directory; SHA-256 is
c1c0705ceb4d9f0e2233411a95294c87b30821d85e1cd801fe21ca620ed97900.
Historical source hashes describe the measured code, not later framing changes.
Only intentionally curated, non-secret evidence belongs in the PR; do not force-add
the ignored results tree. Worktree: .worktrees/graph-ptc-notebook; branch:
codex/graph-ptc-notebook. Revision 2 records the latest execution authority and
merged baseline; the success criteria and review boundary are unchanged.

### Execution Checkpoint

| Execution status | Current proving slice | Evidence admitted | Next action | Blockers / stop condition |
| --- | --- | --- | --- | --- |
| review-ready | Notebook workflow and historical evidence, TD-SC-1 through TD-SC-3. | TD-SC-1: key-cleared nbconvert completes all seven code cells without errors; guarded Run All and pairing checks pass. TD-SC-2: primary/secondary labels and distinct historical evidence inspected. TD-SC-3: raw projection and published arithmetic verified, all 24 attempts retained, 23 preserved hashes match. Full suite: 154 passed; focused: 17 passed. Evidence: results/graph-ptc-notebook/verification.json. | Open the final notebook/findings PR against main for independent review. | Not independently approved. Stop before paid calls, raw-evidence edits, runtime redesign or merge. |

## Follow-up / Non-blocking Work

Held-out seeds/query variants and production graph services require separate
work. The pilot cannot establish broad accuracy, latency or scaling claims.
