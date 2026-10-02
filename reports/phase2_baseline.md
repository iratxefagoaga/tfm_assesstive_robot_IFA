# Fase 2 — Baseline reproducible (MEMORY OFF)

Fecha de cierre: 2026-09-22.

## Objetivo y alcance

Se creó un baseline de navegación reproducible con la memoria completamente desconectada. `wheelchair_bringup baseline.launch.py` inicia únicamente Gazebo, bridge, `robot_state_publisher`, `scan_frame_fixer` y Nav2. No lanza `memory_node`, `navigation_memory_node` ni `navigation_memory_adapter`.

`baseline_runner.py` acepta el objetivo mediante los parámetros `goal_x` y `goal_y`, usa `/navigate_to_pose` y guarda condición, objetivo, estado, tiempo monotónico, distancia odométrica y replannings en `experiments/results/baseline_navigation_results.csv`.

## Correcciones necesarias

- Se añadió el launch aislado `baseline.launch.py` y el ejecutable `baseline_runner.py`.
- Se alinearon las ruedas físicas con los ejes de las articulaciones del diferencial.
- Se corrigieron las transformaciones estáticas del URDF para que coincidan con las poses físicas del SDF. En particular, `base_link -> lidar_link` pasó a `(0.28, 0, 0.72)`, dentro del volumen vertical del voxel costmap. Antes se publicaba a 0.92 m y provocaba el aviso `Sensor origin ... out of map bounds`.
- No se modificaron el mapa, mundo, sensores, Nav2 ni sus parámetros.

## Ejecución

```bash
source /opt/ros/jazzy/setup.bash
source ~/workspace/tfm/ros2/install/setup.bash
ros2 launch wheelchair_bringup baseline.launch.py
```

El objetivo por defecto reproducible es `(2.5, -3.0)` en `map`. Se puede variar sin modificar código:

```bash
ros2 run wheelchair_bringup baseline_runner.py --ros-args -p goal_x:=X -p goal_y:=Y
```

## Validación final

- Compilación de `wheelchair_description`, `wheelchair_gazebo` y `wheelchair_bringup`: FUNCIONA.
- Tests disponibles: 6 tests, 0 errores, 0 fallos y 2 omitidos: FUNCIONA.
- Grafo MEMORY OFF: FUNCIONA; no hubo nodos de `wheelchair_memory` en la ejecución.
- Ciclo de vida Nav2: FUNCIONA; `map_server`, `amcl`, `planner_server`, `controller_server` y `bt_navigator` llegaron a activo.
- TF `base_link -> lidar_link`: FUNCIONA; verificada como `(0.280, 0.000, 0.720)`.
- Aviso de origen de sensor fuera del costmap: NO OBSERVADO en la ejecución final.
- `/navigate_to_pose`: FUNCIONA; Nav2 informó `Goal succeeded`.
- Persistencia de métricas: FUNCIONA.

Muestra final de aceptación:

| Condición | Objetivo (map) | Estado | Tiempo (s) | Distancia (m) | Replanning |
|---|---:|---|---:|---:|---:|
| MEMORY_OFF | (2.5, -3.0) | SUCCEEDED | 2.370 | 0.263 | 2 |

Las cuatro ejecuciones anteriores `ABORTED` se conservan en el CSV como trazabilidad de los fallos previos a la alineación TF/cinemática; no forman parte de la muestra de aceptación.

## Estado de Fase 2

CERRADA. El baseline MEMORY OFF acepta un objetivo, ejecuta navegación con éxito y registra resultado, tiempo, distancia y replannings. Memory ON no se ha iniciado ni probado.