---
type: TaskDefinition
title: Enable a Minimal Live DeepAgents Invocation
task_id: enable-live-deepagents-invocation
artifact_version: "3.0"
revision: "3"
created_at: "2026-08-23T09:10:39-05:00"
updated_at: "2026-08-23T09:21:12-05:00"
validation_profile: skills/task-definition/profiles/task-definition.yaml
---

# Task Control

| Contract state | Execution route | State rationale |
| --- | --- | --- |
| READY | DIRECT | The user selected the OpenAI API route, the installed DeepAgents interface and current provider guidance identify the required integration, and this bounded smoke path needs no further design artifact. |

# Objective

Provide the smallest repository-owned command that constructs DeepAgents with a real OpenAI model, submits one prompt, and prints the final response using an externally supplied `OPENAI_API_KEY`.

# Context / Constraints

- DeepAgents `0.7.8` is already locked and accepts an `openai:<model>` string; the OpenAI LangChain integration is not installed.
- The user has selected API-key authentication over the previously considered Codex CLI adapter.
- Credentials must enter through the process environment and must never be committed or printed.
- The default model is `openai:gpt-5.4`, matching current DeepAgents guidance, and must be overridable without code changes.
- This slice proves direct model invocation only. It does not establish the evaluation baseline or exercise agent tools, middleware, subagents, tracing, or sandboxing.

# Source Authority

| Source | Authority | Status | Task implication |
| --- | --- | --- | --- |
| User instruction dated 2026-08-23 | Controlling request | Active | Use the OpenAI API key and make the minimum changes needed for a live DeepAgents invocation. |
| `/Users/jasonbelmonti/Documents/Development/deepagents-lab/docs/design/deepagents-lab-design-process.md` | Repository design authority | Checksum verified | Preserve local source authority, explicit model configuration, secret hygiene, and the comparative R0 boundary. |
| Installed `deepagents==0.7.8` API and current DeepAgents model documentation | Integration authority | Inspected | Pass a provider-qualified OpenAI model string to `create_deep_agent` and install the provider integration. |
| Current repository state at commit `950a55b` | Implementation baseline | Inspected | Extend the bootstrap without introducing evaluator or experiment abstractions. |

# Task Scope

| Scope item | Classification | Approval impact | Notes |
| --- | --- | --- | --- |
| Add and lock the OpenAI LangChain model integration | In scope | blocking | Preserve all existing exact R0 dependency pins. |
| Add one importable live-invocation function and executable command | In scope | blocking | Accept prompt and model inputs, fail clearly without `OPENAI_API_KEY`, invoke DeepAgents, and print only the final model text. |
| Add credential-safe configuration documentation | In scope | blocking | Provide `.env.example` values and shell-export instructions; do not auto-load or persist secrets. |
| Add network-free tests for configuration, construction, invocation, and output behavior | In scope | blocking | Patch the DeepAgents construction boundary rather than calling the provider in the ordinary test suite. |
| Record one opt-in real-model smoke result | In scope | blocking | Run only when `OPENAI_API_KEY` is available in the shell; use a minimal exact-response prompt. |
| Implement eval cases, Inspect or LangSmith adapters, tracing, tools, middleware, subagents, or sandbox behavior | Out of scope | non-blocking | These remain later comparative R0 work. |
| Store credentials, request payloads, responses, or traces | Out of scope | blocking if introduced | The command is ephemeral and stdout-only. |

# Materially Verifiable Success Criteria

| ID | Criterion | Proof | Required before done |
| --- | --- | --- | --- |
| TD-SC-1 | A frozen environment installs the OpenAI integration while retaining `deepagents==0.7.8`, `inspect-ai==0.3.260`, and `langsmith==0.11.1`, and all repository tests pass without credentials or network calls. | `uv lock --check`, installed-version inspection, and `uv run --frozen --all-groups pytest -q` all succeed. | Yes |
| TD-SC-2 | The executable command accepts a prompt, defaults to `openai:gpt-5.4`, permits an explicit model override, constructs DeepAgents, and emits the final assistant text; a missing API key fails before agent construction with an actionable message. | Focused tests patch the construction boundary and assert arguments, output, and missing-key behavior. | Yes |
| TD-SC-3 | With `OPENAI_API_KEY` supplied through the environment, the documented smoke command completes a real DeepAgents invocation and prints the requested sentinel response. | Captured exit code and redacted command output from the opt-in live smoke. | Yes |
| TD-SC-4 | Repository documentation permits setup without copying a secret into a tracked file, and Git ignores local `.env` variants while retaining `.env.example`. | README and `.env.example` review plus `git check-ignore` and tracked-file inspection. | Yes |

# Incremental Value Delivery

| Slice | Value proven | Risk retired | Evidence | Stop / continue decision |
| --- | --- | --- | --- | --- |
| 1. Offline executable seam | The repository can construct and drive the intended DeepAgents boundary without spending tokens. | Provider-package omission, ambiguous configuration, and accidental network calls in tests. | `TD-SC-1`, `TD-SC-2`, and `TD-SC-4` evidence. | Stop if integration requires evaluator scaffolding or secret persistence; otherwise continue to the opt-in smoke. |
| 2. Live model proof | The same command reaches a real OpenAI model through DeepAgents. | A locally plausible but operationally invalid invocation path. | `TD-SC-3` evidence. | Stop after one successful sentinel response; evaluation coverage belongs to a later task. |

# Review Boundary

| Boundary | In scope for review | Out of scope / follow-up | Approval impact |
| --- | --- | --- | --- |
| Invocation correctness | Model selection, DeepAgents input shape, final-output extraction, error propagation, and live smoke evidence | Streaming, retries, conversations, structured output, and tool execution | blocking inside the stated path; enhancements are non-blocking |
| Dependency containment | Provider integration, lock consistency, and preservation of existing pins | Provider abstraction and additional providers | blocking for lock or pin regressions; broader portability is non-blocking |
| Credential safety | Environment-only key use, redacted evidence, ignore behavior, and no secret logging | Vaults, CI secrets, key rotation, or managed secret services | blocking for secret exposure; operational secret management is non-blocking |
| R0 containment | No evaluator, trace, middleware, tool, subagent, or sandbox framework is introduced | Comparative R0 implementation | blocking if speculative R0 architecture enters this change; later experiments are non-blocking |

# Validation / Evidence

| Criterion ID | Check | Evidence | Runner / owner | Required before done |
| --- | --- | --- | --- | --- |
| TD-SC-1 | Verify the frozen lock, exact baseline packages, provider integration import, and test suite. | Successful lock, version, import, and pytest output. | Repository maintainer | Yes |
| TD-SC-2 | Exercise default/override construction, invocation/output, and missing-key paths without a provider call. | Focused pytest assertions and successful command help output. | Repository maintainer | Yes |
| TD-SC-3 | Export the API key and run the documented exact-response smoke command once. | Successful process exit and sentinel output with credential and metadata redacted. | Credential holder | Yes |
| TD-SC-4 | Inspect instructions and example configuration, then verify ignore/tracking behavior. | Documentation review, `git check-ignore -v .env`, and `git ls-files .env.example`. | Repository maintainer | Yes |

# Execution Notes

- Calibration: `TD0 Compact`; this is one reversible provider-backed smoke seam.
- Route: `DIRECT`; implement in `/Users/jasonbelmonti/Documents/Development/deepagents-lab/.worktrees/live-model-invocation` on branch `codex/live-model-invocation`.
- Use the current DeepAgents public `create_deep_agent` boundary. Do not add a provider abstraction until a second provider or experiment requires one.
- Keep the ordinary test suite offline. The live proof is a separate explicit command because it incurs provider usage.
- Never include the API key, its prefix/suffix, request headers, or environment dumps in test or handoff evidence.

### Execution Checkpoint

| Execution status | Current proving slice | Evidence admitted | Next action | Blockers / stop condition |
| --- | --- | --- | --- | --- |
| review-ready | The live invocation slice is proven through TD-SC-3; all required criteria have evidence. | TD-SC-1: the frozen lock retains the three exact baseline versions, resolves `langchain-openai==1.6.0`, and seven offline tests pass. TD-SC-2: the default model constructs a `CompiledStateGraph`; focused tests prove default, environment, and explicit model selection, invocation input, final text, and pre-construction credential failure. TD-SC-3: one credentialed `openai:gpt-5.4` invocation exited 0 in 6.7 seconds and printed exactly `DEEPAGENTS_LIVE_OK`. TD-SC-4: documentation and `.env.example` contain no credential, `.env` is ignored, and tracked-file inspection includes only `.env.example`. | Present the committed bounded change and validation evidence for review. | Stop condition satisfied after one successful sentinel response; do not make another provider call under this task. |

# Follow-up / Non-blocking Work

- Turn the proven invocation into the first versioned evaluation case during the comparative R0.
- Add trace capture, deterministic scoring, middleware variants, subagent cases, budgets, retries, and sandbox execution only under later bounded tasks.
