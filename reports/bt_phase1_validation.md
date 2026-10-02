# BT Phase 1 — Validation: N0 / MEMORY_OFF

## Validation scope

This validation covers only the new explicit Behavior Tree N0 path. It is not an N1 validation and it is not a final experimental campaign.

## Commands executed

### 1. Package compilation

```bash
cd /home/iratxefagoaga/workspace/tfm/ros2
deactivate 2>/dev/null || true
source /opt/ros/jazzy/setup.bash
which python3
colcon build --packages-select wheelchair_assistive_bt --symlink-install
```

Result: `wheelchair_assistive_bt` built successfully. `python3` was verified as `/usr/bin/python3`.

### 2. XML-load / failure-path smoke test

```bash
source /opt/ros/jazzy/setup.bash
source /home/iratxefagoaga/workspace/tfm/ros2/install/setup.bash
timeout 3s ros2 run wheelchair_assistive_bt assistive_bt_orchestrator --ros-args \
  -p experiment_id:=bt_phase1_xml \
  -p scenario_id:=S001_shared_safe_goal \
  -p run_id:=xml_load \
  -p goal_x:=2.5 -p goal_y:=-3.0 \
  -p wait_for_nav2_timeout_s:=1.0
```

Observed output:

```text
Assistive BT N0 XML loaded: .../n0_assistive_navigation.xml
Assistive BT N0 blackboard: experiment_id=bt_phase1_xml scenario_id=S001_shared_safe_goal condition=MEMORY_OFF run_id=xml_load nav2_result=NOT_STARTED final_goal_nav2_result=NOT_SENT success=false failure_stage=wait_for_nav2_active failure_reason=TIMEOUT waiting for /bt_navigator active
```

This establishes that the XML loads and that the absence of active Nav2 produces an explicit, traceable failure rather than a hidden fallback.

### 3. Integrated N0 single-stack smoke test

```bash
source /opt/ros/jazzy/setup.bash
source /home/iratxefagoaga/workspace/tfm/ros2/install/setup.bash
ros2 launch wheelchair_assistive_bt bt_n0_smoke.launch.py \
  experiment_id:=bt_phase1_smoke \
  scenario_id:=S001_shared_safe_goal \
  run_id:=n0_bt_001 \
  initial_x:=2.0 initial_y:=-3.0 initial_z:=0.11 initial_yaw:=0.0 \
  goal_x:=2.5 goal_y:=-3.0 goal_yaw:=0.0 \
  wait_for_nav2_timeout_s:=60.0 navigation_timeout_s:=120.0
```

Observed evidence:

```text
lifecycle_manager_navigation: Managed nodes are active
assistive_bt_orchestrator: Assistive BT N0 XML loaded: .../n0_assistive_navigation.xml
assistive_bt_orchestrator: Assistive BT N0: final_goal sent to /navigate_to_pose.
bt_navigator: Begin navigating from current location (2.00, -3.00) to (2.50, -3.00)
controller_server: Received a goal, begin computing control effort.
controller_server: Reached the goal!
bt_navigator: Goal succeeded
assistive_bt_orchestrator: Assistive BT N0 blackboard: experiment_id=bt_phase1_smoke scenario_id=S001_shared_safe_goal condition=MEMORY_OFF run_id=n0_bt_001 nav2_result=SUCCEEDED final_goal_nav2_result=SUCCEEDED success=true failure_stage= failure_reason=
```

### 4. Full workspace compilation

```bash
cd /home/iratxefagoaga/workspace/tfm/ros2
deactivate 2>/dev/null || true
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
```

Observed result:

```text
Summary: 9 packages finished [3.66s]
```

### 5. Isolation checks

The installed package reports only:

```text
wheelchair_assistive_bt assistive_bt_orchestrator
```

A source scan for `memory/query`, `navigation_recommendation`, `MemoryQuery`, and `NavigationRecommendation` under `src/wheelchair_assistive_bt` returned no matches. The N0 launch contains no memory node/client and no baseline runner.

After smoke cleanup, no temporary `gz sim`, `planner_server`, `bt_navigator`, or `assistive_bt_orchestrator` processes remained.

## Requirement-by-requirement result

| Requirement | Status | Evidence |
|---|---|---|
| Explicit BT orchestration for N0 | PASS | XML tree loaded and executed in the integrated smoke test. |
| `condition=MEMORY_OFF` is explicit | PASS | Terminal blackboard log contains `condition=MEMORY_OFF`; executable rejects another condition. |
| No memory query/client/service in N0 | PASS | Package source scan returned no memory interface references; N0 launch starts no memory nodes. |
| Nav2 receives the final goal through `/navigate_to_pose` | PASS | Orchestrator log reports send; `bt_navigator` logs `(2.00,-3.00)` to `(2.50,-3.00)`. |
| Nav2 remains planner/controller/costmap authority | PASS | The orchestrator only uses `NavigateToPose`; `controller_server` computed control effort and reached goal. |
| Terminal result is traceable | PASS | Blackboard log records IDs, condition, final-goal Nav2 result, terminal Nav2 result, success, and failure fields. |
| Failure is explicit | PASS | No-Nav2 XML test recorded `TIMEOUT waiting for /bt_navigator active`. |
| Existing baseline runner preserved | PASS | No modification made to `baseline_runner.py`. |
| Existing baseline compatibility reference | PASS (reference only) | Existing `baseline_experiment.launch.py` completed S001 direct navigation with `SUCCEEDED` to the same final pose; this was not a replacement for the BT test. |

## Observed non-blocking issue

At launch shutdown, the pre-existing `scan_frame_fixer.py` attempted a second `rclpy.shutdown()` after the launch context had already shut down, producing an `RCLError` during tear-down. Gazebo also required termination after its parent launch stopped, leaving two temporary processes that were explicitly terminated after verification. These occurred after the N0 terminal success and do not invalidate the evidence that the BT sent the final goal and Nav2 completed it. They should be addressed separately before relying on repeated unattended runs.

## Limits of this validation

- It does not validate Memory ON / N1.
- It does not validate retrieval, recommendation, strategies, waypoints, or memory writes.
- It does not measure experimental metrics or establish scientific performance.
- It uses the existing S001 safe-goal smoke geometry only; it does not alter or freeze final scenarios.

## Phase 1 conclusion

**BT Phase 1 N0 is validated at smoke-test level.** A real Nav2 execution completed successfully through the explicit Behavior Tree path with `MEMORY_OFF`, and the evidence distinguishes the orchestrator’s decision to send the final goal from Nav2’s successful execution.