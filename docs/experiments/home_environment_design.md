# HOME environment design — S1 candidate

Status: HISTORICAL DESIGN ONLY, superseded for runtime by [HOME_01.md](HOME_01.md) and [SCENARIO_MATRIX.md](SCENARIO_MATRIX.md). All coordinates are proposed, metres; yaw in radians.
No world, map, launch, memory, metric or experimental ground truth is created.

## 1. Current environment audit

Evidence paths are relative to the repository root.

| Evidence | Observation |
| --- | --- |
| ros2/src/wheelchair_gazebo/models/apartment/model.sdf | Static floor 12 × 10; walls 0.20 thick, 2.60 high; free inner bounds x ±5.80, y ±4.80; no internal room partitions. |
| Same SDF | Table (-1.2,0.8), 1.20 × 0.70 × 0.76; sofa (2,1.8), 1.60 × 0.75 × 0.80; bed (3.3,-1.7), 1.80 × 1.35 × 0.60; cabinet (-3,-2), 1.20 × 0.45 × 1.30; plant (-3.8,3), radius 0.28. |
| ros2/src/wheelchair_navigation/maps/apartment.pgm and apartment.yaml | P5, 240 × 200, resolution 0.05; origin (-6,-5,0), trinary, negate 0, thresholds 0.65/0.25. Extent 12 × 10. |
| ros2/src/wheelchair_bringup/launch/simulation.launch.py | Apartment world/wheelchair model selected internally; spawn (2,-3,0.11), yaw 0; GZ_SIM_RESOURCE_PATH uses installed models share. |
| ros2/src/wheelchair_navigation/launch/navigation.launch.py | Apartment map and nav2_params selected internally; canonical lifecycle node list loaded from resource. |
| ros2/src/wheelchair_navigation/config/nav2_params.yaml | AMCL initial (2,-3,0), yaw 0; costmap resolution 0.05; inflation radius 0.70, scaling 3.0; NavFn and regulated pure pursuit. |
| ros2/src/wheelchair_bringup/launch/bridge.launch.py | clock, cmd_vel, odom, tf, joint_states, scan bridges; scan_frame_fixer supplies scan_fixed. |
| ros2/src/wheelchair_bringup/launch/bringup.launch.py | Legacy flow uses 3/5/10 s timers and starts memory/adapter; do not select it as campaign supervisor. |
| ros2/src/wheelchair_assistive_bt/launch/bt_n0_smoke.launch.py and bt_n1_phase3_smoke.launch.py | Engineering flows preserve readiness and launch-owned shutdown. Environment resource selection is apartment-specific. |
| ros2/src/wheelchair_assistive_bt/src/memory_observation_orchestrator.cpp | Configured global dx/dy added to final goal; optional single waypoint then final goal, preserving goal yaw. |

Keep apartment available for engineering. Nav2 lifecycle/service discovery remains
intermittent; successful integrated navigation in the public candidate remains
unvalidated. HOME design does not resolve that limitation.

## 2. Wheelchair dimensions and footprint

Evidence: ros2/src/wheelchair_gazebo/models/wheelchair/model.sdf:

- Base collision box: x length 0.72, y width 0.68, height 0.20.
  Base link z=0.20 in model frame.
- Drive wheels: radius 0.16, thickness 0.045, y centres ±0.31;
  separation 0.62. Lateral extremes ±0.3325 fit inside base width.
- Casters: radius 0.05, centres (-0.30,±0.23,0.05), inside base XY envelope.
- Planar collision envelope: 0.72 × 0.68.
- Visual silla.stl uses scale 0.001; its visual size is not the collision size.
  No occupant collision envelope/overall occupied height is defined.
- LiDAR z=0.92, maximum range 12; camera z=0.88.
- URDF links.xacro primarily declares TF links, not dimensional collisions.

Both Nav2 costmaps specify:
[[0.36,0.34],[0.36,-0.34],[-0.36,-0.34],[-0.36,0.34]].

Centred forward lateral clearance = (clear width−0.68)/2.
In-place rotational swept diameter = sqrt(0.72²+0.68²) ≈0.990.
Provide 2 × 2 unobstructed turning pockets. Avoid turning inside narrow throats.
These are simulated robot dimensions, not real occupied-wheelchair accessibility
certification. Existing STL provenance remains independently unresolved.

## 3. Proposed house and room layout

External extent 20 × 16: x=[-10,10], y=[-8,8], area 320 m².
Outer/internal wall thickness 0.20, height 2.60. Floor thickness 0.10,
top z=0; ceiling omitted. Inner exterior faces x=±9.80, y=±7.80.
World and map axes aligned; +x east, +y north.

Approximate ASCII plan; numerical clear bounds are authoritative:

    NORTH +y             <------------ 20 m ------------>
    y=+8   +---------------+---------------+---------------+
           | office        | second bed    | main bedroom  |
           | 6.4 × 4.4     | 6.4 × 4.4     | 6.4 × 4.4     |
    y=3.3  +----D----------+--D------------+----D----------+
           | living          north band        dining     |
           | 6.4 × 6.4    [fixed cabinet]      6.4 × 6.4   |
           |                  A: 1.35 m                   |
    y=1.2  |       +--------- CORE ----------+              |
           |       | bathroom | storage     |              | 16 m
    y=-1.2 |       +------------------------+              |
           |                  B: 2.00 m                   |
    y=-3.3 +----D----------+------D----------+----D----------+
           | kitchen       | hall/entrance | utility/guest |
           | 6.4 × 4.4     | 6.4 × 4.4     | 6.4 × 4.4     |
    y=-8   +---------------+----ENTRY------+---------------+
            x=-10         -3.3            3.3            10

| Space | Clear x bounds | Clear y bounds | Dimensions |
| --- | --- | --- | --- |
| Living room | -9.8…-3.4 | -3.2…3.2 | 6.4 × 6.4 |
| Dining area | 3.4…9.8 | -3.2…3.2 | 6.4 × 6.4 |
| Kitchen | -9.8…-3.4 | -7.8…-3.4 | 6.4 × 4.4 |
| Entrance/hall | -3.2…3.2 | -7.8…-3.4 | 6.4 × 4.4 |
| Utility/guest | 3.4…9.8 | -7.8…-3.4 | 6.4 × 4.4 |
| Office | -9.8…-3.4 | 3.4…7.8 | 6.4 × 4.4 |
| Second bedroom | -3.2…3.2 | 3.4…7.8 | 6.4 × 4.4 |
| Main bedroom | 3.4…9.8 | 3.4…7.8 | 6.4 × 4.4 |
| Bathroom inside core | -3.0…-0.1 | -1.0…1.0 | 2.9 × 2.0 |
| Storage inside core | 0.1…3.0 | -1.0…1.0 | 2.9 × 2.0 |

Omitted 0.20 bands are separating walls. Core outer bounds include its walls:
x=[-3.2,3.2], y=[-1.2,1.2]. Distribution bands are x=[-3.2,3.2],
north y=[1.2,3.2], south y=[-3.2,-1.2]. Living and dining open onto BOTH
bands; core-side wall segments must not close these connections.
Core separates the routes and prevents a direct central shortcut.

## 4. Door and corridor widths

Clear widths exclude jambs. Doors remain statically fully open, no swing volumes.

| Opening | Centre | Wall orientation | Clear width |
| --- | --- | --- | --- |
| Exterior entrance | (0,-7.9) | horizontal | 1.80 |
| Hall/south band | (0,-3.3) | horizontal | 1.80 |
| Kitchen/living | (-6,-3.3) | horizontal | 1.60 |
| Kitchen/hall | (-3.3,-5.6) | vertical | 1.60 |
| Utility/dining | (6,-3.3) | horizontal | 1.60 |
| Utility/hall | (3.3,-5.6) | vertical | 1.60 |
| Office/living | (-6,3.3) | horizontal | 1.60 |
| Second bedroom/north band | (-2.4,3.3) | horizontal | 1.60 |
| Main bedroom/dining | (5.4,3.3) | horizontal | 1.60 |
| Bathroom/south band | (-1.7,-1.1) | horizontal | 1.40 |
| Storage/south band | (1.7,-1.1) | horizontal | 1.40 |

- Ordinary distribution: 2.00 clear, ideal side margin 0.66.
- Narrow A throat: 1.35 clear, ideal side margin 0.335.
- Room doors: 1.60 clear, ideal side margin 0.46.
- Core doors: 1.40 clear, ideal side margin 0.36.
- Reserve 2 × 2 turning areas at route junctions and room approaches.
- Second-bedroom opening spans x=[-3.2,-1.6], clear of cabinet.
- Bathroom is not a through-route; fixture arrangement/turning accessibility
  requires a later check and is not claimed as fully accessible.
- Map rasterization/tracking errors reduce these ideal margins.

## 5. Furniture inventory and proposed coordinates

Static boxes, yaw 0, dimensions dx × dy × dz; centre z=dz/2.
Visual and collision footprints match, including furniture overhangs.
Tables use conservative solid-to-floor envelopes: no navigation underneath.
Primitive geometry/colours, no new external mesh/texture licensing dependencies.

| Furniture / room | Centre (x,y) | Dimensions |
| --- | --- | --- |
| Sofa / living | (-8.5,0) | 2.4 × 0.9 × 0.9 |
| Armchairs N/S | (-8.7,2.3), (-8.7,-2.2) | each 0.9 × 0.9 × 0.9 |
| Coffee table | (-7.2,-0.4) | 1.2 × 0.6 × 0.5 |
| Side table | (-9,1.3) | 0.5 × 0.5 × 0.6 |
| North-band cabinet | (0.7,2.875) | 4.2 × 0.65 × 1.1 |
| Dining table | (8.3,0) | 1.2 × 2.0 × 0.76 |
| Dining chairs W1/W2 | (7.35,-0.6), (7.35,0.6) | each 0.45 × 0.45 × 0.9 |
| Dining chairs E1/E2 | (9.35,-0.6), (9.35,0.6) | each 0.45 × 0.45 × 0.9 |
| Dining chairs N/S | (8.3,1.45), (8.3,-1.45) | each 0.45 × 0.45 × 0.9 |
| Kitchen west counter | (-9.4,-5.6) | 0.6 × 3.6 × 0.9 |
| Kitchen south counter | (-6.8,-7.4) | 4.6 × 0.6 × 0.9 |
| Fridge | (-4.2,-7.1) | 0.7 × 0.7 × 1.8 |
| Kitchen island | (-6.8,-5.5) | 1.5 × 0.8 × 0.9 |
| Main bed | (8.3,6.5) | 1.6 × 2.0 × 0.6 |
| Main wardrobe | (9.4,4.8) | 0.6 × 2.0 × 2.0 |
| Bedside table | (7,7.3) | 0.45 × 0.45 × 0.55 |
| Second bed | (1.7,6.4) | 1.4 × 2.0 × 0.6 |
| Second wardrobe | (2.8,4.8) | 0.6 × 2.0 × 2.0 |
| Office desk | (-8.1,6.9) | 1.8 × 0.8 × 0.75 |
| Office chair | (-8.1,5.9) | 0.55 × 0.55 × 0.9 |
| Bookcase | (-9.4,5.5) | 0.5 × 1.8 × 1.8 |
| Hall console | (2.5,-6.5) | 0.6 × 1.5 × 0.9 |
| Utility cabinet | (9.4,-5.6) | 0.6 × 3.6 × 1.8 |
| Shower tray | (-2.4,0.5) | 1.0 × 0.8 × 0.1 |
| WC | (-0.65,0.5) | 0.55 × 0.7 × 0.8 |
| Basin | (-0.6,-0.6) | 0.7 × 0.4 × 0.85 |
| Storage shelf | (2.6,0.1) | 0.5 × 1.6 × 1.8 |

North cabinet spans x=[-1.4,2.8], y=[2.55,3.2]. Against core outer face
y=1.2 it creates a 1.35 throat, length 4.2. Furniture must not intrude on
the route lines or turning pockets. Check fixture overlap and actual envelopes
when modelling; the table is a deterministic proposal, not a generated scene.

## 6. Candidate narrow and wide routes

Same start S=(-6,1.875) and goal G=(5.4,5.2), identical world state.

A: S → (-4,1.875) → (4,1.875) → (5.4,1.875) → G.
Rectilinear reference length 14.725; crosses north throat along its centre.
Ideal straight-throat footprint side clearance 0.335.

B: S → (-4,1.875) → (-4,-2.2) → (0,-2.2) → (4,-2.2)
→ (5.4,-2.2) → G.
Reference length 22.875, approximately 55% longer; south band width 2.00,
ideal side margin 0.66. Both share the final 1.60 bedroom door.

Reference polylines are analytic design measurements, NOT Nav2 trajectories.
Both are geometrically feasible for the current footprint with turning pockets
outside the throat. Nav2 planability/execution are validation gates, not proven:
current inflation radius 0.70 makes the 1.35 passage costly. Its centre is 0.675
from obstacles, outside circumscribed footprint radius ≈0.495; padding,
rasterization and controller tracking still need checking with unchanged tuning.
If A is rejected, revise HOME geometry explicitly instead of relaxing safety.

Do not assume N0 takes A: NavFn minimizes cost, not just distance; B may already
be preferred by inflation. Whether personalization changes routes is an open
experimental question. No expected efficacy or frozen route labels are assigned.

## 7. Candidate start/goal poses

| Name | (x,y,yaw) | Candidate use |
| --- | --- | --- |
| HOME_ENTRY | (0,-6.5,1.570796) | Preferred HOME spawn |
| HOME_LIVING | (-6,1.875,0) | S |
| HOME_MAIN_BEDROOM | (5.4,5.2,1.570796) | G, open staging area |
| HOME_OFFICE | (-6,5.5,1.570796) | Entrance → office |
| HOME_KITCHEN | (-4.6,-5.0,3.141593) | Bedroom → kitchen |
| HOME_SECOND_BEDROOM | (-0.7,5.8,1.570796) | Future destination |
| HOME_WIDE_CONTROL | (0,-2.2,1.570796) | Route-B selector candidate |

Provisionally retain spawn z=0.11; verify floor/wheel settling later.
AMCL initial pose MUST match selected spawn. Do not retain apartment initial
x/y/yaw when HOME is selected. Poses are not seeded memories or S1 ground truth.
All future queries use the same static house. No actors or moving doors/chairs;
Mall/Airport dynamic contexts remain future work.

### Strategy waypoint limitation

Resolver uses final_goal+(dx,dy) in global coordinates and preserves final yaw.
The engineering west:-0.25:0.0 near G does NOT force a route around this core.
For this G only, the illustrative wide control point (0,-2.2) corresponds to
offset (-5.4,-7.4). This is design arithmetic, NOT a configuration or approved
meaning for west. Scenario-specific binding needs separate approval and checks
for BOTH legs; one fixed offset is not a general room-navigation policy.
Do not change resolver, memory, ranking or datasets for this drawing.

## 8. Required future Gazebo artifacts

Not created now:

- ros2/src/wheelchair_gazebo/models/home/model.config
- ros2/src/wheelchair_gazebo/models/home/model.sdf
- ros2/src/wheelchair_gazebo/worlds/home.world

Static model named home; existing wheelchair unchanged; deterministic furniture
IDs and primitive geometry. Reuse current physics/sensor/system plugin pattern
and installed models resource path. No random positions or new external assets.

## 9. Required future Nav2/map artifacts

- ros2/src/wheelchair_navigation/maps/home.pgm
- ros2/src/wheelchair_navigation/maps/home.yaml
- Proposed geometry manifest experiments/configs/home_geometry_v1.json.
- Proposed named poses experiments/configs/home_poses_v1.yaml, marked CANDIDATE.

Resolution proposal 0.05. Include 1 m exterior margin: extent 22 × 18,
origin (-11,-9,0), image 440 × 360. Same world/map axes and fixed origin.
Rasterize static collision envelopes deterministically from the same geometry
authority used for SDF; record algorithm, obstacle-height policy and hashes.
No hand-painted mismatch. Low fixtures require explicit static occupancy policy
rather than sole reliance on LiDAR detection. Validate image y-axis convention,
free widths and pose feasibility. Preserve current thresholds provisionally.
No planner/controller/footprint/inflation changes proposed.

## 10. Integration plan

1. Freeze HOME geometry version and door schedule independently of memories,
   queries, route hypotheses or scientific results.
2. Implement only new HOME resources and map from one geometry specification;
   check room bounds, collision/visual agreement, door widths and turning sweep.
3. Add allowlisted environment resource selection with apartment defaults intact,
   using ament_index paths. Choose small launch parameterization or separate HOME
   launch after review. Select world, map and initial pose together.
4. Forward initial pose to spawn AND AMCL. Propagate profile to N0/N1 wrappers;
   preserve bridge/scan_fixed, readiness before each goal and one shutdown owner.
   No TimerAction delays. Canonical lifecycle list remains map_server, amcl,
   planner_server, controller_server, behavior_server, bt_navigator,
   waypoint_follower, velocity_smoother.
5. Existing models/worlds/maps install directories can include new resources;
   verify install contents and profile loading without stale private paths.
6. Later bounded engineering validation: both routes planable/executable,
   correct localization, failure blocks goals, shutdown clean. Known discovery
   instability remains unresolved; no arbitrary timeout increases.
7. Separately approve S1 strategy binding, frozen poses and measurement protocol.
   No scientific campaign is authorized by K0.

N0/N1 must use identical geometry hashes, furniture and reset poses/state.
Distinguish centre-to-obstacle distance, footprint clearance and executed
trajectory clearance. Ideal margins here do not implement min_clearance_m:
existing logging remains N/A pending separate metric definition/authorization.

## 11. Existing files that remain untouched

Apartment model/world/map/YAML; wheelchair SDF/STL/URDF; nav2_params.yaml;
required_nav2_nodes.txt; all bridge, launch, lifecycle and BT contracts;
resolver/logging; memory/config/retrieval; seed/queries; B1–B4/results/manifests;
historical reports. K0 creates only this document; no build, simulation,
stage, commit, remote or push.

## 12. Reproducibility and open decisions

- Approve numerical room/furniture layout and bathroom fixture/turning approach.
  These dimensions do not claim real-world accessibility compliance.
- Confirm A with unchanged costmaps/controller; validate useful A/B tradeoff
  without presupposing baseline route or personalization benefit.
- Choose launch environment selector and canonical spawn/AMCL binding.
- Approve goal-conditioned waypoint meaning separately from resolver semantics.
- Freeze geometry/map/pose hashes and relevant initial localization/random seeds
  before future runs; no random furniture or dynamic actors in HOME.
- Define future clearance measurement separately from these analytic margins.
- Existing silla.stl provenance/redistribution remains independently unresolved.
- Nav2 lifecycle/discovery limits remain; this design cannot promise a campaign.

K0b HOME IMPLEMENTATION: READY for separate geometric implementation and its
validation gates. S1 campaign: NOT READY.
