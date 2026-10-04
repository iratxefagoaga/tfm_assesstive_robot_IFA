# PARK-01 — final engineering validation with bounded infrastructure retries

Status: **RUNTIME_VALIDATED**. **KINEMATIC_FIX VALIDATED**. Engineering runtime validation only; experimental efficacy is not validated.

HOME remains frozen as previously **RUNTIME_VALIDATED**, with post-fix N0 SUCCEEDED (18.020 s, 2.625 m) and positive N1 waypoint/final evidence including 51.299 s, 6.210 m. HOME was neither modified nor executed in this block. Infrastructure flakes remain a separate limitation.

## Infrastructure retry policy

Infrastructure investigation is closed as **TRANSIENT_INFRASTRUCTURE_INSTABILITY; ROOT_CAUSE = UNKNOWN**. ROS 2/Nav2 showed intermittent lifecycle/readiness/discovery/action-handshake and cleanup failures in the preserved earlier runs. The internal cause was not isolated. No timeout, middleware, physics, navigation tuning, query or BT semantics was modified to favor results. `default_server_timeout` remains 20 ms.

The same policy applies to N0 and N1: one principal attempt and at most one clean retry per repetition (maximum two attempts). A lifecycle/service/discovery/readiness/action-server/bond failure or unexpected critical ROS process exit permits that one retry. A ComputePathToPose SendGoal acknowledgement timeout is operationally classified **INFRASTRUCTURE_ACTION_HANDSHAKE_FAILURE**, without claiming its root cause; recurrence on the retry ends the repetition as **INFRASTRUCTURE_BLOCKED**. A real planner/controller/recovery failure after readiness and accepted navigation is **NAVIGATION_FAILURE** and receives no retry; the block stops as **NAVIGATION_BLOCKED**. No internal retries or added sleeps were introduced.

Navigation and cleanup are recorded separately. A successful navigation followed by SIGKILL remains navigation SUCCEEDED with cleanup FAILED. No subsequent attempt starts unless the environment is verified clean. All failed infrastructure attempts remain in the audit trail and are excluded from efficacy observations. No additional smoke or HOME run was performed.

The current validation uses fresh ROS domains 70 onward and unique Gazebo partitions equally for both conditions, following the already established runner isolation protocol. Temporary execution manager only; no probes, UUID instrumentation or synthetic clients. The legacy runner shown in the historical reproduction section is not the authoritative implementation of this revised policy.

## Current final repetitions — 2026-10-04

Frozen PARK spawn (0,-9,0), final (1,-9,0), west waypoint (-1,-9,0), offset `west:-2.0:0.0`. N1 expected and observed retrieval `M013|M015|M007`, source M013, strategy west.

| Condition | Repetition | Attempt | Classification | Cleanup | Time s | Distance m | Replanning | Waypoint | Final |
|---|---:|---:|---|---|---:|---:|---:|---|---|
| N0 | 1 | 1 | SUCCESS | CLEAN | 4.720 | 0.740 | 4 | N/A | SUCCEEDED |
| N0 | 2 | 1 | SUCCESS | CLEAN | 4.760 | 0.739 | 4 | N/A | SUCCEEDED |
| N1 | 1 | 1 | SUCCESS | CLEAN | 38.380 | 2.999 | 38 | SUCCEEDED | SUCCEEDED |
| N1 | 2 | 1 | SUCCESS | CLEAN | 37.240 | 2.901 | 36 | SUCCEEDED | SUCCEEDED |

All recorded CSVs have the common 35-column header and one finalized row. N0 memory/intervention fields are N/A; N1 strategy_applied is true. Independent min_clearance_m/context_compliance/intervention_appropriate remain N/A. Navigation time and distance are logger metrics; no independent ground truth was fabricated.

Host WSL access briefly returned `Wsl/Service/0x8007274c` during N1 repetition 1. Access subsequently recovered; the navigation completed successfully and cleanup/residue checks passed. This is retained as an operational host-access flake, without attributing a ROS root cause or discarding the run. Startup TF waits before readiness and controller/planner loop-rate warnings are also retained in the full logs and operational_audit.json. No lifecycle/readiness failure or ComputePathToPose acknowledgement timeout blocked these four repetitions.

Precheck: existing installed build usable; current BT suite 58 tests, zero failures/errors/skips; launch syntax and --show-args pass; PARK model/world SDF valid; frozen endpoint map connectivity/clearance checks pass; source and installed PARK map hashes equal. No extra runtime smoke.

DB READ-ONLY: 50 before and after, canonical_memory_fingerprint_v2 unchanged: content `46ea5969b3047c1eb3bc526bb08fbb11b8ddac6f77f18a97e362fcdba9e97898`; embeddings `8f9bf33815930952e3a7ee169d1edb4c7027d5cb5c77c173a3b1a16bb7af2599`.

Artifacts: `/tmp/park_final_policy_34b7114d02a0421392b189247c0c6caf` (attempts.json, individual CSV/logs, active attempt manifest, execution manager, status, DB snapshots, precheck/test logs, before-state checkpoint and integrity verification). No stage/commit/push/reset/branch switch.

## Preserved earlier record — superseded status and retry protocol

The following record is historical. Earlier BLOCKED/PENDING/HOME regression statements and the older runner retry policy are superseded by the current section above; diagnostic failures and physical evidence remain preserved.

# PARK-01 — production collision fix and gated runtime validation

Status: **PARK BLOCKED**. **KINEMATIC_FIX VALIDATED**. This is engineering validation only; runtime navigation and experimental efficacy are not interchangeable. HOME's previous validation remains historical; its regression with the shared collision fix is **NOT RUN / PENDING** because PARK smoke prerequisites failed. No HOME configuration changed.

## Physical diagnosis and causal A/B

The original isolated turn (linear0, angular+0.3, five SIM seconds, then zero for three) gave yaw wheels/odom1.488600rad vs Gazebo1.389334rad:0.099266rad error,6.6684%. Wheel integration, radius0.16m, center separation0.62m, axes/signs and wheel limits were coherent. Independent physical poses showed symmetric longitudinal residual~0.00629m/s per drive wheel and negligible lateral residual. Fixed-vs-ball caster experiment reduced the error only0.0408% with comparable support: **CASTER_FIXED_NOT_MAIN_CAUSE**, investigation closed.

A single controlled A/B changed only drive-wheel collision cylinder length45mm→5mm. A: yaw physical1.389334, error6.6684%; B: yaw physical1.478475, error0.6802%; relative error reduction89.7999%. Supports/height/roll/pitch were comparable. Prediction based on Leff≈0.62+0.005=0.625m: physical steady omega0.297600rad/s; observed0.297607, stable deficit0.7977%. **WHEEL_WIDTH_CAUSAL**: finite cylinder collision width produces effective physical kinematic separation greater than center separation assumed by DiffDrive during turns. This demonstrates the causal effect of collision width; the exact internal DART force/contact point is not known. No more contact/force/caster investigations or tuning were performed.

Evidence: `/tmp/wheelchair_drive_contact_2b1ac92c2c9b48e6b83edc87e522c45b/` and `/tmp/wheelchair_wheelwidth_ab_757f7416e2b04c05a980414c05af4318/`.

## Authorized production fix

Only `ros2/src/wheelchair_gazebo/models/wheelchair/model.sdf`, the two collision cylinder lengths, changed0.045→0.005m. Collision centers unchanged. The represented visual wheel still has45mm width; this is a narrower centered collision approximation to avoid the finite-width contact altering effective turn kinematics in DART. Radius, center separation, joints/axes, mass/inertia, friction/slip, casters, chassis, DiffDrive/odom, Nav2/AMCL and safety remain unchanged. The consumed xacro declares links/joints with no duplicate collision geometry, so it required no edit. Existing dirty changes, including prior axis corrections, were preserved.

## Production verification

Seven-package sequential system-Python build PASS;64 BT tests,0 failures/errors/skips. SDF valid, consumed xacro expansion valid, launch syntax and existing scenario asset validator PASS. No build/install/log deletion. The sole production isolated turn used five SIM seconds and three SIM seconds at zero: wheels1.483800000, odom1.483800000, Gazebo1.473705886rad; deficit0.680288% (criterion≤1.5%). Thus **KINEMATIC_FIX VALIDATED**, consistent with prior A/B. Slight difference in total wheel angle from A/B is compatible with delivered-command timing, not a changed command or duration.

## PARK smoke and gated stop

Candidate unchanged: spawn(0,-9,0), final(1,-9,0), west waypoint(-1,-9,0), offset west:-2.0:0.0. Two attempts: nominal plus one infrastructure retry, fresh ROS domain86 and unique Gazebo partition each. Both readiness PASS and retrieval M013|M015|M007/sourceM013/strategywest. Both waypoint SENT then ABORTED; final NOT_SENT. Logs identify timeout while waiting for acknowledgement of **compute_path_to_pose**, so navigation classification **INFRASTRUCTURE_FAILURE**, not a new physical/Navfn cause.

Attempt1:11.382s,0.614m,11 replannings; clean launch shutdown. Attempt2:0.060s,0m,0 replannings; automatic launch shutdown escalated through SIGTERM to SIGKILL for Gazebo. **CLEANUP_FAILURE** stops the block under the existing failure policy. No manual SIGKILL or broad process kill was issued; expected ROS/Gazebo/observer residues absent afterwards. No third attempt.

Attempt1 captured Gazebo/odom/TF-map/AMCL and ROS bag. Aligned physical/odom discrepancy maximum0.044868m, yaw maximum0.020524rad, physical/map discrepancy maximum0.038671m during this short movement. This materially removes the previous large turn mismatch in the observed segment; it does not establish long-route localization robustness. The isolated production test independently verifies the fix. Do not revert it due to the infrastructure failure.

PARK smoke N0: **NOT RUN**, N1 success gate unmet. HOME N0/N1 regression: **NOT RUN**, PARK gates unmet; no proven HOME regression. Clean final PARK N0 two runs and N1 two runs: **NOT RUN**, prerequisites unmet. PARK remains **BLOCKED**, no2/2 claim. No coordinate/safety/query/controller/BT adjustment made.

## Integrity, CSV and remaining work

DB frozen:50→50; canonical v2 content `46ea5969b3047c1eb3bc526bb08fbb11b8ddac6f77f18a97e362fcdba9e97898`, embeddings `8f9bf33815930952e3a7ee169d1edb4c7027d5cb5c77c173a3b1a16bb7af2599`, identical in all READ-ONLY snapshots. No online learning. Both smoke CSVs have35 columns, one finalized row each, expected retrieval, and independent context_compliance/intervention_appropriate/min_clearance_m=N/A. There are no four final CSVs to validate.

Artifacts: `/tmp/wheelwidth_production_validation_26ed7eab8e6743f08594eda9711e2be1/`: private external checkpoint, before-state hashes/diff/status, fix-only diff, semantic proof, static/build/test logs, isolated turn, two smoke attempts with bags/poses/logs/CSV, classifications and DB fingerprints. A temporary manager reporting error (joining a deliberately disabled audit thread) occurred after attempt1 capture/cleanup; it was fixed only in /tmp and required no extra navigation run. Capture remained valid.

Remaining: known action acknowledgement/discovery/lifecycle and shutdown instability; HOME post-fix regression pending; final PARK paired validation pending; independent scientific ground truth/compliance pending. No new physics investigation. No commit/push/reset/stage/branch switch or remote contact.

## Historical pre-fix record (superseded diagnosis/status)

The following preserved record describes earlier attempts before the shared collision fix. Its old assertions about no wheelchair change, root cause unisolated, and next physics investigation are historical and superseded above.

# PARK-01 — engineering validation of one memory-derived west waypoint

Status: **BLOCKED**. The final paired validation stopped on a real N1 navigation failure. No PARK configuration is frozen as RUNTIME_VALIDATED. These runs are engineering validation, not evidence for H1/H2/H3 or memory efficacy.

## Latest reproducible candidate (not validated)

- Current `park` world/model and deterministic `park.pgm`/YAML; same wheelchair as validated HOME.
- Spawn `(0.0,-9.0,yaw=0.0)`, z `0.11`.
- Final goal `(1.0,-9.0,yaw=0.0)` for N0 and N1.
- N0: strict Nav2 readiness → final goal → finalize.
- N1: memory query → recommendation → resolver → one west waypoint `(-1.0,-9.0,yaw=0.0)` → final goal → finalize, with readiness before each navigation goal.
- Goal-relative offset: `west:-2.0:0.0`.
- Shared Nav2 unchanged: Navfn/GridBased, regulated pure pursuit, desired speed 0.20, minimum scaling speed 0.05, footprint `[[0.36,0.34],[0.36,-0.34],[-0.36,-0.34],[-0.36,0.34]]`, inflation 0.70, obstacle/collision checking and recoveries retained. No timeout or sleep increased.

Frozen retrieval remains query `repetir ruta oeste habitual rodeando el jardin central`, U01, park, navegacion, semantic goal `salida_norte`, k=3. Expected/observed `M013|M015|M007`, source `M013`, strategy `west`. No dataset, parser, retrieval, ranking or embedding change.

The shortened route stays in the broad southern open area. N0 proceeds east directly; N1 first takes a west excursion, then reaches the same goal. It is a west alternative relative to both spawn and final goal, not a full circumnavigation of the central garden or physical arrival at the northern exit. The semantic query/goal label are retained from the existing retrieval case. Independent ground truth must be defined for this actual route before scientific evaluation. The former y=0/x≤-7 proposal does not apply here.

`context_compliance`, `intervention_appropriate` and `min_clearance_m` stay N/A; never derive them from expected strategy, strategy_applied or source memory. CSV schema remains 35 columns. Initial pose metrics are recorded in odometry coordinates; the controlled map/Gazebo spawn is documented above.

## Why calibration changed

The first runtime used the original `(0,-9) → (0,9)` configuration after the wheelchair axis correction, without calibration changes. Readiness passed and a goal was sent, but the controller detected collision/patience exceeded; Navfn then failed repeatedly from estimated pose `(1.29,-4.16)` adjacent to the garden's south boundary. Result: ABORTED. This reproduced a navigation failure, not a missing readiness/action failure. The exact localization/controller contribution to reaching that pose was not isolated; no new Navfn defect is claimed.

The source/installed map was already aligned with geometry: deterministic regeneration to `/tmp/park_geometry_check.pgm` matched SHA-256 `f0a1a1e22b5ca85106e136160e28dec428ea33bf96f398902726aa0fe05dfd06`. No geometry or map was edited. SDF model and world validate.

Static screening selected a broad southern route. Spawn/final are in the same connected component after a conservative 0.70 m distance mask; all final straight segments have at least 2.70 m center-to-static-obstacle clearance. This is diagnostic screening, not an experimental min-clearance metric or a proof of Navfn feasibility.

The first longer west candidate `(-3,-6.5)` aborted near arrival with controller `Resulting plan has 0 poses in it`. This was recorded as navigation failure, not infrastructure. The first leg was shortened to `(-1,-8)` while keeping the already-successful spawn/final fixed. An initial attempt at this waypoint aborted before moving on action acknowledgement timeout; its generated plan arrived later (55 poses). Gazebo also required automatic launch shutdown escalation in that attempt. These are preserved infrastructure/cleanup failures, not final repetitions.

The shorter west candidate reached its waypoint but failed on the final leg. During the failure period, a Gazebo pose snapshot was approximately `(2.57,-6.19)` while Navfn repeatedly reported start `(0.62,-4.17)`: a substantial physical/estimated pose discrepancy placed the estimated robot against the garden. No further random coordinates or geometry changes were made. The final local task limits all nominal robot-center positions to x∈[-1,1], y=-9, with N0 nominal length 1 m and N1 nominal length 3 m plus turns. It tests the strategy execution mechanism only; it does not fix localization on longer routes. Evidence: `/tmp/park_short_physical_pose_3.json`, `/tmp/park_short_n1_3.log`.

On the minimal configuration, N0 succeeded and N1 completed both goals in a calibration retry, but default shared-domain launches still exhibited action-acknowledgement and shutdown escalation failures. Final repetitions therefore isolate the ROS domain and Gazebo transport partition per attempt, equally for N0/N1; this changes only the PARK runner process environment. No middleware, Nav2 or HOME setting was changed. This is a reproducible namespace-isolation protocol, not a claimed production fix or proof of the underlying infrastructure cause.

Diagnostic artifacts: `/tmp/park_current_n0.log`, `/tmp/park01_n0.csv` (historical and diagnostic rows preserved), `/tmp/park_preexisting_n0_csv_preserved_20261004.csv`, `/tmp/park_short_n0_1.*`, `/tmp/park_short_n1_*`, `/tmp/park_pose_plan_probe.jsonl`, `/tmp/park_static_validation.txt` and `/tmp/park_asset_validation.txt`.

## Reproduction

Build using system Python from repository root:

```bash
deactivate 2>/dev/null || true
source /opt/ros/jazzy/setup.bash
test "$(command -v python3)" = /usr/bin/python3
cd ros2
CMAKE_BUILD_PARALLEL_LEVEL=1 colcon build --symlink-install --executor sequential
cd ..
```

Load private MEMORY_DB_* values without displaying credentials; use the cached embedding model. Then:

```bash
PARK01_ATTEMPTS=2 bash scripts/experiments/run_park01_headless.sh
```

The PARK-specific runner uses isolated ROS/Gazebo namespaces and reuses HOME's failure policy without modifying the HOME runner: paired fresh launches, unique IDs/CSV paths under a new `/tmp/park01_<uuid>` directory, at most two fresh retries for explicitly identified lifecycle/discovery/action acknowledgement failures per condition/repetition. Controller collision, no-path, empty transformed plan or generic ABORTED are not relabeled infrastructure. Navigation or shutdown escalation stops the block. Shutdown child exits after successful goals are reported separately. The runner sends a single interrupt to its owning launch when needed, waits, and never issues broad pkill or a SIGKILL timeout fallback. Each run records ROS_DOMAIN_ID/GZ_PARTITION in `run_manifest.jsonl`; domains are allocated from `PARK01_DOMAIN_BASE` (default 60) and Gazebo partitions use unique run IDs. All children of one run inherit the same namespace. PGOPTIONS forces read-only transactions; canonical v2 fingerprints are captured before/after.

The PARK wrappers now declare their arguments so externally supplied run IDs and result paths actually reach the included navigation launch. Previously they overwrote these with fixed values.

Individual runs:

```bash
ROS_DOMAIN_ID=60 GZ_PARTITION=park_unique_n0 ros2 launch wheelchair_assistive_bt park_n0.launch.py gui:=false result_csv:=/tmp/park_n0_<unique>.csv run_id:=<unique>
ROS_DOMAIN_ID=63 GZ_PARTITION=park_unique_n1 ros2 launch wheelchair_assistive_bt park_n1.launch.py gui:=false result_csv:=/tmp/park_n1_<unique>.csv run_id:=<unique>
```

## Final attempted validation / concrete blocker

The final isolated batch did not pass: N0 repetition 1 succeeded; N1 repetition 1 retrieved the expected episode, succeeded at the waypoint, then aborted the final goal. The runner stopped on that NAVIGATION_FAILURE; no second pair was run and no 2/2 result is claimed.

| Run | Attempt | Result | Waypoint | Final | navigation_time_s | distance_m |
|---|---:|---|---|---|---:|---:|
| `park_n0_1_1_29d5378534fd4589ad263cd6d7da9d3d` | 1 | SUCCEEDED | N/A | SUCCEEDED | 4.680 | 0.737 |
| `park_n1_1_1_79ba8260f5214b23b156f42dd4810830` | 1 | ABORTED | SUCCEEDED | ABORTED | 67.880 | 2.536 |

Evidence: `/tmp/park01_60b621f29fb74f0e9b993fc5587cb3f5/summary.tsv`, two unique CSVs and logs, `run_manifest.jsonl`, `db_before.json` and `db_after.json`; runner log `/tmp/park_final_runner.log`. ROS domains were 60 (N0) and 63 (N1), each with its unique run-ID Gazebo partition. Neither final launch required shutdown escalation or left process residues.

The final N1 repeatedly failed to plan from estimated pose `(0.27,-11.48)` to `(1,-9)`; the estimated robot was only about 0.22 m from the occupied south boundary, within the footprint/inscribed obstacle region. The nominal route had all y=-9 and 2.70 m static clearance. The earlier direct Gazebo/estimated-pose contrast on the longer candidate establishes that physical and navigation poses can disagree by meters. This cannot be certified as robust navigation merely by shortening goals, and it is not an action-discovery failure in this final run. No planner/controller/safety change was made to force success. The exact cause of the localization disagreement is not isolated; no production fix is claimed.

The minimal candidate had a calibration N0 success (`park_minimal_n0_1`) and a calibration N1 success (`park_short_n1_5`, 32.296 s, 2.748 m), but the latter needed Gazebo/bridge shutdown escalation. These were not counted as final repetitions. Selecting only those successes would conceal the demonstrated fragility.

DB: 50 rows before/after, canonical v2 content hash `46ea5969b3047c1eb3bc526bb08fbb11b8ddac6f77f18a97e362fcdba9e97898`, embedding hash `8f9bf33815930952e3a7ee169d1edb4c7027d5cb5c77c173a3b1a16bb7af2599`, both identical to the pre-diagnostic fingerprint. All recorded final CSVs retain the common 35 columns; N0 memory fields and all independent evaluation metrics remain N/A. There are two valid final CSVs, not four successful final CSVs.

Validation: 7-package system-Python sequential build; 64 BT tests passed (0 failures/errors/skips); PARK model/world SDF valid; deterministic map equality; endpoint/segment clearance and conservative connectivity screening; PARK wrappers Python compilation and runner syntax check. Relevant logs: `/tmp/park_final_build.log`, `/tmp/park_final_tests.log`, `/tmp/park_static_validation_final.txt` and `/tmp/park_asset_validation_final.txt`.

Changed in this block: `park_n0.launch.py` / `park_n1.launch.py` (candidate coordinates and externally configurable launch arguments), new `run_park01_headless.sh` (isolated, read-only paired validation and failure policy), this document and the PARK portion/status of `SCENARIO_MATRIX.md`. No PARK geometry/map or shared runtime source was changed.

Next necessary investigation is the map/scan/TF/physical-pose inconsistency during rotations and replanning. The raw occupancy map matching SDF footprints does not prove that AMCL has observable, consistent LiDAR features. A change to sensing/localization or PARK geometry is not justified quantitatively enough here to apply blindly. Full-route validity and independent scientific compliance remain unvalidated. HOME is not reopened.

## HOME and remaining limits

No HOME geometry, map, coordinates, query, waypoint, shared Nav2, wheelchair, joints, BT, memory worker or HOME runner were changed in this block. Protected source/asset hashes remain identical. HOME remains RUNTIME_VALIDATED; another HOME runtime campaign is not required for PARK-only configuration and documentation changes.

Known lifecycle/discovery/action-acknowledgement instability is not claimed fixed. Earlier Gazebo shutdown escalation is retained as a real infrastructure limitation. Engineering navigation success is not independent context compliance, a scientific campaign, or evidence of memory efficacy.

Repository note: PARK_01.md is currently ignored by the existing ignore rules. It is preserved locally; no staging or ignore-rule change was performed. Tracked pre-existing diff is byte-identical to the pre-block snapshot.
