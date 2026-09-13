# Graph interpreter pilot: promising token savings, limited latency evidence

This is **historical development evidence**, not a fresh benchmark of the current
checkout. The corrected pilot ran on 2026-09-12 with `openai:gpt-5.6-luna`,
two seeds per workload and three agent configurations. All 24 invocations
finished: 19 were recorded correct, across 86 model requests and 404,846 tokens
(359,236 input + 45,610 output). Usage includes wrong answers and repairs.

**Primary: no interpreter (ordinary) versus interpreter with PTC.**
**Secondary: compute-only interpreter versus PTC.** The primary emphasis was
clarified after the pilot; this is a post-hoc descriptive presentation, not a
preregistered result. Recorded attempts and the raw summary are not rewritten.

## What the primary comparison actually shows

All percentages below use only matched seeds where both arms passed the
historical answer, route, read-evidence and usage checks. They are medians of
per-pair changes, not ratios of pooled totals. Success counts include both seeds.

| Workload | Ordinary correct | PTC correct | Eligible pairs | Total tokens, PTC vs ordinary | Latency, PTC vs ordinary |
| --- | --- | --- | --- | --- | --- |
| Lookup (negative control) | 2/2 | 2/2 | 2 | 30.8% more | 24.9% slower |
| Depth-2 | 2/2 | 2/2 | 2 | 6.9% fewer | 17.9% slower |
| Depth-3 | 1/2 | 2/2 | 1 | 56.3% fewer | 17.7% faster |
| Width-12 | 1/2 | 2/2 | 1 | 52.6% fewer | 32.8% faster |

This supports trying interpreter-backed orchestration on deeper investigations.
It does **not** establish a general speedup or reliable accuracy advantage.
Each deeper-case efficiency result rests on one successful matched pair.
Depth-2 is mixed even within the case: PTC uses more tokens on seed 1103 and
fewer on seed 2213. The failed baseline attempts remain in the cost tables.

## What the secondary control adds

The compute-only arm can calculate in JavaScript but cannot call graph tools
from that code. It used eval in only one of its eight trials; it was allowed,
not required, to use the interpreter. That limits claims about computation alone.

The most informative secondary pair is width-12, seed 1103: both compute and
PTC used code and were recorded correct. Compute made six model requests using
41,092 tokens; PTC made two using 13,790 tokens (**66.4% fewer**).
Input tokens fell from 37,031 to 10,147 (**72.6% fewer**).

Both made five backend reads returning 8,720 logical JSON response bytes.
Their read signatures match after normalizing order-insensitive batch IDs and
call order; names, options, multiplicities, counts and byte sizes are retained.
Cumulative tool-result text shown across model calls fell from 35,203 to 2,331
characters (**93.4% less**). That supports the proposed mechanism: keeping
intermediate graph data inside code can reduce repeated model context.

But PTC took **37.742 seconds**, versus **35.043 seconds** for compute:
**7.7% slower**. Fewer tokens or model turns do not guarantee lower latency.
The other secondary cases are visible in the supporting tables: lookup is worse,
depth-2 saves tokens but is slower, and depth-3 has no correct compute/PTC pair.

## Failures and costs are part of the result

Five attempts failed the historical final-answer check, despite passing its
route/read checks: ordinary depth-3/1103, compute depth-3/1103,
compute depth-3/2213, ordinary width-12/2213 and compute width-12/2213.
They are wrong-answer outcomes, not missing usage or administrative cancellation.
No post-hoc repair or partial-credit rescoring is applied here.

The successful PTC depth-2/1103 attempt needed code repair and four model
requests; all 18,195 tokens remain charged. Complete observed usage exists for
every attempt. Token totals include failures, not just eligible efficiency pairs.

For width-12, tokens per recorded correct answer are 58,725 ordinary,
70,623 compute and 13,539 PTC when each arm pays for all its attempts.
These are descriptive sample ratios, not expected future cost. Depth-3 compute
has no correct answer; its tokens per correct answer are undefined, not zero.

Token counts are not dollars. Cached input and reasoning details are subsets,
not additions; provider pricing and cache behavior affect monetary cost.
Latency spans invocation, excluding fixture, oracle and agent construction.
Backend time is nested, potentially overlapping; no exclusive interpreter or
remote database timing is claimed.

## Historical limits and excluded evidence

- The first pilot had unequal model-visible tool documentation and was stopped.
  It remains **inconclusive** and is excluded from every table here. Its digest is
  preserved alongside the corrected report's digest; the raw files remain local.
- The corrected pilot fixed documentation parity but reused development seeds.
  Two observations per arm/case cannot establish statistical reliability or p95.
- These numbers use the **historical scorer and measured source hashes**.
  Later PRs fixed workload validation, accounting and interpreter cleanup and
  changed primary framing. No paid run or rescoring against current code happened
  in this PR. Do not present the recorded 19/24 as current-harness validation.
- Synthetic small in-process graphs do not establish production scale,
  persistence performance, real-service latency or concurrent-user capacity.
  Graph workspace remains separate exploratory materialization research.
- Provider load, generation/reasoning, cache behavior and tracing can affect
  latency. This pilot cannot causally assign those contributions or prove PTC
  beats a purpose-built graph query.

## Audit

Open the [notebook](../../../notebooks/experiments/graph-ptc-value.ipynb)
for the offline workflow. [All attempt and comparison tables](pilot-tables.md)
are recomputed from [the curated metric extract](pilot-metrics.json).
The extract contains all 24 rows, per-request token counts, recorded validation,
configuration, measured versions/source hashes and normalized backend-read digests.
It deliberately excludes credentials, local paths, trace IDs, prompts, programs,
answers and graph records. It is **not** a self-contained replay of the full agent
or an independent verification of historical correctness.

From the repository root, without credentials:

```bash
uv run --frozen --group notebooks python scripts/check_graph_pilot.py
uv run --frozen --group notebooks pytest -q tests/test_graph_pilot_evidence.py
```

To additionally verify every extracted field against the preserved local raw
report, supply its path (the command does not modify it):

```bash
uv run --frozen --group notebooks python scripts/check_graph_pilot.py \
  --verify-raw /absolute/path/to/the/corrected/report.json
```

Corrected raw SHA-256:
`c1c0705ceb4d9f0e2233411a95294c87b30821d85e1cd801fe21ca620ed97900`.
Excluded first raw SHA-256:
`c102c9bd0b8202afd98bad196d06e419374acdf3d157eaa296f00fc1ebc81e0b`.

The digests identify preserved evidence; without the original raw report they
cannot alone authenticate an extract. Colleagues can reproduce published
arithmetic from the committed metrics; raw access is needed to verify extraction
or investigate generated programs. No ignored results tree is published.
