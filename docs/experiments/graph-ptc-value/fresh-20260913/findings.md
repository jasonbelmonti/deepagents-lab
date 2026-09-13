# Fresh graph PTC campaign — 2026-09-13

## Outcome

The harness at the measured main commit completed all 60 planned paid invocations on fresh seeds with no post-result tuning or reruns. The results strengthen the case for PTC on exact multi-step graph work, especially token efficiency and successful completion. They do not establish a universal latency advantage or production accuracy rate.

This is fresh-case evidence measured on the identified main commit, separate from both historical development pilots. “Fresh” describes the selected cases; it is not a statistical declaration that the hypothesis is confirmed.

## Fixed setup and provenance

- Main commit: cb919679e221b39541d928358830f9b39f8d5124.
- Model: openai:gpt-5.6-luna.
- Seeds: 39047, 58271, 76493, 91807.
- Five workloads, four seeds, three arms: 60 invocations.
- Primary: ordinary, without an interpreter, versus PTC.
- Secondary: compute-only interpreter versus PTC.
- Original four workload families plus the reserved security/two-connectors query variant.
- Same fixture generator, tool APIs, prompt generation, scorer, limits, and model settings as merged code; only the configured seeds and workload list changed.
- LangSmith tracing enabled. No historical results pooled, altered, or rescored.
- All 60 attempts have complete reported usage: 232 model requests, 1,001,618 input tokens + 117,249 output tokens = 1,118,867 total tokens. These are usage counts, not dollar costs.
- 37 of 60 attempts passed the current complete-task validator. Failed attempts remain charged.

## Correctness comes first

Passing means the exact requested answer, including ranking, connector counts, canonical supporting paths and JSON format, plus route/read-evidence checks. For PTC, the interpreter result must also match. This is not a score for merely naming some relevant people.

| Workload | No interpreter | Compute-only | PTC |
| --- | ---: | ---: | ---: |
| Lookup | 4/4 | 4/4 | 3/4 |
| Depth-2 | 4/4 | 3/4 | 4/4 |
| Depth-3 | 1/4 | 2/4 | 4/4 |
| Width-12 | 0/4 | 0/4 | 3/4 |
| Security / two connectors | 1/4 | 1/4 | 3/4 |

PTC's lookup failure raised ValueError after one recorded model request. The report does not retain enough exception detail to establish its precise cause; it remains a failed attempt, not a removed infrastructure outlier.

The other 22 failures have final-answer mismatches. Local raw-report inspection found candidate-set, connector-count, ranking, supporting-path and JSON-format discrepancies. Some attempts found the correct people but failed the required supporting paths. Two PTC graph attempts also failed interpreter-result validation; no scoring was changed during this inspection. These diagnostic observations require raw access to investigate beyond the published check flags.

## Primary efficiency: only same-seed pairs where both pass

Numbers below are medians of per-pair percentage changes, not ratios of pooled totals.

| Workload | Eligible pairs | PTC total tokens vs ordinary | PTC latency vs ordinary |
| --- | ---: | --- | --- |
| Lookup | 3 | 30.9% more | 58.8% slower |
| Depth-2 | 4 | 36.5% fewer | Essentially unchanged: 0.1% faster |
| Depth-3 | 1 | 47.8% fewer | 24.1% faster |
| Width-12 | 0 | No valid comparison | No valid comparison |
| Security / two connectors | 0 | No valid comparison | No valid comparison |

The cleanest token result is depth-2: both primary arms passed all four seeds, and PTC used fewer tokens on each. PTC halved model calls, but output tokens increased and median per-pair latency was effectively unchanged.

Depth-3 offers encouraging completion results, but its primary efficiency percentage rests on only one successful pair.

Width-12 has no successful ordinary attempts. The security variant has one successful ordinary attempt and three successful PTC attempts, but on different seeds. Do not manufacture an efficiency comparison from these unmatched successes.

## All-attempt cost per correct answer

These sample ratios charge each arm for its failed attempts; they are not expected production costs. Undefined means no correct answer, not zero cost.

| Workload | Ordinary tokens / correct | Compute tokens / correct | PTC tokens / correct |
| --- | ---: | ---: | ---: |
| Lookup | 4,883.5 | 7,759.8 | 7,706.3 |
| Depth-2 | 14,197.5 | 22,544.7 | 9,071.25 |
| Depth-3 | 102,630.0 | 54,158.0 | 14,173.25 |
| Width-12 | Undefined | Undefined | 21,538.3 |
| Security / two connectors | 92,725.0 | 129,128.0 | 21,954.7 |

## Secondary control

Compute-only versus PTC comparisons remain conditional and separate:

- Lookup: three pairs; PTC uses 12.4% more tokens and is 13.1% slower.
- Depth-2: three pairs; PTC uses 41.4% fewer tokens but is 6.7% slower.
- Depth-3: two pairs; PTC uses 34.5% fewer tokens and is 7.1% faster.
- Width-12: no eligible pairs.
- Security variant: one pair; PTC uses 56.0% fewer tokens and is 20.1% faster.

The compute-only arm may elect not to use its interpreter; this campaign does not impose a mandatory-computation baseline.

## Interpretation and remaining limits

This fresh run supports trying PTC for investigations that require accurate traversal, connector accounting, ranking and supporting paths. It does not support adding an interpreter to simple lookups for efficiency. Fewer tokens and model calls are more consistent than lower latency.

This is still four seeds per workload, one model, one campaign, one reserved question variant, and one synthetic generator. It is fresh-case validation, not an independently designed real-world benchmark or reliable estimate of production accuracy, latency tails, or dollar savings. One depth-2 seed has an empty correct answer, retained as selected; the harder workloads have nonempty answers.

Provider caching/load and tracing are uncontrolled. Preflight checks overlapped campaign startup, so the first lookup timing is not an isolated microbenchmark. No further tests ran during live execution. Neither these effects nor failures justified dropping or rerunning observations.

## Audit and artifacts

[All attempts and comparison tables](tables.md) are reproducible from the
[whitelisted metrics](metrics.json). The extract includes all 60 attempts,
per-request token counts, recorded validation/error types, configuration,
versions and measured source hashes. It excludes credentials, local paths,
trace identifiers, prompts, generated programs, answers and graph records.

The [frozen configuration](frozen-config.json) is an exact copy of the file
written before provider execution. Its launcher digest identifies a local
launcher, not a committed executable. To reconstruct the selected configuration
without making a call:

```python
from dataclasses import replace
from deepagents_lab.experiments.graph_ptc_value.config import CASES, VARIANT, Config

config = replace(
    Config(), model="openai:gpt-5.6-luna",
    seeds=(39047, 58271, 76493, 91807), cases=(*CASES, VARIANT),
)
```

From the repository root, these commands are read-only and need no credentials:

```bash
uv run --frozen --group notebooks python scripts/check_graph_fresh.py
uv run --frozen --group notebooks pytest -q tests/test_graph_fresh_evidence.py
```

If you have the preserved raw report, verify exact extraction as well:

```bash
uv run --frozen --group notebooks python scripts/check_graph_fresh.py \
  --verify-raw /absolute/path/to/report.json
```

Raw report SHA-256:
`7b84342ae0f2bb99cb35c1314080e586fe2b1516ea40aafdc61240162b1c164e`.

Frozen configuration SHA-256:
`1c4c4046e138e6d26777d1f63aa026ea2113247ce472f975ceb0e993c6292bf0`.

The audit verifies the committed artifact digests and recomputes all tables.
With raw access, it checks every selected field against the exact original.
Digests alone cannot authenticate extraction without the source report, and
this extract is not a replay or independent rescoring of generated programs.

The [earlier pilot](../pilot-findings.md) remains separate and unchanged.
This publication makes no new model calls and changes no runtime, dependency,
notebook execution behavior or historical evidence.
