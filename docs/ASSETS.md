# Simulation assets: ownership and provenance

These six assets were copied byte for byte from the current private project
tree in Phase J3e to preserve the experimental system. They were not regenerated,
converted, optimized or geometrically modified.

## Project-authored assets

The thesis author explicitly confirmed creation of:

- ros2/src/wheelchair_gazebo/models/apartment/model.config
- ros2/src/wheelchair_gazebo/models/apartment/model.sdf
- ros2/src/wheelchair_gazebo/models/wheelchair/model.config
- ros2/src/wheelchair_gazebo/models/wheelchair/model.sdf
- ros2/src/wheelchair_navigation/maps/apartment.pgm

The author confirmed ownership of the project's own source code and chose
Apache License 2.0 for that code and the five author-created assets listed above.
The complete, unmodified license text is in [LICENSE](../LICENSE).
Third-party materials retain their own applicable terms. Existing copyright,
license and attribution notices remain applicable to their respective components.
This document records the licensing decision; the five asset files were not edited.

## Supervisor-provided asset

Path: ros2/src/wheelchair_gazebo/models/wheelchair/meshes/silla.stl

Asset provided by thesis supervisor; original licensing/provenance
not documented in the repository.

The author explicitly chose to retain this asset unchanged in the public
candidate for reproducibility of the experimental system. It is not attributed
to the thesis author. This decision does not establish an undocumented legal
permission or license.

This mesh is explicitly excluded from the project's Apache-2.0 grant.
Neither authorship by the project author nor authorship by the supervisor is
asserted. No license is assigned to it by this project.
Its original provenance, license and redistribution permission remain unresolved.

## Validation scope

Phase J3e checked source/destination SHA-256 equality, XML structure, the PGM
header and resource references. It did not run a build, tests or simulation.
The STL was not exhaustively inspected for embedded secrets.

## Remaining package-install structure

Static inspection found three empty directories in the private source that
were not retained in the file-based candidate:

- ros2/src/wheelchair_gazebo/launch
- ros2/src/wheelchair_gazebo/config
- ros2/src/wheelchair_navigation/behavior_trees

Phase J3g classified all three as empty source directories with no tracked
contents and no active runtime consumers. Git does not preserve empty directories;
the file-based candidate therefore omitted them. No runtime files were lost.

The decision for each directory was REMOVE_INSTALL_RULE. Only the three stale
entries were removed from the two package CMake install rules:

- wheelchair_gazebo now installs worlds and models. Its active simulation launch
  is in wheelchair_bringup and loads those resources.
- wheelchair_navigation still installs launch, config and maps. Its Nav2
  configuration does not select a BT XML from the empty behavior_trees directory.
  The high-level assistive BT XML files remain in wheelchair_assistive_bt.

No directories, placeholders or runtime resources were fabricated. Static
inspection confirmed that the remaining install source directories exist.
This resolves the identified directory-install blocker; build, tests and
runtime validation remain for Phase J4.


## Scenario assets added after the public candidate

HOME/PARK/AIRPORT SDF worlds/models use local primitive geometry. Their PGM maps are deterministic rasterizations of source collision geometry using the versioned generators. AIRPORT additionally uses a small local COLLADA primitive (`models/airport/meshes/airport_pedestrian.dae`), whose metadata names the TFM deterministic scenario primitive tool; no external pedestrian model is imported. This records the inspected structure, not a new ownership or licensing assertion. Authorship/provenance and the applicable license for these newer scenario assets remain **REVIEW REQUIRED**; no automatic license grant is assigned here. Existing third-party exclusions and unresolved supervisor mesh provenance remain unchanged.
