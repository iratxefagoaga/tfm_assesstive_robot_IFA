# E1 technical runtime validation — 2026-10-05

E1_RUNTIME_MEASUREMENT_VALIDATED. Engineering evidence only: excluded from E1 campaign and H1 analysis.

The exact-current-/clock lookup failed with future ExtrapolationException at approximately 989 callbacks per simulation second. Initial map absence was separately observed. capture_trajectory now samples at 10 Hz, waits for initial TF, uses latest common TF with transform.header.stamp, and retains post-start errors. No manually invented, smoothed or interpolated positions and no classifier/threshold changes.

Diagnostic: /home/iratxefagoaga/tfm-runtime-validation/20261005T152200_e1_capture_diagnostic
Validation: /home/iratxefagoaga/tfm-runtime-validation/20261005T152457_e1_capture_fixed_validation
N0: 253 samples, zero TF errors, max gap 0.100 s, max segment 0.03113 m, endpoint 0.23648 m, direct.
N1: 498 samples, zero TF errors, max gap 0.100 s, max segment 0.04362 m, endpoint 0.24464 m, west.
Both: navigation SUCCEEDED, 36-column CSV, raw consumed without editing, initial/offline replay byte-identical and no cleanup residues.

experiments/runtime/e1_runtime_validation.json records source, frozen input, validation record and artifact hashes. The E1 guard checks preserved evidence; missing/mutated evidence fails closed. Scientific freeze and historical documentation remain intact.

The existing E1 CLI branch emits the frozen 40-job plan. E1 --execute now checks this technical guard before emitting that plan; neither mode launches the campaign. Campaign process supervision remains outside this technical validation change.

## Post-race evidence after global WSL recovery — 2026-10-05

The preceding evidence is historical. Current certificate uses the preserved N0 at 20261005T154747_e1_capture_race_postfix_validation/N0 (287 samples, zero errors) and the single new N1 at 20261005T185514_e1_n1_global_recovery_revalidation/N1 (515 samples, zero errors, gap 0.220 s, segment 0.040 m, endpoint 0.244 m, west, context compliance 1). Both succeeded, have 36-column final CSVs and byte-identical offline replay. N0 was not repeated. Interrupted N1 evidence remains preserved and excluded. The 10 Hz ROS timer retains actual TF timestamps and removes the invalid comparison against an older clock snapshot. The guard implementation and all five scientific hashes remain unchanged. Both technical runs are excluded from E1/H1. Host stability passed 90 seconds; the original DB retained count 50 and both fingerprints in READ-ONLY checks.
