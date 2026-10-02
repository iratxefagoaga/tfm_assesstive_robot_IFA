# BT Phase 2 — Implementation: MEMORY_ON observation path

## Scope

BT Phase 2 adds an explicit N1 Behavior Tree path that consumes the existing ROS memory services, records their output on a fresh blackboard, and then sends the unchanged common `final_goal` to Nav2. It does not apply a strategy to navigation.

Initial Git HEADs recorded before implementation:

- `/home/iratxefagoaga/workspace/tfm`: `70802a13ca80936d8ab0c773c2d376f6699d946b`
- `/home/iratxefagoaga/workspace/tfm-robot-memory`: `6430e4a5042ccea391ba29cf78489df6be06570a`

No Git staging, commit, restore, reset, checkout, or clean operation was performed.

## Files modified or created

In `/home/iratxefagoaga/workspace/tfm/ros2/src/wheelchair_assistive_bt/`:

- Modified `CMakeLists.txt`: declares `wheelchair_interfaces` and builds the N1 executable.
- Modified `package.xml`: adds the `wheelchair_interfaces` dependency.
- Created `src/memory_observation_orchestrator.cpp`.
- Created `behavior_trees/n1_memory_observation_navigation.xml`.
- Created `launch/bt_n1_phase2_smoke.launch.py`.

N0 sources and its XML remain unchanged:

- `src/assistive_bt_orchestrator.cpp`
- `behavior_trees/n0_assistive_navigation.xml`
- `launch/bt_n0_smoke.launch.py`

No file in `wheelchair_memory`, `wheelchair_interfaces`, `wheelchair_bringup`, Nav2, Gazebo, map, robot, scenarios, dataset, PostgreSQL, pgvector, embeddings, B1–B4, or experimental results was modified by Phase 2.

## N1 tree

`n1_memory_observation_navigation.xml` is deliberately small:

```text
Sequence(MemoryObservationNavigation)
  QueryMemory
  GetNavigationRecommendation
  WaitForNav2Active
  NavigateNav2(final_goal)
  FinalizeExperiment
```

The sequence ensures that a memory failure prevents `WaitForNav2Active` and `NavigateNav2` from being reached. There is no silent fallback to N0.

## Added BT nodes

### QueryMemory

Uses the existing `/memory/query` service of type `wheelchair_interfaces/srv/MemoryQuery` with blackboard context `query`, `user_id`, `location`, `task`, `goal_label` (mapped to the service `goal` field), and `k`.

On success it stores:

- `memory_ids`, `summaries`, `observations`, `actions`, `outcomes`, `preferences`
- `semantic_scores`, `context_scores`, `final_scores`
- `memory_query_result=SUCCEEDED`

It fails explicitly with `failure_stage=query_memory` for service timeout, transport error, `success=false`, no response, or empty `memory_ids`.

### GetNavigationRecommendation

Uses the existing `/memory/navigation_recommendation` service of type `wheelchair_interfaces/srv/NavigationRecommendation`, with the same request context.

On success it stores:

- `source_memory`, `recommendation_reason`, `retrieved_strategy`
- `avoid_obstacle`, `prefer_clearance`
- `recommendation_semantic_score`, `recommendation_context_score`, `recommendation_final_score`
- `recommendation_result=SUCCEEDED`

It fails explicitly with `failure_stage=get_navigation_recommendation` on timeout, transport error, `success=false`, missing response, empty strategy, or empty source memory.

The existing recommendation service performs its own internal `/memory/query`; this intentional double query was observed during the smoke test and was not optimized in this phase.

### Nav2 nodes

`WaitForNav2Active`, `NavigateNav2`, and `FinalizeExperiment` are implemented for the N1 executable only. `NavigateNav2` sends one `nav2_msgs/action/NavigateToPose` goal, whose pose is the blackboard `final_goal`. It does not call planner/controller/costmaps directly, issue `cmd_vel`, alter final goal coordinates, or create a waypoint.

## Blackboard contract

Every N1 process creates a new blackboard containing all Phase 1 terminal fields plus:

- context: `query`, `user_id`, `location`, `task`, `goal_label`, `k`
- retrieval arrays: `memory_ids`, `summaries`, `observations`, `actions`, `outcomes`, `preferences`, `semantic_scores`, `context_scores`, `final_scores`
- recommendation: `source_memory`, `recommendation_reason`, `retrieved_strategy`, `avoid_obstacle`, `prefer_clearance`, and recommendation scores
- state: `memory_query_result`, `recommendation_result`, `strategy_applied`

`strategy_applied` is initialized to `false` and is never changed in Phase 2. No `expected_*` scenario field is operationalized in this blackboard.

## Explicitly deferred to BT Phase 3

The package contains no `ResolveStrategyWaypoint`, `WaypointApplicable`, `strategy_waypoint_offsets`, `selected_waypoint`, `NavigateThroughPoses`, sequential waypoint navigation, or memory-write mechanism. A retrieved strategy is traceability information only in this phase.

## Build commands

```bash
cd /home/iratxefagoaga/workspace/tfm/ros2
deactivate 2>/dev/null || true
source /opt/ros/jazzy/setup.bash
which python3  # /usr/bin/python3
colcon build --packages-select wheelchair_interfaces wheelchair_assistive_bt --symlink-install
colcon build --symlink-install
```

## Difference from Phase 1

Phase 1 provides a fully isolated N0 executable with no memory client. Phase 2 preserves that executable and adds a separate N1 executable, `memory_observation_bt_orchestrator`, so N0 cannot instantiate memory clients by construction. N1 observes/reports retrieval and recommendation, but invokes Nav2 exactly once with the same final goal geometry used by N0.