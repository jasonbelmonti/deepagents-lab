---
type: TaskDefinition
title: Connect Unmodified Agent Chat UI to the Local Agent Server
task_id: add-local-agent-chat-ui
artifact_version: "3.0"
revision: "10"
created_at: "2026-08-26T07:24:16-05:00"
updated_at: "2026-08-26T10:20:05-05:00"
validation_profile: skills/task-definition/profiles/task-definition.yaml
---

# Task Control

| Contract state | Execution route | State rationale |
| --- | --- | --- |
| READY | DIRECT | The maintainer's no-fork authority is resolved through an exact-pinned, unmodified upstream Git submodule and a lab-owned launcher. Source authority is complete, Markdown Engine 3.5.0 validation passes without diagnostics, and semantic plus post-draft review found no blocker. |

# Objective

Run the official Agent Chat UI locally from an exact-pinned, unmodified upstream checkout and connect it to the accepted DeepAgents Agent Server through a lab-owned launcher that supplies only public loopback configuration.

This task delivers the browser half of the local development workbench without copying, patching, or maintaining Agent Chat UI source. It does not modify agent semantics, own server state, implement evaluation, or create a custom product UI.

# Context / Constraints

- The maintainer's 2026-08-26 no-fork directive is controlling. Do not vendor, scaffold, copy, patch, or modify upstream Agent Chat UI source.
- Consume https://github.com/langchain-ai/agent-chat-ui.git as a Git submodule at exact commit 2a76b8e0da2be9115348eaba0a08dd2020967fe8. The gitlink is the version pin; the upstream MIT license and frozen pnpm lock remain inside the untouched submodule.
- Keep all lab-specific behavior outside the submodule. A small lab-owned launcher may initialize the submodule, install its frozen dependencies, set public local defaults, strip inherited provider, LangSmith, and AI-agent detection variables from the UI process, and invoke upstream Next.js on loopback. Removing detection variables prevents Next.js from generating untracked instruction files inside the submodule.
- The accepted Agent Server is present on current main merge a7735df. It owns URL http://127.0.0.1:2024, graph ID deepagents_lab, the messages state, streaming API, thread semantics, Python dependencies, model credentials, and runtime licensing.
- The lab launcher shall default the upstream-supported NEXT_PUBLIC_API_URL and NEXT_PUBLIC_ASSISTANT_ID variables to the accepted server coordinates. It shall not pass OPENAI_API_KEY, LANGSMITH_API_KEY, LANGGRAPH_API_URL, or an authentication scheme to the UI process.
- Upstream remains a general-purpose UI and retains its own remote-deployment, authentication, Studio, and proxy capabilities. This task governs only the lab-owned launcher and its default local session; it does not claim those upstream capabilities are absent.
- Bind the local UI process to 127.0.0.1:3000. Public hosting, sharing, tunnels, and production operation are not authorized.
- Node 22.20.0, pnpm 10.30.3, and npx 11.13.0 are available in the inspected environment. Upstream's committed packageManager field and lockfile are the package-manager and dependency authority.
- Submodule dependency trees, build caches, local environment files, browser evidence, and Agent Server runtime state must remain ignored.

# Source Authority

| Source | Authority | Status | Task implication |
| --- | --- | --- | --- |
| Maintainer no-fork directive dated 2026-08-26 | Controlling ownership and integration decision | Active | Replace the forked import entirely; no upstream source file may be copied or changed. |
| [Agent Chat UI documentation](https://docs.langchain.com/oss/python/langgraph/ui) | Official local-operation and connection authority | Re-inspected 2026-08-26 | Run the upstream application locally and configure graph ID, deployment URL, and an optional API key through supported inputs. |
| [Agent Chat UI source repository](https://github.com/langchain-ai/agent-chat-ui) | Upstream source, lockfile, and license authority | Main resolved to exact commit 2a76b8e0da2be9115348eaba0a08dd2020967fe8; MIT-licensed | Reference the exact upstream commit as a Git submodule and preserve its tree unchanged. |
| docs/tasks/add-local-agent-server.md, accepted head 93fa7ed, and merge a7735df | Predecessor server and launcher authority | Accepted and present | Consume the accepted loopback URL, graph ID, streaming, thread behavior, and deepagents-server command without changing server ownership. |
| PR #6 implementation at pre-correction commit b07a339 | Superseded implementation evidence | Rejected by maintainer no-fork directive | Retain only as recoverable Git history; none of its fork-specific source or evidence is admissible. |

# Task Scope

| Scope item | Classification | Approval impact | Notes |
| --- | --- | --- | --- |
| Reference exact upstream Agent Chat UI as a Git submodule | In scope | blocking | Commit .gitmodules and a gitlink at the approved upstream commit; do not commit upstream files as lab-owned blobs. |
| Add a lab-owned deepagents-ui launcher outside the submodule | In scope | blocking | Initialize the submodule when needed, install from upstream's frozen lock, supply public loopback defaults, strip inherited credentials and agent-detection variables, and bind Next.js to loopback. |
| Document the server and UI one-command workflow | In scope | blocking | A clean checkout shall use deepagents-server and deepagents-ui in separate terminals. |
| Prove unmodified provenance, buildability, streaming, and thread behavior | In scope | blocking | Re-run evidence against the submodule-backed current head. |
| Modify, patch, scaffold, vendor, or copy any Agent Chat UI source file | Out of scope | blocking if introduced | Any upstream tree difference rejects the task. |
| Remove or alter upstream remote deployment, authentication, Studio, proxy, or dependency behavior | Out of scope | blocking if introduced | These remain upstream-owned capabilities; the lab launcher only controls its own default process environment. |
| Change DeepAgents construction, Agent Server configuration, graph ID, messages state, or Python dependencies beyond the launcher entry point | Out of scope | blocking if introduced | Return server changes to the predecessor task. |
| Add custom visual design, evaluation visualization, generative UI, or artifact panels | Out of scope | non-blocking | Upstream presentation is accepted unchanged. |
| Add production hosting, authentication, analytics, or multi-user behavior | Follow-up | non-blocking | Requires a separate production contract. |

# Materially Verifiable Success Criteria

| ID | Criterion | Proof | Required before done |
| --- | --- | --- | --- |
| TD-SC-1 | apps/agent-chat-ui is a gitlink at exact upstream commit 2a76b8e0da2be9115348eaba0a08dd2020967fe8; its worktree is clean and identical to that commit, and its frozen install, format, lint, and build checks pass without any lab-owned upstream source change. | Git tree-mode and submodule inspection, upstream commit comparison, frozen install output, and upstream checks. | Yes |
| TD-SC-2 | deepagents-ui initializes and runs the exact-pinned submodule on 127.0.0.1:3000, supplies http://127.0.0.1:2024 and deepagents_lab through upstream-supported configuration, and removes provider, LangSmith, deployment-proxy, auth, and AI-agent detection variables from the UI child environment. | Focused launcher tests, process/listener inspection, child-environment audit, clean submodule status during runtime, and browser/server request correlation for the default session. | Yes |
| TD-SC-3 | A browser-submitted message visibly streams to a terminal assistant response; a second message remains in the same server thread, and a new chat creates a different thread without inherited messages. | Browser automation or recorded inspection plus matching server thread, run, and message-state evidence on the submodule-backed head. | Yes |
| TD-SC-4 | The README's clean-checkout commands start server and UI in two terminals, initialize required local state, leave generated output ignored, stop both processes cleanly, and finish with clean parent and submodule status. | Documented-command execution, ignore probes, process cleanup, git status, and git submodule status. | Yes |

# Incremental Value Delivery

| Slice | Value proven | Risk retired | Evidence | Stop / continue decision |
| --- | --- | --- | --- | --- |
| 1. No-fork upstream boundary | The lab references a reproducible upstream UI without owning or modifying its source. | Accidental fork maintenance, hidden patches, floating source, and license ambiguity. | TD-SC-1 evidence. | Stop if any upstream file must change; revise the integration or use the hosted UI instead. |
| 2. Local launcher boundary | One lab-owned command starts the upstream UI with safe public defaults and no inherited credentials. | Manual setup drift, accidental credential exposure, and non-loopback binding. | TD-SC-2 and TD-SC-4 launcher evidence. | Stop if upstream cannot run unchanged through supported configuration. |
| 3. Browser workbench handoff | Streaming, retained-thread continuation, and new-thread isolation work through the unmodified UI. | A reproducible dependency that does not actually support the lab workflow. | TD-SC-3 and final TD-SC-4 evidence. | Present for review only when browser/server identities reconcile and all processes are stopped. |

# Review Boundary

| Boundary | In scope for review | Out of scope / follow-up | Approval impact |
| --- | --- | --- | --- |
| Upstream immutability | Gitlink mode and commit, clean submodule tree, upstream license/lockfile, and absence of copied or patched UI source | Alternative UI selection and upstream contribution strategy | blocking for any local upstream source ownership or mutation; alternatives are non-blocking |
| Lab launcher | Submodule initialization, frozen install, public defaults, credential stripping, loopback binding, error behavior, and focused tests | General package management and production process supervision | blocking for unsafe environment forwarding, floating installation, or non-loopback exposure |
| Local UI correctness | Page identity, streaming render, same-thread continuation, new-thread isolation, and browser errors | Custom styling, advanced artifacts, and assistant management | blocking for failure of the accepted browser path; feature expansion is non-blocking |
| Server-boundary preservation | Consumption of accepted URL, graph, messages, streaming, and thread contracts without server behavior changes | Server refactors and new runtime configuration | blocking if UI work changes or duplicates server ownership |
| Evidence quality | Exact submodule proof, current-head checks, browser-to-server correlation, documented commands, and clean final state | Additional browsers, visual regression suites, load tests, and CI | blocking for unrepeatable or stale evidence; broader coverage is non-blocking |

# Validation / Evidence

| Criterion ID | Check | Evidence | Runner / owner | Required before done |
| --- | --- | --- | --- | --- |
| TD-SC-1 | Inspect gitlink mode and commit, compare the submodule tree to upstream, and run upstream's frozen install and required checks. | git ls-files --stage, git submodule status, clean submodule status, upstream ref comparison, and pnpm outputs. | Repository maintainer | Yes |
| TD-SC-2 | Exercise the launcher with focused process mocks and a real local run; inspect its child environment and listeners. | Unit tests plus live loopback process and request evidence showing no forwarded credential or deployment variables. | Repository maintainer | Yes |
| TD-SC-3 | Submit two messages in one chat, create a new chat, and reconcile the UI with server thread/run/message records. | Browser capture or automation output plus matching distinct server identifiers and state. | Repository maintainer and credential holder | Yes |
| TD-SC-4 | Follow the clean-checkout README workflow, verify ignored output, terminate services, and inspect parent and submodule status. | Command transcript, ignore evidence, no residual listeners, and clean Git outputs. | Repository maintainer | Yes |

# Execution Notes

- Calibration: TD1 Standard; the implementation is small, but immutable upstream ownership and credential/process boundaries require explicit proof.
- Route: DIRECT; a pinned Git submodule and lab-owned launcher use supported upstream configuration without changing either agent or UI internals.
- Execute in /Users/jasonbelmonti/Documents/Development/deepagents-lab/.worktrees/agent-chat-ui on branch codex/agent-chat-ui, rebased on main merge a7735df.
- Replace the tracked upstream source import with a Git submodule at the exact accepted commit. The rejected implementation remains recoverable at b07a339.
- Add the launcher only under lab-owned Python source and expose it as deepagents-ui; do not add files inside the submodule.
- The launcher may set NEXT_PUBLIC_API_URL=http://127.0.0.1:2024 and NEXT_PUBLIC_ASSISTANT_ID=deepagents_lab. It must remove OPENAI_API_KEY, LANGSMITH_API_KEY, LANGGRAPH_API_URL, and NEXT_PUBLIC_AUTH_SCHEME from the UI child environment.
- Invoke upstream Next.js with explicit host 127.0.0.1 and port 3000 without editing its package scripts.
- Treat upstream's retained generic endpoint, authentication, Studio, and proxy capabilities as upstream behavior. Validate only that the documented lab launch uses local public configuration and no credential-bearing child environment.
- The exact upstream commit emits 18 lint warnings, a Tailwind module-format build warning, an API-passthrough notice, and a React clip-path development warning while still passing format, lint, build, and the accepted browser path. These are upstream-owned observations and must not be patched under this task.
- Do not interpret browser interaction as evaluation evidence.

### Execution Checkpoint

| Execution status | Current proving slice | Evidence admitted | Next action | Blockers / stop condition |
| --- | --- | --- | --- | --- |
| review-ready | TD-SC-1 through TD-SC-4 are proven on the no-fork implementation; all three incremental slices are complete. | TD-SC-1: parent mode 160000 and submodule HEAD both equal exact upstream commit 2a76b8e0da2be9115348eaba0a08dd2020967fe8, the submodule stayed clean, frozen pnpm install and format passed, lint exited 0 with 18 upstream warnings, and production build/type validation passed with upstream notices. TD-SC-2: three focused launcher tests prove supported public defaults plus credential and agent-detection removal; live deepagents-ui bound only to 127.0.0.1:3000, connected to the accepted graph, and produced no generated submodule files. TD-SC-3: browser runs 01a03ea6-e247-7af1-9086-e131983c3c7d and 01a03ea7-2153-7c32-8c82-318700d0bf14 retained four messages on thread 01a03ea6-e231-7590-9737-f0a23c242040; isolated run 01a03ea7-66e7-77a3-8040-0a1967cf572f produced two messages on distinct thread 01a03ea7-66d4-7b72-a45f-bffdd772d7f8. TD-SC-4: documented deepagents-server and deepagents-ui commands passed, 18 Python tests passed, the submodule remained clean, temporary credentials were removed, and ports 2024/3000 are clear. | Perform independent review of the no-fork diff and current evidence. | None. |

# Follow-up / Non-blocking Work

- Evaluate the hosted Agent Chat UI as a zero-local-install alternative if localhost operation is no longer required.
- Add named model, middleware, subagent, or experiment-variant selection only through upstream-supported configuration or a separate lab UI.
- Add custom UI or upstream patches only if the maintainer explicitly authorizes a fork in a future task.
- Add production hosting, persistence, analytics, and multi-user operation only through a separate production contract.
