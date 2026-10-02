# Auditoría final de preparación experimental

Fecha: 2026-09-28. Ámbito: tfm-robot-memory y /home/iratxefagoaga/workspace/tfm/ros2/src. Auditoría de solo lectura: no se modificó código, configuración ni resultados; este informe es la única salida persistente.

## 1. Executive summary

La plataforma implementa y ha ejecutado ROS 2 Jazzy, Gazebo, Nav2, PostgreSQL/pgvector, recuperación, recomendación y automatización N0/N1. La compilación actual de ocho paquetes ROS 2 termina correctamente. Esta auditoría verificó en vivo un baseline y los servicios de memoria.

No está preparada para experimentos definitivos. En N1, use_strategy_waypoint está fijado a false: la estrategia recuperada se registra, pero se ejecuta la misma meta directa que N0. No puede medirse un efecto de memoria sobre trayectoria o preferencia. Sólo hay un escenario de navegación, faltan métricas comprometidas y los activos experimentales no están congelados en una versión reproducible.

Estados: **READY** verificado; **PARTIAL** existe pero faltan controles/cobertura; **BLOCKED** impide experimento final reproducible o interpretable; **NOT TESTED** no ejecutado en esta auditoría.

## 2. Architecture status

| Elemento | Estado | Evidencia / motivo |
|---|---|---|
| Arquitectura Memory → Recommendation → Adapter → Nav2 → Gazebo | READY | Paquetes, interfaces y lanzadores separan memoria de planificación y ejecución Nav2. |
| Paquetes ROS 2 | READY | wheelchair_api, bringup, description, gazebo, interfaces, memory, navigation y vla. |
| Build | READY | 2026-09-28: colcon build --symlink-install: 8/8 terminados con /usr/bin/python3. |
| Tests | PARTIAL | API y VLA: 2 passed, 1 skipped cada uno. wheelchair_memory no contiene tests: colcon test devuelve código 5 por cero tests. |
| Dependencias | READY | ros_gz_sim/bridge y map_server, amcl, planner, controller, bt_navigator, velocity_smoother, lifecycle_manager, costmap y nav2_msgs resuelven desde /opt/ros/jazzy. |
| Launch/runners | READY | Sintaxis compilada con py_compile para launch, runners y scripts experimentales. |
| Versionado de la campaña | BLOCKED | Hay cambios y archivos no rastreados en los dos workspaces, incluidos robot, mundo, mapa, Nav2, launch, scripts, escenarios y resultados. No hay commit/huella congelada para la campaña. |

Interfaces verificadas: MemoryQuery incluye query, user_id, location, task, goal y k, y devuelve IDs, contenido episódico y scores. NavigationRecommendation devuelve estrategia, evitación, clearance, memoria fuente, razón y scores. Nav2 declara NavigateToPose y ComputePathToPose.

## 3. ROS2/Nav2 status

| Elemento | Estado | Evidencia / motivo |
|---|---|---|
| Gazebo, mundo, robot y bridge | READY | La ejecución temporal de baseline inició gz sim con apartment.world y parameter_bridge. |
| Mapa, AMCL, planner, controller y lifecycle | READY | Log temporal: map_server, amcl, planner_server, controller_server y lifecycle se activaron; controller recibió plan/objetivo. |
| Costmaps | READY | Log: local costmap activado y transform comprobada. No se repitió inspección de celdas/capas. |
| Velocity smoother y cmd_vel | READY | velocity_smoother activo; controller remapea a /cmd_vel_nav, smoother a /cmd_vel; bridge confirmó Twist ROS → Gazebo. |
| NavigateToPose | READY | Ejecución aislada desde (2.0,-3.0) a (2.5,-3.0): SUCCEEDED, 3.115 s, 0.261 m, 3 replannings. El CSV quedó sólo en /tmp. |
| TF y sensores | PARTIAL | Fase 2 verificó base_link→lidar_link=(0.280,0,0.720). Esta auditoría no conservó una captura independiente de /scan, /scan_fixed y TF. |
| ComputePathToPose | NOT TESTED | Declarado y validado históricamente, pero no se envió una solicitud actual separada. |
| Grafo ROS completo | PARTIAL | El baseline real demuestra simulación/Nav2; el intento separado de snapshot de nodos/tópicos/servicios/acciones no se mantuvo activo. |
| Robustez Nav2 | PARTIAL | Hay ejecuciones SUCCEEDED; protocol_20260928 conserva un NO_RESULT ON por pérdida de heartbeat de planner_server. |

## 4. Memory system status

| Elemento | Estado | Evidencia / motivo |
|---|---|---|
| PostgreSQL y pgvector | READY | Contenedor healthy, puerto 5433 aceptando conexiones y extensión vector instalada. |
| Dataset y embeddings | READY | memory_seed.csv: 50 memorias; retrieval_queries.csv: 15 consultas. Base real: 50 embedding y 50 episodic_embedding, ambos 1024 dimensiones. |
| Entorno | READY | .venv: numpy 2.5.2, pandas 3.0.5, SQLAlchemy 2.0.52, torch 2.13.0+cu130, transformers 5.15.1, sentence-transformers 6.0.0. |
| Retrieval semántico, usuario y contexto | READY | B1–B3 se reprodujeron byte a byte en la auditoría B1–B4; MemoryQuery actual devolvió M001 primero. |
| Retrieval episódico | PARTIAL | B4 se reproduce, pero no incluye score contextual pese a describirse como contexto+episódico; pesos históricos no son el máximo de sensibilidad. |
| MemoryQuery | READY | Prueba real: success=true; M001,M046,M015,M007,M009. M001: semantic 0.7508675148, context 1.0, final 0.7757807633. |
| NavigationRecommendation | READY | Prueba real: M001 → west, avoid_obstacle=true, prefer_clearance=true, final 0.7758. |
| Base reproducible autónoma | PARTIAL | Funciona ahora, pero no se registra hash/versionado del estado efectivo de PostgreSQL y semillas por ejecución. |

## 5. Baseline status

| Elemento | Estado | Evidencia / motivo |
|---|---|---|
| Memory OFF | READY | baseline_experiment inicia simulación, bridge, descripción, scan fixer, navegación y runner; no inicia nodos de memoria. |
| No consulta memoria | READY | baseline_runner no importa interfaces ni crea clientes MemoryQuery/NavigationRecommendation; graba MEMORY_OFF y campos de memoria vacíos. |
| Ejecución/registro | READY | Objetivo parametrizable, espera bt_navigator activo y navegación real SUCCEEDED. |
| Métricas baseline | PARTIAL | Guarda identidad, tiempo, distancia odométrica, replanning, éxito/Nav2. No guarda obstáculos, distancia restante, cancelación, trayectorias o preferencias. |

## 6. Memory ON status

| Elemento | Estado | Evidencia / motivo |
|---|---|---|
| request → context → retrieval → recommendation | READY | Adapter envía query y contexto a MemoryQuery y luego NavigationRecommendation; servicios probados en vivo. |
| recommendation → adapter → Nav2 | PARTIAL | Fase 3 y resultados históricos lo muestran; no se ejecutó ahora un ciclo Memory ON completo por su calentamiento de 180 s y el fallo de heartbeat documentado. |
| Estrategia aplicada a ejecución | BLOCKED | memory_on_experiment.launch.py fuerza use_strategy_waypoint=false: west se registra, pero el goal ejecutado es la meta común directa. |
| Logging ON | PARTIAL | Guarda IDs, scores, estrategia, waypoint, Nav2, éxito, tiempo, distancia, replanning. Falta query, source_memory explícita, razón, datos episódicos, obstáculos, remaining distance, cancelación y compliance. |
| Robustez ON | PARTIAL | Cuatro CSV SUCCEEDED en el lote; uno sin CSV por timeout/heartbeat de planner_server. |


## 7. Retrieval experiments status

| Experimento | Estado | Ejecución, resultados y limitación |
|---|---|---|
| B1 semantic retrieval | READY | memory/embedding/evaluate_baseline.py. Reproducido byte a byte: P@5=0.4133, R@5=0.5959, nDCG@5=0.6239. |
| B2 user-filtered retrieval | READY | experiments/evaluate_user_filtering.py. Reproducido: P@5=0.5600, R@5=0.7943, nDCG@5=0.8366. |
| B3 context-aware retrieval | READY | experiments/evaluate_context_aware.py, pesos 0.90/0.10. Reproducido: P@5=0.5600, R@5=0.7981, nDCG@5=0.8441. |
| B4 episodic reranking | PARTIAL | experiments/evaluate_episodic_reranking.py. Reproducido: P@5=0.5333, R@5=0.7625, nDCG@5=0.7862; no es ablación contexto+episódico coherente con documentación. |
| Reejecución final B1–B4 | BLOCKED | Los scripts usan rutas de salida fijas. Una nueva ejecución puede sobrescribir CSV históricos si no se aísla por lote/directorio. |
| Métricas retrieval | PARTIAL | Calculan Precision@5, Recall@5 y nDCG@5. MRR está definida en docs/06_metrics.md y SPEC.md, pero no se calcula. |

## 8. Navigation experiments status

| Elemento | Estado | Evidencia / motivo |
|---|---|---|
| N0 baseline navigation | READY | S001 y runner definidos; ejecución temporal actual SUCCEEDED; resultados históricos conservados. |
| N1 memory-assisted navigation | PARTIAL | Launch, adapter y CSV existen, con resultados históricos. No aplica la estrategia recuperada a trayectoria. |
| Escenarios finales | BLOCKED | Sólo existe S001_shared_safe_goal: recorrido corto/seguro que no operacionaliza rutas alternas, clearance o preferencia. |
| Repeticiones | PARTIAL | --number-of-runs y run_id emparejado están implementados. Sólo hay cinco pares solicitados, una observación ON sin resultado y ningún tamaño muestral justificado. |
| Almacenamiento | READY | El runner rechaza artefactos crudos existentes y guarda CSV, log y manifiesto por ejecución. |
| Ejecución definitiva interpretable | BLOCKED | Sin aplicación de estrategia, pluralidad de escenarios y métricas de preferencia, N0/N1 no responde H1/H3. |

## 9. Metrics status

| Grupo | Estado | Evidencia / motivo |
|---|---|---|
| Éxito y Nav2 result | READY | success y nav2_result en N0/N1. |
| Tiempo, distancia y replanning | READY | Tiempo monotónico, /odom y /plan se registran automáticamente. |
| Identidad, modo y timestamp | READY | timestamp_utc, experiment_id, scenario_id, condition y run_id están en CSV. |
| Información de memoria | PARTIAL | IDs, tres scores, estrategia y waypoint; no query, source_memory explícita, razón ni campos episódicos usados. |
| Obstáculos, distancia restante, cancelación | BLOCKED | Previstas por docs/06/SPEC pero ausentes de RESULT_FIELDS e instrumentación. |
| Trayectoria planificada/ejecutada y desviación | BLOCKED | No se guardan. distance_m odométrica no sustituye estas métricas. |
| Preference/strategy match y compliance | BLOCKED | expected_preference existe en escenario, pero no preference_followed, strategy match ni clearance. |
| MRR | BLOCKED | Métrica requerida pero ausente de B1–B4. |
| Estadística | PARTIAL | Script con descriptivos, IC y McNemar para protocol_20260928; un escenario, cuatro pares completos, p=0.250. |

## 10. Reproducibility status

| Elemento | Estado | Evidencia / motivo |
|---|---|---|
| Escenario declarativo | PARTIAL | S001 fija pose, goal, usuario, contexto, obstáculo y preferencia; faltan diversidad y semilla explícita. |
| Condiciones compartidas | PARTIAL | JSON declara mismo robot, mundo, mapa, Nav2 y sensores. N1 añade calentamiento 180 s y timeout distinto, que deben constar en la configuración congelada. |
| Número de repeticiones | PARTIAL | Parametrizable, pero sin plan/tamaño muestral predefinido. |
| Seeds | NOT TESTED | No se verificó semilla explícita de Gazebo, Nav2, Python, PyTorch ni evaluación. |
| No sobrescritura N0/N1 | READY | El runner rechaza paths crudos existentes y conserva logs/manifiestos. |
| Versionado de datos/configuración | BLOCKED | No se guarda hash/commit de DB, datasets, modelo, mundo, mapa, parámetros Nav2 o escenario en el manifiesto; worktrees sucios. |
| Dependencias externas | PARTIAL | PostgreSQL y pesos Qwen están disponibles. Hay aviso HF sin token y dependencia de contenedor/cache/temporización. |

## 11. Scientific traceability

| Objetivo / hipótesis | Implementación | Experimento | Métrica | Resultado actual | Estado |
|---|---|---|---|---|---|
| H1: navegación adaptada | MemoryQuery, Recommendation, Adapter, N0/N1 | S001 protocol_20260928 | éxito, tiempo, distancia, replanning | OFF 1/5 éxito; ON 4/4 CSV con éxito; McNemar p=0.250, 4 pares completos | BLOCKED: N1 no aplica estrategia y no hay métrica de adaptación/preferencia |
| H2: contexto mejora relevancia | B1/B2/B3 | 15 queries, 50 memorias | P@5, R@5, nDCG@5 | B1 0.4133/0.5959/0.6239; B3 0.5600/0.7981/0.8441 | PARTIAL: descriptivo reproducido, sin inferencia ni ablación aislada |
| H3: episódico selecciona estrategia coherente | episodic_embedding, B4, Recommendation | B4 y trazas N1 | retrieval y strategy | B4 0.5333/0.7625/0.7862; M001→west | BLOCKED: B4 no mide preferencia-navegación y N1 no ejecuta west |
| Persistencia/embeddings | PostgreSQL, pgvector, Qwen | auditoría actual | filas/dimensiones | 50/50 embeddings, 1024 | READY |
| Integración segura Nav2 | Adapter y Nav2 | Fase 2/3 + baseline actual | NavigateToPose | SUCCEEDED documentados y actual | READY para integración; PARTIAL para robustez |
| Comparación cuantitativa | escenarios, runner, CSV, estadística | protocol_20260928 | descriptivos, IC, McNemar | informe existente | BLOCKED para evaluación definitiva |

La trazabilidad documental de fuentes y límites se recoge también en reports/thesis_evidence.md. H1 y H3 siguen sin evaluación suficiente.


## 12. Known issues

1. N1 registra una estrategia de memoria, pero fija use_strategy_waypoint=false y navega a la meta directa.
2. Sólo existe S001, escenario de aceptación corto y seguro.
3. protocol_20260928 conserva un NO_RESULT Memory ON por pérdida de heartbeat de planner_server.
4. wheelchair_memory no tiene tests; colcon test global termina con código 5.
5. Esta auditoría no repitió ComputePathToPose ni capturó una instantánea independiente y estable del grafo completo.
6. El CSV común no cubre todas las métricas documentadas.
7. B4 y documentación difieren sobre uso de contexto; sus pesos históricos no son el máximo de sensibilidad.
8. B1–B4 usan salidas fijas y pueden sobrescribir resultados si se reejecutan.
9. No hay huella de DB/datasets/activos en cada manifiesto.
10. Ambos workspaces tienen cambios Git pendientes/no rastreados.

## 13. Blocking issues

1. N1 no ejecuta la recomendación/estrategia de memoria y no constituye una intervención de navegación medible frente a N0.
2. Sólo existe un escenario; no permite evaluar H1/H3 bajo preferencias o rutas alternativas.
3. Faltan métricas científicas requeridas: compliance/preferencia, estrategia, clearance o equivalente, obstáculos, distancia restante, cancelación, trayectorias/desviación y MRR.
4. No está fijada la versión exacta de código, mundo, mapa, parámetros, datasets, DB/seed y modelo.
5. B1–B4 no tienen una salida nueva aislada que proteja los resultados históricos.

## 14. Non-blocking issues

1. Advertencia Hugging Face sin token y coste de carga del modelo.
2. Timeout y calentamiento de N1 mayores que N0; deben quedar documentados en la configuración final.
3. Cobertura de tests insuficiente de wheelchair_memory.
4. Falta prueba actual independiente de ComputePathToPose y snapshot completo de grafo.
5. B4 requiere aclaración metodológica antes de interpretación.
6. Controller emitió un aviso único por goal/progress checker por defecto durante el baseline temporal.

## 15. Exact tests still required

1. Una vez congelada la revisión, ejecutar smoke tests N0/N1 y capturar nodos, tópicos, servicios, acciones, lifecycle, TF y pipeline /cmd_vel.
2. Ejecutar ComputePathToPose y NavigateToPose en el mismo despliegue activo, conservando respuesta/log.
3. Ejecutar un smoke test actual integrado Memory ON: request → context → MemoryQuery → NavigationRecommendation → adapter → Nav2 → resultado y CSV sin timeout.
4. Validar contra tópico/log fuente cada métrica comprometida antes de campaña.
5. Ejecutar B1–B4 a directorios/IDs de lote nuevos sin sobrescribir CSV históricos y comprobar hashes/filas.
6. Ejecutar pares completos N0/N1 para todos los escenarios finales con repeticiones/tamaño muestral predefinidos.
7. Verificar que cada manifiesto registra hashes o identificadores de datasets, DB/seed, modelo, configuración, mundo, mapa, Nav2 y revisión Git.
8. Repetir la estabilidad Nav2 Memory ON hasta descartar o cuantificar el fallo de heartbeat.

## 16. Final readiness checklist

| Criterio | Estado |
|---|---|
| Build ROS 2 actual | READY |
| PostgreSQL/pgvector y memoria actual | READY |
| Baseline Memory OFF real | READY |
| MemoryQuery y NavigationRecommendation reales | READY |
| Nav2 y NavigateToPose reales | READY |
| Memory ON integrado actual completo | PARTIAL |
| N0/N1 comparables para H1 | BLOCKED |
| Escenarios finales suficientes | BLOCKED |
| Métricas completas y automáticas | BLOCKED |
| B1–B4 protegidos contra sobrescritura y preparados | BLOCKED |
| Revisión/configuración/dataset/DB congelados | BLOCKED |
| Robustez demostrada para campaña | PARTIAL |

## READY FOR FINAL EXPERIMENTS: NO

1. Hacer que N1 aplique una intervención de memoria medible y segura, o redefinir explícitamente el experimento para medir sólo recomendación; la configuración actual no permite evaluar efecto de memoria en navegación.
2. Definir y congelar varios escenarios que operacionalicen preferencias y rutas alternativas, con pares N0/N1 comparables.
3. Instrumentar y validar las métricas necesarias para H1/H3 y las comprometidas: compliance/preferencia, estrategia, clearance o equivalente, obstáculos, distancia restante, cancelación y trayectoria; añadir MRR si sigue siendo métrica comprometida de retrieval.
4. Congelar y registrar la versión exacta de código, configuración, mundo, mapa, Nav2, datos, DB/seed y modelo antes de generar datos definitivos.
5. Garantizar que B1–B4 puedan ejecutarse en un lote nuevo sin sobrescribir los resultados existentes.
