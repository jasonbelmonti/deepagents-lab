---
type: TaskDefinition
title: Connect Agent Chat UI to the Local Agent Server
task_id: add-local-agent-chat-ui
artifact_version: "3.0"
revision: "2"
created_at: "2026-08-26T07:24:16-05:00"
updated_at: "2026-08-26T07:48:51-05:00"
validation_profile: skills/task-definition/profiles/task-definition.yaml
---

# Task Control

| Contract state | Execution route | State rationale |
| --- | --- | --- |
| BLOCKED | BLOCKED | The accepted Agent Server implementation is not yet present on the current repository baseline; it controls the UI's endpoint, graph identity, messages and streaming contract, and thread semantics, so no UI execution is authorized. |

| Missing authority / input | Affected scope / decision | Why blocking | Permitted independent work | Decision owner | Exact resume condition |
| --- | --- | --- | --- | --- | --- |
| An independently accepted implementation of predecessor `add-local-agent-server`, including its concrete loopback URL, stable graph ID, messages and streaming contract, and thread semantics. | Tracked UI connection defaults, compatibility decisions, browser streaming behavior, and same-thread/new-thread validation. | Implementing against an unaccepted or inferred server interface could bind the UI to the wrong graph, invalidate thread behavior, or force prohibited changes across the Python ownership boundary. | None. | Repository maintainer and predecessor implementation reviewer. | Resume only after the `add-local-agent-server` implementation has independently accepted evidence for every required criterion, its accepted commit is the UI task's current repository baseline, and that baseline documents the concrete loopback URL, graph ID, messages state, streaming contract, and thread semantics. |

# Objective

Add a pinned, locally running Agent Chat UI that connects to the accepted DeepAgents Agent Server, renders streamed responses, and exposes server-owned thread behavior without receiving model-provider credentials or requiring a LangSmith account.

This task delivers the browser half of the local development workbench. It does not modify agent semantics, own server state, implement evaluation, or create a custom product UI.

# Context / Constraints

- `add-local-agent-server` is the required predecessor. It owns the stable graph ID, loopback server URL, messages state, streaming API, thread semantics, Python dependencies, model credential, and Agent Server license disclosure.
- This task may begin UI implementation only after the predecessor's required criteria have accepted evidence on the current branch baseline. If that contract changes, this task must be revised before execution continues.
- Agent Chat UI is an MIT-licensed Next.js application maintained by LangChain. It can connect to a local Agent Server by deployment URL and graph ID, and its local connection does not require a LangSmith API key.
- The UI shall bind to loopback and connect only to the predecessor's loopback server. Public hosting, sharing, tunnels, production authentication, and remote access are not authorized.
- `OPENAI_API_KEY` remains exclusively in the Python server environment. It must not enter UI environment files, browser storage, rendered markup, client bundles, logs, screenshots, or requests.
- Preserve the upstream UI behavior and structure except for the minimum local configuration and compatibility changes. A material fork, custom design system, or new application architecture requires task revision.
- Record an exact upstream Agent Chat UI commit or scaffold package version, retain MIT attribution, and commit a pnpm lock so setup does not float with upstream.
- Node `22.20.0`, pnpm `10.30.3`, and npx `11.13.0` are available in the inspected environment; committed metadata and the frozen lock remain the reproducibility authority.
- UI build caches, local environment files, browser evidence, and generated runtime state must remain ignored.

# Source Authority

| Source | Authority | Status | Task implication |
| --- | --- | --- | --- |
| Maintainer instructions dated 2026-08-26 | Controlling UI and task-boundary decision | Active | Use local Agent Chat UI in a separate task after Agent Server, not Gradio or a combined implementation boundary. |
| `docs/tasks/add-local-agent-server.md` | Predecessor server contract | Contract defined; implementation not yet accepted | Consume its accepted loopback URL, graph ID, messages/stream contract, and thread semantics without changing Python ownership. |
| [Agent Chat UI documentation](https://docs.langchain.com/oss/python/langgraph/ui) | UI integration authority | Inspected 2026-08-26 | Configure the local server URL and graph ID, require no LangSmith key for the local connection, and consume the predecessor's existing messages and thread contract. |
| [Agent Chat UI source repository](https://github.com/langchain-ai/agent-chat-ui) | Upstream implementation and license authority | Inspected 2026-08-26; MIT-licensed | Pin provenance, preserve attribution, and avoid maintaining a material fork under this task. |
| Accepted repository state after `add-local-agent-server` | Implementation baseline | Missing; blocks UI execution | Add only focused UI files, configuration, documentation, and browser validation after the exact resume condition in Task Control is satisfied. |

# Task Scope

| Scope item | Classification | Approval impact | Notes |
| --- | --- | --- | --- |
| Add a pinned Agent Chat UI application in a focused repository directory | In scope | blocking | Commit Node metadata, pnpm lock, upstream provenance, MIT attribution, and only required compatibility changes. |
| Configure loopback server URL and stable graph ID without secrets | In scope | blocking | Checked-in defaults may contain public localhost identifiers only; local overrides remain ignored. |
| Add documented UI installation/startup and combined two-process workflow | In scope | blocking | Provide frozen commands for starting the accepted server and the UI in separate terminals. |
| Prove streaming and thread interactions through the browser | In scope | blocking | Use the predecessor's accepted graph; capture bounded, credential-redacted browser and server evidence. |
| Add focused UI build/type/lint checks required by the upstream scaffold | In scope | blocking | Do not introduce a separate frontend test architecture unless needed for the acceptance path. |
| Change DeepAgents construction, Agent Server configuration, graph ID, messages state, or Python dependencies | Out of scope | blocking if introduced | Return changes to the predecessor task or revise this contract if compatibility requires them. |
| Add custom visual design, generative UI, artifact panels, or broad component refactors | Out of scope | non-blocking | Upstream presentation is sufficient for this workbench slice. |
| Add LangSmith tracing, Studio, datasets, evaluators, or trace upload | Out of scope | non-blocking | UI connectivity must not make LangSmith an implicit prerequisite. |
| Add production hosting, authentication, public access, analytics, or multi-user behavior | Out of scope | non-blocking | The accepted boundary is a single-maintainer loopback application. |
| Add evaluation result visualization or use UI behavior as evaluation evidence | Out of scope | non-blocking | Inspect/LangSmith evaluation remains governed by the comparative R0. |
| Add model/variant/assistant selection controls or extensive tool/artifact presentation | Follow-up | non-blocking | Add only after the default graph UI seam is accepted. |

# Materially Verifiable Success Criteria

| ID | Criterion | Proof | Required before done |
| --- | --- | --- | --- |
| TD-SC-1 | The Agent Chat UI is reproducibly installed from committed Node metadata and a frozen pnpm lock, records an exact upstream source version and MIT attribution, and passes its required build/type/lint checks. | Frozen install output, checks/build output, lock inspection, and provenance/license review. | Yes |
| TD-SC-2 | The UI starts on loopback and connects to the accepted loopback server and graph ID without `LANGSMITH_API_KEY`; no `OPENAI_API_KEY` value or credential-bearing request is present in browser-visible configuration, storage, bundles, logs, or network traffic. | Listening-address inspection, browser configuration/storage/network audit, build-output search, and credential-redacted server correlation. | Yes |
| TD-SC-3 | A browser-submitted message visibly receives streamed events and a terminal assistant response; a second message remains in the same server thread, and creating a new chat produces a different thread without inherited prior messages. | Browser automation or recorded inspection plus matching server thread/run identifiers and message-state evidence. | Yes |
| TD-SC-4 | The README's clean-checkout commands start the accepted server and UI in two terminals, generated UI/runtime evidence is ignored, both processes terminate cleanly, and the repository finishes with no unexpected tracked or untracked output. | Documented-command execution, `git check-ignore` probes, process/listener cleanup, and final `git status --short`. | Yes |

# Incremental Value Delivery

| Slice | Value proven | Risk retired | Evidence | Stop / continue decision |
| --- | --- | --- | --- | --- |
| 1. Frozen local UI connection | The maintained UI installs reproducibly and connects to the accepted local graph without secrets or LangSmith. | Floating upstream code, client credential exposure, hidden account dependency, and accidental server changes. | `TD-SC-1` and `TD-SC-2` evidence. | Stop if the UI requires a client secret, a LangSmith account, a non-loopback service, or material upstream forking; return for contract revision. |
| 2. Browser workbench handoff | Streaming, existing-thread continuation, new-thread isolation, documented startup, and cleanup work from a clean checkout. | A UI that renders a single demo but cannot support real agent-development sessions reproducibly. | `TD-SC-3` and `TD-SC-4` evidence. | Present for review only when browser/server identities reconcile and both processes are cleanly stopped. |

# Review Boundary

| Boundary | In scope for review | Out of scope / follow-up | Approval impact |
| --- | --- | --- | --- |
| Upstream and dependency containment | Exact UI provenance, MIT attribution, frozen Node install, focused modifications, and required build checks | Alternative UIs, frontend framework changes, and upstream contribution strategy | blocking for floating source, missing attribution, unreproducible build, or material fork; alternatives are non-blocking |
| Local UI correctness | Loopback startup, server/graph configuration, streaming render, existing-thread continuation, new-thread isolation, and errors | Agent logic, server internals, advanced artifacts, custom styling, and assistant management | blocking for failure of the browser path; server implementation and polish are non-blocking here |
| Credential and network safety | No provider key in the client, no LangSmith key requirement, local request targets, ignored overrides/evidence, and process cleanup | Production authentication, remote access, managed secrets, and tracing governance | blocking for browser secret exposure, unintended remote transfer, or non-loopback exposure; production controls are non-blocking |
| Server-boundary preservation | Consumption of the accepted graph ID, URL, messages state, streaming, and thread contract without Python changes | Server refactors and new runtime configuration | blocking if UI work alters or duplicates server ownership; future server changes are non-blocking |
| Evidence quality | Frozen install/checks, browser-to-server correlation, documented commands, and clean final state | Additional browsers, visual regression suites, load tests, and CI | blocking for unrepeatable acceptance evidence; broader coverage is non-blocking |

# Validation / Evidence

| Criterion ID | Check | Evidence | Runner / owner | Required before done |
| --- | --- | --- | --- | --- |
| TD-SC-1 | Install from the frozen pnpm lock, run required UI checks, and inspect upstream provenance/license files. | Install/check/build output, resolved dependency audit, exact source record, and MIT attribution. | Repository maintainer | Yes |
| TD-SC-2 | Start the UI locally, connect to the accepted graph without LangSmith credentials, and inspect client configuration, bundles, storage, logs, network requests, and listeners. | Browser/tooling audit showing only loopback API traffic and no provider or LangSmith credential. | Repository maintainer | Yes |
| TD-SC-3 | Submit two messages in one chat, create a new chat, and reconcile rendered behavior with server thread/run/message records. | Browser capture or automation output plus matching distinct server identifiers and state. | Repository maintainer and credential holder | Yes |
| TD-SC-4 | Follow the clean-checkout README workflow, verify ignored output, terminate services, inspect listeners, and inspect Git status. | Command transcript, ignore evidence, no residual listeners, and clean final status. | Repository maintainer | Yes |

# Execution Notes

- Calibration: `TD1 Standard`; this is a focused Node/browser client integration with an external local API dependency and credential-safety review.
- Route: `BLOCKED`; do not begin UI implementation until the exact resume condition in Task Control is observed. After resumption and all four readiness gates pass, the intended route is `DIRECT` if the accepted server contract remains unchanged.
- Do not create the UI implementation worktree while this task is blocked. After resumption, execute in `/Users/jasonbelmonti/Documents/Development/deepagents-lab/.worktrees/agent-chat-ui` on branch `codex/agent-chat-ui` created from the accepted Agent Server commit.
- At resumption, read this complete task and `docs/tasks/add-local-agent-server.md`, verify the server task's accepted required evidence, and confirm its URL, graph ID, messages state, streaming, and thread contract. Stop and revise this task if any required value is absent or incompatible.
- Keep the UI in a focused directory such as `apps/agent-chat-ui/`; record its exact upstream commit or scaffold package version, preserve MIT attribution, and commit the pnpm lock.
- Configure only public localhost identifiers in tracked files. Keep provider and LangSmith credentials out of UI environment files and all `NEXT_PUBLIC_*` values.
- Preserve upstream UI structure and behavior. Avoid unrelated component refactors, design changes, analytics, and production proxy/authentication code.
- Bind to loopback, disable public sharing/tunnels, and shut down UI and server processes after validation.
- Limit live provider use to the browser interaction required by `TD-SC-3`; consume the predecessor's agent unchanged and do not interpret the interaction as evaluation evidence.
- Do not modify Python packages, agent construction, `langgraph.json`, or the stable graph ID under this task.

### Execution Checkpoint

| Execution status | Current proving slice | Evidence admitted | Next action | Blockers / stop condition |
| --- | --- | --- | --- | --- |
| blocked | Await the accepted Agent Server contract before beginning the TD-SC-1 and TD-SC-2 proving slice. | None admitted. | Check whether the Task Control resume condition has been observed; if it has, reload both task contracts and the accepted repository baseline, then rerun all four readiness gates before creating the UI worktree. | The predecessor implementation is not yet independently accepted on the UI baseline with its concrete URL, graph ID, messages state, streaming contract, and thread semantics documented. |

# Follow-up / Non-blocking Work

- Add named model, middleware, subagent, or experiment-variant selection after the default graph path is stable.
- Prove safe tool-call, interrupt, and artifact rendering with deterministic fixtures in separate tasks.
- Add custom styling, generative UI, or lab-specific result comparison only for a concrete experiment need.
- Add LangSmith tracing or Studio only through an explicit opt-in task with approved data and credential policy.
- Add production hosting, authentication, persistence, analytics, and multi-user operation only through a separate production contract.
