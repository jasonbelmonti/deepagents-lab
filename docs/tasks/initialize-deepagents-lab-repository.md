---
type: TaskDefinition
title: Initialize the DeepAgents Lab Repository
task_id: initialize-deepagents-lab-repository
artifact_version: "3.0"
revision: "1"
created_at: "2026-08-23T08:24:27-05:00"
updated_at: "2026-08-23T08:27:31-05:00"
validation_profile: skills/task-definition/profiles/task-definition.yaml
---

# Task Control

| Contract state | Execution route | State rationale |
| --- | --- | --- |
| READY | DIRECT | Source authority is resolved, deterministic validation passed, the post-draft review found no open blocker or major issue, and the bounded initialization can execute without another planning artifact. |

# Objective

Convert the current design-only directory into a clean, reproducible, local-first Python 3.12 Git repository that is ready for the comparative R0 work defined by the approved design packet. The completed repository shall preserve the design authority, lock the approved R0 dependencies, prove imports and a minimal package test, protect credentials and generated evaluation evidence from accidental commits, and establish the first commit required for all subsequent work to use `.worktrees/`.

This task delivers repository readiness only. It does not implement DeepAgents experiments, shared lab contracts, Inspect or LangSmith adapters, model calls, trace evaluation, sandbox execution, or a statistical baseline.

# Context / Constraints

- The workspace currently contains only the approved design packet and its checksum and validation sidecars. It is not a Git repository.
- The design packet is ready for a comparative R0 experiment, not for a final evaluation-platform selection or a broad lab scaffold.
- Python 3.12 and `uv` are the approved environment assumptions. `uv 0.10.0` is available locally; a standalone `python3.12` executable is not, so implementation shall use `uv`-managed Python rather than assuming a system interpreter.
- The evaluated releases are fixed at `deepagents==0.7.8`, `inspect-ai==0.3.260`, and control-only `langsmith==0.11.1`. A newer release is outside this task.
- Local repository artifacts remain authoritative. Managed-service state, credentials, provider access, and networked model execution are unnecessary for this task.
- Secrets, raw traces, evaluator logs, generated results, caches, virtual environments, and disposable worktrees must not enter the baseline commit.
- The workspace operating manual requires implementation work in `.worktrees/`. Because no initial commit exists, this task may initialize and prove the base repository in place; follow-on implementation must use an isolated worktree.
- The first commit must not imply that Inspect or LangSmith has won the Section 8 trade study. The comparative R0 and its eight-point indifference rule remain controlling.

# Source Authority

| Source | Authority | Status | Task implication |
| --- | --- | --- | --- |
| User instruction dated 2026-08-23 | Controlling request | Active | Begin with a task contract for repository initialization. |
| `/Users/jasonbelmonti/Documents/Development/deepagents-lab/docs/design/deepagents-lab-design-process.md` | Approved engineering design process packet | Verified against SHA-256 `78df8a1aa03906874465d729b86bce7380be6263a23692babd37a2c254ea79d4` | Preserve the Python/`uv` assumptions, exact evaluated releases, local-authority constraints, comparative R0 boundary, and repository-workflow finding `DP-6`. |
| `/Users/jasonbelmonti/Documents/Development/deepagents-lab/docs/design/deepagents-lab-design-process.validation.json` | Deterministic packet validation evidence | Valid: engine 3.5.0, 42 of 42 rules, zero diagnostics | Treat the packet as structurally valid source authority. |
| Workspace inspection dated 2026-08-23 | Current implementation baseline | Confirmed | The directory has no `.git`; only the three design artifacts existed before this task artifact was drafted. |
| Workspace operating manual supplied with this task | Repository workflow authority | Active | Establish a `main` baseline commit, ignore `.worktrees/`, then prove that local worktree creation is available for follow-on tasks. |

# Task Scope

| Scope item | Classification | Approval impact | Notes |
| --- | --- | --- | --- |
| Initialize local Git history on branch `main` | In scope | blocking | Create one baseline commit containing the preserved design authority, this task artifact, and the minimal repository scaffold. |
| Add Python 3.12 and `uv` project metadata | In scope | blocking | Declare distribution `deepagents-lab`, import package `deepagents_lab`, and Python range `>=3.12,<3.13`. |
| Lock approved R0 dependencies | In scope | blocking | Core pins are DeepAgents and Inspect AI; LangSmith is an explicitly named control dependency group. The test dependency is resolved and frozen in `uv.lock`. |
| Add a minimal importable package and smoke test | In scope | blocking | Prove packaging and environment health without introducing lab domain contracts or runner behavior. |
| Add root documentation and repository ignore policy | In scope | blocking | Explain the repository's R0-only status and keep secrets, raw evidence, generated outputs, environments, caches, and worktrees untracked. |
| Prove `.worktrees/` readiness | In scope | blocking | Create and remove a disposable local worktree only after the baseline commit exists; leave no disposable branch or worktree behind. |
| Implement lab contracts, cases, variants, scorers, adapters, exports, or reports | Out of scope | non-blocking | These belong to the comparative R0 and later design work. |
| Execute Inspect, LangSmith, model-provider, trace, or sandbox runs | Out of scope | non-blocking | No credentials, account access, provider/model calls, trace uploads, Docker execution, or managed-service data transfer is authorized. |
| Select the final evaluation baseline or change the trade-study scores | Out of scope | non-blocking | Selection remains governed by `VAL-9` and the Section 8 decision rule. |
| Configure CI, create a remote repository, push commits, or publish packages | Out of scope | non-blocking | Provider, budget, CI, hosting, and publication policy remain unresolved follow-up work. |

# Materially Verifiable Success Criteria

| ID | Criterion | Proof | Required before done |
| --- | --- | --- | --- |
| TD-SC-1 | The workspace is a Git repository on branch `main` with a baseline commit, no remote configured, and a clean tracked working tree at handoff. | Record `git rev-parse --is-inside-work-tree`, `git branch --show-current`, `git log -1 --oneline`, empty `git remote -v` output, and empty `git status --short` output. | Yes |
| TD-SC-2 | The baseline commit tracks the design packet, its checksum and validation sidecars, and this task artifact; the design packet still matches its recorded SHA-256. | Record `git ls-files docs/design docs/tasks` and a successful checksum verification against the committed sidecar. | Yes |
| TD-SC-3 | Project metadata declares Python `>=3.12,<3.13`, distribution `deepagents-lab`, import package `deepagents_lab`, a standard PEP 517 build backend, and `uv`-managed dependency groups. | Inspect the committed `.python-version` and `pyproject.toml`; record `uv lock --check`. | Yes |
| TD-SC-4 | `uv.lock` resolves exact `deepagents==0.7.8`, `inspect-ai==0.3.260`, and control-group `langsmith==0.11.1`; a clean `uv`-managed Python 3.12 environment installs the frozen lock and imports all three packages. | Record the clean-environment frozen sync, Python version, imported distribution versions, and `uv lock --check`. | Yes |
| TD-SC-5 | The minimal `deepagents_lab` package imports successfully and at least one repository smoke test passes through the locked test environment without credentials or networked model execution. | Record `uv run --frozen --all-groups pytest -q` and a direct `deepagents_lab` import. | Yes |
| TD-SC-6 | The root README identifies this repository as the comparative R0 lab, links the authoritative design packet, preserves the provisional Inspect-versus-LangSmith status, and gives the frozen setup and test commands. | Review the committed README against the design packet and execute its local setup and test commands. | Yes |
| TD-SC-7 | Git ignore rules cover `.worktrees/`, virtual environments, Python/build/test caches, environment and credential files, local evaluator logs, raw traces, generated results, and disposable sandbox artifacts; representative files from each sensitive class remain untracked. | Record targeted `git check-ignore -v` probes and `git status --short --ignored`; confirm no credential-like or generated evidence file is tracked. | Yes |
| TD-SC-8 | After the baseline commit, a disposable Git worktree can be created under `.worktrees/`, observed in Git's worktree inventory, and removed cleanly with no disposable branch or worktree left behind. | Record the creation and `git worktree list --porcelain` evidence, then the final worktree inventory, branch list, and clean root status after cleanup. | Yes |

# Incremental Value Delivery

| Slice | Value proven | Risk retired | Evidence | Stop / continue decision |
| --- | --- | --- | --- | --- |
| 1. Authority-preserving Git baseline | The approved design state and initialization contract have durable local history on `main`. | Accidental loss of the only design authority and inability to use repository worktrees. | `TD-SC-1` and `TD-SC-2` evidence. | Stop if source checksum verification fails or the first commit would omit an authoritative artifact; otherwise continue. |
| 2. Reproducible Python substrate | A clean Python 3.12 environment can install and import the exact R0 package set, and the lab package test runs. | Hidden system-Python reliance, unconstrained dependency drift, and an unusable R0 starting point. | `TD-SC-3` through `TD-SC-5` evidence. | Stop if the exact pins cannot lock, install, or import; report the compatibility evidence without widening versions. Otherwise continue. |
| 3. Safe follow-on workspace | Maintainers have accurate entry documentation, protected local artifacts, and a proven isolated-worktree path. | Premature platform claims, accidental secret/result commits, and follow-on work occurring in the base checkout. | `TD-SC-6` through `TD-SC-8` evidence. | Continue to the comparative R0 only when all blocking criteria pass and the base checkout is clean. |

# Review Boundary

| Boundary | In scope for review | Out of scope / follow-up | Approval impact |
| --- | --- | --- | --- |
| Git baseline and authority preservation | Branch name, baseline commit, tracked source artifacts, checksum validity, clean handoff, and absence of an assumed remote | Remote hosting, pull-request policy, release tags, and branch-protection configuration | blocking inside the stated scope; remote policy is non-blocking |
| Python project reproducibility | Python range, package metadata, PEP 517 buildability, exact approved dependency pins, lock consistency, clean frozen installation, imports, and smoke test | Lab architecture, experiment schemas, adapters, scorer behavior, and seed-suite design | blocking inside the stated scope; R0 implementation is non-blocking |
| Repository safety | Ignore coverage, absence of tracked secrets/generated evidence, no provider calls, and no retained disposable worktree | Production secret management, trace redaction implementation, Docker containment, and managed-service governance | blocking inside the stated scope; operational policy is non-blocking |
| Documentation accuracy | README setup/test commands, link to source authority, and accurate provisional-candidate language | Final evaluator selection, score revisions, provider choice, judge policy, budget, and CI policy | blocking for inaccurate current claims; unresolved downstream choices are non-blocking |
| Change containment | Minimal files and no implementation beyond initialization | Refactors or abstractions justified only by future experiments | blocking if speculative scaffolding enters this task; future structures are non-blocking |

# Validation / Evidence

| Criterion ID | Check | Evidence | Runner / owner | Required before done |
| --- | --- | --- | --- | --- |
| TD-SC-1 | Verify repository, `main`, baseline commit, remotes, and clean status. | Captured Git command output attached to the implementation handoff. | Repository maintainer | Yes |
| TD-SC-2 | Verify tracked authority files and packet checksum. | `git ls-files` output and successful checksum command output. | Repository maintainer | Yes |
| TD-SC-3 | Verify Python/project metadata and lock consistency. | Reviewed metadata plus successful `uv lock --check` output. | Repository maintainer | Yes |
| TD-SC-4 | Recreate a clean `uv`-managed Python 3.12 environment, sync all groups from the frozen lock, and import the exact distributions. | Sync output, Python version, package versions, and import-smoke output. | Repository maintainer | Yes |
| TD-SC-5 | Import the lab package and run the smoke suite. | Successful import output and pytest summary. | Repository maintainer | Yes |
| TD-SC-6 | Review README claims and execute documented local commands. | Review note plus successful command output. | Repository maintainer | Yes |
| TD-SC-7 | Probe ignore policy and inspect tracked/ignored status. | `git check-ignore -v`, ignored-status output, and tracked-file audit. | Repository maintainer | Yes |
| TD-SC-8 | Create, inventory, remove, and re-inventory a disposable `.worktrees/` checkout. | Before/after worktree and branch inventories plus final clean status. | Repository maintainer | Yes |

# Execution Notes

- Calibration: `TD1 Standard`. The work is a bounded multi-file repository initialization with dependency and Git-history effects, but no architectural or externally integrated behavior.
- Execution route: `DIRECT` once this contract reaches `READY`. The approved design packet and this task provide enough authority; a separate design specification or execution plan would add no necessary decision for this slice.
- Before implementation, read the design packet from its exact path, verify its checksum sidecar, and read its validation sidecar. The latest user instruction remains controlling if it changes this boundary.
- Perform the in-place Git initialization and baseline commit as the explicit bootstrap exception to the worktree rule. After `TD-SC-8` proves the mechanism, execute every follow-on implementation task in a repository-local `.worktrees/` checkout.
- Use `uv` to acquire and select Python 3.12. Do not depend on a system `python3.12` executable.
- Package-registry access is permitted only to acquire the approved Python interpreter and locked dependencies. It does not authorize managed evaluation-service access or model/provider execution.
- Keep DeepAgents and Inspect AI in the core R0 environment. Keep LangSmith in a clearly named control dependency group so repository initialization does not imply platform selection.
- A standard test runner may be added to the development group; its resolved version must be present in the committed lock. Do not add formatting, linting, typing, documentation, orchestration, or application frameworks without a current success criterion.
- Do not relax or silently upgrade the three approved package versions. If compatibility fails, preserve the command output and return the task for source-authority revision.
- Do not add credentials, make provider/model calls, send traces, create accounts, run Docker workloads, create a remote, push, or publish.
- Use the existing Git identity only if one is configured. If committing requires inventing or changing user identity, stop and request repository-owner direction.
- Keep modules small: this task should need only project metadata, one minimal package module, one smoke-test module, README, ignore rules, and the existing design/task documents.

# Follow-up / Non-blocking Work

- Execute the Section 11 comparative R0, including `VAL-1`, `VAL-3`, `VAL-5`, and `VAL-9`, in a dedicated repository-local worktree.
- Define only the minimum lab records and adapter seams required by the R0; defer broad scaffolding until the experiment supports it.
- Resolve the canonical model/provider, optional judge, spend limits, credential flow, and local-versus-CI trigger policy before publishing baseline results.
- Exercise privileged filesystem or shell cases only after the applicable `VAL-4` containment evidence passes.
- Update the design packet, checksum, and validation sidecar with the empirical trade-study result before authoring a downstream design specification.
- Decide remote hosting, collaboration policy, automated dependency updates, and CI after the local R0 proves the repository shape.
