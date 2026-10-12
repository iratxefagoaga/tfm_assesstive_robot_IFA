# E1 — acquisition and frozen analysis closed

40 valid observations; 46 physical attempts. 34 SUCCEEDED, 6 ABORTED; 3 invalid measurements and 3 infrastructure attempts preserved and excluded.

## Primary: context_compliance

| Scenario | Condition | Total | Evaluable | Compliant | Non-compliant | N/A | Coverage | Compliance among evaluable |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| home | N0 | 10 | 10 | 0 | 10 | 0 | 100% | 0% |
| home | N1 | 10 | 10 | 10 | 0 | 0 | 100% | 100% |
| park | N0 | 10 | 10 | 0 | 10 | 0 | 100% | 0% |
| park | N1 | 10 | 4 | 4 | 0 | 6 | 40% | 100% |
| aggregate | N0 | 20 | 20 | 0 | 20 | 0 | 100% | 0% |
| aggregate | N1 | 20 | 14 | 14 | 0 | 6 | 70% | 100% |

N/A remains missing evidence and is not converted into non-compliance. PARK is limited directional transfer. No clearance, physical avoidance, shorter-distance or shorter-time claims.

- home: difference 100 percentage points; Fisher p=1.08250882e-05; risk difference=1.000; Holm p=2.165017644893806e-05.
- park: difference 100 percentage points; Fisher p=0.000999000999; risk difference=1.000; Holm p=0.000999000999000999.
- aggregate: difference 100 percentage points; Fisher p=7.18403377e-10; risk difference=1.000; Holm p=not applied to pooled aggregate.

## Secondary

| Scenario | Condition | Navigation successes | Mean time (s), all valid outcomes | Mean distance (m), all valid outcomes | Mean replans |
|---|---|---:|---:|---:|---:|
| home | N0 | 10/10 | 19.618 | 2.668 | 18.7 |
| home | N1 | 10/10 | 46.044 | 6.212 | 45.1 |
| park | N0 | 10/10 | 4.980 | 0.738 | 4.2 |
| park | N1 | 4/10 | 52.422 | 2.474 | 44.3 |

Continuous inferential comparisons use successful navigation only; six ABORTED outcomes remain valid observations. Full frozen tests, correction, effect sizes, 20 N1 recommendation records, all attempts, DB fingerprints and five scientific hashes are in final_e1_report.json.

DB READ-ONLY: count 50; logical 46ea5969b3047c1eb3bc526bb08fbb11b8ddac6f77f18a97e362fcdba9e97898; embeddings 8f9bf33815930952e3a7ee169d1edb4c7027d5cb5c77c173a3b1a16bb7af2599.

All source identities and runtime certificate intact. No code/threshold/design changes; no stage, commit, push, merge, reset or clean. No E2/E3/AIRPORT.

Git: scenario-home 596f54c83c343c0a8e40e092478ec21783fd948a

NEXT STEP: HUMAN_INTERPRETATION_E1_AND_FINAL_H1_H2_H3_SYNTHESIS.
