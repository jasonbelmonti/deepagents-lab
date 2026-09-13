# Historical pilot: reproducible supporting tables

Recorded historical correctness, not current-head validation. Primary: ordinary → PTC. Secondary: compute → PTC.

Positive reduction favors PTC; negative favors the baseline. Median of per-seed percentages, not a ratio of pooled totals. A dash means no eligible pair. Cases are never pooled.

## Every attempt

| Case | Seed | Arm | Correct | Calls | Input tokens | Output tokens | Total tokens | Seconds |
|---|---|---|---|---|---|---|---|---|
| lookup | 1103 | ordinary | True | 2 | 4810 | 70 | 4880 | 3.619 |
| lookup | 1103 | compute | True | 2 | 5436 | 74 | 5510 | 3.273 |
| lookup | 1103 | ptc | True | 2 | 6290 | 82 | 6372 | 4.968 |
| lookup | 2213 | ptc | True | 2 | 6307 | 95 | 6402 | 3.234 |
| lookup | 2213 | compute | True | 2 | 5549 | 183 | 5732 | 3.579 |
| lookup | 2213 | ordinary | True | 2 | 4816 | 72 | 4888 | 2.876 |
| depth-2 | 1103 | compute | True | 4 | 14451 | 860 | 15311 | 10.913 |
| depth-2 | 1103 | ptc | True | 4 | 16710 | 1485 | 18195 | 15.871 |
| depth-2 | 1103 | ordinary | True | 4 | 13494 | 973 | 14467 | 11.058 |
| depth-2 | 2213 | ordinary | True | 4 | 13295 | 603 | 13898 | 10.033 |
| depth-2 | 2213 | ptc | True | 2 | 7501 | 891 | 8392 | 9.267 |
| depth-2 | 2213 | compute | True | 4 | 14513 | 552 | 15065 | 7.389 |
| depth-3 | 1103 | ptc | True | 3 | 15942 | 3061 | 19003 | 32.506 |
| depth-3 | 1103 | ordinary | False | 5 | 18978 | 2437 | 21415 | 28.154 |
| depth-3 | 1103 | compute | False | 5 | 20448 | 2369 | 22817 | 35.560 |
| depth-3 | 2213 | compute | False | 6 | 25440 | 2521 | 27961 | 26.497 |
| depth-3 | 2213 | ordinary | True | 6 | 23867 | 2662 | 26529 | 31.873 |
| depth-3 | 2213 | ptc | True | 2 | 9004 | 2579 | 11583 | 26.232 |
| width-12 | 1103 | ordinary | True | 5 | 24531 | 4552 | 29083 | 56.126 |
| width-12 | 1103 | compute | True | 6 | 37031 | 4061 | 41092 | 35.043 |
| width-12 | 1103 | ptc | True | 2 | 10147 | 3643 | 13790 | 37.742 |
| width-12 | 2213 | ptc | True | 2 | 9903 | 3385 | 13288 | 32.562 |
| width-12 | 2213 | compute | False | 5 | 25806 | 3725 | 29531 | 33.885 |
| width-12 | 2213 | ordinary | False | 5 | 24967 | 4675 | 29642 | 42.345 |

## All-attempt costs, including wrong answers

| Case | Arm | Correct / attempts | Complete usage | Total tokens | Tokens / correct |
|---|---|---|---|---|---|
| depth-2 | ordinary | 2/2 | 2 | 28365 | 14,182.5 |
| depth-2 | compute | 2/2 | 2 | 30376 | 15,188.0 |
| depth-2 | ptc | 2/2 | 2 | 26587 | 13,293.5 |
| depth-3 | ordinary | 1/2 | 2 | 47944 | 47,944.0 |
| depth-3 | compute | 0/2 | 2 | 50778 | — |
| depth-3 | ptc | 2/2 | 2 | 30586 | 15,293.0 |
| lookup | ordinary | 2/2 | 2 | 9768 | 4,884.0 |
| lookup | compute | 2/2 | 2 | 11242 | 5,621.0 |
| lookup | ptc | 2/2 | 2 | 12774 | 6,387.0 |
| width-12 | ordinary | 1/2 | 2 | 58725 | 58,725.0 |
| width-12 | compute | 1/2 | 2 | 70623 | 70,623.0 |
| width-12 | ptc | 2/2 | 2 | 27078 | 13,539.0 |

## Matched efficiency, conditional on both arms passing

| Case | Role | Baseline → PTC | Pairs | Latency reduction % | Calls reduction % | Input reduction % | Output reduction % | Total reduction % |
|---|---|---|---|---|---|---|---|---|
| depth-2 | primary | ordinary → PTC | 2 | -17.9 | 25.0 | 9.9 | -50.2 | 6.9 |
| depth-2 | secondary | compute → PTC | 2 | -35.4 | 25.0 | 16.3 | -67.0 | 12.7 |
| depth-3 | primary | ordinary → PTC | 1 | 17.7 | 66.7 | 62.3 | 3.1 | 56.3 |
| depth-3 | secondary | compute → PTC | 0 | — | — | — | — | — |
| lookup | primary | ordinary → PTC | 2 | -24.9 | 0.0 | -30.9 | -24.5 | -30.8 |
| lookup | secondary | compute → PTC | 2 | -21.1 | 0.0 | -14.7 | 18.6 | -13.7 |
| width-12 | primary | ordinary → PTC | 1 | 32.8 | 60.0 | 58.6 | 20.0 | 52.6 |
| width-12 | secondary | compute → PTC | 1 | -7.7 | 66.7 | 72.6 | 10.3 | 66.4 |
