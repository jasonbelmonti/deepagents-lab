# DeepAgents Lab Design Process Packet

## Document Control

| Field | Value |
| --- | --- |
| Title | DeepAgents OSS Experiment Lab and Evaluation Baseline |
| Status | Ready for R0 Experiment |
| Packet owner | Repository maintainer |
| Reviewers | Codex remediation review complete; maintainer review pending |
| Decision owner | Repository maintainer |
| Downstream target | `R0 experiment`, then `design-spec` if the gates pass |
| Expected downstream rigor | `R1` |
| Last updated | 2026-08-26 |
| Related docs | Validation and checksum sidecars named in Section 12 |
| Related tickets | None provided |

## 0. Design Mission Summary

Decision requested:

Select the organizing architecture and initial open-source evaluation foundation for a Python laboratory used to compare DeepAgents techniques, patterns, middleware, backends, context strategies, and subagent configurations.

Problem summary:

At kickoff on 2026-08-22, the target directory had no repository, dependency policy, experiment contract, case corpus, scoring model, or durable result format. Repository initialization, locked dependencies, and live-model smoke coverage now exist, but the comparative evaluation runner, R0 cases, scoring contract, and durable result format remain unimplemented. Ad hoc examples can demonstrate behavior but do not establish whether a technique improves task completion, trajectory quality, safety, latency, or cost relative to a controlled baseline.

Selected direction:

Run a comparative R0 around a provisional local-first direction. Keep small lab-owned contracts for agent variants, evaluation cases, run records, and scores. Implement the first local runner adapter with open-source Inspect AI `0.3.260`, but separate its execution into a trusted in-process `agent_bridge()` lane and a containerized `sandbox_agent_bridge()` lane. The in-process lane is not a security boundary and may not expose shell or host-filesystem capabilities. The containerized lane runs DeepAgents itself inside the sample sandbox for privileged cases. Use Inspect-owned generation configuration for the canonical comparison lane and record the effective configuration. Evaluate released DeepAgents `0.7.8` by default while preserving an exact local-checkout path. Run the same tool and subagent cases through a LangSmith trace-evaluation control before final runner selection. Deterministic outcome and artifact checks remain primary; trajectory constraints apply where behavior is part of the claim; model-judge scoring is versioned and used only where code cannot determine success.

Top risks or unknowns:

- `RISK-1`: Inspect's documented LangChain agent bridge has not yet been proven to capture a DeepAgents parent run, delegated subagent generations, tool calls, usage, and final state without semantic loss.
- `RISK-2`: DeepAgents and Inspect are both pre-1.0 and released frequently; uncontained dependency coupling would make experiments expensive to maintain.
- `RISK-3`: LLM-judged scores can drift and create cost or false precision if they become the baseline's only signal.
- `RISK-4`: Filesystem, shell, memory, and trace experiments can leak secrets or modify the host if isolation and retention defaults are weak.
- `RISK-7`: Inspect can silently apply provider or Inspect defaults instead of agent-requested generation parameters unless configuration authority is explicit and the effective settings are captured.
- `RISK-8`: Inspect and LangSmith are within the trade-study indifference band; selecting either without a same-case control would convert a sourcing preference into an unsupported technical conclusion.

Readiness statement:

Ready for a bounded comparative R0 experiment. It is not ready for `design-spec` until bridge capture, generation authority, trace normalization, execution-lane isolation, dependency compatibility, and the Inspect-versus-LangSmith control gate in Section 11 pass.

Section status: Complete

## 1. Problem Frame and Decision Needed

Problem declaration:

DeepAgents behavior is shaped by models, prompts, tools, middleware order, backends, filesystem state, context compression, delegation, and runtime limits. Without a controlled experiment boundary, a change in any one of those inputs can be mistaken for an improvement in the technique under study. Without a reusable evaluation runner, each exploration also creates its own datasets, result formats, and judging assumptions.

Current-state baseline:

- The directory `/Users/jasonbelmonti/Documents/Development/deepagents-lab` contained no files on 2026-08-22.
- It was not a Git repository and therefore could not host the preferred in-repository `.worktrees/` workflow at kickoff.
- No local evaluation or testing capability existed to reuse.

Evidence or source:

Local filesystem and Git inspection recorded as `SRC-1`, plus the maintainer's stated need to explore DeepAgents patterns and begin with an agent-focused open-source evaluation baseline.

Decision trigger:

Choose a durable starting direction before repository scaffolding, examples, or baseline cases create accidental contracts and migration cost.

In scope:

- Python repository and dependency-management direction.
- Boundaries between DeepAgents variants, cases, execution, scoring, and artifacts.
- Open-source agent evaluation technology selection.
- A first baseline evaluation portfolio and comparison method.
- Local execution, optional CI execution, observability, safety, reproducibility, and upgrade/exit posture.
- Compatibility with released DeepAgents and an exact local source checkout.

Out of scope:

- Implementing the lab or its R0 in this packet.
- Selecting one production model provider or committing credentials or spend.
- Production deployment, online evaluation, end-user telemetry, or a multi-user service.
- Proving benchmark validity across every DeepAgents use case.
- Contributing changes upstream to DeepAgents or any evaluation framework.
- Production adoption or standing configuration of a commercial observability service. One bounded, sanitized LangSmith Developer-plan control is in scope for R0 because it is required to settle the sourcing decision.

Section status: Complete

## 2. Stakeholders, Concerns, and Viewpoints

| Stakeholder or role | Concern | Viewpoint required | Required action |
| --- | --- | --- | --- |
| Repository maintainer and experiment author | Fast creation of techniques without copying runner or scoring plumbing | Developer workflow and experiment authoring | Approve |
| DeepAgents OSS contributor | Reproduce behavior against a released package or exact local commit | Dependency provenance and source-checkout compatibility | Review |
| Evaluation author | Cases and scores express task success without overfitting one valid trajectory | Dataset, scoring, and statistical validity | Review |
| Reviewer of a technique | Compare variants with controlled inputs and inspect failure evidence | Results, traceability, and review ergonomics | Consult |
| Local operator or CI maintainer | Bound cost, concurrency, retries, artifacts, and failure recovery | Operations and automation | Review |
| Security and privacy reviewer | Prevent host mutation, secret capture, unsafe network access, and untrusted fixture execution | Trust boundaries and data lifecycle | Review |
| Future lab maintainer | Upgrade or replace the evaluation framework without rewriting every experiment | Modularity, lifecycle cost, and exit | Consult |
| LangChain/DeepAgents community reader | Run a documented experiment and understand the exact system under test | Reproducibility and portability | Inform |

Decision authority:

The repository maintainer owns the selection, risk acceptance, default model/judge policy, and any future external-service adoption.

Section status: Complete

## 3. Constraints, Invariants, and Assumptions

| ID | Type | Statement | Source or basis | Design impact |
| --- | --- | --- | --- | --- |
| CON-1 | Constraint | The lab and primary extension interfaces shall be Python. | User request and DeepAgents Python package | Excludes a Node-first runner as the baseline. |
| CON-2 | Constraint | DeepAgents is the system under test; the evaluator shall not require rewriting the technique as a native evaluator-framework agent. | Lab mission | Requires bring-your-own-agent execution. |
| CON-3 | Invariant | A comparison run shall record the exact DeepAgents source, model and effective generation settings exposed by the runner/provider, an explicit `provider_default` marker for any unreported value, configuration authority, agent variant, case revision, evaluator version, scorer/judge settings, limits, and repetition/epoch. | Reproducibility concern | Requires a run manifest, effective-configuration capture without fabricated defaults, and stable identifiers. |
| CON-4 | Invariant | Experiment modules shall not import evaluator-framework types. | Change-containment concern | Requires a lab contract and adapter boundary. |
| CON-5 | Invariant | Deterministic success evidence shall outrank model-judge opinion when the outcome can be checked in code. | Evaluation validity concern | Baseline cases need explicit artifacts, state, output, or tool invariants. |
| CON-6 | Invariant | Credentials, private prompts/data, provider payloads, and unredacted secrets shall not be committed. | Security concern | Requires environment-based secrets, sanitized fixtures, ignored artifacts, and safe logging defaults. |
| CON-7 | Invariant | A shell-, arbitrary-code-, or host-filesystem-capable agent shall execute only when the agent process and its privileged operations are inside a disposable, scoped environment with explicit resource and network policy. An in-process bridge plus a provisioned sandbox does not satisfy this invariant. | DeepAgents backend capabilities, Inspect bridge documentation, and host-safety concern | Trusted non-shell cases and privileged cases require distinct execution lanes; host shell is never a baseline default. |
| CON-8 | Invariant | Case definitions, deterministic scorers, and a minimum normalized result shall remain repository-owned and exportable; a managed service shall not be the sole authority for baseline meaning. | User preference for an open-source baseline and exit concern | A managed trace-eval system remains viable only with a local contract, export, and replacement path. |
| CON-9 | Invariant | Results from different model or judge identities/configurations shall not be merged into one comparable baseline series. | Model sensitivity | Comparison keys include execution and judge identities. |
| CON-10 | Invariant | A technique under test shall vary one declared experimental factor at a time unless the experiment explicitly declares a factorial design. | Causal interpretation | Variant manifests declare control and changed factors. |
| CON-11 | Invariant | Every runner lane shall declare exactly one generation-configuration authority. During comparative R0, CAND-4 uses Inspect-owned configuration with bridge forwarding disabled, while CAND-5's repository target receives the matched explicit configuration. Any Inspect technique that requires agent-owned parameters shall run in a separately named lane with `forward_generation_config=True` and a distinct comparison key. | Inspect bridge generation-config semantics and comparison fairness | Removes ambiguous parameter precedence without presupposing the final runner and prevents unlike effective configurations from sharing a baseline series. |
| CON-12 | Invariant | Agent behavior, DeepAgents state semantics, harness validity, and evaluator observability shall be recorded as separate outcomes. A missing evaluator event shall not be scored as an agent failure, and absence from an incomplete trace shall not be accepted as proof of context isolation. | Evaluation validity and comparative-runner fairness | Requires independent deterministic checks against canonical agent state plus a separate per-adapter trace-coverage result and failure taxonomy. |
| ASM-1 | Assumption | Python 3.12 and `uv` are acceptable defaults for the new repository. | Both selected packages support the interpreter; `uv` provides locking and ephemeral source overrides | Non-load-bearing; the design remains compatible with another lock-capable Python tool. |
| ASM-2 | Assumption | Docker is available where shell-execution scenarios run. | Inspect supplies a built-in Docker sandbox; local environment not yet checked | Load-bearing only for the shell baseline; routed to `VAL-4`. |
| ASM-3 | Assumption | The maintainer can provide at least one model-provider credential for R0. | Agent bridge smoke test needs real model traffic unless a compatible fake path is proven | Routed to `VAL-2`; no provider is selected here. |
| ASM-4 | Assumption | A 14-21-case seed suite—two or three cases for each of seven initial behavior categories—is affordable to curate and review. | Internal planning estimate for a small lab; this is not a statistical-validity claim | R0 uses only plumbing cases. `VAL-6` must establish coverage, repetitions, and an inconclusive rule before the seed suite is called baseline `v1`. |
| Q-1 | Question | Which execution model and judge model/configuration become the first canonical comparison lane? Owner: repository maintainer. | No provider or budget supplied | Must be decided before publishing baseline numbers; architecture remains provider-neutral. |
| Q-2 | Question | Which CI provider, spend ceiling, and secret policy will run non-local evaluations? Owner: repository maintainer. | No CI context supplied | May remain deferred until after local R0. |
| Q-3 | Question | Should the lab default to released DeepAgents only, or also maintain a named upstream-checkout lane? Owner: repository maintainer. | OSS contribution workflow suggests both | R0 shall prove an explicit local-checkout override; policy can be finalized in `design-spec`. |

Section status: Complete

## 4. Design Space Decomposition

| ID | Decision surface | Why it matters | Variable or fixed | Related constraints |
| --- | --- | --- | --- | --- |
| SURF-1 | Repository and environment | Locking, Python compatibility, task commands, and source overrides determine reproducibility | Variable | CON-1, CON-3, ASM-1 |
| SURF-2 | Experiment authoring contract | Determines whether a new middleware or pattern requires runner-specific code | Variable | CON-2, CON-4, CON-10 |
| SURF-3 | Agent construction boundary | Released packages and local checkouts need the same factory surface | Variable | CON-2, CON-3, Q-3 |
| SURF-4 | Evaluation runner and orchestration | Controls datasets, repetitions, limits, retries, resumption, and output | Variable | CON-3, CON-8 |
| SURF-5 | Case and fixture model | Controls scenario readability, workspace setup, expected results, and future corpus growth | Variable | CON-3, CON-5, ASM-4 |
| SURF-6 | Scoring composition | Agent success needs outcome, trajectory, policy, performance, and sometimes judge evidence without conflating subject behavior with evaluator coverage | Variable | CON-5, CON-9, CON-12 |
| SURF-7 | State and execution isolation | DeepAgents can use memory, filesystems, shell, and subagents; evaluator provisioning is not proof that the agent process is contained | Variable: trusted in-process and containerized-agent lanes are distinct | CON-6, CON-7, ASM-2 |
| SURF-8 | Models, judges, credentials, and configuration authority | Model identity, effective settings, parameter precedence, and credentials materially alter results and cost | Variable with a fixed canonical authority policy | CON-3, CON-6, CON-9, CON-11, Q-1 |
| SURF-9 | Result provenance and analysis | A score without its trace, run manifest, or case revision cannot support a contribution claim | Variable | CON-3, CON-9 |
| SURF-10 | Change containment | Both core dependencies are fast-moving pre-1.0 packages | Variable | CON-4, Q-3 |
| SURF-11 | CI and operating controls | Provider failures, concurrency, cost caps, and interrupted runs affect trust and usability | Variable | CON-3, Q-2 |
| SURF-12 | Managed trace evaluation and observability | LangSmith can evaluate full offline traces and online runs/threads, but changes account, retention, cost, and data boundaries | Variable; compare as a first-class candidate and retain an extension seam | CON-6, CON-8 |
| SURF-13 | User interface | A dedicated lab web application does not improve the first design decision | Fixed: use CLI and evaluator-provided result viewer | Scope boundary |

Surface coupling notes:

- `SURF-2`, `SURF-4`, `SURF-6`, and `SURF-10` are tightly coupled. Direct evaluator imports in experiment modules improve day-one speed but make framework exit a repository-wide migration.
- `SURF-3`, `SURF-8`, and `SURF-9` form the reproducibility chain: the exact agent source and model configuration must be present in the same run record as scores and traces.
- `SURF-5`, `SURF-6`, and `SURF-7` determine validity. A filesystem task is only meaningful if each sample gets a known initial workspace and deterministic post-run checks. For a subagent case, canonical state proves agent and shared-artifact behavior while the candidate trace separately proves that it observed the hidden child execution.
- `SURF-7` and `SURF-11` share resource and safety controls; high concurrency must not multiply unbounded sandboxes or model spend.
- `SURF-7`, `SURF-8`, and `SURF-12` distinguish evaluation from execution: a trace or sandbox product may observe or host a run, but the packet must name exactly where the agent process, tools, model proxy, credentials, and network boundary reside.

Technology sourcing applicability: Applicable

Applicability rationale:

The lab could adopt an open-source runner, use a managed evaluation platform, combine libraries with pytest, or build its own harness. Those choices materially change agent integration, result provenance, sandboxing, lifecycle cost, and exit posture. At kickoff no repository-local evaluation capability existed. The initialized repository now supplies locked dependencies and live-model smoke coverage, but no comparative evaluation runner or reusable case/scoring baseline exists to reuse.

Research cutoff date: 2026-08-22 for candidate selection and time-sensitive sourcing inputs; targeted DeepAgents subagent-semantics refresh observed 2026-08-26.

Section status: Complete

## 5. Option Families

| ID | Evidence type | Candidate or claim | Source or reference | Version or observed date | Confidence or limitation |
| --- | --- | --- | --- | --- | --- |
| SRC-1 | Local observation | Target directory was empty and not a Git repository; no internal lab or eval capability existed | Local `find`, `ls`, and `git status` inspection | 2026-08-22 | High confidence for the inspected path only |
| SRC-2 | Maintainer documentation | DeepAgents is a LangGraph-based agent harness with planning, context management, filesystem backends, shell execution in sandbox backends, subagents, memory, permissions, streaming, and durable execution | [Deep Agents overview](https://docs.langchain.com/oss/python/deepagents/overview) and [backends](https://docs.langchain.com/oss/python/deepagents/backends) | Observed 2026-08-22 | Primary maintainer documentation; capabilities still require lab-level verification |
| SRC-3 | Package registry | DeepAgents latest release is `0.7.8`, MIT, Python `>=3.11,<4.0`; package metadata depends on LangChain/LangGraph ecosystem components | [PyPI JSON](https://pypi.org/pypi/deepagents/json) and [license](https://github.com/langchain-ai/deepagents/blob/main/LICENSE) | `0.7.8`, uploaded 2026-08-20; observed 2026-08-22 | Time-sensitive; exact dependency resolution belongs in the lockfile |
| SRC-4 | Maintainer documentation | Inspect has two materially different bridges: `agent_bridge()` runs a Python agent in the Inspect process, while `sandbox_agent_bridge()` invokes an agent installed inside a sandbox through `sandbox().exec()` and proxies supported model APIs back to Inspect. The in-process bridge retains host filesystem/network access and is not a security boundary. Both bridges default to Inspect/provider generation configuration and drop listed client generation parameters unless `forward_generation_config=True`; all model calls are captured, but complete DeepAgents tool/subagent semantics are not promised. | [Inspect Agent Bridge](https://inspect.aisi.org.uk/agent-bridge.html) | Observed 2026-08-22 | Primary documentation resolves execution and configuration semantics; DeepAgents-specific trace completeness still requires `VAL-2`. |
| SRC-5 | Package registry and source | Inspect AI is an MIT-licensed Python evaluation framework; latest release is `0.3.260` for Python `>=3.10` | [PyPI JSON](https://pypi.org/pypi/inspect-ai/json) and [source repository](https://github.com/UKGovernmentBEIS/inspect_ai) | `0.3.260`, uploaded 2026-08-21; observed 2026-08-22 | Beta/pre-1.0 and high release cadence increase upgrade cost |
| SRC-6 | Maintainer documentation | Inspect provides first-class tasks, solvers, scorers, tools, re-scoring, model grading, result logs, limits, and packaging extension points | [Components](https://inspect.aisi.org.uk/extensions-components.html), [scoring](https://inspect.aisi.org.uk/scoring.html), and [running evals](https://inspect.aisi.org.uk/running.html) | Observed 2026-08-22 | Maintainer claims; lab-specific scorer ergonomics require implementation evidence |
| SRC-7 | Maintainer documentation | Inspect eval sets support retries, resumption, completed-work reuse, multiple epochs, standalone log bundles, and local model-output caching | [Eval Sets](https://inspect.aisi.org.uk/eval-sets.html) and [Caching](https://inspect.aisi.org.uk/caching.html) | Observed 2026-08-22 | Cache policy can conceal provider changes if provenance is incomplete |
| SRC-8 | Maintainer documentation | Inspect supplies per-sample sandboxes, built-in Docker integration, concurrency and resource limits, cleanup, and network controls. Provisioning a sandbox does not move an agent, tool, or scorer into it; only work invoked through `sandbox()` executes there. Custom Compose replaces the generated `network_mode: none`, so egress denial must be restated explicitly. | [Sandboxing](https://inspect.aisi.org.uk/sandboxing.html) | Observed 2026-08-22 | Docker availability and a container-installed DeepAgents process through `sandbox_agent_bridge()` remain unproven locally. |
| SRC-9 | Maintainer documentation and registry | DeepEval is Apache-2.0, local-capable, and provides agentic task-completion, step-efficiency, plan, and tool-correctness metrics plus a pytest-oriented CLI | [Introduction](https://deepeval.com/docs/introduction), [agentic metrics](https://deepeval.com/docs/metrics-introduction), [PyPI JSON](https://pypi.org/pypi/deepeval/json), and [license](https://github.com/confident-ai/deepeval/blob/main/LICENSE.md) | `4.1.10`, uploaded 2026-08-21; observed 2026-08-22 | Full-trajectory metrics require DeepEval tracing; no direct DeepAgents integration evidence found |
| SRC-10 | Maintainer documentation and registry | OpenEvals is an MIT evaluator library with exact/semantic scoring, agent trajectory match and judge prompts, multi-turn simulation, pytest examples, and optional LangSmith logging | [OpenEvals repository](https://github.com/langchain-ai/openevals) and [PyPI](https://pypi.org/project/openevals/) | `0.2.0`, released 2026-04-07; observed 2026-08-22 | It supplies evaluators rather than a complete sandboxed experiment runner |
| SRC-11 | Vendor documentation | LangSmith offline experiments capture outputs, evaluator scores, and execution traces with child LLM/tool runs; online evaluators score production runs or whole threads; trajectory evaluators assess agent tool use and decision paths | [Evaluation concepts](https://docs.langchain.com/langsmith/evaluation-concepts), [manage evaluators](https://docs.langchain.com/langsmith/evaluators), and [complex agent evaluation](https://docs.langchain.com/langsmith/evaluate-complex-agent) | Observed 2026-08-22 | Strongest ecosystem-native trace-eval evidence; service data/retention and non-OSS control plane remain material tradeoffs |
| SRC-12 | Doctrine source | A new external component requires provenance, maintenance ownership, update posture, vulnerability response, and replacement planning | [NIST SSDF 1.1](https://www.nist.gov/publications/secure-software-development-framework-ssdf-version-11-recommendations-mitigating-risk) | Observed 2026-08-22 | Design lens, not product evidence |
| SRC-13 | Vendor pricing and hosting documentation | LangSmith Developer is listed at $0/seat with 5,000 base traces/month, Plus at $39/seat with 10,000, and Enterprise custom; base traces retain data for 14 days, extended traces for 400 days; self-hosted observability/evaluation is an Enterprise add-on | [LangSmith pricing](https://www.langchain.com/pricing), [retention and billing](https://docs.langchain.com/langsmith/administration-overview), and [self-hosted LangSmith](https://docs.langchain.com/langsmith/self-hosted) | Observed 2026-08-22 | Pricing, allowances, retention, and plans are time-sensitive; self-hosting is not an open-source local fallback |
| SRC-14 | Maintainer and vendor documentation | DeepAgents documents a direct `LangSmithSandbox` backend, and LangSmith offers programmatic isolated environments, snapshots, resource sizing, command/file APIs, and credential proxying. LangSmith Sandboxes are in private preview. | [DeepAgents sandboxes](https://docs.langchain.com/oss/python/deepagents/sandboxes), [LangSmith Sandboxes](https://docs.langchain.com/langsmith/sandboxes), and [Sandbox SDK](https://docs.langchain.com/langsmith/sandbox-sdk) | Observed 2026-08-22 | Strong direct integration evidence, but preview access, API stability, managed execution cost, and evaluation coupling are unproven for this lab. |
| SRC-15 | Vendor documentation | LangSmith traces can be queried through the SDK/API; bulk Parquet export is restricted to Plus or Enterprise, while dataset export supports common local formats. | [Query traces](https://docs.langchain.com/langsmith/export-traces), [bulk trace export](https://docs.langchain.com/langsmith/data-export), and [manage datasets](https://docs.langchain.com/langsmith/manage-datasets) | Observed 2026-08-22 | Per-run SDK export is available to test in R0; high-volume bulk exit has a plan dependency. |
| SRC-16 | Package registry | The LangSmith Python SDK latest release is `0.11.1`, requires Python `>=3.10`, and its project metadata describes the SDK as MIT-licensed. | [PyPI JSON](https://pypi.org/pypi/langsmith/json) and [PyPI project](https://pypi.org/project/langsmith/) | `0.11.1`, uploaded 2026-08-19; observed 2026-08-22 | The SDK is open source, but the hosted control plane evaluated in CAND-5 is managed and plan-governed. |
| SRC-17 | Maintainer documentation and release source | DeepAgents subagents run in isolated message context and return one final report. In release `0.7.8`, `SubAgentMiddleware` removes parent `messages`, `todos`, and structured output from child input, installs the delegation description as the child's only human message, and adds only the final child result to the parent message history while forwarding non-private shared state such as files. `create_deep_agent` installs the same backend in the parent and dictionary-subagent filesystem middleware. | [Subagents documentation](https://docs.langchain.com/oss/python/deepagents/subagents), [`SubAgentMiddleware` at `deepagents==0.7.8`](https://github.com/langchain-ai/deepagents/blob/deepagents%3D%3D0.7.8/libs/deepagents/deepagents/middleware/subagents.py), and [`create_deep_agent` backend wiring at `deepagents==0.7.8`](https://github.com/langchain-ai/deepagents/blob/deepagents%3D%3D0.7.8/libs/deepagents/deepagents/graph.py) | Tag commit `1e261ba201bb1af4dbc5cbc8b6424e709b850ea8`; observed 2026-08-26 | Primary evidence for the pinned release's intended state boundary; model compliance and evaluator visibility remain empirical. A custom `CompiledSubAgent` is not covered by the shared-backend claim. |
| SRC-18 | Maintainer sample | The Deep Agents Deep Dive demonstrates a dictionary subagent writing an artifact to a shared backend, returning only a path receipt, and the supervisor reading that artifact while the child's intermediate tool calls stay outside the supervisor transcript. | [Deep Dive basics notebook](https://github.com/langchain-samples/deepagents-deep-dive/blob/6cc94f911d1b78a4b91c5ad5b83f0018643f0843/deepagents-basics.ipynb) | Commit `6cc94f911d1b78a4b91c5ad5b83f0018643f0843`; observed 2026-08-26 | Maintainer sample, not a normative evaluator contract. It allows `deepagents>=0.6.12`, targets Python 3.13, and exposes no repository license through GitHub; no implementation is copied into this lab. |

| ID | Option family | Sourcing class | Summary | Surfaces varied | Promoted to candidate? | Rationale |
| --- | --- | --- | --- | --- | --- | --- |
| OPT-1 | Ad hoc examples only | No change | Add standalone DeepAgents scripts and manually inspect outputs | SURF-2, SURF-4, SURF-6, SURF-9 | No | Conservative but cannot create a repeatable baseline or defensible comparisons. |
| OPT-2 | Existing internal lab platform | Internal reuse | Reuse an existing repository-local experiment/eval platform | SURF-1, SURF-4 | No | `SRC-1` found no existing capability in scope. No broader organizational platform was supplied. |
| OPT-3 | Pytest plus OpenEvals | Hybrid | Use JSONL/Python cases, pytest parametrization, a thin custom runner, and OpenEvals trajectory/judge functions | SURF-2, SURF-4, SURF-5, SURF-6, SURF-9 | Yes | Local, Python-native, low adoption cost; runner, logs, sandboxing, resumption, and analysis remain lab-owned. |
| OPT-4 | DeepEval | Open source | Adopt DeepEval datasets, test cases, tracing, agentic metrics, and `deepeval test run` | SURF-4, SURF-5, SURF-6, SURF-9 | Yes | Agent-specific scoring is strong; DeepAgents trace and sandbox integration are less directly evidenced. |
| OPT-5 | Inspect AI directly | Open source | Define each experiment as Inspect tasks/solvers/scorers and invoke DeepAgents through the agent bridge | SURF-2 through SURF-11 | Yes | Best complete-runner and agent-bridge fit; direct imports would spread framework coupling. |
| OPT-6 | LangSmith trace-eval baseline | Commercial or managed | Use repository-owned targets/evaluators with LangSmith datasets, offline experiments, full execution traces, trajectory evaluators, online run/thread evaluators, comparison UI, and optionally the preview DeepAgents `LangSmithSandbox` backend | SURF-4, SURF-6 through SURF-12 | Yes | DeepAgents ecosystem, trace, and sandbox fit are strong enough for full comparison; preview access, managed retention, price, export, and non-OSS control-plane posture remain material tradeoffs. |
| OPT-7 | Purpose-built eval platform | Custom build | Build datasets, orchestration, trace format, retries, scorers, viewer, and sandbox coordination in the lab | SURF-4 through SURF-11 | No | Maximum control but duplicates mature non-differentiating infrastructure and creates the highest lifecycle cost. |
| OPT-8 | Lab contract with Inspect adapter | Hybrid | Keep lab domain contracts stable; implement the first adapter with Inspect and expose native logs as linked evidence | SURF-2 through SURF-11 | Yes | Preserves Inspect capability while containing fast-moving dependency details and enabling an evidence-based exit. |
| OPT-9 | Integration experiment before specification | Hybrid | Prove bridge capture, state normalization, configuration authority, isolation, export, and locks with two small cases before formalizing repository mechanisms | SURF-3, SURF-4, SURF-7 through SURF-10, SURF-12 | No | This is the required convergence route for comparing `OPT-8` and `OPT-6`, not a production candidate. |

Section status: Complete

## 6. Candidate Elaboration

| ID | Source option | Mechanism | Boundaries and interfaces | Ownership and lifecycle cost | Rollback or exit posture | Load-bearing assumptions |
| --- | --- | --- | --- | --- | --- | --- |
| CAND-1 | OPT-3 | Pytest collects lab cases; a custom target invokes DeepAgents and normalizes LangGraph messages; OpenEvals supplies trajectory and judge functions | Lab owns case schema, runner, artifact schema, CLI, concurrency, sandbox coordination, and result comparison | Low initial dependency cost; medium-high continuing custom-runner and analysis cost | Remove OpenEvals and preserve custom deterministic scorers; all runner obligations remain local | Message normalization is sufficient; bespoke logs and isolation stay small enough to maintain |
| CAND-2 | OPT-4 | DeepEval test cases/datasets and tracing wrap DeepAgents; agentic metrics score task completion, plan/step behavior, and tool correctness | DeepEval types enter evaluation definitions unless a lab adapter is added; DeepAgents spans must map into its trace model | Medium integration and calibration cost; framework owns metrics/CLI; lab owns instrumentation and safe execution | Export local dataset files and scores, then replace metrics/runner; trace-specific tests require migration | DeepAgents parent/subagent/middleware activity can be captured completely and sandboxed without a documented bridge |
| CAND-3 | OPT-5 | Inspect tasks invoke a trusted DeepAgents variant inside `agent_bridge()`; Inspect datasets, limits, scorers, logs, eval sets, and cache drive runs | Experiments directly implement Inspect task/solver/scorer interfaces; the agent remains in the host process and no sandbox claim is made | Lowest initial runner work; medium recurring upgrade cost because Inspect types spread across the corpus | Pin/downgrade Inspect or rewrite every experiment when exiting | The LangChain bridge captures DeepAgents sufficiently; direct coupling stays tolerable; privileged scenarios remain excluded |
| CAND-4 | OPT-8 | Lab contracts define `AgentVariant`, `ExperimentCase`, `RunRecord`, and `ScoreRecord`. Lane A uses `agent_bridge()` only for trusted, non-shell cases. Lane B installs and invokes DeepAgents inside an Inspect sample container through `sandbox_agent_bridge()` and `sandbox().exec()`. Both lanes use Inspect-owned generation configuration by default. | Experiment modules depend only on lab contracts. Inspect types, bridge selection, effective-configuration capture, container image, proxy, and native-log behavior live under one adapter boundary. Agent factories isolate released/local DeepAgents source differences. | Modest adapter and container-image cost plus Inspect upgrades. The lab owns its schema, deterministic scorers, lane policy, and image definition; Inspect owns orchestration, native logs, retries, cache, limits, sandbox provisioning, and cleanup, but the adapter owns proof that execution actually crosses the boundary. | Freeze the lab result schema, retain JSON summaries/native-log references, and add a replacement adapter. Lane A can remain available if Lane B fails, but shell publication is prohibited. Exit is triggered by bridge failure, license/governance change, unmanageable churn, or a better runner clearing the same contract tests. | A small contract preserves needed semantics; each bridge works with DeepAgents; exposed effective settings or honest `provider_default` markers are capturable; Lane B contains the agent and privileged tools. `VAL-2`, `VAL-4`, and `VAL-9` test these claims. |
| CAND-5 | OPT-6 | LangSmith SDK runs repository-defined targets against datasets; native LangChain/LangGraph tracing records nested runs; offline code/judge/trajectory evaluators score experiments and online evaluators can later score traced runs or threads. Privileged cases may use DeepAgents' documented `LangSmithSandbox` backend if preview access is available; otherwise they remain out of this candidate's R0 control. | Agent factories, case meaning, deterministic evaluator code, effective model configuration, and normalized summaries stay local; trace storage, datasets, experiment comparison, feedback, UI, and optional sandbox resources are managed LangSmith resources. | Lowest likely DeepAgents trace-instrumentation cost; recurring trace/retention and optional seat/sandbox cost; self-hosting requires Enterprise and substantial services; preview sandbox churn adds adoption risk. | Export datasets, query each R0 trace through the SDK, retain normalized summaries and evaluator source, and switch the execution adapter. Bulk export is plan-dependent and expired base traces cannot be recovered. | Native tracing captures all required semantics; service data boundary and preview availability are acceptable; current allowances and retention meet lab volume; per-run exports are complete enough for exit. `VAL-9` tests these claims. |

Candidate notes:

### CAND-1 — Pytest plus OpenEvals

- Data and operations: cases live in versioned Python or JSONL; pytest parameters invoke variants; outputs and normalized messages are written as JSON artifacts.
- Verification: deterministic assertions are straightforward and OpenEvals can score exact/subset/superset trajectories or apply trajectory judge prompts.
- Expected failure: the lab gradually rebuilds run identity, resumption, usage accounting, concurrency controls, log browsing, and sandbox lifecycle. This creates an evaluation-platform project rather than a DeepAgents lab.

### CAND-2 — DeepEval

- Data and operations: local datasets and test cases feed `deepeval test run`; `@observe`/trace instrumentation supplies full-run agentic metrics.
- Verification: strong packaged agentic metrics reduce custom judge-prompt work and support deterministic tool correctness.
- Expected failure: DeepAgents middleware, subagent, and backend events require manual instrumentation that either misses semantics or couples agent code to the evaluator. The R0 effort would be larger than for an explicitly documented LangChain bridge.

### CAND-3 — Direct Inspect

- Data and operations: Inspect owns the dataset/sample lifecycle, model routing, logs, repetitions, limits, retries, and optional Docker environments.
- Verification: custom code scorers inspect final output and sandbox artifacts; model graders cover irreducibly semantic outcomes; logs enable transcript review and re-scoring.
- Expected failure: experiments accumulate Inspect state, task, solver, scorer, and registry conventions. A breaking release or exit requires repository-wide edits.

### CAND-4 — Lab contract with Inspect adapter

- Stable experiment inputs: variant identity, technique factor, agent factory, case input, seeded workspace/initial state, expected deterministic invariants, tags, and declared required capabilities.
- Stable run outputs: final response, normalized parent/subagent messages, tool events, selected state/artifact digests, scores, error/limit outcome, usage, duration, dependency/source provenance, and an opaque link to native Inspect evidence.
- Control flow: the adapter maps a case to an Inspect sample and selects a lane from declared capabilities. Lane A invokes a trusted DeepAgents factory in the Inspect process under `agent_bridge()`. Lane B builds or selects a pinned image containing DeepAgents and the lab entry point, starts `sandbox_agent_bridge()`, and invokes that entry point through `sandbox().exec()`. Both lanes normalize the result into a `RunRecord`, run deterministic scorers first, and emit Inspect-compatible scores. Optional model graders receive only the minimum sanitized evidence.
- Generation authority: the canonical lane leaves `forward_generation_config=False`; Inspect task/CLI model configuration and provider defaults govern generation. The manifest records authority=`inspect`, the resolved model identity, and every effective setting Inspect exposes. A separately named technique lane may set `forward_generation_config=True`; it records authority=`agent` and cannot share a comparison key with the canonical lane.
- State and security: Lane A is explicitly trusted and has host access; it receives no shell, arbitrary-code, host-filesystem, remote-MCP, or unbounded network capability. Lane B contains the DeepAgents process and its ordinary tools inside a disposable sample sandbox. Its image and Compose policy declare CPU, memory, time, filesystem, and `network_mode: none`; any provider-hosted or bridged capability is separately allowlisted. Provisioning a sandbox without invoking the agent through `sandbox().exec()` is a failed gate, not isolation evidence.
- Repository boundary direction: small modules separate contracts, DeepAgents factories, cases/fixtures, deterministic scorers, Inspect adapter code, and report/export code. Experiment directories declare a control and one or more variants but do not own runner plumbing.
- Source modes: the canonical lane uses the exact locked release. A contributor lane may overlay an exact local checkout without editing the committed lock; the run manifest must record the checkout path-independent Git commit, dirty state, and resolved package version.
- Seed-suite portfolio: begin with 14-21 reviewed cases spanning planning/decomposition, tool selection and arguments, filesystem context, subagent delegation/context isolation, middleware retry/limit behavior, permissions/safety, and long-context or summarization behavior. Each category begins with one nominal and one failure-path case with deterministic evidence. Do not label the suite baseline `v1` until `VAL-6` establishes repetitions, paired analysis, variance reporting, and the inconclusive rule.
- Expected failure: the lab contract grows into a lowest-common-denominator framework. Control this by keeping only comparison-critical fields stable, allowing adapter-specific evidence references, and adding a field only after two experiments need it.

### CAND-5 — LangSmith trace-eval baseline

- Data and operations: a repository target function runs each DeepAgents variant over a versioned dataset. Each experiment associates outputs and evaluator feedback with a trace containing intermediate child runs. The comparison UI groups scores, latency, tokens, model, tools, and metadata.
- Trace evaluation: offline evaluators receive the example and traced run, including intermediate steps. Online evaluators can later score a production run or a whole multi-turn thread. Trajectory templates and custom code/judge evaluators cover agent decisions and tool use.
- Verification: LangSmith's ecosystem-native trace tree is likely the lowest-friction diagnostic view for DeepAgents. Repository-owned deterministic evaluators can inspect run outputs/intermediate steps, while human review and judge feedback remain additional score lanes.
- Execution and security: local target execution remains the default control shape. If preview access is available, a separate privileged lane may use DeepAgents' documented `LangSmithSandbox` backend; that path must prove isolation, resource, egress, secret-proxy, cleanup, and cost behavior rather than inherit trust from the trace platform.
- Ownership and cost: the Developer plan may cover an early personal lab, but trace retention and evaluator feedback can upgrade storage/cost. High-volume bulk export requires Plus or Enterprise. Self-hosted evaluation is an Enterprise product with PostgreSQL, Redis, ClickHouse, queue, UI, and related services—not a lightweight OSS substitute.
- Expected failure: convenient managed traces become the only durable evidence, then expire or become costly; experiment meaning leaks into workspace-only evaluator/dataset state; preview sandbox access changes; contributors cannot reproduce results without accounts. `CON-8` requires local case/evaluator source, normalized exports, and a tested exit path if this candidate is selected.

Section status: Complete

## 7. Stress Scenarios and Failure Modes

| ID | Scenario | Stimulus and environment | Candidates tested | Expected response | Result |
| --- | --- | --- | --- | --- | --- |
| SCN-1 | Nominal controlled comparison | Run control and one middleware variant on the same small case set, effective model config, limits, and case revision | CAND-1 through CAND-5 | Produce separate run identities, comparable scores, traces, usage, declared changed factor, and configuration authority | All can execute the nominal case; CAND-4 best contains an OSS runner while CAND-5 provides the strongest documented native managed-trace comparison. Final choice remains inside the indifference band pending `VAL-9`. |
| SCN-2 | Filesystem artifact task | Each sample starts from a known workspace and must create or modify exact artifacts | CAND-1 through CAND-5 | Use per-sample state; score file content and digests deterministically; leave host unchanged | A provisioned Inspect sandbox is insufficient by itself. CAND-4 passes only through Lane B with the DeepAgents process invoked by `sandbox_agent_bridge()` plus `sandbox().exec()`. CAND-5 has a documented direct DeepAgents sandbox backend, but it is preview and requires access and policy proof. CAND-1 owns a separate sandbox integration. |
| SCN-3 | Isolated subagent with shared-artifact handoff | In `R0-SUB-1@1`, a parent delegates once to a dictionary subagent whose system prompt contains a sanitized child-only canary. The child reads a fixed state-backed input, writes a fixed-schema artifact to the shared backend, and returns only its path; the parent reads the artifact and returns the hidden value. | CAND-1 through CAND-5 | Deterministically verify artifact and final-answer correctness, required event partial order, absence of child-only context and internal child events from parent state, and presence of those hidden child events in the candidate trace. Record agent behavior, DeepAgents semantics, harness validity, and adapter coverage separately; permit irrelevant extra model/planning turns but not another delegation or a parent read of the source input. | `SRC-17` establishes the intended pinned-release semantics and `SRC-18` demonstrates the pattern. CAND-5 has the strongest ecosystem-native trace path; Inspect has the strongest OSS third-party bridge path. Both remain empirical until `R0-SUB-1` clears `VAL-2`/`VAL-9`; no candidate receives credit from mere event absence. |
| SCN-4 | Middleware fault and limit | Tool fails once; retry middleware may recover; a second case exceeds a call/message/time limit | CAND-1 through CAND-5 | Distinguish recovered failure, exhausted retry, and limit termination; never report silent success | LangSmith traces are diagnostically strong but target limits remain repository-owned. Inspect owns evaluation limits and errors, while CAND-4 must preserve normalized semantics across both execution lanes. |
| SCN-5 | Provider partial outage | Transient rate limit or timeout during a multi-case run | CAND-1 through CAND-5 | Bound retries and spend, retain completed work, mark incomplete/error samples, and resume without double-counting | Inspect candidates document eval-set retry/resumption; LangSmith records failures but target retry/resumption policy still requires proof |
| SCN-6 | Stochastic variance | Repeat a small case set across five epochs with fixed configuration | CAND-1 through CAND-5 | Keep per-epoch results, report aggregate and dispersion/pass-rate, and avoid treating one sample as a stable baseline | All feasible; Inspect supplies epochs/reducers, LangSmith supports repetitions/experiment comparison, and both need an explicit lab comparison policy |
| SCN-7 | Unsafe tool request | Fixture attempts host traversal, secret-file read, network egress, provider-hosted tool use, remote MCP access, or destructive shell action | CAND-1 through CAND-5 | Deny undeclared capability, record policy failure safely, expose no secret, and destroy sample state | CAND-4 Lane A is ineligible. Lane B must withhold provider-hosted capabilities, deny container egress, and prove the agent process is containerized. CAND-5 trace evaluation alone supplies no isolation; its preview sandbox path must independently pass the same policy tests. |
| SCN-8 | Judge drift or disagreement | Re-score stored outputs with a new judge version or rubric | CAND-1 through CAND-5 | Preserve original score, record new judge identity, permit re-scoring without re-running the agent, and keep deterministic score separate | Inspect supports re-scoring; LangSmith workspace evaluators and stored traces support trace feedback but retention/auto-upgrade cost is material |
| SCN-9 | Dependency/maintainer change | Inspect bridge changes, release regresses, or a selected provider's license/support/plan changes | CAND-1 through CAND-5 | Locked last-known-good lane continues; upgrade contract tests fail visibly; replacement does not rewrite experiment definitions | CAND-4 strongest local exit; CAND-5 requires export and service-exit proof; CAND-3 has broad coupling |
| SCN-10 | DeepAgents API change/local checkout | Run a released version and an exact dirty/clean local checkout with the same cases | CAND-1 through CAND-5 | Agent factory absorbs construction changes and manifest prevents cross-source comparisons | CAND-4 explicitly contains the boundary; CAND-5 likely traces either source naturally; both require provenance evidence |
| SCN-11 | Cost/concurrency pressure | Dataset or epochs grow while provider, trace, and sandbox quotas remain fixed | CAND-1 through CAND-5 | Enforce token/message/time/cost and concurrency bounds, emit usage, and allow targeted subsets | Inspect has local runner controls and container concurrency costs. LangSmith adds trace-retention and optional managed-sandbox spend; evaluator feedback can change retention class. Both require measured R0 usage. |
| SCN-12 | Rollback and evidence retention | A runner/adapter release fails or managed traces approach expiry after results exist | CAND-3, CAND-4, CAND-5 | Re-run with locked version or downgrade where possible; old summaries remain readable; native evidence remains linked/exported; no destructive migration | CAND-4 passes by design if export contract tests exist; CAND-3 depends on Inspect backward compatibility; CAND-5 requires proactive export before retention expiry |
| SCN-13 | Future managed observability | Maintainer later wants LangSmith trace comparison without replacing local truth | CAND-1 through CAND-5 | Add an optional sink; local cases/manifests/results remain authoritative | CAND-4's run-record seam supports this; CAND-5 supplies it natively but must prove export/local authority |
| SCN-14 | Generation-configuration conflict | Agent factory requests temperature, token, or reasoning settings that differ from the evaluator's model configuration | CAND-3, CAND-4 | One declared authority wins; the effective settings and dropped/forwarded behavior are observable; unlike lanes receive different comparison keys | CAND-4 resolves the canonical case with Inspect authority and forwarding disabled. `VAL-2` verifies effective settings. Agent-authoritative techniques require a distinct opt-in lane. CAND-3 has the same bridge semantics but spreads the policy across experiments. |
| SCN-15 | Inspect-versus-LangSmith trace audit | Execute the identical deterministic tool case and `R0-SUB-1@1` with the same DeepAgents source, model settings, fixture digest, limits, and repetitions | CAND-4, CAND-5 | Reconcile the fixed subagent partial order and coverage matrix, diagnose both successful and failed agent behavior without relabeling it as adapter failure, compare setup/diagnostic/export effort, and update only evidence-sensitive scores | Documentation predicts stronger native hierarchy in CAND-5 and stronger local-runner/exit posture in CAND-4. `VAL-9` is required because the current one-point weighted gap is not decision-significant. |

Section status: Complete

## 8. Trade Study

Evaluation horizon:

18 months. This is long enough to expose repeated pre-1.0 upgrades, new experiment categories, CI operation, scorer recalibration, and a credible framework-exit exercise, while acknowledging that agent evaluation technology changes too quickly for a five-year product forecast to be decision-useful.

TCO basis:

Relative engineering and service cost across initial integration, case authoring, scorer calibration, model/judge calls, local or managed sandbox compute, local/CI execution, result inspection, dependency/security upgrades, incident diagnosis, contributor training, migration, and exit. No license fee is assigned to open-source packages, but maintainer time and infrastructure are not treated as free. LangSmith inputs use the observed Developer, Plus, retention, sandbox, and export terms from `SRC-13` through `SRC-15`; they are not an 18-month guarantee.

Effort bands below are explicit analyst estimates to be replaced with R0 measurements: `S` is at most three maintainer-days, `M` is four to ten, and `L` is more than ten for the named activity over the evaluation horizon.

| Candidate | Initial integration | Recurring maintenance | Service or infrastructure exposure | Exit exercise | Dominant TCO risk |
| --- | --- | --- | --- | --- | --- |
| CAND-1 | M | L | Model calls plus a separately selected sandbox | S | A thin runner grows into an evaluation platform and consumes ongoing maintainer time |
| CAND-4 | M | M | Model calls, local Docker compute, image builds, and log storage | M | Two bridge lanes and a pinned agent image increase compatibility-test work |
| CAND-5 | S-M | S-M | Model calls, trace retention, optional seats/overages, and optional managed sandbox compute | M-L | Managed state becomes authoritative or plan/preview changes make export and replacement expensive |

Hard-constraint screen:

| Candidate | CON-2: run DeepAgents as the target | CON-4/CON-8: lab-owned boundary and local meaning | CON-7: privileged execution boundary | CON-3/CON-11: effective configuration authority | Eligibility |
| --- | --- | --- | --- | --- | --- |
| CAND-1 | Pass | Pass | Conditional on a separately implemented sandbox | Pass by locally owned runner policy | Eligible for non-shell comparison; shell track conditional |
| CAND-2 | Conditional on complete instrumentation | Fail as elaborated because evaluator tracing/types enter definitions without the required adapter | Conditional and not directly evidenced | Conditional | Screened out; would require a new adapter candidate |
| CAND-3 | Pass | Fail because Inspect types are intentionally spread through experiments | Fail for privileged cases because `agent_bridge()` is in-process | Pass only if every experiment repeats the bridge policy | Screened out by `CON-4`; aggregate scoring cannot rescue it |
| CAND-4 | Pass by design; verify in `VAL-2` | Pass by design; verify in `VAL-3` | Conditional on Lane B passing `VAL-4` | Pass by design; verify effective values in `VAL-2` | Eligible for comparative R0 |
| CAND-5 | Pass by documented ecosystem path; verify in `VAL-9` | Conditional on local source plus per-run export passing `VAL-9` | Conditional on preview access and sandbox policy proof; non-shell control remains eligible | Pass through repository target policy; verify in `VAL-9` | Eligible for comparative R0 |

`CAND-2` and `CAND-3` remain useful option evidence but are not ranked as selectable designs because they fail a current invariant. Their prior aggregate scores are removed.

| ID | Criterion | Priority | Source concern or constraint |
| --- | --- | --- | --- |
| CRIT-1 | DeepAgents integration and faithful parent/subagent/tool trajectory capture | High (weight 5) | CON-2, RISK-1, SURF-3 |
| CRIT-2 | Reproducible orchestration, durable evidence, retries/resumption, and re-scoring | High (weight 5) | CON-3, CON-8, SURF-9, SURF-11 |
| CRIT-3 | Actual execution containment, state isolation, capability policy, and resource controls | High (weight 5) | CON-7, SURF-7, RISK-4 |
| CRIT-4 | Deterministic, trajectory, custom, and model-judge scoring composition | High (weight 4) | CON-5, SURF-6 |
| CRIT-5 | Open-source/local-first posture, portability, and exit | Medium (weight 3) | User preference, CON-8, lifecycle concern |
| CRIT-6 | Change containment across evaluator and DeepAgents churn | High (weight 4) | CON-4, RISK-2, SURF-10 |
| CRIT-7 | Integration effort, maintenance TCO, and experiment-author ergonomics | Medium (weight 3) | Maintainer and future-maintainer concerns |
| CRIT-8 | Trace-diagnostic quality and optional online trace/thread evaluation | Medium (weight 2) | Reviewer workflow, SURF-12 |

Scoring scale: 1 = poor, 2 = weak, 3 = adequate with material cost or risk, 4 = strong, 5 = best fit. A hard-constraint failure cannot be rescued by an aggregate score. A difference of eight points or fewer—approximately 5% of the 155-point maximum—is an indifference band, not evidence of technical superiority.

| Candidate | CRIT-1 | Decisive strengths | Decisive weaknesses |
| --- | --- | --- | --- |
| CAND-1 | 3/5; analyst inference. `CRIT-3=2` is also inferred because the lab owns normalization and sandbox integration. | Small stack, Python/pytest familiarity, easy deterministic tests, and maximum local control | The lab builds orchestration, isolation, result, and analysis behavior; high maintenance exposure |
| CAND-4 | 4/5; Inspect documents capture of all model calls but not full DeepAgents tool/subagent semantics. `CRIT-3=3` because the correct sandbox-agent mechanism is documented but unproven with DeepAgents. | Complete open-source runner, local logs, strong orchestration, explicit two-lane containment, and a narrow exit boundary | Adapter/image work, less native DeepAgents trace structure than LangSmith, and two load-bearing R0 scores |
| CAND-5 | 5/5 from documented native child-run tracing. `CRIT-3=3` reflects a direct DeepAgents sandbox backend reduced by private-preview/access risk. | Best documented DeepAgents trace hierarchy, offline trace evaluation, online run/thread evaluation, comparison UI, and low initial friction | Managed control plane, retention and export plan boundaries, preview sandbox risk, and weaker local-first posture |

| Candidate | CRIT-1 | CRIT-2 | CRIT-3 | CRIT-4 | CRIT-5 | CRIT-6 | CRIT-7 | CRIT-8 | Weighted result |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| CAND-1 | 3 | 3 | 2 | 4 | 5 | 4 | 3 | 3 | 102/155 (65.8%) |
| CAND-2 | — | — | — | — | — | — | — | — | Not ranked: hard-screen failure |
| CAND-3 | — | — | — | — | — | — | — | — | Not ranked: hard-screen failure |
| CAND-4 | 4 | 5 | 3 | 4 | 5 | 5 | 3 | 4 | 128/155 (82.6%) |
| CAND-5 | 5 | 4 | 3 | 5 | 2 | 4 | 5 | 5 | 127/155 (81.9%) |

Decisive criteria:

- The hard screen eliminates direct framework coupling before scoring; `CON-4` is not a preference that a high feature score can offset.
- `CRIT-1` favors `CAND-5`; `CRIT-2`, `CRIT-5`, and `CRIT-6` favor `CAND-4`. `CRIT-3` is presently tied because both candidates have a documented mechanism with a different unresolved risk: integration proof for Inspect and preview/access proof for LangSmith.
- `CRIT-4` makes deterministic-first composition a lab policy independent of framework choice. Packaged judge metrics are useful but are not ground truth.
- The one-point `CAND-4` lead is inside the eight-point indifference band. It supports a provisional R0 starting point only; it does not support final selection.

R0 decision rule:

1. Both candidates run the identical tool case and `R0-SUB-1@1` with the same DeepAgents source, fixture digest, effective model settings, limits, and three plumbing repetitions.
2. Required parent, subagent, model, tool, retry/error, final-state, and usage events are reconciled against canonical agent state and a lab-owned, runner-neutral ledger that records event order, actor, and rendered parent/child model-request inputs before candidate-specific export. Agent behavior, DeepAgents semantics, harness validity, and adapter coverage receive separate statuses. An independently verified event missing or attributed to the wrong actor is a hard failure for the affected trace lane; an agent that takes a wrong action is an agent failure only when the trace represents that action faithfully. Absence from an incomplete trace never proves isolation.
3. The operator records setup time, adapter-specific code touched, time to identify one seeded failure, local artifact completeness, and teardown behavior. These observations update `CRIT-1`, `CRIT-2`, `CRIT-3`, and `CRIT-7`; documentation-only scores are not changed without evidence.
4. If both candidates pass and remain within the indifference band, the stated open-source/local-first preference breaks the tie in favor of `CAND-4`. If `CAND-4` fails a hard gate or `CAND-5` leads by more than eight points after evidence and the owner accepts its account/data/cost boundary, selection reopens in favor of `CAND-5`. A dual-runner design requires unique measured value; it may not win merely by accumulating both feature sets.

Sensitivity points:

- A one-level reduction in either `CAND-4` `CRIT-1` or `CRIT-3` removes five points and gives `CAND-5` the lead. Losing both makes `CAND-5` decisively superior under the current weights.
- If LangSmith preview sandbox access is unavailable, `CAND-5` loses one `CRIT-3` level; non-shell trace evaluation remains viable, but shell comparison moves outside its R0 scope.
- If the lab only runs black-box response checks and never shell, filesystem, subagent, or long-running tasks, `CAND-1` becomes preferable due to lower dependency surface.
- If the maintainer makes native DeepAgents trace diagnostics and online run/thread evaluation decisive rather than medium priority, `CAND-5` becomes the likely selection once its service boundary is accepted.
- If the open-source requirement changes from preference to hard constraint, `CAND-5` is screened out as the authoritative baseline while remaining an optional sink.
- If the adapter exceeds roughly four stable domain records or repeatedly hides required native capabilities, reopen `CON-4` and the candidate screen; do not silently switch to direct Inspect coupling or create a parallel framework.

Accepted tradeoffs:

- Accept a small adapter and contract-test burden to localize pre-1.0 evaluator churn.
- Accept Inspect's relatively large dependency footprint and a container image in exchange for orchestration, local logs, bridges, limits, and a local sandbox path.
- Accept that the first R0 and baseline require model-provider usage; do not pretend a seed makes LLM output deterministic.
- Accept that native Inspect logs remain adapter-specific evidence while normalized summaries support cross-run comparison and future migration.
- Accept the cost of one bounded LangSmith control run before final selection; its trace-evaluation capability and direct DeepAgents sandbox integration are decision-relevant evidence.

Section status: Complete

## 9. Source Doctrine Validation

| Doctrine lens | Applied check | Result | Follow-up |
| --- | --- | --- | --- |
| NASA systems design | Stakeholder needs were converted into constraints, then decomposed into experiment, runner, scoring, isolation, provenance, configuration, and lifecycle surfaces before selecting mechanisms | Pass | Revalidate after the comparative R0; do not let scaffold details silently redefine the mission |
| ISO 42010 architecture description | User, contributor, evaluator, operator, security, reviewer, and maintainer concerns have distinct viewpoints and decision authority | Pass | A future `design-spec` shall add concrete module, data-flow, trust-boundary, and deployment views |
| SEI ATAM | Modifiability, reproducibility, validity, safety, operability, cost, and ergonomics are expressed through scenarios, hard screening, an indifference band, arithmetic sensitivity points, and tradeoffs | Pass | Update only evidence-sensitive scores after `VAL-9`; preserve the selection rule |
| Parnas information hiding | The lab contract hides evaluator registry/log/bridge changes; the agent factory hides released-versus-checkout construction; experiments expose only comparison-relevant data | Pass | `VAL-3` shall reject an adapter that leaks Inspect types or becomes a generic framework |
| NIST SSDF and threat modeling | External components have provenance/version/owner/exit posture; Lane A is explicitly trusted; Lane B contains the agent process; provider-hosted tools, network egress, secret capture, unsafe tools, dependency churn, and vulnerability response are explicit | Risk bounded by R0 | Complete `VAL-4`; add automated dependency updates and a documented log-retention/redaction policy in `design-spec` |
| SRE and Well-Architected operations | User-relevant signals, limits, retries, resumption, error states, usage, artifacts, configuration authority, isolation, rollback, lifecycle cost, and managed-service exit are considered | Pass for R0 | Measure control-run setup, diagnosis, export, cleanup, and spend; `design-spec` shall define concrete defaults and runbooks |

Doctrine conflict:

The Parnas/change-containment lens favors an adapter, while minimal initial complexity favors direct framework definitions. Change containment wins because the lab is a reusable experiment platform and the dependencies are fast-moving. The ATAM trace-diagnostic lens favors LangSmith, while sourcing and local-authority concerns favor Inspect. Neither concern is hidden in the aggregate: the candidates are inside the indifference band, `VAL-9` supplies empirical evidence, and the open-source preference is used only as an explicit tie-breaker. `RISK-5` bounds adapter growth.

Section status: Complete

## 10. Selected Design Decision Record

Decision:

`DEC-1`: Proceed with a comparative R0, not final platform adoption. Start from `CAND-4` as the provisional local/open-source target and require `CAND-5` as the same-case trace-evaluation control. Apply the hard gates, evidence updates, indifference band, and tie-break rule in Section 8 before selecting the baseline for `design-spec`.

`DEC-2`: The canonical Inspect-backed comparison lane uses Inspect-owned generation configuration with `forward_generation_config=False`. An agent-authoritative configuration is a separately named experimental lane and cannot share a comparison key.

Selected candidate:

Provisional `CAND-4` — lab-owned experiment and result contracts with an Inspect AI `0.3.260` adapter, trusted and containerized execution lanes, and DeepAgents `0.7.8` or an explicitly recorded local commit. `CAND-5` remains an unrejected, required R0 comparator.

Acquisition or ownership decision:

Pin Inspect as an MIT-licensed R0 dependency and the LangSmith SDK as an optional, exactly locked control dependency. This does not authorize LangSmith as the authoritative service or approve recurring spend. The repository maintainer owns dependency upgrades, vulnerability response, adapters, scorer policy, container images, log retention, service-account/data-boundary approval, and replacement. The lab owns only its narrow domain contracts and deterministic scorer library; it does not fork or reproduce either platform. License observations are technical sourcing inputs, not legal advice.

Rationale:

Inspect provides the strongest documented local open-source runner bundle and a specific sandbox-agent mechanism. LangSmith provides the strongest documented DeepAgents-native trace evaluation and a direct, preview sandbox backend. After hard screening and corrected isolation scores, `CAND-4` leads `CAND-5` by only one of 155 points. The provisional choice therefore follows the requested local/open-source preference, not a claimed technical victory. The comparative R0 is load-bearing and must test the decision-sensitive integration, trace, configuration, isolation, export, and ergonomics claims.

Rejected alternatives:

- `CAND-1`: rejected as baseline because it turns the lab into the owner of orchestration, trace/result schema, retries, sandbox lifecycle, and analysis. OpenEvals remains a possible future scorer source behind the lab scorer boundary.
- `CAND-2`: rejected in its current shape because its agentic metrics are attractive but it fails the lab-boundary screen and direct DeepAgents trace/subagent integration evidence is weak. Reconsider only after `CAND-5` if comparative R0 rejects CAND-4 and a new adapter-contained DeepEval candidate is justified.
- `CAND-3`: rejected because it violates `CON-4`; direct framework imports create unnecessary upgrade and exit blast radius. Its in-process bridge also cannot support privileged scenarios.
- `CAND-5`: not rejected. It is the mandatory comparative control and becomes selectable under the Section 8 decision rule. Final adoption still requires explicit acceptance of account, region, data, retention, export, preview, and spend controls.
- `OPT-7`: rejected because evaluation-platform infrastructure is not the lab's differentiating work.

Accepted risks:

- `RISK-1` (owner: repository maintainer): Bridge completeness is unproven. No `design-spec` until `VAL-2` passes.
- `RISK-2` (owner: repository maintainer): Rapid package churn. Mitigate with exact locks, upgrade contract tests, and deliberate dependency PRs.
- `RISK-3` (owner: evaluation author): Judge drift and cost. Mitigate with deterministic-first scores, named judge lanes, stored rubric/version, separate judge results, and re-scoring.
- `RISK-4` (owner: repository maintainer): Secret/host exposure. Mitigate with sanitized fixtures, ignored/local logs, minimal provider payload logging, scoped capabilities, and disposable shell environments.
- `RISK-5` (owner: future lab maintainer): Adapter abstraction growth. Mitigate with a four-record target, adapter-specific evidence links, and a two-consumer rule before adding shared fields.
- `RISK-6` (owner: local operator): Docker may be unavailable or slow. Non-shell cases retain an ephemeral lane; shell baseline publication waits for `VAL-4`.
- `RISK-7` (owner: repository maintainer): Requested and effective model settings can diverge at the Inspect bridge. Mitigate with `DEC-2`, manifest authority, effective-setting capture, and configuration assertions in `VAL-2`.
- `RISK-8` (owner: decision owner): The framework choice is score-sensitive. Mitigate with the identical-case `VAL-9` control, the eight-point indifference band, and an explicit post-R0 decision record.

Exit trigger:

Reopen sourcing immediately if `VAL-9` changes the provisional result under the Section 8 rule. After selection, reopen if the selected bridge cannot capture required semantics; the privileged lane cannot establish containment; two consecutive pinned upgrades require experiment-wide edits; maintenance or vulnerability response becomes unacceptable; license, plan, preview, governance, or data-boundary posture materially changes; required local export or re-scoring becomes unavailable; or another runner clears the same contract suite with at least 25% lower measured maintenance effort over three upgrades. On exit, retain lab cases and normalized results, add a replacement adapter, and keep old native evidence read-only.

Decision owner:

Repository maintainer.

Section status: Complete

## 11. Uncertainty, Experiments, and R0 Gates

R0 mission:

Prove the lab boundary and settle the evidence-sensitive Inspect-versus-LangSmith decision with the smallest credible vertical slice. Do not scaffold the full lab or claim a statistical baseline during R0.

R0 slice:

1. Create an isolated Python 3.12 environment with exact `deepagents==0.7.8`, `inspect-ai==0.3.260`, and optional-control `langsmith==0.11.1` pins plus a reproducible lock.
2. Define only the minimum draft records needed for one variant, one case, one run, and multiple scores.
3. Define a deterministic tool-use case, the `R0-SUB-1@1` context-isolation/shared-artifact case below, and one single-retry middleware variant. Fix the same DeepAgents source, fixture digests, prompts, model identity, effective generation settings, limits, and three plumbing repetitions for every runner control.
4. Run those cases through CAND-4 Lane A under `agent_bridge()` with Inspect-owned generation configuration. Capture native Inspect evidence and a normalized run summary; verify which requested parameters were dropped, which structural parameters were forwarded, and which effective values were recorded.
5. Run the same cases through CAND-5 with LangSmith tracing and offline code evaluators. Query and persist each R0 trace locally; do not require bulk export. Record setup time, code touched, time to diagnose a seeded failure, evidence completeness, and teardown behavior for both candidates.
6. Capture canonical returned state plus a minimal lab-owned DeepAgents/LangGraph oracle ledger at the event and rendered-model-input boundaries. The ledger is shared across candidates, records E1-E6 event order and actor plus the exact rendered parent/child model-request inputs, and is populated before candidate-specific trace export; it shall not derive fields from Inspect or LangSmith evidence. Treat its implementation as shared R0 harness cost, not candidate-specific effort, and do not extend it into a third evaluation platform. Reconcile each candidate's native evidence against this oracle, apply the `R0-SUB-1` failure taxonomy, update the Section 8 evidence-sensitive scores, and record the owner's resulting selection or explicit managed-service refusal.
7. Run one release case against an exact local DeepAgents checkout or temporary clone commit without changing the committed release lock.
8. If Docker is available, install and invoke DeepAgents inside an Inspect sample container through `sandbox_agent_bridge()` and `sandbox().exec()` for one disposable filesystem/shell probe. If LangSmith Sandbox preview access is available, run the same policy probe through `LangSmithSandbox` as additional `CRIT-3` evidence. Lack of preview access does not block the non-shell LangSmith control. If Docker is unavailable, record `VAL-4` as blocked and exclude the shell track.

`R0-SUB-1@1` case contract:

| Field | Fixed contract |
| --- | --- |
| Purpose | Test the paired DeepAgents claim that child message context is isolated while a dictionary subagent and its parent exchange durable work through one shared backend. Separately test whether each evaluator exposes enough of that hidden child execution to score and diagnose it. |
| Construction | Use one dictionary subagent named `artifact-worker` and the default `StateBackend`. Do not use `CompiledSubAgent`, a checkpointer-backed cross-thread store, host filesystem, shell, network, remote MCP, or model-judge scoring. |
| Initial state | Seed `/inputs/mission.txt` in agent state with the fixed records `mission_id=R0-SUB-1` and `handoff_code=ORBIT-731`. Record the exact fixture digest. The parent user prompt names the paths and required workflow but does not contain the handoff value or child canary. |
| Child-only context | Put the sanitized marker `R0_CHILD_CANARY_7F3C` only in the subagent system prompt. Instruct the child never to emit the marker or artifact payload in its final response. The marker is test data, not a secret. |
| Shared artifact | The child reads `/inputs/mission.txt` and writes `/artifacts/subagent-handoff.json`. After JSON parsing, the artifact shall equal `{"mission_id":"R0-SUB-1","handoff_code":"ORBIT-731"}` with no additional fields. Byte formatting is not scored. |
| Handoff and final result | The child returns only `artifact:/artifacts/subagent-handoff.json`. After delegation completes, the parent reads that artifact and returns only `ORBIT-731`. The parent shall not read `/inputs/mission.txt` directly. |
| Repetition rule | Preserve all three predeclared plumbing repetitions for each candidate. At least one repetition per candidate shall pass the agent-behavior, DeepAgents-semantics, and adapter-observability lanes together to prove the nominal handoff and positive trace coverage; otherwise the case is inconclusive and the design gate stays open. Do not silently tune the prompt, replace a repetition, or change the fixture under the same case revision. |

Required partial order and visibility:

| Event | Actor | Requirement | Independent evidence |
| --- | --- | --- | --- |
| E1 | Parent | A parent model call emits exactly one `task` delegation to `artifact-worker`; no parent event reads `/inputs/mission.txt`. | Canonical parent messages plus runner-neutral event ledger |
| E2 | Child | A nested child run begins with the delegation description as its human message and a system prompt containing `R0_CHILD_CANARY_7F3C`; prior parent messages are absent. | Runner-neutral event and rendered-model-input ledger |
| E3 | Child | After one or more child model turns, successful `read_file(/inputs/mission.txt)` precedes successful `write_file(/artifacts/subagent-handoff.json)`. Extra child planning/model/tool turns are retained and reported rather than hidden. | Runner-neutral event ledger and canonical returned state |
| E4 | Child to parent | The child final response and resulting parent `task` tool message contain only the fixed artifact receipt; they contain neither the canary nor inline artifact fields. | Canonical parent messages plus runner-neutral event and rendered-model-input ledger |
| E5 | Parent | Only after E4, the parent successfully calls `read_file(/artifacts/subagent-handoff.json)` and then emits the exact final result. | Runner-neutral event ledger and canonical parent messages |
| E6 | Final state | The shared state retains the expected parseable artifact. On a repetition where E4 passes, parent model-request inputs and parent transcript contain no child canary, child-internal model request, or child-internal filesystem tool result. | Canonical returned state plus runner-neutral parent/child rendered-model-input ledger; candidate traces are compared against, never used to populate, this oracle |

Scoring and failure taxonomy:

| Evidence lane | Deterministic decision | Failure classification |
| --- | --- | --- |
| Agent behavior | Required delegation and partial order occur; artifact object and parent final answer are exact; forbidden parent source read and inline child payload do not occur. | `agent_failure` when the faithfully observed model/tool trajectory violates the case contract. |
| DeepAgents semantics | Final state shares the artifact while parent messages exclude child-internal messages and events; on a compliant E4 receipt, the child canary also remains absent. | `deepagents_semantic_failure` when runner-neutral state/event evidence contradicts `SRC-17`. A child that explicitly emits the canary or payload is `agent_failure`, not proof of a library leak. |
| Harness validity | Case revision, fixture and prompt digests, source/model/settings/limits, canonical state, and the runner-neutral event and rendered-model-input oracle ledger are complete and match the run manifest. | `invalid_run` when the fixture, oracle, or manifest is incomplete or inconsistent; do not score the agent or candidate from that repetition. |
| Adapter observability | Candidate evidence matches the runner-neutral oracle; nests the child under the task/parent run; exposes the child-only canary in child model input and, on a compliant E4 receipt, nowhere in parent model input; attributes E1 through E5 to the correct actor; preserves actual errors and results; and records parent, child, and total usage or an explicit provider-unreported marker. | `adapter_coverage_failure` only when the valid independent oracle proves an event or model input occurred but the candidate omits or misattributes it. A faithfully captured `agent_failure`, including an echoed canary, is positive diagnostic evidence rather than adapter failure. |

No lane may infer context isolation solely because the candidate trace lacks child data. The runner-neutral oracle must first demonstrate that the child canary and child events occurred and that rendered parent model inputs excluded them. The adapter lane passes only when the candidate evidence matches that oracle: it positively exposes the canary and child events under the child run while excluding them from parent model inputs.

| ID | Uncertainty or validation need | Gate type | Owner | Evidence required | Due point |
| --- | --- | --- | --- | --- | --- |
| VAL-1 | Exact dependency compatibility and released/local source modes | R0 experiment | Repository maintainer | Frozen lock installs on a clean environment; import smoke; run manifest records release or local Git SHA and dirty state; no committed lock mutation for local overlay | Before `design-spec` |
| VAL-2 | Inspect Lane A captures DeepAgents parent, subagent, model, tool, final-state, error/retry, and usage evidence completely enough for scoring/debugging, preserves the `R0-SUB-1` context boundary, and applies the declared generation authority | R0 experiment | Repository maintainer | Native log, normalized summary, canonical state, and the runner-neutral E1-E6 event/rendered-model-input oracle ledger for tool, `R0-SUB-1`, and retry runs; the `R0-SUB-1` coverage lane positively exposes the child-only canary and E1-E5 under the correct actor while matching the oracle's isolated parent inputs and E6 final state; failure classes stay separate; manifest shows authority=`inspect`, forwarding disabled, requested-versus-effective settings, resolved model, and a distinct key for any agent-authoritative probe | Before `design-spec`; blocking for CAND-4 |
| VAL-3 | Lab contract contains evaluator churn without recreating a framework | R0 experiment | Future lab maintainer | Experiment modules import no Inspect or LangSmith evaluation type; adapter contract tests cover round-trip identity, errors, scores, evidence links, and unknown fields for each R0 adapter; internal review confirms four core records are sufficient | Before `design-spec`; blocking |
| VAL-4 | CAND-4 Lane B places the DeepAgents process and ordinary privileged tools inside the Inspect sandbox and enforces the declared resource/capability policy | R0 experiment | Security reviewer or repository maintainer | Evidence that the agent is installed and launched through `sandbox_agent_bridge()` plus `sandbox().exec()`; disposable sample cannot escape its workspace, read an unmounted fake host secret, persist after cleanup, exceed CPU/memory/time policy, reach network without allowlisting, or obtain withheld provider/remote-MCP capabilities; host diff remains clean | Before shell baseline enters `design-spec`; blocking for shell track |
| VAL-5 | Repeated run identity and score separation prevent invalid comparisons | R0 experiment | Evaluation author | Three-epoch results preserve each epoch; changing model/judge/source/case revision creates a new comparison key; deterministic scores reproduce on cached/stored output | Before `design-spec` |
| VAL-6 | Seed-suite coverage, repetitions, variance, and decision thresholds | Post-design-spec check | Evaluation author | Reviewed 14-21-case inventory with at least one nominal and one failure-path case in each of planning, tools, filesystem, subagents, middleware/failures, permissions, and context management; deterministic evidence for every case; a predeclared repetition budget; per-case and per-category pass rates; paired variant deltas with a case-stratified 95% bootstrap interval; `inconclusive` whenever the interval includes zero or the run budget is not met; `regressed` whenever any hard safety result worsens regardless of aggregate score | Before declaring baseline `v1` or claiming improvement |
| VAL-7 | Default provider, judge, spend, and CI policy | Validate before design-spec | Repository maintainer | Written choice for canonical model lane, optional judge lane, per-run cost/time ceilings, credentials, and CI/manual trigger policy | Before canonical baseline numbers; may follow technical R0 |
| VAL-8 | Structural validation of this packet | Completed before design-spec | Packet author | `markdown-engine` validation report with active fleet-policy engine version and zero structural violations, or an explicit runtime failure | At packet completion |
| VAL-9 | Identical-case Inspect-versus-LangSmith trace-evaluation control retires candidate sensitivity | R0 experiment | Repository maintainer and decision owner | Same source, `R0-SUB-1@1` fixture/prompt digests, effective model, limits, and repetitions; separate agent/DeepAgents/harness/adapter statuses; reconciled E1-E6 matrices against canonical state and the runner-neutral event/rendered-model-input oracle ledger; setup/code-touch/seeded-diagnosis/export/cleanup observations; per-run LangSmith trace export; updated Section 8 scores; hard-screen result; signed decision applying the eight-point indifference band and tie-break rule | Before `design-spec`; blocking |

Pass condition:

`VAL-1`, `VAL-3`, `VAL-5`, and `VAL-9` pass, plus the validation items required by the candidate selected under the Section 8 rule. For each candidate, `R0-SUB-1@1` must contain at least one nominal repetition that passes its agent-behavior, DeepAgents-semantics, and adapter-observability lanes together, and every retained repetition must have an explicit harness and adapter-coverage status. CAND-4 selection requires `VAL-2`; CAND-5 selection requires its `VAL-9` trace/export evidence and explicit owner acceptance of the service boundary. `VAL-4` must also pass before the CAND-4 shell track is specified; if Docker is intentionally deferred, the first `design-spec` shall exclude that track. Missing or misattributed required events, inference of isolation from absent trace data, collapsed failure classes, ambiguous effective configuration, evaluator types leaking through the lab boundary, provenance collision, or failure to record the post-R0 decision prevents `design-spec`. If the owner declines a LangSmith account or data transfer, `VAL-9` may close only with that explicit sourcing decision; the packet may then prefer CAND-4 for policy reasons but shall not claim technical superiority.

Section status: Deferred

## 12. Handoff to design-spec

Recommended downstream action:

Before acting, read `/Users/jasonbelmonti/Documents/Development/deepagents-lab/docs/design/deepagents-lab-design-process.md`, verify it against `/Users/jasonbelmonti/Documents/Development/deepagents-lab/docs/design/deepagents-lab-design-process.sha256`, and read `/Users/jasonbelmonti/Documents/Development/deepagents-lab/docs/design/deepagents-lab-design-process.validation.json`. Execute the Section 11 comparative R0 without broad scaffolding, update this packet and sidecars with empirical results and the final selection, then author an implementation `design-spec` only if the pass condition holds.

Recommended downstream rigor:

`R1` for the local lab. Raise the shell/sandbox portion independently if it will execute untrusted third-party fixtures, access real credentials/data, or run in a shared CI environment.

Source authority for design-spec:

- Preserve provisional `CAND-4`, required comparator `CAND-5`, `DEC-1`, `DEC-2`, `CON-1` through `CON-12`, the selected risks, the hard screen, the eight-point indifference band, and the 18-month evaluation horizon until `VAL-9` records the final decision.
- Pin and lock the evaluated releases from the research cutoff: DeepAgents `0.7.8`, Inspect AI `0.3.260`, and LangSmith SDK `0.11.1`. A newer version requires rerunning the affected R0 compatibility gates and updating this packet; do not silently substitute it.
- Define small, focused modules for lab contracts, DeepAgents construction/source provenance, case fixtures, deterministic scorers, the selected runner adapter, the R0 control adapter or disposable comparison code, and result export. Keep experiment modules focused on the technique under study.
- Specify canonical record schemas, stable identifiers, comparison-key rules, fixture lifecycle, scorer precedence, artifact layout/retention, CLI tasks, default limits, and error states.
- Specify a release lane and local-checkout lane that cannot be confused in results.
- Preserve `R0-SUB-1@1` as the subagent plumbing contract unless an explicit new case revision records the changed fixture, prompts, visibility rules, and scorer effect. Keep agent behavior, DeepAgents semantics, harness validity, and adapter observability as separate result lanes.
- Specify the initial seed-suite inventory and the `VAL-6` evidence required before it is called baseline `v1` or used to claim that a variant improved, regressed, or was inconclusive.

Risks and gates to preserve:

- No implementation approval before the Section 11 pass condition, including `VAL-9`, holds.
- Exclude shell scenarios unless `VAL-4` passes; an ephemeral in-memory/filesystem-safe lane may proceed independently.
- Resolve `Q-1` and `VAL-7` before publishing baseline numbers or enabling non-local runs.
- Preserve deterministic and judge scores separately. No aggregate may hide errors, limit terminations, or hard policy failures.
- Treat evaluator logs as potentially sensitive. Define ignore, redaction, retention, cleanup, and optional sharing controls.

Sourcing commitments to preserve:

- Inspect remains behind the adapter; Lane A and Lane B are never conflated; native logs are referenced, not normalized exhaustively.
- The canonical Inspect-backed lane uses Inspect-owned generation configuration. Agent-owned forwarding is a named, comparison-separated exception.
- The lab owns maintenance, upgrades, vulnerability response, and exit; no managed service is required for local truth.
- Package versions and hashes are controlled by the lockfile. Dependency updates run adapter contract tests and the R0 slice before merge.
- LangSmith is a required R0 comparator and may become the selected runner or an optional sink only through the recorded Section 8 decision rule. It may not become authoritative by convenience or unreviewed workspace state.
- Exit retains versioned cases, normalized summaries, scorer definitions, and read-only native evidence.

Traceability notes:

- `CON-2`/`CON-12` -> `SURF-3`/`SURF-4`/`SURF-6` -> `CRIT-1` -> `SCN-3`/`R0-SUB-1@1` -> `VAL-2`/`VAL-9` -> `CAND-4`/`CAND-5`.
- `CON-3`/`CON-9` -> `SURF-8`/`SURF-9` -> `CRIT-2` -> `SCN-6`/`SCN-10` -> `VAL-1`/`VAL-5`.
- `CON-4` -> `SURF-2`/`SURF-10` -> `CRIT-6` -> `SCN-9` -> `VAL-3`.
- `CON-5` -> `SURF-6` -> `CRIT-4` -> `SCN-2`/`SCN-8` -> `VAL-5`/`VAL-6`.
- `CON-6`/`CON-7` -> `SURF-7`/`SURF-11` -> `CRIT-3` -> `SCN-7` -> `VAL-4`.
- `CON-3`/`CON-11` -> `SURF-8` -> `CRIT-2` -> `SCN-14` -> `DEC-2` -> `VAL-2`.
- User OSS preference/`CON-8` -> `SURF-12` -> `CRIT-1`/`CRIT-5`/`CRIT-8` -> `SCN-15` -> `DEC-1` -> `VAL-9`.

Section status: Deferred

## Internal Review Record

### Mission Calibration

| Field | Value |
| --- | --- |
| Requested decision | Design a Python DeepAgents technique lab with an agent-focused open-source eval baseline |
| Reviewed decision | Select lab boundaries and evaluation sourcing; determine readiness for specification |
| Calibration result | Route to R0 |
| Rationale | The design creates a reusable repository precedent and compares fast-moving local and managed technologies. Documentation resolves the bridge, configuration, and sandbox semantics, while DeepAgents-specific trace completeness, containment, export, and ergonomics remain bounded empirical claims. |

Process depth: Full packet. The lab is local rather than live-user-facing, but the decision sets a reusable architecture, runs agents with potentially privileged tools, and selects external pre-1.0 technology.

### Section Status Ledger

| Section | Status | Review result |
| --- | --- | --- |
| Document Control | Complete | Owner, authority, downstream target, rigor, and date present |
| 0. Design Mission Summary | Complete | Decision, direction, risks, and R0 readiness explicit |
| 1. Problem Frame and Decision Needed | Complete | Solution-independent kickoff baseline, current implementation gap, scope, and trigger recorded |
| 2. Stakeholders, Concerns, and Viewpoints | Complete | Developer, evaluation, operations, security, review, and maintenance viewpoints covered |
| 3. Constraints, Invariants, and Assumptions | Complete | Facts, assumptions, and questions separated; load-bearing items gated; subject behavior and evaluator coverage cannot be conflated |
| 4. Design Space Decomposition | Complete | Thirteen surfaces and sourcing applicability recorded |
| 5. Option Families | Complete | Internal, OSS, managed, custom, hybrid, conservative, and experiment paths considered |
| 6. Candidate Elaboration | Complete | Five falsifiable candidates include boundaries, ownership, cost, failure, and exit |
| 7. Stress Scenarios and Failure Modes | Complete | Fifteen scenarios include a deterministic context-isolation/shared-artifact subagent contract, configuration conflict, and an identical-case candidate audit in addition to nominal, failure, misuse, rollback, supplier, and future-change pressure |
| 8. Trade Study | Complete | Hard screening precedes scoring; TCO bands, evidence-sensitive rationale, indifference band, arithmetic sensitivities, and a deterministic post-R0 selection rule are explicit |
| 9. Source Doctrine Validation | Complete | Applicable lenses used as tests; security retains an empirical risk |
| 10. Selected Design Decision Record | Complete | Provisional selection, unrejected comparator, configuration decision, risks, owners, and exit triggers recorded |
| 11. Uncertainty, Experiments, and R0 Gates | Deferred | Correctly routes trace, configuration, isolation, provenance, export, ergonomics, and candidate sensitivity to comparative R0; `R0-SUB-1@1` supplies fixed stimuli, oracle evidence, partial order, lane-specific scoring, and stop conditions |
| 12. Handoff to design-spec | Deferred | Exact packet and sidecar paths plus authority, versions, risks, selection rule, and sourcing commitments are preserved |

### Design-Space Adequacy

| Dimension | Score | Review note |
| --- | ---: | --- |
| Problem framing | 3/3 | Kickoff state, current implementation gap, and comparison problem are explicit without assuming a runner |
| Surface decomposition | 3/3 | Technical, evaluation, operational, security, sourcing, and change surfaces are separated and coupled |
| Sourcing evidence | 3/3 | Current primary docs, registries, repositories, versions, licenses, and limitations cover viable classes |
| Option generation | 3/3 | Options differ materially in ownership, runner scope, integration, data boundary, and exit |
| Candidate elaboration | 3/3 | Five candidates are falsifiable; the two viable leaders name their actual execution and trust boundaries |
| Scenario stress | 3/3 | Fifteen scenarios challenge core quality attributes, configuration authority, candidate sensitivity, and selected risks; the subagent R0 now makes both positive visibility and non-leak claims falsifiable |
| Trade study | 3/3 | Hard failures are screened, weights reflect preference strength, score bases and TCO are explicit, and a one-point result is correctly treated as indifference rather than victory |
| Uncertainty routing | 3/3 | Discoverable facts are resolved in the packet; integration and selection-sensitive claims are routed to a bounded same-case R0 with a deterministic close rule |

### Finding Log

| Finding ID | Severity | Status | Section or dimension | Finding | Required action | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| DP-1 | Major | Resolved | Technology sourcing | Initial direction lacked an explicit managed option and lifecycle/exit comparison | Added LangSmith managed option, 18-month TCO basis, maintenance ownership, and exit trigger | Packet author |
| DP-2 | Major | Resolved | Candidate selection | Selecting Inspect from documentation alone would overstate DeepAgents nested trace compatibility | Changed verdict to `Ready for R0 Experiment` and added blocking `VAL-2` | Packet author |
| DP-3 | Major | Resolved | Security/operations | Shell and filesystem exploration could mutate the host or expose credentials | Added `CON-6`, `CON-7`, `SCN-7`, `RISK-4`, and blocking `VAL-4` | Packet author |
| DP-4 | Minor | Resolved | Reproducibility | A package version alone would not identify a local OSS checkout | Added release/local lanes, Git SHA/dirty provenance, comparison-key rule, and `VAL-1` | Packet author |
| DP-5 | Minor | Resolved | Evaluation validity | A single aggregate could hide judge drift, hard policy failure, or stochastic variance | Added deterministic precedence, score separation, epochs, re-scoring, and no-hidden-failure requirement | Packet author |
| DP-6 | Observation | Resolved | Repository workflow | The preferred `.worktrees/` workflow could not be used until the empty directory became a Git repository with an initial commit | Repository initialization is complete; this revision is executing in repository-local `.worktrees/sharpen-subagent-r0` | Repository maintainer |
| DP-7 | Observation | Open | Human decision | Default execution model, judge, budget, and CI lane remain intentionally undecided | Resolve `Q-1`, `Q-2`, and `VAL-7` before canonical baseline publication | Repository maintainer |
| DP-8 | Major | Resolved | Technology sourcing and trace evaluation | LangSmith was initially represented as a managed result sink without enough weight on its full offline traces, intermediate child runs, trajectory evaluators, and online run/thread evaluation | Added current trace-eval, pricing, retention, self-hosting, sandbox, and export evidence; promoted LangSmith to `CAND-5`; stress-tested and scored it; retained it as an unrejected mandatory comparator | Packet author |
| DP-9 | Major | Resolved | Candidate mechanism and security | The selected Inspect candidate conflated in-process `agent_bridge()` with containerized execution and credited sandbox isolation that provisioning alone does not provide | Split CAND-4 into trusted Lane A and containerized Lane B; required `sandbox_agent_bridge()` plus `sandbox().exec()` for privileged cases; re-scored isolation; strengthened `VAL-4` | Packet author |
| DP-10 | Major | Resolved | Reproducibility and model authority | The packet required exact generation settings without deciding whether Inspect or the agent owns parameter precedence | Added `CON-11` and `DEC-2`, chose Inspect authority for the canonical lane, separated agent-authoritative runs by comparison key, and added effective-setting evidence to `VAL-2` | Packet author |
| DP-11 | Major | Resolved | Trade study and uncertainty routing | The original R0 tested only Inspect even though LangSmith could become selected under the packet's own sensitivity analysis | Added current LangSmith sandbox/export evidence, corrected weights and scores, defined an eight-point indifference band, added same-case `SCN-15`/`VAL-9`, and made CAND-5 an unrejected mandatory comparator | Packet author |
| DP-12 | Minor | Resolved | Evaluation validity | The original 12-20-case wording overstated a seed suite and did not define variance or inconclusive behavior | Reframed the corpus as a 14-21-case seed suite and added category coverage, repetitions, paired analysis, variance, safety, and inconclusive requirements to `VAL-6` | Packet author |
| DP-13 | Minor | Resolved | Durable handoff | The handoff said to read the exact packet but did not embed the packet, checksum, and validation paths | Added all three absolute paths and a read/verify-first instruction to Section 12 | Packet author |
| DP-14 | Major | Resolved | Subagent R0 validity and trade-study evidence | The original parent/subagent case did not fix a stimulus, expected artifact, context-isolation oracle, event order, or failure taxonomy, so a missing child event could be mistaken for successful isolation or an agent failure could be blamed on the evaluator | Added `CON-12`, pinned-release evidence `SRC-17`, supporting sample `SRC-18`, the `R0-SUB-1@1` fixture and canary, runner-neutral evidence, a required partial order, separate scoring lanes, bounded repetition/inconclusive rules, and candidate-specific `VAL-2`/`VAL-9` evidence | Packet author |
| DP-15 | Major | Resolved | Subagent failure classification | The first sharpened draft could classify a child that explicitly echoed the canary as a DeepAgents isolation failure and required only one nominal repetition across both candidates | Made a compliant E4 receipt the precondition for the canary non-leak assertion, classified explicit child echo as `agent_failure`, required a nominal repetition per candidate, and required faithful traces of failed behavior | Packet author |
| DP-16 | Major | Resolved | Subagent R0 oracle independence | E6 used per-model candidate evidence as its own completeness oracle, allowing a candidate trace to validate its own context-isolation claim | Defined a lab-owned runner-neutral event/rendered-model-input oracle populated before candidate export; made E1-E6 independent evidence candidate-free; require each candidate trace to match the oracle | Packet author |
| DP-17 | Minor | Resolved | Subagent R0 pass condition | The nominal repetition rule claimed positive trace coverage without requiring the adapter-observability lane to pass | Require one repetition per candidate to pass agent behavior, DeepAgents semantics, and adapter observability together | Packet author |
| DP-18 | Minor | Resolved | Problem framing | Mission and sourcing text described the kickoff empty directory as the present state after repository initialization | Reframed the text as an explicit kickoff baseline and recorded the remaining current evaluation implementation gap | Packet author |

### Source-Doctrine and Decision-Chain Result

Source doctrine result: Pass for comparative R0 readiness. Trust boundaries and candidate sensitivity are explicit experiment gates rather than optimistic mechanism claims.

Decision chain result: Pass. Stakeholder concerns trace through constraints, surfaces, criteria, stress scenarios, provisional decision, and validation gates. Hard-constraint failures are screened before scoring, subject behavior is separated from evaluator coverage, candidate traces are checked against an independent runner-neutral oracle, and the one-point candidate difference is not presented as decisive.

### Validation Result

Passed on 2026-08-26 after the `R0-SUB-1@1` oracle remediation and second internal review. The fleet-policy validation evidence reported `engineVersion: 3.5.0`, Node runtime `v22.20.0`, profile syntax `markdown-engine.validation@v1`, 42 of 42 rules passed, and zero diagnostics. The wrapper does not support a standalone `--version` argument; the required active engine version was taken from the successful validation evidence. A refreshed validation sidecar and SHA-256 checksum accompany this packet.

### Unresolved Findings

- No open `Blocker` or `Major` review finding remains in the authored reasoning.
- `VAL-1` through `VAL-5` and `VAL-9` are empirical R0 gates, not packet defects.
- `DP-7` is the only open non-blocking observation for this design-process deliverable.

### Readiness Verdict

`Ready for R0 experiment`.

The packet is not ready for `design-spec` because complete DeepAgents trace capture, effective configuration, privileged-lane containment, export, and the final Inspect-versus-LangSmith decision are load-bearing and not yet evidenced. Missing discoverable technology evidence is not the blocker; current public evidence is sufficient for the bounded comparative experiment.
