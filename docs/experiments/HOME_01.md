# HOME-01 — memory strategy integration in the current HOME

Status: **RUNTIME_VALIDATED**. This is engineering runtime validation, not an efficacy result or the scientific campaign.

## Final configuration

Both conditions use the current HOME world/map, the same wheelchair, the same shared Nav2 parameters and the same initial/final poses:

- Spawn / AMCL initial pose: `(2.0, -6.0, yaw=0.0)`, spawn z `0.11`.
- Final goal: `(4.0, -4.0, yaw=0.0)`.
- N0: readiness → final goal → finalize.
- N1: canonical retrieval → recommendation → one `west` waypoint `(0.0, -4.0, yaw=0.0)` → final goal → finalize. Offset: `west:-4.0:0.0` relative to the final goal.
- Footprint remains `[[0.36,0.34],[0.36,-0.34],[-0.36,-0.34],[-0.36,0.34]]`; inflation remains `0.70 m`; Navfn/GridBased, regulated pure pursuit, collision checking and recoveries remain enabled.
- Desired velocity `0.20 m/s`; `regulated_linear_scaling_min_speed=0.05` is now explicit in the shared YAML. No timeout or sleep was increased.

The route is deliberately limited to the broad southern living area. Straight-segment geometric screening found minimum center-to-static-obstacle distances of approximately 2.19 m (N0/final segment) and 2.72 m (west segment). These are screening values, not measured experimental `min_clearance_m` and not a substitute for Nav2 runtime.

The unchanged retrieval context is query `navegar evitando la mesa`, U01, salon, navegacion, goal label `dormitorio`, k=3. Expected/observed IDs are `M001|M046|M002`, source `M001`, strategy `west`.

The physical goal is in the southern living area, not the bedroom. `dormitorio` remains the existing semantic retrieval label. This minimum experiment validates execution of a memory-derived west excursion; it does not yet demonstrate table-crossing compliance or arrival in the bedroom. Freeze an independent, applicable trajectory ground truth separately before scientific use. `context_compliance`, `intervention_appropriate` and `min_clearance_m` remain N/A.

## Defects established during calibration (2026-10-03)

1. The checked-out/installed HOME PGM was stale relative to the current SDF: dining-table and northern-partition occupancy differed. Regenerating `home.pgm` from the existing SDF restores exact deterministic correspondence; no HOME geometry was moved. Generated/source/installed map SHA-256: `404c64197089bd17008a0c78044ba7c83ea2de1db48574056862d60bb51a8034`.
2. Wheel joint axes were expressed in rolled child/joint frames. With wheel roll π/2, local `(0,1,0)` points vertically in the model frame rather than along the axle. During a Nav2 west-goal diagnostic, Gazebo reported approximately `(2.031,-6.060,yaw=-0.222)` while odometry reported `(-0.775,0.737,yaw≈2.40)` relative to the start. This explains severe wheel-odometry/physical-motion disagreement; localization/costmap/planner failures were downstream symptoms. Both SDF and URDF now use local `(0,0,-1)`, equivalent to model +Y. Same robot geometry, masses, friction and safety settings are retained. Frame semantics: https://sdformat.org/spec/1.9/joint/.
3. The effective controller minimum speed was 0.25 despite desired speed 0.20. The requested 0.05 is restored explicitly.
4. The dedicated embedding worker completed ROS cleanup but hung in native interpreter finalization (diagnostic traceback: no Python frame). It now disposes its DB pool and exits the dedicated worker after successful ROS cleanup, bypassing that native finalization. Exceptions retain normal error propagation. This is a process-lifecycle workaround; the underlying native-library cause remains unknown.

Initial diagnostics include `/tmp/home_reproduce_n0*.log`, `/tmp/home_west_diagnostic.log`, `/tmp/home_axes_west*.log` and `/tmp/home_south_n1_*.log`. Earlier successes/failures used intermediate configurations and are not final repetitions.

## Reproduction and failure policy

Build from the repository root with system Python, never the memory interpreter:

```bash
deactivate 2>/dev/null || true
source /opt/ros/jazzy/setup.bash
test "$(command -v python3)" = /usr/bin/python3
cd ros2
CMAKE_BUILD_PARALLEL_LEVEL=1 colcon build --symlink-install --executor sequential
cd ..
```

Load the private MEMORY_DB_* variables without displaying credentials, then run:

```bash
HOME01_ATTEMPTS=2 bash scripts/experiments/run_home01_headless.sh
```

The runner defaults to paired N0/N1, fresh launches, unique run IDs and a new `/tmp/home01_<uuid>` evidence directory. It requires a pre-cached embedding model (`HF_HUB_OFFLINE=1`), forces read-only DB transactions and measures canonical v2 fingerprints before/after. No seed/provisioning/write operation is performed. `HOME01_CONDITION=n0` or `n1` restricts the condition.

For both conditions, allow at most two fresh-launch retries per repetition for explicitly identified lifecycle/discovery/action-acknowledgement failures. Preserve their CSV/logs separately. Do not reclassify controller collision, Navfn no-path or generic ABORTED as infrastructure. Navigation failure or shutdown escalation stops validation. A child exit warning after successful navigation is recorded separately and remains a cleanup limitation. The runner sends an interrupt only to its owning launch if necessary, waits for it and never uses broad pkill or a SIGKILL timeout fallback.

Individual launches:

```bash
ros2 launch wheelchair_assistive_bt home_n0.launch.py gui:=false result_csv:=/tmp/home_n0_<unique>.csv run_id:=<unique>
ros2 launch wheelchair_assistive_bt home_n1.launch.py gui:=false result_csv:=/tmp/home_n1_<unique>.csv run_id:=<unique>
```

The 35-column CSV is unchanged. Its `initial_*` metrics come from odometry, whose initial origin can be `(0,0)`, not the Gazebo/map spawn; the common map spawn is fixed in the launch and documented above.

## Final runtime evidence

**HOME = RUNTIME_VALIDATED** for this engineering configuration, with the separate infrastructure limitation below. On 2026-10-03 the final headless runner completed two fresh paired repetitions (four launches), all successful on attempt 1, without manual intervention or cleanup escalation.

| Condition / repetition | Final Nav2 | Waypoint Nav2 | navigation_time_s | distance_m |
|---|---|---|---:|---:|
| N0 / 1 | SUCCEEDED | N/A | 29.720 | 2.651 |
| N1 / 1 | SUCCEEDED | SUCCEEDED | 61.978 | 6.166 |
| N0 / 2 | SUCCEEDED | N/A | 23.940 | 2.646 |
| N1 / 2 | SUCCEEDED | SUCCEEDED | 64.420 | 6.286 |

Both N1 runs returned `M001|M046|M002`, source `M001`, strategy `west`, `strategy_applied=true`, selected waypoint `(0,-4)`. Every run passed external readiness, dispatched its expected goals and produced exactly one final row with the common 35-column schema. A direct Gazebo pose-topic capture during the second N1 confirmed physical northwest motion at approximately `(1.655,-5.471,yaw=2.36)`; this was not just an odometry-only result.

Evidence directory: `/tmp/home01_48208ee408d945f985d48628e3198b81`, containing `summary.tsv`, four unique CSVs/logs and `db_before.json`/`db_after.json`; runner log `/tmp/home_final_runner.log`. Run IDs:

- `home_n0_1_1_108add8e767b4513ab83839698dac719`
- `home_n1_1_1_07ae3d69b4e145fbba914389298f5a0b`
- `home_n0_2_1_01044bc3e99d4117bdf711218c227215`
- `home_n1_2_1_eb24ad6cfa1749f4be95a4d29e3b8a4c`

DB remained read-only: 50 rows before/after, canonical v2 logical hash `46ea5969b3047c1eb3bc526bb08fbb11b8ddac6f77f18a97e362fcdba9e97898`, embedding hash `8f9bf33815930952e3a7ee169d1edb4c7027d5cb5c77c173a3b1a16bb7af2599`; both hashes also match the fingerprint taken before the diagnostic runs.

Validation: system-Python sequential colcon build (7 packages), `gz sdf -k` wheelchair model (`Valid`), exact regenerated/source/installed HOME-map comparison, shell syntax check, Python compilation, and real BT package tests (64 tests, 0 failures/errors/skips). Logs: `/tmp/home_build_axes.log`, `/tmp/home_final_tests.log`. No commit/push/reset/staging or remote Git operation was performed.

`git diff --check` still reports pre-existing CRLF line-ending whitespace in other user-modified files. `git -c core.whitespace=cr-at-eol diff --check` passes. Existing unrelated changes were preserved; this is not a clean working tree.

One final run (`home_n1_2_1_eb24ad6cfa1749f4be95a4d29e3b8a4c`) had a shutdown-only bridge failure: after both goals succeeded and launch sent SIGINT, `parameter_bridge` threw `std::system_error: Invalid argument` and exited -6. No process residues remained; the memory worker closed normally. Navigation success and this cleanup warning must remain separate. The runner reports child exits separately from CSV navigation outcomes.

Known lifecycle/discovery/action-acknowledgement instability remains a separate infrastructure limitation. No production fix for its underlying cause is claimed. Readiness checks cannot guarantee that a lifecycle node will not fall immediately afterwards. The wheel-axis correction is shared with other environments; PARK/AIRPORT/apartment outcomes are not validated by HOME. Scientific compliance ground truth, clearance measurement and the full campaign remain separate work.
