# Validación — Blocker 1

Fecha: 2026-09-29

## Cambios realizados

- navigation_adapter.py aplica una política declarativa strategy_waypoint_offsets, relativa a la meta final.
- N1 ejecuta dos acciones Nav2 cuando existe una estrategia aplicable: waypoint de estrategia y, sólo tras SUCCEEDED, meta final común.
- Si el waypoint falla, guarda WAYPOINT_<resultado> y final_goal_nav2_result=NOT_SENT.
- Se añadieron campos: retrieved_strategy, strategy_applied, waypoint seleccionado, resultado Nav2 del waypoint, meta final y resultado Nav2 final.
- memory_on_experiment.launch.py habilita la política. N0 permanece sin memoria; su runner sólo recibe campos CSV vacíos por compatibilidad.
- El esquema consolidado del runner experimental conserva los nuevos campos.

## Comandos ejecutados

- colcon build --packages-select wheelchair_memory wheelchair_bringup --symlink-install
- python3 -m py_compile de adapter, launch y baseline runner.
- Arranque temporal de Gazebo, bridge, robot, scan fixer, memory_node, Nav2 y navigation_memory_node.
- docker compose up -d postgres tras observar que PostgreSQL estaba detenido.
- Smoke test temporal del adapter contra el stack activo, con resultados en /tmp/blocker1_smoke.csv.

## Resultados reales

La fila smoke_005 exitosa registra:

| Campo | Valor |
|---|---|
| retrieved_strategy / strategy | west / west |
| strategy_applied | true |
| selected waypoint | (2.250, -3.000), derivado del offset temporal west:-0.25:0.0 |
| waypoint_nav2_result | SUCCEEDED |
| final goal común | (2.500, -3.000) |
| final_goal_nav2_result | SUCCEEDED |
| resultado global | SUCCEEDED |
| tiempo / distancia / replanning | 11.573 s / 0.260 m / 10 |
| memorias | M001, M046, M015, M007, M009 |

La misma evidencia temporal conserva un intento anterior con waypoint ABORTED, strategy_applied=true y final_goal_nav2_result=NOT_SENT. Confirma la política explícita: si Nav2 no alcanza el waypoint, N1 no oculta el fallo ni continúa a la meta final.

## Evidencia

- CSV temporal: /tmp/blocker1_smoke.csv.
- Log temporal del stack: /tmp/blocker1_manual.log.
- La salida no se escribió en experiments/results/ y no es un experimento definitivo.

## Problemas restantes

- El offset utilizado fue exclusivamente un parámetro temporal de smoke test; los waypoints de escenarios finales deben definirse y validarse más adelante, sin ajustar resultados para favorecer N1.
- PostgreSQL estaba detenido al comienzo del smoke test; se arrancó el contenedor existente.
- Este cambio resuelve únicamente el blocker 1. No resuelve los demás blockers de escenarios, métricas, versionado, B1–B4 y robustez de campaña.
