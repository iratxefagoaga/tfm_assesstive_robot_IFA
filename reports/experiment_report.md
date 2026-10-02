# Informe de ejecución experimental

Fecha: 2026-09-28

## Protocolo ejecutado

- Escenario: S001_shared_safe_goal.
- Configuración: phase5_automated_navigation.
- Lote: protocol_20260928.
- Repeticiones solicitadas: 5.
- Orden aplicado en cada repetición: baseline MEMORY_OFF, seguido de MEMORY_ON.
- Pose inicial declarada: x=2.0, y=-3.0, yaw=0.0.
- Meta declarada: x=2.5, y=-3.0, etiqueta dormitorio.
- Resultados: experiments/results/phase5/acceptance_final.

No se sobrescribieron los resultados previos. Se preservaron los CSV crudos, logs y manifiestos de todas las ejecuciones, incluido el intento sin resultado crudo.

## Registros observados

| run_id | condición | nav2_result observado | success | time_s | distance_m | replanning_events | memoria / estrategia |
|---|---|---|---|---:|---:|---:|---|
| protocol_20260928_001 | MEMORY_OFF | ABORTED | false | 1.276 | 0.073 | 1 | campos vacíos por diseño |
| protocol_20260928_001 | MEMORY_ON | SUCCEEDED | true | 3.031 | 0.260 | 2 | M001,M046,M015,M007,M009; west |
| protocol_20260928_002 | MEMORY_OFF | SUCCEEDED | true | 3.161 | 0.261 | 2 | campos vacíos por diseño |
| protocol_20260928_002 | MEMORY_ON | SUCCEEDED | true | 3.651 | 0.264 | 3 | M001,M046,M015,M007,M009; west |
| protocol_20260928_003 | MEMORY_OFF | ABORTED | false | 0.644 | 0.000 | 0 | campos vacíos por diseño |
| protocol_20260928_003 | MEMORY_ON | SUCCEEDED | true | 3.264 | 0.261 | 2 | M001,M046,M015,M007,M009; west |
| protocol_20260928_004 | MEMORY_OFF | ABORTED | false | 0.899 | 0.052 | 0 | campos vacíos por diseño |
| protocol_20260928_004 | MEMORY_ON | NO_RESULT | no registrado | no registrado | no registrado | no registrado | manifiesto y log preservados |
| protocol_20260928_005 | MEMORY_OFF | ABORTED | false | 3.487 | 0.132 | 2 | campos vacíos por diseño |
| protocol_20260928_005 | MEMORY_ON | SUCCEEDED | true | 3.671 | 0.261 | 3 | M001,M046,M015,M007,M009; west |

## Trazabilidad Memory ON observada

Las cuatro ejecuciones Memory ON con CSV registraron:

- memory_ids: M001,M046,M015,M007,M009.
- semantic_score de la memoria seleccionada: 0.7510414032.
- context_score: 1.0000000000.
- final_score: 0.7759372629.
- strategy: west.
- waypoint: x=2.500, y=-3.000.
- resultado Nav2: SUCCEEDED.

## Ejecución sin resultado CSV

Memory ON protocol_20260928_004 no produjo CSV crudo. El manifiesto registra launcher_timed_out=true y observed_nav2_status=NO_RESULT. El log asociado contiene la pérdida de heartbeat de planner_server y la posterior desactivación del ciclo de vida de Nav2. El log se conserva en:

experiments/results/phase5/acceptance_final/S001_shared_safe_goal__memory_on__protocol_20260928_004.log

## Artefactos

- Consolidado: experiments/results/phase5/acceptance_final/navigation_results.csv.
- Manifiesto: experiments/results/phase5/acceptance_final/run_manifest.csv.
- CSV y logs individuales: experiments/results/phase5/acceptance_final/.

Este informe presenta únicamente registros observados. No contiene comparación estadística, interpretación de mejora o empeoramiento, ni inferencia de significancia.