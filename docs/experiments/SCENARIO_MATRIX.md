# Experimental scenario matrix

Status: HOME and PARK are engineering **RUNTIME_VALIDATED**; the shared **KINEMATIC_FIX is VALIDATED** (drive-wheel visual width 45 mm, collision width 5 mm). PARK final N0 2/2 and N1 2/2 succeeded on the first attempt with clean shutdown. AIRPORT is exploratory: dynamic perception scan/marking/clearing PASS, navigation **NAVIGATION_BLOCKED** after one N0 **NAVIGATION_FAILURE**; N1 not run. See [HOME_01.md](HOME_01.md), [PARK_01.md](PARK_01.md), and [AIRPORT_01.md](AIRPORT_01.md) for authoritative current evidence and preserved history. Engineering validation is not experimental efficacy. No campaign or E1/E2/E3 has started. The shared Nav2 configuration is retained, with an AIRPORT-only local-costmap plugin-order overlay: StaticLayer → VoxelLayer → InflationLayer. The database remains frozen and independent compliance/clearance/intervention metrics remain N/A.

## Shared protocol

- Conditions: N0 sends only the final goal; N1 may retrieve one episode, resolve its strategy to one goal-relative waypoint, then send the same final goal. Nav2 retains planning, control, and collision avoidance.
- Timeout: 300 s navigation watchdog per condition; this is the existing HOME launch default and is held equal for N0/N1. Readiness has its separately configured timeout.
- Repetitions: plan 10 paired runs per scenario after calibration; this is a practical protocol proposal, not a power-analysis result.
- Controlled: robot model, spawn, Nav2 parameters/footprint, map resolution, goal, simulator version, and launch protocol. Database remains frozen; no online learning during campaign.
- Primary adaptation outcome: independent path-based compliance rule below. Current CSV logger leaves `context_compliance`, `intervention_appropriate`, and `min_clearance_m` as N/A; do not infer them from expected strategy fields. Implement and validate a separate trajectory evaluator before final campaign use.
- Success: final Nav2 goal result is SUCCEEDED within 300 s, with no manual intervention. For N1, waypoint failure means final goal remains NOT_SENT under the existing contract and the run is not successful.
- Infrastructure failure: required lifecycle/action/service/sensor readiness fails or simulator/ROS process exits; record separately from navigation failure and exclude only under a predeclared failure policy.

| scenario_id | environment / hypothesis | user, location, task, goal | N1 query / candidate memory | spawn → final goal | N0 / N1 candidate | Independent ground truth and compliance | Metrics / status |
|---|---|---|---|---|---|---|---|
| `HOME_01_clearance_preference` | `home`; engineering validation of personalized strategy integration | U01, salon, navegacion, dormitorio (semantic retrieval label; physical goal is in southern living area) | `navegar evitando la mesa`, k=3; M001/M046/M002; M001/west | (2.0,-6.0,0) → (4.0,-4.0,0) | N0 final only. N1 one west waypoint (0.0,-4.0), offset `west:-4.0:0.0`, then same final. | Independent compliance ground truth remains unfrozen. The former table-crossing window does not apply to this shortened route. Never infer compliance from strategy_applied/expected fields. | HOME `RUNTIME_VALIDATED`: two final paired repetitions, all four runs SUCCEEDED on first attempt. `context_compliance`, `min_clearance_m`, `intervention_appropriate` remain N/A. See HOME_01 for evidence and limitations. |
| `PARK_01_west_path_preference` | `park`; engineering strategy integration; full route unvalidated | U01, park, navegacion, salida_norte (semantic label) | `repetir ruta oeste habitual rodeando el jardin central`, k=3; observed M013/M015/M007, M013/west | (0,-9,0) → (1,-9,0), latest candidate only | N0 final only; N1 west waypoint (-1,-9), offset `west:-2.0:0.0`, then same final. | Independent ground truth remains unfrozen; former y=0/x≤-7 rule does not apply to this shortened southern route. | `RUNTIME_VALIDATED`: final N0 2/2 and N1 2/2 succeeded on attempt 1; N1 waypoint and final SUCCEEDED. Earlier failed batches are historical. All independent metrics N/A. See PARK_01. |
| `AIRPORT_01_east_detour` | `airport`; H1/H3 contextual detour under a repeatable dynamic crossing | U02, airport, navegacion, puerta | `pequeno desvio este ante obstaculo en pasillo central`, k=3; candidate M022 / alternative from its frozen small-detour episode. Cross-location retrieval is unverified. | (0,-8,0) → (0,8,0) | N0 direct final goal. N1 candidate east waypoint (7,0), offset `alternative:7.0:-8.0`; goes around the east of the security island. Airport actor starts its deterministic crossing after 20 s and repeats a 12 s trajectory; it is non-colliding but sensed by gpu_lidar; local marking and clearing are validated, without a successful navigation interaction claim. | At the island crossing y=0, score compliant if the independently measured center x≥4.5, the east bypass. This is independent of retrieval fields. The actor crossing is a controlled environmental factor only after LiDAR/costmap interaction is validated; otherwise keep dynamic factor out of the causal interpretation. | Same common metrics. Read-only retrieval observed M022/M028/M026, M022/alternative. Actor scan/marking/clearing PASS. N0 smoke NAVIGATION_FAILURE; N1 NOT RUN; route feasibility remains blocked. Until actor is detected and handled reproducibly, interpret as static detour scenario only. Compliance evaluator `CALIBRATION_REQUIRED`; `min_clearance_m=N/A`. |

## Interpretation and calibration gates

The three settings are complementary: HOME tests a known personalized clearance preference; PARK tests transfer of a previously successful route preference to an open layout; AIRPORT tests a small detour preference in a terminal-like layout and provides a deterministic actor visual for future dynamic validation. The Park island is offset so the unobstructed east bypass has the shorter geometric detour; the west waypoint requires a distinct side choice. HOME and PARK exact retrievals are supported by read-only runtime evidence. PARK engineering navigation is validated; AIRPORT navigation remains blocked; run exact read-only queries and record returned IDs/strategies before freezing those scenarios. Do not alter seed memories to force a match.

Before campaign use, validate free-space paths and N0/N1 routes in runtime, verify retrieval per exact context, and independently validate trajectory sampling/compliance. For AIRPORT also prove the actor is sensed and causes the intended deterministic interaction, or explicitly retain it as a visual-only nuisance factor. Keep infrastructure failures separate from navigation failures.

## Historical calibration evidence (2026-10-03; superseded statuses)

- Database remained read-only during calibration. Row count before/after the real retrieval checks was 50/50.
- HOME canonical retrieval was exercised through the live memory and recommendation pipeline: `M001|M046|M002`, source `M001`, strategy `west`. HOME N0 passed readiness and sent the final goal, but Nav2 aborted after the robot reached approximately `(3.69,-0.39)` and the controller repeatedly detected a collision near the dining-table route. HOME N1 retrieved the same result and sent waypoint `(-1.0,-1.0)`, but Nav2 aborted while planning from approximately `(2.56,0.55)` to that waypoint; the final goal remained `NOT_SENT`. Both are `CALIBRATION_REQUIRED` navigation outcomes, not retrieval failures.
- Offline HOME map analysis with the configured 0.70 m inflation and the 0.36 m footprint half-width found the spawn, waypoint, and goal in free cells. The direct graph route intersects the inflated dining-table region; a west segment to `(-1,-1)` is connected, but runtime still selected a collision-prone local trajectory near the table. This is geometric/navigation evidence, not a `min_clearance_m` experiment metric.
- PARK real retrieval returned `M013|M015|M007`, source `M013`, strategy `west`. The first PARK N0 launch did not dispatch a goal because the external readiness probe exited during lifecycle/service discovery while Nav2 was still activating. This is `INFRASTRUCTURE_FAILURE`; route feasibility remains unvalidated.
- A subsequent PARK N0 attempt reached the readiness probe and then the orchestrator process exited with code 1 before writing a CSV. No navigation goal was dispatched. The exact process-level cause is still unresolved and is recorded as infrastructure/launch instability.
- AIRPORT real retrieval returned `M022|M028|M026`, source `M022`, strategy `alternative`. No AIRPORT navigation smoke was run after the PARK readiness failure. The actor remains unvalidated for LiDAR/costmap interaction.
- The memory worker now starts with the monorepo CPU venv and ROS/interface overlay. On shutdown the embedding-backed memory process still exceeded launch's graceful wait and was escalated to SIGTERM/SIGKILL; this is a cleanup/runtime limitation to resolve before repeated calibration or campaign runs.

Status at the end of that earlier calibration block: HOME/PARK/AIRPORT `CALIBRATION_REQUIRED`. HOME was subsequently validated below.

## Current candidate launch commands

After rebuilding/installing the ROS workspace, use one condition at a time and temporary CSVs. The repaired HOME headless runner uses owner-only shutdown, temporary outputs and read-only DB fingerprints; see HOME_01.md. PARK is engineering validated; AIRPORT navigation remains blocked.

```bash
ros2 launch wheelchair_assistive_bt home_n0.launch.py environment:=home result_csv:=/tmp/home01_n0.csv run_id:=home_unique_n0
ros2 launch wheelchair_assistive_bt home_n1.launch.py environment:=home result_csv:=/tmp/home01_n1.csv run_id:=home_unique_n1
ROS_DOMAIN_ID=60 GZ_PARTITION=park_unique_n0 ros2 launch wheelchair_assistive_bt park_n0.launch.py gui:=false result_csv:=/tmp/park_unique_n0.csv run_id:=park_unique_n0
ROS_DOMAIN_ID=63 GZ_PARTITION=park_unique_n1 ros2 launch wheelchair_assistive_bt park_n1.launch.py gui:=false result_csv:=/tmp/park_unique_n1.csv run_id:=park_unique_n1
ros2 launch wheelchair_assistive_bt home_n0.launch.py environment:=airport experiment_id:=airport01 scenario_id:=AIRPORT_01_east_detour run_id:=airport_n0_001 result_csv:=/tmp/airport01_n0.csv initial_x:=0 initial_y:=-8 initial_yaw:=0 goal_x:=0 goal_y:=8 goal_yaw:=0
ros2 launch wheelchair_assistive_bt home_n1.launch.py environment:=airport experiment_id:=airport01 scenario_id:=AIRPORT_01_east_detour run_id:=airport_n1_001 result_csv:=/tmp/airport01_n1.csv query:='pequeno desvio este ante obstaculo en pasillo central' user_id:=U02 location:=airport task:=navegacion goal_label:=puerta initial_x:=0 initial_y:=-8 initial_yaw:=0 goal_x:=0 goal_y:=8 goal_yaw:=0 strategy_waypoint_offsets:=alternative:7.0:-8.0
```

These commands exercise candidates only. Do not use their outputs as campaign evidence until the calibration gates above pass.

### PARK orchestrator calibration update (2026-10-03)

The initial PARK/AIRPORT wrappers passed integer launch literals (0, 9,
etc.) into assistive_bt_orchestrator, whose declared parameters are
double. ROS 2 rejected goal_x before tree construction with a parameter
type error: goal_x was declared double but received integer.
The four wrappers now use decimal literals (0.0, 9.0, etc.) and the
wheelchair_assistive_bt package rebuild passes.

A subsequent PARK N0 run reached READY, loaded the installed N0 XML, and
sent the final goal. It then failed in Nav2: the controller reported
collision-ahead/patience exceeded and the planner failed from approximately
(1.18,-4.23) to (0.00,9.00). This is NAVIGATION_FAILURE; the run was
interrupted during diagnostic cleanup before a final CSV row was written.
The PARK geometry remains CALIBRATION_REQUIRED.

## HOME runtime closure (2026-10-03)

HOME now uses the current SDF-derived map, corrected wheel-joint axes in the same wheelchair, and the broad southern route described in [HOME_01.md](HOME_01.md). Final batch: N0 2/2 and N1 2/2, all at attempt 1; N1 applied M001/west and succeeded at waypoint and final goal. DB count and both canonical v2 hashes were unchanged. This is engineering runtime validation; ground truth and scientific efficacy remain unvalidated. Known infrastructure instability is not claimed fixed. The older failures above are retained as historical calibration evidence.

Final HOME navigation was successful in all four final launches; one bridge exited -6 during shutdown after completed goals. This cleanup warning is recorded in HOME_01 and is not a navigation failure or a resolved infrastructure cause.

## Historical PARK closure (superseded by final validation in PARK_01.md)

PARK is **BLOCKED**; the latest minimal configuration is not frozen. Final isolated batch: N0 repetition 1 SUCCEEDED, N1 repetition 1 retrieved M013/M015/M007 and applied M013/west, waypoint SUCCEEDED, final ABORTED. Estimated planner start (0.27,-11.48) departed from the nominal y=-9 corridor; earlier Gazebo/estimated pose evidence shows meter-scale disagreement. No second pair was run. Both final launches closed without escalation. DB remained 50 rows with identical canonical v2 hashes. No geometry/map, shared runtime or HOME configuration changed. See [PARK_01.md](PARK_01.md) for preserved failures, exact artifacts and unresolved localization cause.


## Publication baseline (2026-10-04)

HOME and PARK RUNTIME_VALIDATED; KINEMATIC_FIX VALIDATED. AIRPORT dynamic perception PASS, N0 NAVIGATION_FAILURE, N1 NOT RUN. No additional simulation was run for publication. Historical calibration statuses above are retained as evidence, not the current status. Next phase: Experimental Evaluation Design; independent ground truth and the campaign remain planned.

Publication tooling limits: the static asset validator retains historical HOME/PARK design coordinates; publication additionally checked the current launch coordinates without changing that tool. The PARK legacy runner defaults to two infrastructure retries; the final validation policy used one principal attempt plus at most one retry through a temporary manager, as documented in PARK_01. AIRPORT wrappers hardcode their example run IDs/CSV destinations; do not use them as a campaign supervisor. No runtime behavior was changed for publication.
