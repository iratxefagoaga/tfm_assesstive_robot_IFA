# Fase 4 - Infraestructura de escenarios comparables

Fecha: 2026-09-22.

## Objetivo alcanzado

Se creó infraestructura reproducible para ejecutar BASELINE (N0) y MEMORY ON (N1) sobre la misma definición de escenario. No se realiza análisis, agregación ni atribución de rendimiento en esta fase.

## Artefactos

- `experiments/scenarios/S001_shared_safe_goal.json`: escenario declarativo con pose inicial, objetivo, usuario, contexto, configuración de obstáculos y preferencia esperada.
- `experiments/configs/navigation_conditions.json`: activos compartidos, condiciones N0/N1, lanzadores y límites de ejecución.
- `experiments/scripts/run_navigation_scenario.py`: ejecutor que lee JSON, evita sobrescritura, conserva logs, termina procesos al aparecer un resultado y escribe un manifiesto.
- `experiments/results/phase4/run_manifest.csv`: trazabilidad por ejecución.
- `wheelchair_bringup/launch/baseline_experiment.launch.py` y `memory_on_experiment.launch.py`: lanzadores parametrizados por escenario.

## Controles de comparabilidad

- Misma pose inicial declarada: `(2.0, -3.0, 0.0)`.
- Mismo objetivo declarado: `(2.5, -3.0)`, etiqueta `dormitorio`.
- Mismo usuario, ubicación, tarea, mundo, mapa, robot, sensores y parámetros Nav2.
- N0 no inicia nodos de memoria.
- N1 inicia la memoria y registra retrieval/recommendation; durante Fase 4 conserva la estrategia recuperada pero usa el mismo objetivo final declarado. No se introduce una ventaja de navegación distinta.
- N1 calienta el modelo antes de Nav2 para evitar pérdida de heartbeats; no cambia parámetros de Nav2.

## Ejecuciones reales de aceptación

Escenario: `S001_shared_safe_goal`; ejecución: `phase4_acceptance_002`.

| Condición | Resultado observado | Archivo crudo |
|---|---|---|
| BASELINE | `SUCCEEDED` | `S001_shared_safe_goal__baseline__phase4_acceptance_002.csv` |
| MEMORY ON | `SUCCEEDED` | `S001_shared_safe_goal__memory_on__phase4_acceptance_002.csv` |

La fila de manifest conserva escenario, condición, ejecución, contexto, pose, objetivo, rutas de artefactos, timeout y estado Nav2 observado.

## Incidencia registrada

La ejecución `phase4_acceptance_001` de BASELINE no generó navegación por un shebang con CRLF en `baseline_runner.py`. El manifiesto conserva `NO_RESULT`; se corrigieron sólo los finales de línea y se repitió con `phase4_acceptance_002`. No se reemplazó ni manipuló ningún resultado.

## Límite de esta fase

Los dos resultados de aceptación prueban que la infraestructura ejecuta ambas condiciones sobre la misma especificación. No constituyen análisis de superioridad, comparación de métricas ni evidencia estadística.
