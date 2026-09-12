---
type: TaskDefinition
title: Deliver the graph interpreter notebook and pilot findings
task_id: graph-ptc-notebook
artifact_version: "3.0"
revision: "1"
created_at: "2026-09-12T21:10:09Z"
updated_at: "2026-09-12T21:10:09Z"
validation_profile: skills/task-definition/profiles/task-definition.yaml
---

## Task Control

| Contract state | Execution route | State rationale |
| --- | --- | --- |
| READY | DIRECT | Source, structural, semantic and post-draft gates pass; this bounded successor is ready for later execution against the PR 2 baseline, not started by the current request. |

## Objective

Make the no-interpreter versus interpreter-with-PTC graph comparison easy to
run and scrutinize through an offline-first notebook and a curated account of
the existing pilot. Keep the compute-only arm as a clearly secondary control.

## Context / Constraints

PR 3 depends on graph-ptc-benchmark.md and targets its branch while stacked.
Retain synchronized, output-free notebook sources and keyless default execution.
The full prototype and local pilot artifacts remain in .worktrees/graph-ptc-value.
The first campaign is confounded and separate; the corrected campaign contains
24 invocations and complete usage. Do not rerun either or rewrite their raw JSON.
The present request begins PR 1 only; this records the final delivery slice.

## Source Authority

| Source | Authority | Status | Task implication |
| --- | --- | --- | --- |
| User-approved stack and interpreter/no-interpreter comparison | Primary | Confirmed | Deliver the notebook and findings after the benchmark, with the correct emphasis. |
| graph-ptc-benchmark.md | Predecessor contract | Inspected | Consume the verified runner and retain all three arms. |
| Existing notebook and pilot evidence in .worktrees/graph-ptc-value/results/graph-ptc-value | Evidence source | Located and previously verified | Reload and verify hashes before curating any findings; do not imply held-out confirmation. |

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
the ignored results tree. Current authorization records this task but does not start it.

## Follow-up / Non-blocking Work

Held-out seeds/query variants and production graph services require separate
work. The pilot cannot establish broad accuracy, latency or scaling claims.
