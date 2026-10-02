# Implementation log

## 2026-09-22 - Fase 1: estabilizacion de infraestructura

Cambios minimos realizados:

- Se inicio PostgreSQL/pgvector existente y se verificaron 50 memorias con embeddings de 1024 dimensiones.
- Se alineo `database/init.sql` con la columna `episodic_embedding` ya presente en la base efectiva.
- Se completo la declaracion de dependencias de Nav2 y bringup.
- Se corrigio `z_voxels` de 40 a 16, limite soportado por VoxelLayer.
- Se corrigio la espera del cliente asincrono en `navigation_memory_node`.
- Se reconstruyo el apartamento y su PGM de Nav2 desde la misma geometria: limites, mesa, sofa, cama, armario y planta.
- Se mejoraron los materiales de la silla sin modificar colisiones, ruedas, joints, sensores o footprint.

No se implemento baseline, Memory OFF, VLA, cambios de retrieval ni registro longitudinal.

## 2026-09-22 - Fase 2: baseline reproducible MEMORY OFF

- Se añadieron `baseline.launch.py` y `baseline_runner.py` para ejecutar Gazebo, Nav2 y una única navegación sin nodos de memoria.
- El runner guarda estado, tiempo, distancia de `/odom` y replannings de `/plan` en el CSV experimental.
- Se alineó la geometría de ruedas con los ejes diferenciales y se corrigieron las TF estáticas del URDF contra las poses físicas del SDF.
- Se verificó el objetivo `(2.5, -3.0)` con resultado `SUCCEEDED`, 2.370 s, 0.263 m y 2 replannings.
- Memory ON no se ejecutó.
## 2026-09-22 - Fase 3: Memory ON

- Añadido launch Memory ON y adaptador trazable Query -> Recommendation -> Nav2.
- Persistencia CSV de contexto, IDs, scores, estrategia, waypoint y resultado Nav2.
- Prueba real: M001 -> west -> (1.500, -3.000) -> ABORTED; ver reports/phase3_memory_on.md.

## 2026-09-22 - Fase 3: Memory ON estabilizada

- Se implementó el flujo trazable MemoryQuery -> NavigationRecommendation -> NavigateToPose.
- El adaptador guarda query, contexto, IDs, scores, estrategia, waypoint y resultado Nav2 en el CSV experimental.
- Se añadió espera explícita de bt_navigator active antes de enviar el objetivo.
- Se detectó que cargar Qwen tras iniciar Nav2 podía perder heartbeats. Se cambió el lanzador para calentar memoria antes de Nav2, sin tocar parámetros Nav2.
- Verificación final integrada: M001 -> west -> (2.5, -3.0) -> SUCCEEDED.
- Limitación registrada: el waypoint seguro valida integración, no el efecto geométrico de una ruta oeste.

## 2026-09-22 - Fase 4: infraestructura experimental comparable

- Se creó `experiments/scenarios/`, `experiments/configs/` y `experiments/scripts/`.
- Se definió S001_shared_safe_goal con pose, meta y contexto comunes.
- Se parametrizó la pose inicial de simulación y los lanzadores experimentales N0/N1.
- Baseline y Memory ON registran identificadores de experimento, escenario y ejecución en sus CSV crudos.
- Memory ON conserva la recomendación, pero en Fase 4 usa el objetivo final compartido para no cambiar la condición de navegación.
- Se creó `run_navigation_scenario.py`, que no sobrescribe resultados y genera un manifiesto de ejecuciones.
- Pruebas: compilación de wheelchair_bringup y wheelchair_memory; py_compile de lanzadores/runners; ambos lanzadores verificaron argumentos.
- Ejecución real S001 phase4_acceptance_002: BASELINE=SUCCEEDED y MEMORY ON=SUCCEEDED; sin análisis comparativo.
- Problema corregido: CRLF en el shebang de baseline_runner impidió phase4_acceptance_001; el intento quedó preservado como NO_RESULT y se repitió con un run_id nuevo.

## 2026-09-22 - Fase 5: automatización de experimentos

- Se extendió el ejecutor con condition, number_of_runs y run_id deterministas.
- Se unificó el esquema CSV de baseline y Memory ON.
- Baseline espera bt_navigator active antes de enviar el objetivo.
- Se creó una configuración aislada de Fase 5 y validación de métricas y trazabilidad de memoria.
- Prueba real pequeña: S001, ambas condiciones, una repetición; ambos resultados SUCCEEDED.
- Evidencia y ampliación: reports/phase5_automation.md. No se ejecutaron lotes masivos ni análisis comparativo.
## 2026-09-28 - Auditoría retrieval B1-B4

- PostgreSQL/pgvector restaurado y 50 memorias con embeddings 1024 verificados.
- B1, B2, B3 y B4 reprodujeron byte a byte sus CSV históricos en salida temporal.
- Corrección mínima: optimize_context_weights.py escribe B3_context_weight_sensitivity.csv y protege la evaluación B3.
- Informe creado en reports/retrieval_validation.md.
## 2026-09-28 - Ejecución de protocolo experimental

- Se ejecutaron cinco repeticiones emparejadas de S001_shared_safe_goal con baseline seguido de Memory ON.
- Se conservaron todos los CSV, logs y manifiestos en experiments/results/phase5/acceptance_final.
- Se registraron cuatro resultados baseline ABORTED, un baseline SUCCEEDED, cuatro resultados Memory ON SUCCEEDED y un Memory ON sin CSV crudo.
- El manifiesto de Memory ON 004 registra timeout y NO_RESULT; el log conserva la pérdida de heartbeat de planner_server.
- Informe descriptivo creado en reports/experiment_report.md. No se realizó interpretación comparativa.

## 2026-09-28 - Análisis estadístico del protocolo

- Se analizaron exclusivamente las cinco repeticiones del lote protocol_20260928, sin modificar CSV originales ni eliminar outliers.
- Se creó experiments/scripts/generate_statistical_tables.py y tablas derivadas bajo experiments/results/statistical_analysis/.
- Se calcularon descriptivos, intervalos t para métricas cuantitativas, intervalos Wilson para éxito y McNemar exacto para las cuatro parejas completas.
- Informe: reports/statistical_analysis.md. No se afirmó significancia ni superioridad.


## 2026-09-29 - Blocker 1: estrategia Memory ON aplicada mediante Nav2

- navigation_adapter ahora convierte estrategias configuradas en offsets declarativos relativos a la meta común, sin modificar retrieval ni Nav2.
- Si existe waypoint aplicable, envía NavigateToPose al waypoint y, tras SUCCEEDED, envía NavigateToPose a la misma meta final de N0.
- Si el waypoint falla, registra el resultado explícito y no envía la meta final.
- Se añadieron campos de trazabilidad para estrategia aplicada, waypoint, resultado de waypoint y resultado final; baseline y consolidado sólo se ajustaron por compatibilidad de esquema.
- Build de wheelchair_memory y wheelchair_bringup correcto.
- Smoke test temporal real: M001 -> west, strategy_applied=true, waypoint (2.250,-3.000) SUCCEEDED, meta final (2.500,-3.000) SUCCEEDED. El intento de waypoint ABORTED también se conservó con final_goal_nav2_result=NOT_SENT.
- Informes: reports/blocker1_design.md y reports/blocker1_validation.md.
