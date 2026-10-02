# BT Phase 1 — Implementation: N0 / MEMORY_OFF

## Scope and decision

This report records the implementation of Phase 1 of the Behavior Tree integration defined in `reports/behavior_tree_architecture_design.md`: an explicit, reproducible N0 orchestration path with `condition=MEMORY_OFF`.

The implementation deliberately stops here. It does not implement N1, retrieval, recommendations, strategy selection, intermediate waypoints, or persistence of episodic experience.

## New ROS 2 package

A new isolated package was added to the ROS 2 workspace:

- `src/wheelchair_assistive_bt/`
- executable: `wheelchair_assistive_bt/assistive_bt_orchestrator`
- BT XML: `behavior_trees/n0_assistive_navigation.xml`
- smoke launch: `launch/bt_n0_smoke.launch.py`

The package is `ament_cmake` / C++ and depends only on ROS 2, Nav2 action messages, lifecycle messages, `ament_index_cpp`, and BehaviorTree.CPP. It has no dependency on `wheelchair_memory`, `wheelchair_interfaces`, PostgreSQL, pgvector, sentence-transformers, or the memory virtual environment.

## BT implementation

The tree loaded by the orchestrator is:

```text
Sequence(MemoryOffNavigation)
  WaitForNav2Active
  NavigateNav2(final_goal)
  FinalizeExperiment
```

`NavigateNav2` is a custom BT action node that uses the Nav2 public action `/navigate_to_pose` (`nav2_msgs/action/NavigateToPose`). It does not invoke planner, controller, costmaps, recovery, or `cmd_vel` directly. Consequently, the installed Nav2 BT remains responsible for planning, control, costmap use, recovery, and collision-related behavior.

The final goal is supplied through ROS parameters (`goal_x`, `goal_y`, `goal_yaw`); no scenario identifier or S001 coordinate is hardcoded into the executable.

## Blackboard contract

A fresh blackboard is created for every orchestrator execution and contains at least:

- `experiment_id`
- `scenario_id`
- `condition` (strictly validated as `MEMORY_OFF`)
- `run_id`
- `final_goal` (`geometry_msgs/PoseStamped`, frame `map`)
- `final_goal_nav2_result`
- `nav2_result`
- `success`
- `failure_stage`
- `failure_reason`

The result vocabulary used by the orchestrator includes `SUCCEEDED`, `ABORTED`, `CANCELED`, `REJECTED`, and `TIMEOUT`, plus the pre-execution states `NOT_SENT` and `NOT_STARTED`.

## Failure behavior

- `WaitForNav2Active` waits for `/bt_navigator/get_state` to become `active` and fails explicitly on timeout.
- `NavigateNav2` fails explicitly if the action server is unavailable, a goal is rejected, the action returns a failure result, or the configured navigation timeout is reached. A timed-out sent goal is canceled.
- `FinalizeExperiment` preserves the terminal Nav2 result in the blackboard/log.

No recovery policy is reimplemented in the assistive layer. Nav2 retains its installed recovery policy.

## Launch isolation

`bt_n0_smoke.launch.py` starts one simulation/Nav2 stack and the new N0 orchestrator. It does not start `baseline_runner.py`, `memory_node`, `navigation_memory_node`, `navigation_memory_adapter`, or any other memory service/client. The orchestrator ending triggers launch shutdown, preventing the helper from becoming a second concurrent navigation client.

Existing baseline files, including `wheelchair_bringup/scripts/baseline_runner.py`, were preserved and were not modified.

## Explicitly unchanged by this phase

No modification was made by this implementation to:

- PostgreSQL / pgvector, embeddings, datasets, `MemoryQuery`, or `NavigationRecommendation`;
- `navigation_adapter.py`, `navigation_memory_node.py`, `memory_node.py`, or memory launch files;
- Nav2 planner/controller/costmap configuration or installed Nav2 XML;
- robot, Gazebo world, map, sensors, final scenarios, or B1–B4;
- the existing baseline runner.

The repository already had local modifications to Nav2 and other packages before this phase. The working tree was therefore not a clean provenance baseline; this report does not claim those pre-existing changes were introduced by Phase 1.

## Build evidence

Package-only build, using `/usr/bin/python3` after sourcing ROS Jazzy:

```text
Starting >>> wheelchair_assistive_bt
Finished <<< wheelchair_assistive_bt [1.46s]
Summary: 1 package finished [1.68s]
```

Full workspace build:

```text
Summary: 9 packages finished [3.66s]
```

The installed executable was confirmed as:

```text
wheelchair_assistive_bt assistive_bt_orchestrator
```

## Deferred work

N1 remains intentionally deferred. The future N1 BT must make the validated memory/recommendation/waypoint policy explicit without changing Nav2’s planner, controller, costmaps, or recovery behavior, and must preserve paired N0/N1 comparability.