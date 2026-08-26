---
type: TaskDefinition
title: Expose DeepAgents Through a Local Agent Server
task_id: add-local-agent-server
artifact_version: "3.0"
revision: "1"
created_at: "2026-08-26T07:24:16-05:00"
updated_at: "2026-08-26T08:26:51-05:00"
validation_profile: skills/task-definition/profiles/task-definition.yaml
---

# Task Control

| Contract state | Execution route | State rationale |
| --- | --- | --- |
| READY | DIRECT | The maintainer selected Agent Server as the local runtime boundary, the existing DeepAgents object is a compiled LangGraph graph, and the bounded Python-only server integration can proceed without a separate plan or specification. |

# Objective

Expose the repository's DeepAgents graph through a reproducible, loopback-only local Agent Server that supports streamed runs and stateful threads without requiring a LangSmith account or trace upload. Preserve the existing `deepagents-live` command by moving agent construction behind one repository-owned boundary shared by the CLI and server.

This task delivers the server/API prerequisite for a later Agent Chat UI task. It does not add a browser application or make Agent Server part of the evaluation-runner decision.

# Context / Constraints

- Remote `main` at merge commit `28063c6` contains DeepAgents `0.7.8`, the `deepagents-live` one-shot command, exact Inspect and LangSmith R0 pins, and seven passing offline tests.
- The maintainer selected a local Agent Server plus Agent Chat UI workbench and then required separate tasks. This task owns only the design reconciliation and Python server boundary; `add-local-agent-chat-ui` owns the browser application.
- The design packet's `SURF-13` currently says a dedicated UI is excluded. The maintainer's later decision supersedes that conclusion, so this task must update and revalidate the packet and its checksum before relying on its remaining constraints.
- DeepAgents' `create_deep_agent()` returns a compiled LangGraph graph. The server export and CLI shall share construction code rather than execute the CLI as a subprocess or maintain two agent definitions.
- The initial exported graph may use the current default `openai:gpt-5.4`. Runtime model/variant selection is follow-up, while the CLI's existing explicit model override must continue to work.
- `OPENAI_API_KEY` remains an environment-only server credential. Ordinary tests and server startup checks must not require it; only the bounded streamed and thread-continuity live proof may use it.
- Agent Server shall bind to loopback. Public tunnels, deployment, remote clients, production authentication, and multi-user access are not authorized.
- The default workflow shall set `LANGSMITH_TRACING=false` and run with `LANGSMITH_API_KEY` absent. If no compatible pinned local runtime can start under that condition, stop with exact evidence rather than add an account requirement.
- The current `langgraph-api` development runtime is Elastic License 2.0, not OSI open source. Its exact resolved version and license boundary must be recorded.
- `.langgraph_api/` and other local server state are generated runtime data and must remain ignored and untracked.

# Source Authority

| Source | Authority | Status | Task implication |
| --- | --- | --- | --- |
| Maintainer instructions dated 2026-08-26 | Controlling runtime and task-boundary decision | Active | Add Agent Server first as an independently reviewable predecessor to Agent Chat UI. |
| `/Users/jasonbelmonti/Documents/Development/deepagents-lab/docs/design/deepagents-lab-design-process.md` and sidecars | Existing lab design authority | Checksum verified; `SURF-13` partially superseded | Preserve local-first operation, credential safety, dependency provenance, and evaluation separation; reconcile the workbench decision and sidecars first. |
| GitHub PR `jasonbelmonti/deepagents-lab#1` and remote `main` commit `28063c6` | Implementation baseline | Merged and inspected | Preserve the one-shot CLI, its model override, and exact R0 package pins. |
| [LangGraph local-server documentation](https://docs.langchain.com/oss/python/langgraph/local-server) and [application structure](https://docs.langchain.com/langsmith/application-structure) | Local configuration authority | Inspected 2026-08-26 | Register an importable graph with `langgraph.json` and prove the local API, graph identity, and streaming boundary. |
| [Agent Server architecture](https://docs.langchain.com/langsmith/agent-server) | Runtime semantics authority | Inspected 2026-08-26 | Prefer a compiled graph for fixed configuration and use server-owned runs, threads, and checkpoints. |
| [PyPI `langgraph-api`](https://pypi.org/project/langgraph-api/) | Package and license authority | `0.13.0` observed 2026-08-26; Elastic License 2.0 | Pin a compatible development runtime and avoid claims or workflows that imply production or fully open-source server authority. |

# Task Scope

| Scope item | Classification | Approval impact | Notes |
| --- | --- | --- | --- |
| Reconcile the design packet's local-workbench decision and regenerate its validation/checksum sidecars | In scope | blocking | Record the selected Agent Server plus Agent Chat UI workbench while keeping evaluator selection separate. |
| Extract one focused agent-construction module shared by server and CLI | In scope | blocking | Export the fixed compiled graph and retain CLI default/override behavior, key checking, and final-text output. |
| Add and lock compatible local Agent Server development dependencies | In scope | blocking | Preserve exact `deepagents==0.7.8`, `inspect-ai==0.3.260`, and control `langsmith==0.11.1` pins. |
| Add `langgraph.json` and a documented loopback development command | In scope | blocking | Register one stable graph ID and load only server-side environment configuration. |
| Add offline server/CLI contract tests and bounded live API proof | In scope | blocking | Prove import, startup, streaming, thread continuity, and isolation; keep routine tests network-free. |
| Add or scaffold Agent Chat UI, Node dependencies, or browser automation | Out of scope | blocking if introduced | Those files and validations belong exclusively to `add-local-agent-chat-ui`. |
| Add LangSmith tracing, Studio reliance, datasets, evaluators, or trace upload | Out of scope | non-blocking | The comparative R0 and any opt-in observability remain separate. |
| Implement Inspect adapters, evaluation records, scorers, cases, or reports | Out of scope | non-blocking | Agent Server is an interaction API, not the selected evaluation runner. |
| Add production deployment, authentication, durable database services, public access, or multi-user policy | Out of scope | non-blocking | The accepted runtime is a single-maintainer loopback development process. |
| Expose shell, arbitrary code, host-filesystem, remote-MCP, or sandbox capabilities | Out of scope | blocking if introduced | No privileged execution containment is established here. |
| Add runtime assistant/model/variant selection | Follow-up | non-blocking | Add after the fixed graph and client contract are accepted. |

# Materially Verifiable Success Criteria

| ID | Criterion | Proof | Required before done |
| --- | --- | --- | --- |
| TD-SC-1 | The design packet identifies Agent Server plus Agent Chat UI as the selected local workbench, no longer excludes all dedicated UI, preserves the separate evaluation decision, and has valid regenerated validation and checksum sidecars. | Design-profile validation with the required engine version and zero diagnostics, checksum verification, and focused decision-text review. | Yes |
| TD-SC-2 | One repository-owned construction module provides an importable compiled graph for Agent Server and agents for the CLI; `deepagents-live` retains its default/override selection, missing-key failure, and final-text behavior. | Focused offline tests, graph import/type evidence, CLI help/error/output checks, and the complete frozen Python suite. | Yes |
| TD-SC-3 | With `LANGSMITH_API_KEY` absent and `LANGSMITH_TRACING=false`, the pinned server starts on loopback, loads the configured graph ID, exposes API documentation and discovery, and leaves no unexplained external trace connection or upload. | Credential-redacted startup/version/listener logs, local HTTP/SDK discovery output, trace-disabled configuration evidence, and local-state inspection. | Yes |
| TD-SC-4 | A bounded credentialed SDK/API probe receives streamed events and a terminal assistant response; two runs in one thread retain a unique context token, while a new thread does not contain that token before receiving it. | Stream-event capture and server thread/run records with credentials and unrelated message content redacted. | Yes |
| TD-SC-5 | The committed server setup is reproducible and contained: Python locks are consistent, existing exact R0 pins remain unchanged, runtime version/license are recorded, generated state is ignored, README commands work, the test suite passes offline, and no service remains listening after cleanup. | Lock/install/version/license inspection, `git check-ignore`, documented-command output, offline pytest summary, listening-address cleanup, and clean Git status. | Yes |

# Incremental Value Delivery

| Slice | Value proven | Risk retired | Evidence | Stop / continue decision |
| --- | --- | --- | --- | --- |
| 1. Shared graph and keyless local API | The existing agent has one construction owner and loads behind a standard local server without LangSmith. | Divergent definitions, subprocess coupling, hidden service-account requirements, and incompatible dependency resolution. | `TD-SC-1` through `TD-SC-3` evidence. | Stop if the server requires LangSmith, changes an exact R0 pin, or cannot load the graph without duplication; otherwise continue to runtime behavior. |
| 2. Stateful streaming server contract | The API streams a real DeepAgents result and provides the thread behavior needed by the UI successor. | Deferring protocol, state, and cleanup failures into UI implementation. | `TD-SC-4` and `TD-SC-5` evidence. | Present for review only when the API contract passes and all processes and generated state are contained. |

# Review Boundary

| Boundary | In scope for review | Out of scope / follow-up | Approval impact |
| --- | --- | --- | --- |
| Design and ownership | Reconciled workbench decision, one agent-construction owner, and interaction/evaluation separation | Final evaluator selection and browser implementation | blocking for stale authority or duplicate construction; UI and evaluation details are non-blocking here |
| Agent Server correctness | Graph registration, compiled lifecycle, messages state, loopback binding, discovery, streaming, threads, errors, and cleanup | UI rendering, production persistence, jobs, scaling, webhooks, and deployment | blocking for failure of the local API contract; downstream UI and production behavior are non-blocking |
| Credential and data safety | Environment-only OpenAI key, absent LangSmith key, tracing disabled, ignored local state, sanitized evidence, and no privileged tools | Managed secrets, remote clients, trace governance, and sandbox containment | blocking for secret exposure, unintended trace transfer, tracked state, or privileged capability; broader controls are non-blocking |
| Dependencies and licensing | Compatible exact server locks, preserved R0 pins, resolved runtime provenance, and Elastic License disclosure | Alternative runtimes and production licensing decisions | blocking for pin drift, unreproducible install, or misleading license claims; alternatives are non-blocking |
| Regression evidence | CLI compatibility, offline tests, bounded live calls, documented commands, and clean shutdown | Browser tests, additional models, load tests, and CI | blocking for regression or unrepeatable server evidence; broader coverage is non-blocking |

# Validation / Evidence

| Criterion ID | Check | Evidence | Runner / owner | Required before done |
| --- | --- | --- | --- | --- |
| TD-SC-1 | Update the design decision, run its profile, and verify its checksum. | Valid design JSON with required engine version and zero diagnostics, successful checksum output, and decision review. | Repository maintainer | Yes |
| TD-SC-2 | Run construction/graph/CLI tests and the complete frozen Python suite without credentials or network access. | Pytest output, graph type/import record, and preserved CLI behavior evidence. | Repository maintainer | Yes |
| TD-SC-3 | Start the server with LangSmith credentials absent and tracing disabled; inspect listener, API, graph identity, logs, and local state. | Startup/version output, local HTTP/SDK responses, trace-disabled evidence, and filesystem audit. | Repository maintainer | Yes |
| TD-SC-4 | Use the local SDK or REST API for the minimal streaming and thread continuity/isolation probe. | Credential-redacted events, terminal response, thread IDs, run IDs, and state inspection. | Repository maintainer and credential holder | Yes |
| TD-SC-5 | Recreate from the frozen lock, inspect versions/license/ignore behavior, run documented commands and tests, terminate the server, and inspect final status. | Clean-install and lock output, provenance review, ignore probes, pytest summary, listener cleanup, and clean status. | Repository maintainer | Yes |

# Execution Notes

- Calibration: `TD1 Standard`; this is a bounded Python runtime integration with one external model smoke, durable local state, and a downstream client contract.
- Route: `DIRECT`; the runtime, local-only boundary, graph identity requirement, and failure gates are resolved.
- Execute in `/Users/jasonbelmonti/Documents/Development/deepagents-lab/.worktrees/agent-server` on branch `codex/agent-server` created from then-current remote `main`.
- Before implementation, read this complete task, reload repository state, then reconcile and revalidate the design packet before using its remaining constraints.
- Keep agent construction/export separate from CLI parsing and output. Do not run `deepagents-live` as a subprocess from the server.
- Prefer a compiled graph export for the fixed first server. Use a factory only if the pinned runtime requires it or a required criterion cannot otherwise preserve the CLI override; record the reason.
- Add compatible exact Agent Server development dependencies without changing the three exact R0 pins. Record `langgraph-api` provenance and Elastic License 2.0.
- Set `LANGSMITH_TRACING=false`, remove `LANGSMITH_API_KEY` for startup/proof, bind to loopback, and do not use Studio, tunnels, or hosted services.
- Keep routine tests offline. Limit provider use to the minimum streamed/thread probe required by `TD-SC-4`; it is operational evidence, not an evaluation result.
- Do not add Node or Agent Chat UI files under this task.

### Execution Checkpoint

| Execution status | Current proving slice | Evidence admitted | Next action | Blockers / stop condition |
| --- | --- | --- | --- | --- |
| review-ready | TD-SC-1 through TD-SC-5 are proven and ready for independent review. | TD-SC-1: after rebasing onto current `origin/main`, the reconciled design preserved the subagent R0 chain as `CON-12` and the workbench chain as `CON-13`; design profile `3.5.0` returned `valid: true`, zero diagnostics, input hash `3dae03017841f3f4ed4564b6e90245421ed193b1a810c023b4fd1b5c8ab18b96`, and checksum `0b3d2d5e83f0d43655fbba7dbc5d7cb3aebbfbcea081624ada738aaf527036f8` verified. TD-SC-2: CLI and server share `create_agent`; 13 offline tests pass, server factory returns `Pregel`, config validates, CLI help works, and missing-key exit remains `2`. TD-SC-3: keyless `langgraph dev` bound only `127.0.0.1:2024`; `/docs` and `/openapi.json` returned `200`, assistant discovery returned graph ID `deepagents_lab`, and logs reported no license/control-plane key and skipped the metadata loop. TD-SC-4: live SDK stream emitted `metadata,values,updates,updates,values` and terminal `STREAM_OK`; primary thread `01a03e34-5a99-7421-ae9b-b7c5e52331b4` retained `ORBIT-72631` over two runs while isolated thread `01a03e34-8024-7563-8628-e8503e5effe3` returned `NONE`. TD-SC-5: frozen sync/lock pass; controlled pins remain `0.7.8`, `0.3.260`, and `0.11.1`; dev runtime resolves CLI `0.4.31`, API `0.13.0`, in-memory runtime `0.33.0`, and SDK `0.4.3`; ELv2 provenance and commands are documented; `.langgraph_api/` is ignored/untracked; no listener remains on port `2024`. | Conduct independent review against this task boundary; commit or remediate only from review findings. | None observed; the implementation stop conditions did not trigger. |

# Follow-up / Non-blocking Work

- Execute `docs/tasks/add-local-agent-chat-ui.md` after this server contract is accepted.
- Add runtime model, middleware, or variant selection through named assistants after the fixed graph contract is stable.
- Decide whether Agent Server participates in evaluation only through the separate comparative R0.
- Add production deployment, authentication, persistence, and multi-user operation only through a new task.
