# HOME-01 — Personal clearance preference

Status: **route-calibration candidate; not frozen for the final campaign yet**.

## Purpose

Compare the same navigation task with memory disabled (N0) and enabled (N1). N1 retrieves the existing U01 episodic preference for greater lateral clearance and, when the recommendation resolves to `west`, applies one intermediate waypoint. Nav2 remains responsible for planning, control, collision checking, and the final goal in both conditions.

## Common task

- Environment: `home`
- Initial pose: `(2.0, -3.0, yaw=0.0)`
- Final goal candidate: `(6.0, 5.5, yaw=0.0)`
- Scenario id: `HOME_01_clearance_preference`
- Same Nav2 configuration in N0 and N1.

## Conditions

### N0 — MEMORY_OFF

The orchestrator sends only the common final goal to Nav2. No memory services or strategy waypoint are used.

Launch:

```bash
ros2 launch wheelchair_assistive_bt home_n0.launch.py
```

Default CSV: `/tmp/home_01_n0.csv`

### N1 — memory enabled

Frozen retrieval context candidate:

- query: `navegar evitando la mesa`
- user: `U01`
- location: `salon`
- task: `navegacion`
- goal label: `dormitorio`
- k: `3`

The expected retrieved strategy from the existing frozen memory is `west`. The launch maps it to the candidate waypoint `(goal_x - 12.0, goal_y - 3.0)`, i.e. `(-6.0, 2.5)` for the default final goal. This waypoint is intentionally in the open west distributor and is used only when the recommendation actually returns `west`.

Launch:

```bash
ros2 launch wheelchair_assistive_bt home_n1.launch.py
```

Default CSV: `/tmp/home_01_n1.csv`

## Calibration acceptance criteria

Do **not** use HOME-01 in the final experimental campaign until all of these are observed in simulation:

1. N0 reaches the common final goal without manual intervention.
2. N1 retrieves the expected memory/recommendation and reaches the same final goal.
3. N1's `west` waypoint is feasible and produces a visibly/topologically different route from N0.
4. Both routes remain valid under the exact same Nav2 footprint, inflation, controller, and map.
5. The selected waypoint does not create a safety exception or bypass Nav2.

If any item fails, adjust only the candidate goal/waypoint launch arguments and repeat calibration. Do not change the memory dataset or Nav2 safety parameters to force the expected result.

## Experimental interpretation

HOME-01 is intended to test adaptation to a user's clearance preference, not speed optimization. A longer N1 route is therefore acceptable. `navigation_time_s` and `distance_m` are outcomes, while scenario-specific context compliance is the main adaptation outcome once its independent ground-truth rule is frozen.

`min_clearance_m` remains non-primary/N/A until its measurement has been independently validated.
