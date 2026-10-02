# Validation report - Fase 1

## Verificaciones correctas

- PostgreSQL healthy, extension pgvector disponible, 50 memorias; embedding y episodic_embedding con dimension 1024.
- `colcon build --symlink-install`: 8/8 paquetes construidos.
- MemoryQuery: respuesta correcta con M001, M046, M015, M007 y M009; M001 primera, final score 0.7757807633.
- NavigationRecommendation: success=true, strategy=west, avoid_obstacle=true, prefer_clearance=true, source_memory=M001.
- Gazebo bridge publica clock, odom, tf, scan, scan_fixed y joint_states; Nav2 registra lifecycle nodes y actions, incluidas compute_path_to_pose y navigate_to_pose.
- apartment.pgm valido: 240x200, P5, coherente con el modelo SDF actualizado.

## Pruebas

- API: 2 passed, 1 skipped.
- VLA: 2 passed, 1 skipped.
- wheelchair_memory: no contiene tests; colcon marca exit code 5 por cero tests, sin fallos de asercion.

## Pendiente para la siguiente fase

Ejecutar una navegacion manual completa y establecer baseline reproducible. No se ha iniciado baseline en Fase 1.

## Fase 2 - Baseline MEMORY OFF

- `colcon build --packages-select wheelchair_description wheelchair_gazebo wheelchair_bringup --symlink-install`: correcto.
- `colcon test --packages-select wheelchair_bringup`: 6 tests, 0 errores, 0 fallos, 2 omitidos.
- TF `base_link -> lidar_link`: verificada como `(0.280, 0.000, 0.720)`.
- `/navigate_to_pose` hacia `(2.5, -3.0)`: `SUCCEEDED`; 2.370 s, 0.263 m, 2 replannings.
- La ejecución fue MEMORY OFF; no se inició Memory ON.
## Fase 3 - Memory ON

- `colcon build --packages-select wheelchair_memory wheelchair_bringup --symlink-install`: correcto con `/usr/bin/python3`.
- Grafo final: memory_node, navigation_memory_node, map_server, amcl, planner_server, controller_server y bt_navigator presentes.
- `/memory/query`: `wheelchair_interfaces/srv/MemoryQuery`; `/memory/navigation_recommendation`: `wheelchair_interfaces/srv/NavigationRecommendation`.
- Lifecycle Nav2: map_server, amcl, planner_server, controller_server y bt_navigator activos; el gestor informó `Managed nodes are active`.
- Prueba integrada real: IDs M001,M046,M015,M007,M009; M001 primera; strategy=west; waypoint=(2.5,-3.0); `/navigate_to_pose` aceptado y resultado `SUCCEEDED`.
- Resultado persistido: `2026-09-22T14:28:39.529587+00:00` en `experiments/results/memory_on_navigation_results.csv`.
- Sin cambios a PostgreSQL, pgvector, Qwen, VLA ni parámetros Nav2.
