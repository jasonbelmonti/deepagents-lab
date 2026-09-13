---
type: TaskDefinition
title: Bootstrap the DuckDB warm-introduction notebook
task_id: duckdb-warm-introductions
artifact_version: "3.0"
revision: "1"
created_at: "2026-09-13T12:00:00-05:00"
updated_at: "2026-09-13T09:09:53-05:00"
validation_profile: skills/task-definition/profiles/task-definition.yaml
---

## Task Control

| Contract state | Execution route | State rationale |
| --- | --- | --- |
| READY | DIRECT | Resolved source authority, engine 3.5.0 structural validation, semantic checks and post-draft review pass; this bounded notebook can proceed directly. |

## Objective

Fork the basic DuckDB notebook into a runnable, synthetic job-introduction experiment. Show how a Deep Agent can query relationship evidence at runtime, then compare ordinary SQL tools with interpreter-assisted SQL using the same data and task.

## Context / Constraints

Work starts at merged main `aaa836af800301beb52ecb6edafe13deb018ed03` in the `codex/duckdb-warm-introductions` worktree. Reuse the existing read-only DuckDB bridge and notebook conventions. Default execution must require no credentials or provider calls. Tracked notebook outputs must be empty. Use directed, recent relationship evidence, current employment and bounded paths; direct contacts are eligible. Ranking weights are explicit synthetic heuristics, not calibrated probabilities of an introduction succeeding. A live performance claim requires measured provider runs and must not be inferred from scripted execution.

## Source Authority

| Source | Authority | Status | Task implication |
| --- | --- | --- | --- |
| Current user request and preceding warm-path discussion | Primary | Resolved | Create a new notebook experiment for finding connectors into a job. |
| User operating manual | Required conventions | Read | Use an in-project worktree, focused modules and this task contract. |
| Merged main basic DuckDB notebook and DuckDBTools | Implementation baseline | Inspected | Preserve the original demo and reuse its runtime bridge. |
| Existing graph experiment and model accounting | Repository reference | Inspected | Reuse accounting where appropriate; do not inherit its exclusion of direct contacts. |
| Synthetic fixture and heuristic ranking | Implementation assumption | Explicit | Demonstrate mechanically checkable paths without claiming real-world social accuracy. |

## Task Scope

| Scope item | Classification | Approval impact | Notes |
| --- | --- | --- | --- |
| Paired notebook, small fixture/oracle/runtime helpers, focused checks and discoverability | In scope | Required | A complete offline demonstration plus opt-in live comparison. |
| Identical SQL capability and recoverable query errors in both arms | In scope | Required | Do not force the ordinary arm into extra queries or provide an answer endpoint. |
| Production data ingestion, identity resolution, deployment and message sending | Out of scope | None | Synthetic data only. |
| Large repeated benchmark campaign and ranking calibration | Follow-up | Non-blocking | Bootstrap records evidence needed for later measurement. |

## Materially Verifiable Success Criteria

| ID | Criterion | Proof | Required before done |
| --- | --- | --- | --- |
| TD-SC-1 | The synthetic fixture produces bounded, directed, cycle-free routes to current employees on the job's team, includes direct contacts, and returns at most one route per first connector with edge evidence. | An independent Python traversal and executed SQL agree; named expected routes and distractor cases are checked. | Yes |
| TD-SC-2 | Both Deep Agent arms execute the same read-only schema/query tools against DuckDB; SQL failures are visible and recoverable, and result budgets remain enforced. | Offline agent executions check actual tool/eval output, including an error followed by a successful query; bridge limit checks. | Yes |
| TD-SC-3 | Optional live runs allow the model to generate SQL/JavaScript, validate final routes against the oracle, and save per-attempt correctness, latency, model calls and usage without hiding failures or inventing missing token counts. | Scripted success/failure accounting checks and inspection of the opt-in live path; no live-performance claim. | Yes |
| TD-SC-4 | A discoverable, synchronized notebook runs end to end with live execution disabled and tracked outputs empty. | Executed offline notebook, notebook pairing checks and repository regression suite. | Yes |

## Incremental Value Delivery

| Slice | Value proven | Risk retired | Evidence | Stop / continue decision |
| --- | --- | --- | --- | --- |
| Evidence-backed fixture and oracle | Define a checkable warm-path question. | Attractive but invalid paths or duplicate connectors. | TD-SC-1 fixture and SQL checks. | Continue when expected paths and negative cases agree. |
| Runtime comparison and notebook | Demonstrate both tool routes and prepare provider measurement. | Fake answers, unfair SQL restrictions and misleading performance metrics. | TD-SC-2 through TD-SC-4 runtime and notebook evidence. | Stop at a validated offline bootstrap; leave live execution opt-in. |

## Review Boundary

| Boundary | In scope for review | Out of scope / follow-up | Approval impact |
| --- | --- | --- | --- |
| Path correctness | Direction, recency, employment, depth, cycles, evidence and connector diversity. | Whether synthetic relationship strength predicts actual introductions. | Incorrect fixture results block. |
| Comparison integrity | Equal SQL access, actual executed results, failure visibility and honest accounting. | Statistical significance, production scale and provider tuning. | False correctness or performance claims block. |
| Notebook usability | Clean synchronization, offline execution, live opt-in and discoverability. | Deployment and external data connectors. | Broken default execution blocks. |

## Validation / Evidence

| Criterion ID | Check | Evidence | Runner / owner | Required before done |
| --- | --- | --- | --- | --- |
| TD-SC-1 | Compare independent oracle, SQL output and explicit expected routes across fixture changes. | tests/test_duckdb_warm_introductions.py passed: explicit routes, all distractors, recency/depth, empty results and employment-date boundaries; 1000-neighbor SQL probe also agrees with the oracle. | Local pytest / Codex | Yes |
| TD-SC-2 | Execute both agent routes and error recovery; enforce SQL result limits. | Both real Deep Agent transports passed with and without a SQL error; actual ToolMessages match the oracle. Read-only, external-read, row/byte and attempt-limit checks passed. | Local pytest and notebook / Codex | Yes |
| TD-SC-3 | Check final validation and per-attempt accounting, including failed and unmetered calls. | Failure accounting retains successful queries and partial reported usage; missing totals remain null. WI-LATENCY-001 is corrected: natural cleanup tracing and a controlled 100ms cleanup regression verify that latency excludes automatic cleanup while retaining raw wall time. Current suite: 189 passed; provider execution remains unrun. | Local pytest / Codex | Yes |
| TD-SC-4 | Execute the notebook offline, compare paired sources, run regressions. | 189 repository tests passed; see results/convergent-review/warm-introductions-round-2/pytest.txt. All 10 code cells executed offline in that directory/executed.ipynb; LIVE skipped. Source pair is synchronized and output-free. | Jupyter and pytest / Codex | Yes |

## Execution Notes

TD1 scope. Implementation can proceed directly after readiness checks. No new dependencies are anticipated. Reference SQL and expected answers belong only to offline verification; live agents receive the task rules and schema access. Save attempt logs under ignored `results/`. Provider execution is optional and will remain unrun during bootstrap validation.

### Execution Checkpoint

| Execution status | Current proving slice | Evidence admitted | Next action | Blockers / stop condition |
| --- | --- | --- | --- | --- |
| review-ready | Prove the TD-SC-3 timing correction in remediation review. | TD-SC-1: route tests pass; TD-SC-2: both real transports and error recovery pass; TD-SC-3: cleanup tracing and timing regression pass; TD-SC-4: 189 tests and all notebook cells pass. Current file hashes and evidence are under results/convergent-review/warm-introductions-round-2/. | Dispatch three reviewers against the unchanged frozen contract and timing delta. | None. |

## Follow-up / Non-blocking Work

Run matched live trials across graph sizes and task variants; calibrate ranking against consented introduction outcomes; assess production identity and authorization requirements when a real data integration is proposed.
