# AIRPORT-01 — dynamic perception repaired; N0 navigation smoke blocked

Current status: **NAVIGATION_BLOCKED**. Dynamic perception gate **PASS**: scan detection, local marking and later clearing demonstrated. Root-cause classification for the previous perception blockage: **K — OTHER_IDENTIFIED: StaticLayer overwrites dynamic markings**. AIRPORT is not RUNTIME_VALIDATED; no final paired campaign was authorized or executed in this block. Engineering evidence only, not efficacy/context compliance.

## Read-only audit and demonstrated cause

Audit used the original actor/world/robot assets. A temporary no-goal perception launch placed the stationary robot at (-3.4,-2.9), near both the actor and security-island west edge. This is a diagnostic location; the experimental spawn (0,-8), final (0,8) and east waypoint (7,0) remain unchanged. Parameters were retrieved from /local_costmap/local_costmap at runtime, not inferred solely from YAML.

Effective original plugins: voxel_layer (nav2_costmap_2d::VoxelLayer), inflation_layer (InflationLayer), static_layer (StaticLayer), in that order. All enabled. The global costmap is a separate consumer and was not altered. No separate ObstacleLayer plugin is loaded in the local costmap; VoxelLayer inherits its observation handling.

Chain: Gazebo gpu_lidar publishes /scan (gz.msgs.LaserScan), ros_gz_bridge exposes sensor_msgs/msg/LaserScan on /scan; scan_frame_fixer copies ranges to /scan_fixed and changes only frame_id to lidar_link; the local VoxelLayer subscribes to /scan_fixed. Graph confirms the resolved topic and subscriber. Publisher/relay reliability RELIABLE, local subscriber BEST_EFFORT, all scan endpoints VOLATILE; compatible. Endpoint introspection returned UNKNOWN history/depth 0, so no history/depth assertion is made from those values. The relay source requests depth 10. Local combined costmap publisher is RELIABLE/TRANSIENT_LOCAL nav_msgs/msg/OccupancyGrid.

## Effective observation source

| Parameter | Runtime value |
|---|---|
| voxel_layer.observation_sources | scan |
| scan.topic / data_type | /scan_fixed / LaserScan |
| scan.marking / clearing | true / true |
| scan.observation_persistence / expected_update_rate | 0.0 / 0.0 |
| scan.sensor_frame | empty; uses message frame lidar_link |
| costmap transform_tolerance | 0.3 s |
| obstacle_min_range / obstacle_max_range | 0.0 / 2.5 m |
| raytrace_min_range / raytrace_max_range | 0.0 / 3.0 m |
| scan.min_obstacle_height / max_obstacle_height | 0.0 / 2.0 m |
| voxel_layer.min_obstacle_height / max_obstacle_height | 0.0 / 2.5 m |
| scan.inf_is_valid | false |
| voxel_layer.combination_method | 1 (maximum) |
| voxel footprint clearing / static footprint clearing | true / false |
| voxel origin_z / z_resolution / z_voxels | 0.0 / 0.05 / 16 |
| global_frame / robot_base_frame | odom / base_link |
| rolling_window / width / height / resolution | true / 3 m / 3 m / 0.05 m |
| footprint / padding | existing rectangle +/-0.36 x +/-0.34 m / 0.01 m |
| update_frequency / publish_frequency | 5 / 2 Hz |
| use_maximum | false |

The effective voxel observation source is namespaced under voxel_layer; the empty top-level observation_sources parameter is not the active source. Effective values match the consumed YAML/defaults; no accidental topic or disabled marking was found.

## Timestamp TF and return geometry

Baseline: 196 captured scans, 124 scans with actor-region returns, zero TF rejections. Each recorded sample was transformed lidar_link -> odom at scan.header.stamp, with bounded waiting for that exact timestamp, not a latest-transform substitution. Example stamp 10.033 sim seconds (post-fix): range 1.800760 m, angle 2.713390 rad, sensor point (-1.638175,0.747742,0), odom point (-1.358175,0.747742,0.72), approximate world point (-4.758175,-2.152258). Transform translation (0.28,0,0.72), approximately identity orientation. Map at 10.066 s, origin (-1.45,-1.45), gives cell (1,43).

The selected return is inside obstacle range and the local window, above min/below max height and within the voxel height interval [0,0.8), outside the padded footprint, and falls in a valid cell. Some far-phase actor returns lie outside range/window; those are not used to demand local marking. TF, range, height, footprint clearing and outside-window cases do not explain the selected valid near returns.

## Direct layer evidence and static positive control

A temporary external LD_PRELOAD wrapper observed original updateCosts functions and snapshots of the VoxelLayer internal map, master after obstacles and master before/after StaticLayer; it was not installed into production or used in the post-fix perception check/smoke. In 139 updates, actor cell (-1.358,0.748) was 254/LETHAL before StaticLayer and 0/FREE immediately afterward in the same update. Example steady timestamps 58141206265847 -> 58141206844439 ns. Thus marking was generated; this is not immediate raytrace clearing or a published-topic observation error. StaticLayer ran last with use_maximum=false and overwrote master cells with static-map free values. This behavior agrees with Nav2 1.3.11 StaticLayer::updateCosts rolling-window implementation.

Existing static control: west edge of security_island (world x=-2), scan range approximately 1.120017 m, odom surface point approximately (1.400007,-0.004894,0.72). Exact return-cell costs were 100 in all 159 selected baseline and 159 post-fix scan-to-costmap comparisons. The VoxelLayer internal capture also contained lethal cells. The source/layer is not completely broken; static-map occupied values survive while dynamic values in static-map free space are overwritten.

One failed trace attempt used RTLD_NEXT for a locally loaded library and caused controller_server SIGSEGV; its incomplete capture was discarded. Automatic launch shutdown escalated for Gazebo/lifecycle in that instrumented attempt. The wrapper was repaired to resolve the original library handle and the successful layer capture repeated. This probe failure is not evidence of intrinsic ROS/Nav2 instability and was not counted as an experimental attempt. Recorded PIDs were confirmed gone before subsequent launches. The initial baseline launch had no wrapper active because the temporary replacement failed to match source quoting; its parameter/TF/public-costmap capture remained valid. Both limitations remain recorded rather than hidden.

## Minimal AIRPORT-only fix

Added ros2/src/wheelchair_navigation/config/airport_costmap.yaml, overriding only local plugins to [static_layer, voxel_layer, inflation_layer]. navigation.launch.py supplies this second parameter file only to controller_server when environment == airport. HOME/PARK continue to receive the original parameter list; no HOME/PARK files or parameter values changed. All plugin identities, scan topics, numeric ranges/heights, footprint, inflation settings, planner/controller, DDS/RMW and timeouts remain unchanged. Existing mixed line endings and prior edits are preserved. No actor or physics change.

The order avoids StaticLayer erasing later voxel markings and places InflationLayer after the composed obstacles. It restores obstacle visibility; it does not weaken collision checks or grant a navigation-success guarantee.

## Single post-fix perception check

No LD_PRELOAD. Original actor and production navigation launch consume the AIRPORT-only overlay. Effective parameter comparison changes only plugins order. 196 scans, 124 actor scan observations, zero TF rejections, 88 local costmaps; 48 costmaps contain lethal actor-region cells (published OccupancyGrid value 100, internal lethal value 254). Tracked old actor cell is 100 in 17 maps during sim 10..19 s, then 0 in all 7 maps during 24..28 s after departure, and remains 0 in the far windows 36..40 and 48..52. Subsequent nearby cycles produce renewed actor-region marking. The location is separate from static-map obstacles and outside the robot footprint.

Therefore dynamic_obstacle_detected=true, dynamic_obstacle_marked=true, dynamic_obstacle_cleared=true. These are engineering gate facts, not independent efficacy metrics. Both baseline and post-fix checks closed cleanly, no SIGKILL/residues.

## Authorized smoke and stopping policy

One N0 smoke, attempt 1 only: readiness PASS, accepted navigation executed, final ABORTED; 48.360 s, 3.811 m, 31 replannings, strategy_applied=N/A. Controller repeatedly reported collision ahead and controller patience exceeded; classified NAVIGATION_FAILURE. No ComputePathToPose SendGoal timeout justified an infrastructure retry. Cleanup clean; no residues. N1 smoke NOT RUN because N0 was not viable. No 2/2+2/2 final validation, navigation retry, further tuning or new investigation.

The smoke observer captured 194 actor-region scan observations, but no matched local lethal actor cell during that moving run. Four observer timestamp-transform rejections occurred in its map/odom lookup chain; these are capture limitations and do not demonstrate rejection by Nav2. The navigation failure is not causally attributed to the actor. Geometry/map/physics and the frozen experimental coordinates were not changed to obtain success.

Smokes use the frozen PARK policy: principal attempt plus at most one clean retry only for infrastructure; ComputePathToPose acknowledgement timeout is operational INFRASTRUCTURE_ACTION_HANDSHAKE_FAILURE, unknown root cause; actual NAVIGATION_FAILURE is not retried. Navigation outcome and cleanup are separate. Unique domains/partitions and output IDs are retained. Temporary AIRPORT launch copy differs only in run_id/result_csv because existing wrappers hardcode these; production wrappers remain unchanged.

## Integrity and limits

DB READ-ONLY before/after this block: 50->50, canonical_memory_fingerprint_v2 content 46ea5969b3047c1eb3bc526bb08fbb11b8ddac6f77f18a97e362fcdba9e97898, embeddings 8f9bf33815930952e3a7ee169d1edb4c7027d5cb5c77c173a3b1a16bb7af2599, identical. No N1 memory query or online learning. N0 failed-run CSV has 35 columns, one final row, memory fields and context_compliance/intervention_appropriate/min_clearance_m=N/A. It is failure evidence, not an efficacy observation.

Relevant navigation build PASS; 58 BT regression tests, zero errors/failures/skips. End-to-end perception verification supplies the costmap-specific evidence; BT tests do not cover that mechanism. HOME/PARK and the kinematic fix remain intact, no runs there. No commit/push/reset/stage/branch switch.

Artifacts: `/tmp/airport_costmap_audit_0a1af236df23473a843e6a239f565e31` — runtime_parameters/runtime_graph, timestamped observations, direct stages, overwrite_proof.json, perception_summary.json, failed instrumentation and repaired source, post-fix capture, smoke CSV/log/audit, DB snapshots, build/tests, before-state checkpoint and integrity verification.

One next action, not executed: read-only correlate the existing N0 collision-ahead interval with its planned path and local costmap footprint checks to locate the blocking obstacle. No navigation retry or tuning is implied.

## Preserved previous block — superseded perception status

# AIRPORT-01 — engineering gate blocked on local dynamic-obstacle marking

Status: **DYNAMIC_ACTOR_BLOCKED**. Engineering validation only. HOME and PARK remain previously RUNTIME_VALIDATED, intact and not executed. KINEMATIC_FIX remains VALIDATED (5 mm collision width). No scientific efficacy or independent context compliance is claimed.

## Objective and frozen configuration

Use the existing AIRPORT world/model/map and shared Nav2/BT configuration. Spawn (0,-8,0), final (0,8,0); N1 goal-relative offset `alternative:7.0:-8.0` resolves to east waypoint (7,0,0). Existing query `pequeno desvio este ante obstaculo en pasillo central`, U02/airport/navegacion/puerta, k=3. Expected previously validated retrieval M022|M028|M026, source M022, strategy alternative; it was not queried in this block.

## Static precheck

AIRPORT world/model SDF valid, Python launch syntax valid. Source/install assets correspond after restoration. Map eroded by a conservative 0.70 m radius has spawn, east waypoint and final in the same nonzero free-space connected component (footprint circumscribed radius approximately 0.495 m). Endpoint distances to occupied cells: 2.700, 3.000 and 2.650 m respectively. This demonstrates static geometric connectivity around the island, not straight-line feasibility or runtime navigation. Relevant installed build was rebuilt sequentially with system Python; 58 BT tests passed, zero errors/failures/skips.

## Existing dynamic actor

`airport_crossing_actor` uses the local mesh airport_pedestrian.dae and scripted motion at x=-5, from y=-2 to y=2 and back. Initial pose (-5,-2,0); delay_start=20 simulation seconds, waypoint times 0/6/12 s, loop=true. Nominal mean leg speed 4/6 = 0.667 m/s; interpolation may change instantaneous speed. This traverses the west-bypass area, not the centre of the security island. No crowd simulation.

The actor has no physical collision geometry, but its rendered surface is genuinely detected by the configured GPU LiDAR. The first interpretation of a sector minimum mixed short wheelchair returns with actor returns. Corrected analysis excludes ranges below 0.5 m and projects endpoints into the actor's otherwise unoccupied world region; original actor returns move between y approximately -2.15 and +1.85 m and recur after 12 simulation seconds. The original actor therefore is not merely an undetectable visual.

## Detection verification and blocked gate

One original perception check, no navigation goal: stationary robot placed at (-5,-2.9) solely for close-range verification; campaign spawn (0,-8) was not changed. Captured /scan_fixed (the existing relay copies /scan ranges and changes only frame_id), /odom and /local_costmap/costmap through 52 simulation seconds. Original: 215 scan samples, 86 local costmaps. Actor-region near returns approximately 0.747 m before departure, far returns approximately 3.73 m during the far part, then near returns again. This demonstrates presence, scripted movement and scan disappearance/reappearance.

However, every captured local costmap cell remained 0/free, including while the actor was within the 3x3 m local window and observation range. No dynamic marking was demonstrated. Consequently clearing cannot be validated: an always-free map is not evidence of successful mark-then-clear. The cause of the local marking failure was not isolated, and is not attributed to lifecycle, DDS or acknowledgement timeouts.

A minimal actor candidate replaced only the actor with one 0.56x0.36x1.45 m box carrying collision and visual, moved by a small simulation-time Gazebo system along the existing delay/path/period. It was built and the perception check repeated once. Candidate movement was captured in Gazebo poses and scan (216 samples), but all 90 local costmaps still remained free. This actor-only change did not satisfy the gate and was fully withdrawn. Original world, packaging and launches are restored byte-for-byte; rejected source/build and perception evidence are preserved externally. No permanent actor fix remains.

The two checks show a similar initial position and periodic path for original and candidate, but they are different implementations; this is not a claim of two identical production-launch determinism trials. Since the detection gate failed, further trials were stopped.

## Infrastructure retry policy

Same frozen PARK policy for any future AIRPORT repetition: principal attempt plus at most one clean infrastructure retry (maximum two attempts). Lifecycle/service/discovery/readiness/action-server/bond failure permits that single retry. ComputePathToPose SendGoal timeout is operationally INFRASTRUCTURE_ACTION_HANDSHAKE_FAILURE, root cause unknown, with the same retry limit; recurrence ends INFRASTRUCTURE_BLOCKED. Real accepted-navigation planner/controller/recovery failure is NAVIGATION_FAILURE and is not retried. Navigation SUCCEEDED and cleanup FAILED are separate outcomes; a new attempt requires verified absence of residues. No timeout, DDS/RMW, internal retry or sleep adjustment.

## Smoke and final repetitions

N0 smoke NOT RUN. N1 smoke NOT RUN. N0 final repetitions 1/2 NOT RUN; N1 final repetitions 1/2 NOT RUN. The dynamic-obstacle detection prerequisite failed before navigation, so no experimental navigation attempts or CSV rows were fabricated. No retrieval or strategy_applied result is claimed. No further tuning or infrastructure investigation was opened.

Both perception checks shut down with owner SIGINT, launch_exit=0 and observer_exit=0; no SIGKILL, and all recorded process PIDs were gone. Startup TF waits are preserved in full logs. Cleanup remained separate from the dynamic detection failure.

## DB and metrics integrity

No memory launch/query or online learning. Database access READ-ONLY. Baseline is the read-only snapshot from the immediately preceding PARK closure (not a newly acquired pre-simulation snapshot); current closing snapshot matches it: 50->50, canonical_memory_fingerprint_v2 content `46ea5969b3047c1eb3bc526bb08fbb11b8ddac6f77f18a97e362fcdba9e97898`, embeddings `8f9bf33815930952e3a7ee169d1edb4c7027d5cb5c77c173a3b1a16bb7af2599`. No experimental CSV exists for this block; the common 35-column contract remains unchanged. context_compliance/intervention_appropriate/min_clearance_m remain N/A pending independent ground truth.

## Evidence and next bounded action

`/tmp/airport_engineering_fbbb477204884a239875984b8231316e`

Artifacts include static_connectivity.json, precheck/build/restoration logs, original/candidate perception captures, candidate Gazebo poses, detection_summary.json, rejected_actor_fix, DB baseline/current snapshots and before-state hashes/diff/status. Production files are restored; only this AIRPORT document is added/updated. No commit/push/reset/stage/branch switch or remote Git operation.

One next action, not executed: a read-only audit of the local costmap observation/layer composition to explain why actor scan hits inside its window do not mark cells. No Nav2 change is authorized by this block, and the failed gate does not authorize new actor/world redesign.
