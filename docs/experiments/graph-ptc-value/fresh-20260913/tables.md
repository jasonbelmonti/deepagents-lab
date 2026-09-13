# Fresh campaign: reproducible tables

Measured main: cb919679e221b39541d928358830f9b39f8d5124. No historical pilot rows are included.

Correct means the complete task, including exact JSON, ranking and supporting paths. All failures remain charged. Positive reductions favor PTC; a dash means undefined or no eligible pair.

## Every attempt

| Case | Seed | Arm | Correct | Error / failed checks | Calls | Input tokens | Output tokens | Total tokens | Seconds |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lookup | 39047 | ordinary | True | — | 2 | 4811 | 71 | 4882 | 6.469 |
| lookup | 39047 | compute | True | — | 2 | 5525 | 163 | 5688 | 4.501 |
| lookup | 39047 | ptc | True | — | 2 | 6300 | 92 | 6392 | 7.939 |
| lookup | 58271 | ptc | False | ValueError | 1 | 3099 | 318 | 3417 | 5.313 |
| lookup | 58271 | compute | True | — | 3 | 9773 | 266 | 10039 | 5.559 |
| lookup | 58271 | ordinary | True | — | 2 | 4810 | 70 | 4880 | 2.749 |
| lookup | 76493 | compute | True | — | 2 | 5427 | 69 | 5496 | 3.567 |
| lookup | 76493 | ptc | True | — | 2 | 6286 | 82 | 6368 | 4.034 |
| lookup | 76493 | ordinary | True | — | 2 | 4806 | 70 | 4876 | 2.535 |
| lookup | 91807 | ordinary | True | — | 2 | 4822 | 74 | 4896 | 4.289 |
| lookup | 91807 | ptc | True | — | 2 | 6579 | 363 | 6942 | 6.813 |
| lookup | 91807 | compute | True | — | 3 | 9448 | 368 | 9816 | 7.824 |
| depth-2 | 39047 | compute | True | — | 5 | 20086 | 1472 | 21558 | 22.042 |
| depth-2 | 39047 | ptc | True | — | 2 | 7738 | 1130 | 8868 | 12.258 |
| depth-2 | 39047 | ordinary | True | — | 4 | 13314 | 1033 | 14347 | 12.096 |
| depth-2 | 58271 | ordinary | True | — | 4 | 13359 | 1132 | 14491 | 14.379 |
| depth-2 | 58271 | ptc | True | — | 2 | 7908 | 1312 | 9220 | 12.058 |
| depth-2 | 58271 | compute | True | — | 4 | 14627 | 1094 | 15721 | 11.297 |
| depth-2 | 76493 | ptc | True | — | 2 | 7758 | 1152 | 8910 | 11.365 |
| depth-2 | 76493 | ordinary | True | — | 4 | 13385 | 695 | 14080 | 11.550 |
| depth-2 | 76493 | compute | False | answer_correct | 4 | 14634 | 656 | 15290 | 8.836 |
| depth-2 | 91807 | compute | True | — | 4 | 14674 | 391 | 15065 | 7.830 |
| depth-2 | 91807 | ordinary | True | — | 4 | 13432 | 440 | 13872 | 8.341 |
| depth-2 | 91807 | ptc | True | — | 2 | 7944 | 1343 | 9287 | 13.979 |
| depth-3 | 39047 | ptc | True | — | 4 | 21407 | 3099 | 24506 | 26.996 |
| depth-3 | 39047 | ordinary | False | answer_correct | 5 | 19086 | 2617 | 21703 | 27.353 |
| depth-3 | 39047 | compute | True | — | 6 | 26071 | 2820 | 28891 | 25.617 |
| depth-3 | 58271 | compute | False | answer_correct | 6 | 29658 | 4245 | 33903 | 34.406 |
| depth-3 | 58271 | ordinary | True | — | 5 | 19198 | 3188 | 22386 | 26.279 |
| depth-3 | 58271 | ptc | True | — | 2 | 9146 | 2550 | 11696 | 19.944 |
| depth-3 | 76493 | ordinary | False | answer_correct | 5 | 19340 | 1695 | 21035 | 20.557 |
| depth-3 | 76493 | compute | False | answer_correct | 5 | 20703 | 1441 | 22144 | 17.562 |
| depth-3 | 76493 | ptc | True | — | 2 | 8094 | 1581 | 9675 | 14.850 |
| depth-3 | 91807 | ptc | True | — | 2 | 8708 | 2108 | 10816 | 17.521 |
| depth-3 | 91807 | compute | True | — | 5 | 20951 | 2427 | 23378 | 21.781 |
| depth-3 | 91807 | ordinary | False | answer_correct | 8 | 34970 | 2536 | 37506 | 31.854 |
| width-12 | 39047 | ordinary | False | answer_correct | 5 | 24884 | 3758 | 28642 | 31.197 |
| width-12 | 39047 | compute | False | answer_correct | 5 | 26315 | 3563 | 29878 | 27.868 |
| width-12 | 39047 | ptc | False | answer_correct, interpreter_ok | 2 | 9170 | 2753 | 11923 | 22.186 |
| width-12 | 58271 | ptc | True | — | 2 | 9176 | 2789 | 11965 | 16.554 |
| width-12 | 58271 | compute | False | answer_correct | 5 | 26679 | 4187 | 30866 | 33.367 |
| width-12 | 58271 | ordinary | False | answer_correct | 6 | 32594 | 4534 | 37128 | 38.035 |
| width-12 | 76493 | compute | False | answer_correct | 6 | 38403 | 4859 | 43262 | 36.137 |
| width-12 | 76493 | ptc | True | — | 2 | 9089 | 2616 | 11705 | 21.719 |
| width-12 | 76493 | ordinary | False | answer_correct | 5 | 25053 | 3391 | 28444 | 31.350 |
| width-12 | 91807 | ordinary | False | answer_correct | 5 | 25548 | 3415 | 28963 | 33.343 |
| width-12 | 91807 | ptc | True | — | 4 | 24878 | 4144 | 29022 | 34.837 |
| width-12 | 91807 | compute | False | answer_correct | 6 | 33914 | 3398 | 37312 | 28.689 |
| security-two-connectors | 39047 | compute | False | answer_correct | 9 | 47265 | 3384 | 50649 | 34.939 |
| security-two-connectors | 39047 | ptc | False | answer_correct, interpreter_ok | 2 | 8706 | 2110 | 10816 | 19.905 |
| security-two-connectors | 39047 | ordinary | True | — | 6 | 24620 | 2664 | 27284 | 28.432 |
| security-two-connectors | 58271 | ordinary | False | answer_correct | 5 | 19506 | 2146 | 21652 | 26.204 |
| security-two-connectors | 58271 | ptc | True | — | 2 | 8286 | 1689 | 9975 | 15.482 |
| security-two-connectors | 58271 | compute | True | — | 5 | 20623 | 2038 | 22661 | 19.368 |
| security-two-connectors | 76493 | ptc | True | — | 6 | 30519 | 2477 | 32996 | 27.818 |
| security-two-connectors | 76493 | ordinary | False | answer_correct | 5 | 19693 | 2708 | 22401 | 31.250 |
| security-two-connectors | 76493 | compute | False | answer_correct | 5 | 21030 | 3015 | 24045 | 38.246 |
| security-two-connectors | 91807 | compute | False | answer_correct | 6 | 29208 | 2565 | 31773 | 24.301 |
| security-two-connectors | 91807 | ordinary | False | answer_correct | 5 | 19244 | 2144 | 21388 | 21.480 |
| security-two-connectors | 91807 | ptc | True | — | 2 | 9338 | 2739 | 12077 | 24.774 |

## All-attempt costs

| Case | Arm | Correct / attempts | Complete usage | Total tokens | Tokens / correct |
| --- | --- | --- | --- | --- | --- |
| depth-2 | ordinary | 4/4 | 4 | 56790 | 14,197.50 |
| depth-2 | compute | 3/4 | 4 | 67634 | 22,544.67 |
| depth-2 | ptc | 4/4 | 4 | 36285 | 9,071.25 |
| depth-3 | ordinary | 1/4 | 4 | 102630 | 102,630.00 |
| depth-3 | compute | 2/4 | 4 | 108316 | 54,158.00 |
| depth-3 | ptc | 4/4 | 4 | 56693 | 14,173.25 |
| lookup | ordinary | 4/4 | 4 | 19534 | 4,883.50 |
| lookup | compute | 4/4 | 4 | 31039 | 7,759.75 |
| lookup | ptc | 3/4 | 4 | 23119 | 7,706.33 |
| security-two-connectors | ordinary | 1/4 | 4 | 92725 | 92,725.00 |
| security-two-connectors | compute | 1/4 | 4 | 129128 | 129,128.00 |
| security-two-connectors | ptc | 3/4 | 4 | 65864 | 21,954.67 |
| width-12 | ordinary | 0/4 | 4 | 123177 | — |
| width-12 | compute | 0/4 | 4 | 141318 | — |
| width-12 | ptc | 3/4 | 4 | 64615 | 21,538.33 |

## Matched efficiency

Median per-seed percent reductions, conditional on both arms passing. Cases are never pooled.

| Case | Role | Baseline → PTC | Pairs | Latency reduction % | Calls reduction % | Input reduction % | Output reduction % | Total reduction % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| depth-2 | primary | ordinary → PTC | 4 | 0.13 | 50.00 | 41.37 | -40.83 | 36.55 |
| depth-2 | secondary | compute → PTC | 3 | -6.74 | 50.00 | 45.94 | -19.93 | 41.35 |
| depth-3 | primary | ordinary → PTC | 1 | 24.11 | 60.00 | 52.36 | 20.01 | 47.75 |
| depth-3 | secondary | compute → PTC | 2 | 7.09 | 46.67 | 38.16 | 1.63 | 34.46 |
| lookup | primary | ordinary → PTC | 3 | -58.84 | 0.00 | -30.95 | -29.58 | -30.93 |
| lookup | secondary | compute → PTC | 3 | -13.08 | 0.00 | -14.03 | 1.36 | -12.38 |
| security-two-connectors | primary | ordinary → PTC | 0 | — | — | — | — | — |
| security-two-connectors | secondary | compute → PTC | 1 | 20.06 | 60.00 | 59.82 | 17.12 | 55.98 |
| width-12 | primary | ordinary → PTC | 0 | — | — | — | — | — |
| width-12 | secondary | compute → PTC | 0 | — | — | — | — | — |
