# BT Phase 2 — Validation: MEMORY_ON observation path

## Scope and provenance

This is smoke-test validation only. No final N0/N1 campaign was run, no final scenario was changed, no result was written under `experiments/results/`, and no new experience was inserted into memory.

Initial Git HEADs:

- `/home/iratxefagoaga/workspace/tfm`: `70802a13ca80936d8ab0c773c2d376f6699d946b`
- `/home/iratxefagoaga/workspace/tfm-robot-memory`: `6430e4a5042ccea391ba29cf78489df6be06570a`

## Commands and observed evidence

### Package build

```bash
colcon build --packages-select wheelchair_interfaces wheelchair_assistive_bt --symlink-install
```

Result: `wheelchair_interfaces` and `wheelchair_assistive_bt` completed successfully after correcting the ROS Jazzy service-callback type signatures.

### Full workspace build

```bash
colcon build --symlink-install
```

Result:

```text
Summary: 9 packages finished [5.89s]
```

### Controlled memory-service failure

N1 was run with no memory services available and `memory_timeout_s:=1.0`.

Observed terminal blackboard:

```text
condition=MEMORY_ON
memory_query_result=TIMEOUT
recommendation_result=NOT_STARTED
strategy_applied=false
final_goal=(2.500,-3.000)
final_goal_nav2_result=NOT_SENT
nav2_result=NOT_STARTED
success=false
failure_stage=query_memory
failure_reason=TIMEOUT waiting for /memory/query
```

There was no `final_goal sent to /navigate_to_pose` log. Thus memory failure stops the tree before Nav2 and does not fall back to N0.

### N0 regression smoke

A separate, single temporary Gazebo/Nav2 stack ran the existing Phase 1 launch with `(2.00,-3.00) → (2.50,-3.00)`.

Observed:

```text
Assistive BT N0: final_goal sent to /navigate_to_pose.
bt_navigator: Begin navigating from current location (2.00, -3.00) to (2.50, -3.00)
bt_navigator: Goal succeeded
condition=MEMORY_OFF ... nav2_result=SUCCEEDED final_goal_nav2_result=SUCCEEDED success=true
```

### N1 happy-path smoke

A single temporary Gazebo/Nav2 stack ran `bt_n1_phase2_smoke.launch.py` with:

```text
query=navegar evitando la mesa
user_id=U01
location=salon
task=navegacion
goal_label=dormitorio
k=3
initial pose=(2.0,-3.0,0.0)
final goal=(2.5,-3.0,0.0)
```

Observed orchestrator trace:

```text
QueryMemory -> /memory/query
GetNavigationRecommendation -> /memory/navigation_recommendation
memory_ids=M001|M046|M002
semantic_scores=0.636811|0.627409|0.631049
context_scores=1.000000|1.000000|0.750000
final_scores=0.673130|0.664668|0.642944
source_memory=M001
retrieved_strategy=west
recommendation_reason=Memoria M001: Ruta oeste evitando la mesa. Preferencia: Prefiere mayor espacio lateral.
avoid_obstacle=true
prefer_clearance=true
memory_query_result=SUCCEEDED
recommendation_result=SUCCEEDED
strategy_applied=false
final_goal=(2.500,-3.000)
final_goal_nav2_result=SUCCEEDED
nav2_result=SUCCEEDED
success=true
```

Nav2 independently logged:

```text
Begin navigating from current location (2.00, -3.00) to (2.50, -3.00)
Goal succeeded
```

The existing `navigation_memory_node` logged `Consultando /memory/query...` while servicing the recommendation. This is the expected, intentionally preserved second retrieval.

## Checklist

| Item | Status | Evidence |
|---|---|---|
| BUILD PACKAGE | PASS | `wheelchair_interfaces` and `wheelchair_assistive_bt` built successfully. |
| BUILD WORKSPACE | PASS | All 9 workspace packages built successfully. |
| N0 REGRESSION | PASS | Existing N0 launch completed Nav2 with `SUCCEEDED`. |
| N1 BT LOAD | PASS | N1 XML loaded from the installed package. |
| MEMORY QUERY | PASS | Real `/memory/query` returned M001, M046, M002 and scores. |
| RECOMMENDATION | PASS | Real recommendation returned source M001 and strategy `west`. |
| BLACKBOARD TRACEABILITY | PASS | Terminal log contains IDs, context, arrays/scores, recommendation, final goal, Nav2 result and failure fields. |
| STRATEGY NOT APPLIED | PASS | Happy path recorded `retrieved_strategy=west` and `strategy_applied=false`. |
| FINAL GOAL ONLY | PASS | Only one N1 send is logged; Nav2 received `(2.00,-3.00) → (2.50,-3.00)`. |
| NAV2 SUCCESS | PASS | N1 final-goal result and Nav2 result are both `SUCCEEDED`. |
| MEMORY FAILURE POLICY | PASS | Missing service led to explicit `query_memory` timeout and `NOT_SENT` final goal. |
| NO MEMORY WRITE | PASS | The N1 implementation only calls retrieval/recommendation services; no memory write API or dataset/result writer is invoked. The smoke did not target an experimental CSV. |
| NO NAV2 REGRESSION | PASS | N0 remains a separate executable/launch and completed successfully; N1 uses only `/navigate_to_pose`. |

## Observed non-blocking shutdown issue

As in Phase 1, `scan_frame_fixer.py` attempted a second `rclpy.shutdown()` during launch shutdown and Gazebo left two server/GUI processes after its parent exit. They were explicitly terminated after each integrated smoke before starting another stack. This occurred after terminal Nav2 success and is not a BT Phase 2 navigation failure, but should be addressed before unattended repeated campaigns.

## Conclusion

**BT Phase 2 is validated at smoke-test level.** N1 performed real retrieval and recommendation, recorded their traceability fields, then sent exactly the unmodified common final goal to Nav2. The controlled failure case proves that memory unavailability is explicit and does not silently execute the baseline path. BT Phase 3 is not implemented.