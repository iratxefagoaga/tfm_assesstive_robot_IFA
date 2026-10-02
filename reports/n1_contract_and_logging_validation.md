# Validación integrada del contrato y logging N0/N1

Fecha: 2026-09-30, Europe/Madrid. Timestamps CSV en UTC.

## Decisión inicial: BLOCKED

El logging común funciona en ambos smoke reales. N0 termina correctamente.
N1 recupera M001 y west, pero el waypoint aborta por un timeout de confirmación
de compute_path_to_pose tras una pérdida de heartbeat y reinicio del lifecycle
de Nav2. No hay evidencia nueva de éxito waypoint → final_goal.
El BT todavía no queda validado como sustituto experimental N1 en este entorno.
No se modificó Nav2 para sortear el fallo.

## HEADs al inicio

- TFM/ROS: a2e1705c5324f77580e25044de9851a3cf118e32
- tfm-robot-memory: da3708d8ae12dbb9a61c52bb1a77cbf27e9c4ce2

Se preservaron los cambios sin commit. No se realizaron operaciones Git de escritura.

## Preparación y cambios

Se leyeron n1_contract_and_logging_design.md, bt_phase3_validation.md y
bt_adapter_equivalence.md. Se inspeccionaron launches, XML N1 y consumidores
de memoria. Sólo se añadió result_csv a bt_n0_smoke.launch.py y
bt_n1_phase3_smoke.launch.py, con defaults /tmp/bt_n0_contract_smoke.csv y
/tmp/bt_n1_contract_smoke.csv. No se cambiaron resolver, métricas,
orquestadores, retrieval, Nav2, mapas o mundos.

Antes de N0 no había stack activo. Antes de N1 se comprobó limpieza completa
de N0: /tmp/bt_before_n1_processes.txt.

## Comandos relevantes

Desde /home/iratxefagoaga/workspace/tfm/ros2:

    source /opt/ros/jazzy/setup.bash
    source install/setup.bash
    ros2 launch wheelchair_assistive_bt bt_n0_smoke.launch.py experiment_id:=bt_contract_validation run_id:=n0_contract_001 result_csv:=/tmp/bt_n0_contract_smoke.csv
    ros2 launch wheelchair_assistive_bt bt_n1_phase3_smoke.launch.py experiment_id:=bt_contract_validation run_id:=n1_contract_001 result_csv:=/tmp/bt_n1_contract_smoke.csv
    export CMAKE_BUILD_PARALLEL_LEVEL=1
    export MAKEFLAGS=-j1
    colcon build --symlink-install
    colcon test --packages-select wheelchair_assistive_bt
    colcon test-result --verbose

Se compiló sin .venv, con /usr/bin/python3. Defaults usados: initial=(2,-3),
final_goal=(2.5,-3), yaw=0. N0 MEMORY_OFF. N1: query="navegar evitando la mesa",
U01, salon, navegacion, dormitorio, k=3 y west:-0.25:0.0.
strategy_waypoint_enabled=true por defecto del nodo, confirmado en CSV.
No se forzó retrieval.

## Build y tests

- BUILD PACKAGE: PASS. Build específico previo de esta sesión: 46.9 s.
  El build completo posterior verificó wheelchair_assistive_bt en 3.50 s.
- BUILD WORKSPACE: PASS. 9 paquetes completados en 13.4 s.
- Resolver: 10/10 PASS.
- Logging N0: 8/8 PASS.
- Logging N1: 11/11 PASS.
- colcon test del paquete: PASS, 0.63 s.
- colcon test-result --verbose: 38 tests, 0 errors, 0 failures, 2 skipped.
  El agregado incluye resultados ajenos y entradas CTest; los tres XML GTest
  relevantes contienen 29 casos ejecutados, sin errores ni omitidos.
- git diff --check sobre ambos launches modificados: PASS.

Evidencia: /tmp/bt_contract_workspace_build.log, /tmp/bt_contract_tests.log y
build/wheelchair_assistive_bt/test_results/wheelchair_assistive_bt/*.gtest.xml.

## Smoke N0: PASS

Evidencia nueva: /tmp/bt_n0_contract_smoke.log y /tmp/bt_n0_contract_smoke.csv.
Nav2 informa Managed nodes are active; el orquestador envía final_goal y
termina SUCCEEDED, success=true. No se lanzan servicios de memoria ni aparecen
QueryMemory/GetNavigationRecommendation. Campos de memoria/intervención: N/A.

## Smoke N1: FAIL

Evidencia nueva: /tmp/bt_n1_contract_smoke.log y /tmp/bt_n1_contract_smoke.csv.
MemoryQuery y NavigationRecommendation: SUCCEEDED.
memory_ids=M001|M046|M002; source_memory=M001; retrieved_strategy=west;
strategy_applied=true; selected_waypoint=(2.250,-3.000).

Nav2 llegó a ACTIVE, confirmado por lifecycle y log. Después:

1. En 1790747158.120677444, lifecycle_manager reporta pérdida de heartbeat
   de map_server durante 4000 ms y desactiva nodos relacionados.
2. Nav2 reinicia sus nodos; aparecen esperas TF por extrapolación al pasado.
3. En 1790747179.608093060 se envía el waypoint.
4. En 1790747183.180475762, bt_navigator agota la espera de confirmación de
   compute_path_to_pose.
5. El waypoint termina ABORTED; final_goal queda NOT_SENT, success=false,
   failure_stage=navigate_waypoint. No aparece envío posterior de final_goal.

Se prueba la barrera de fallo con logging real, pero no el éxito integrado N1.
Durante carga/inferencia, WSL dejó temporalmente de responder:
Wsl/Service/0x8007274c. Se observaron 3763 MiB de RAM y 1024 MiB de swap.
La presión de recursos es una hipótesis compatible con las pérdidas de
heartbeat; no es una causa raíz demostrada. No se cambiaron recursos ni timeouts.

## Comparación automática CSV: PASS

csv.DictReader y aserciones comprobaron headers idénticos de 35 campos,
exactamente una fila por archivo, sin columnas sobrantes ni valores faltantes,
condiciones MEMORY_OFF/MEMORY_ON, tiempo > 0, distancia >= 0, replanning >= 0,
N/A de campos no implementados y de memoria N0, datos reales N1 y barrera
ABORTED → NOT_SENT. También se verificó ausencia de envío final en el log N1.

Evidencia: /tmp/bt_contract_csv_validation.json.
Esta comparación aprueba formato y fidelidad; no convierte el fallo de navegación en éxito.

| Campo | N0 | N1 |
|---|---|---|
| timestamp_utc | 2026-09-30T05:43:21Z | 2026-09-30T05:46:25Z |
| condition | MEMORY_OFF | MEMORY_ON |
| success | true | false |
| navigation_time_s | 3.177 | 5.821 |
| distance_m | 0.265 | 0.000 |
| replanning_count | 2 | 0 |
| source_memory | N/A | M001 |
| retrieved_strategy | N/A | west |
| strategy_applied | N/A | true |
| selected_waypoint_x | N/A | 2.250 |
| selected_waypoint_y | N/A | -3.000 |
| waypoint_nav2_result | N/A | ABORTED |
| final_goal_nav2_result | SUCCEEDED | NOT_SENT |
| failure_stage | (vacío) | navigate_waypoint |


## Shutdown y limpieza

N0, tras éxito, dejó Gazebo wrapper/server/gui (738830/738900/738901).
Se terminaron con SIGTERM; se comprobó ausencia de stack antes de N1.
N1 dejó 739361/739422/739423; se enviaron SIGTERM y luego SIGKILL al persistir.
La primera comprobación inmediata todavía vio el servidor; la posterior confirmó
la salida de los tres. No queda stack activo.

Hubo errores de doble rclpy.shutdown en scan_frame_fixer y, en N1, en los nodos
de memoria. El launch escaló SIGTERM/SIGKILL para procesos que no terminaban.
Evidencia: logs, /tmp/bt_n0_contract_cleanup.txt,
/tmp/bt_n1_contract_cleanup.txt y /tmp/bt_after_smokes_processes.txt.

La limpieza explícita permitió iniciar N1 tras N0. El shutdown automático
del launch no basta por sí solo para una campaña desatendida. Su fiabilidad
repetida no está validada. Es una incidencia separada del fallo Nav2,
que ocurrió antes del shutdown.

## Checklist

| Criterio | Estado | Evidencia y alcance |
|---|---|---|
| BUILD PACKAGE | PASS | Build específico previo y paquete en build completo |
| BUILD WORKSPACE | PASS | 9 paquetes |
| N0 NO MEMORY | PASS | Smoke nuevo, launch y CSV |
| N1 MEMORY | PASS | Consulta/recomendación reales; no implica éxito Nav2 |
| COMMON CSV SCHEMA | PASS | Comparación automática de 35 campos |
| ONE ROW PER RUN | PASS | Una fila en cada CSV nuevo, incluido fallo N1 |
| STRATEGY DISABLED | PASS | Test Disabled |
| STRATEGY APPLIED | PASS | Smoke N1: west, waypoint 2.25,-3.0 |
| DIRECT NOT APPLIED | PASS | Test Direct |
| MISSING OFFSET NOT APPLIED | PASS | Test MissingStrategy |
| DUPLICATE OFFSET REJECTED | PASS | Test DuplicateStrategy |
| MALFORMED OFFSET REJECTED | PASS | MalformedDx/Dy, NumericSuffix, EmptyStrategy |
| WAYPOINT FAILURE BARRIER | PASS | N1 nuevo: ABORTED, NOT_SENT, sin envío final |
| FINAL GOAL GATE | PASS | Barrera nueva y éxito Phase 3 histórico; éxito N1 actual no validado |
| TIME METRIC | PASS | CSV positivos; tests de continuidad y congelación |
| DISTANCE METRIC | PASS | CSV no negativos; test de suma continua 10 m |
| REPLANNING METRIC | PASS | CSV no negativos; test planes menos uno |
| MIN CLEARANCE | N/A | N/A en ambos CSV, no implementado |
| NO MEMORY WRITE | PASS | Flujo sólo consulta/recomendación, sin llamadas de escritura |
| NO FINAL EXPERIMENT CONTAMINATION | PASS | CSV sólo /tmp, sin campaña ni escritura en experiments/results |

FINAL GOAL GATE usa además el éxito histórico documentado en
bt_phase3_validation.md, log
/home/iratxefagoaga/.ros/log/memory_observation_bt_orchestrator_329960_1790703804039.log.
Se inspeccionó también la barrera histórica en
/home/iratxefagoaga/.ros/log/memory_observation_bt_orchestrator_331131_1790704250349.log.
La evidencia anterior no sustituye el smoke N1 nuevo fallido.

## Limitaciones y condición de cierre

- Éxito integrado N1: FAIL. Requiere diagnosticar estabilidad Nav2/entorno y
  repetir N1 con éxito antes de declarar CLOSED.
- Campaña repetida y shutdown automático fiable: NOT TESTED.
- Clearance físico/colisiones: NOT TESTED; no se instrumentó.
- context_compliance e intervention_appropriate: N/A.
- initial_x/y del CSV son de /odom (cerca de 0,0); la pose de spawn/map es
  2,-3. No deben compararse como si compartieran frame.
- La distancia N0 menor que 0.5 m es compatible con tolerancia de llegada;
  SUCCEEDED no demuestra coincidencia exacta con el centro del goal.
- No se ejecutaron campañas, inserciones de memoria o cambios de BD.
  La ausencia de escrituras se verificó por el flujo ejecutado, no por
  auditoría transaccional de PostgreSQL.

La primera validación terminó BLOCKED por el fallo de navegación N1 descrito.


## Diagnóstico y único rerun — 2026-09-30

### Resultado actualizado: BLOCKED para campañas repetidas; rerun N1 PASS

La navegación del único rerun sí tuvo éxito. El bloqueo ya no es el resultado
de ese run, sino la robustez pendiente del procedimiento estándar de arranque
y shutdown. No se declara resuelta una causa raíz con una única ejecución
manual secuenciada. No se ejecutará otro smoke en esta tarea.

### Cronología del primer fallo (tiempo Unix del log ROS)

| Instante | Evento |
|---|---|
| 1790747104.288889 | Lifecycle manager confirma nodos activos inicialmente |
| 1790747134.226580 | MemoryService termina su inicialización |
| 1790747134.314274 | BT inicia QueryMemory |
| 1790747158.118076 | Lifecycle manager detecta heartbeat ausente de map_server |
| 1790747158.120677 | Tras 4000 ms sin heartbeat, inicia desactivación por bond |
| 1790747161.333203 | bt_navigator destruye su bond |
| 1790747163.102276 | planner_server destruye su bond |
| 1790747163.447354 | map_server destruye su bond |
| 1790747171.250475 | map_server vuelve a crear bond |
| 1790747171.387902 | Manager confirma bond de map_server |
| 1790747172.082764 | BT inicia GetNavigationRecommendation |
| 1790747174.434995 | planner_server vuelve a crear bond |
| 1790747174.657160 | Manager confirma bond del planner |
| 1790747179.539995 | Manager confirma bond de bt_navigator |
| 1790747179.608093 | BT envía waypoint |
| 1790747180.385513 | Manager confirma todos los nodos activos otra vez |
| 1790747183.180476 | Timeout del ACK de compute_path_to_pose |
| 1790747185.104992 | bt_navigator informa Goal failed |
| 1790747185.610401 | BT termina ABORTED / NOT_SENT |
| 1790747187.032747 | Lifecycle manager entra en rcl preshutdown |

La orden global SIGINT del launch aparece DESPUÉS del blackboard terminal.
Los fallos de shutdown y terminaciones de Gazebo/memoria también son posteriores.
No hay salida/crash de map_server o planner antes de perder el heartbeat.
El mismo PID map_server 739625 es reconfigurado; no se demuestra proceso muerto.

### Clasificación causal A–G

- A, lifecycle: mecanismo inmediato demostrado. La pérdida del bond provoca
  desactivación/reinicio y transitorios TF.
- B, launch/shutdown: no inició el primer fallo. El launch arranca por timers
  fijos (memoria 1 s, recomendación 35 s, Nav2 40 s, BT 50 s), sin barrera de
  disponibilidad global. El waypoint se envió antes de que el manager confirmara
  completada toda la reactivación.
- C, planner: timeout de confirmación demostrado, no fallo del algoritmo
  demostrado. El planner registra frecuencia 1.1669 Hz frente a 20 Hz deseados.
- D, timeout: fue excedido; no hay evidencia de que deba aumentarse.
- E, crash: no demostrado antes del resultado. No hay OOM kill en la evidencia
  examinada; el SIGKILL de memoria procede del shutdown posterior del launch.
- F, carga/clock: evidencia de presión de recursos y pérdida de respuesta de
  WSL. Kernel registra page allocation failure order:7 a las 07:46:05 y
  07:46:37 locales, no un OOM kill. La primera coincide con la ventana de
  recuperación Nav2. Esto apoya la hipótesis de carga; no prueba por sí solo
  que originara el primer heartbeat perdido. No se demuestra un salto de /clock.
- G: no se identificó otra causa concreta.

Evidencia kernel completa: /tmp/bt_n1_kernel_diagnosis.log.
Los informes Phase 2 y Phase 3 confirman que el doble shutdown y los residuos
Gazebo ya ocurrían después de navegaciones exitosas.

### Corrección pequeña aplicada

scan_frame_fixer.py usa try_shutdown y captura ExternalShutdownException,
con destrucción en finally. Corrige el segundo rclpy.shutdown demostrado.
No cambia LaserScan ni su frame. Copia previa:
 /tmp/scan_frame_fixer.before_lifecycle_fix.py.

Build wheelchair_bringup: PASS (4.38 s).
Tests unitarios de salida normal, KeyboardInterrupt y ExternalShutdownException:
3/3 PASS, /tmp/test_scan_shutdown.py y /tmp/bt_scan_shutdown_tests.log.
Regresión wheelchair_assistive_bt: PASS, 29 casos GTest (10+8+11);
colcon agregado del paquete: 32 tests, 0 errors, 0 failures, 0 skipped.
git diff --check del archivo modificado: PASS.
BT, resolver, logging, memoria y configuración Nav2 permanecen sin cambios.

### Procedimiento del único rerun

Supervisor temporal: /tmp/bt_n1_single_rerun.py.
Stack temporal: /tmp/bt_rerun_stack.launch.py. Reutiliza simulation, bridge,
robot_state_publisher y navigation existentes; no modifica mapas ni tuning.

1. Verifica ausencia de stack anterior y pg_isready.
2. Arranca memoria con OMP/MKL=1, igual que el launch anterior.
3. Espera servicio y hace una consulta real de preflight: M001,M046,M002.
   Es una lectura adicional antes de Nav2; el BT vuelve a consultar realmente.
4. Espera el servicio de recomendación.
5. Arranca Gazebo/ROS/Nav2.
6. Consulta GetState de map_server, amcl, planner_server, controller_server,
   bt_navigator, behavior_server, waypoint_follower y velocity_smoother.
   Todos ACTIVE antes de arrancar el orquestador.
7. Ejecuta UNA vez el orquestador con los parámetros pedidos y
   result_csv=/tmp/bt_n1_contract_rerun.csv.

No se aumentaron timeouts del BT ni Nav2. Los límites del supervisor son
límites de diagnóstico para esperar disponibilidad, no cambios del sistema.

### Evidencia nueva: PASS de navegación

- PostgreSQL: accepting connections.
- Todos los lifecycle: active en /tmp/bt_n1_rerun_supervisor.log.
- QueryMemory: 1790748276.265508.
- GetNavigationRecommendation: 1790748276.667424.
- Waypoint enviado: 1790748277.406303.
- Nav2 Goal succeeded: 1790748277.469176.
- Final goal enviado: 1790748277.526383.
- Nav2 Goal succeeded: 1790748279.828186.
- Blackboard terminal: 1790748279.851253.
- source_memory=M001, retrieved_strategy=west, strategy_applied=true.
- selected_waypoint=(2.250,-3.000).
- waypoint_nav2_result=SUCCEEDED, final_goal_nav2_result=SUCCEEDED, success=true.
- CSV: exactamente 1 fila y 35 columnas, validado por aserciones csv.DictReader.
- navigation_time_s=2.439, distance_m=0.265, replanning_count=3.
- min_clearance/context_compliance/intervention_appropriate=N/A.
- Sin CRITICAL heartbeat ni timeout de ACK en el nuevo log.

Logs: /tmp/bt_rerun_memory.log, /tmp/bt_rerun_recommendation.log,
/tmp/bt_rerun_stack.log, /tmp/bt_rerun_orchestrator.log y
/tmp/bt_n1_rerun_supervisor.log. CSV sólo en /tmp.

### Limpieza y limitación que impide declarar CLOSED

El supervisor capturó los descendientes y terminó exclusivamente sus procesos.
La inspección final confirma ausencia de procesos activos ROS/Gazebo del run.

La limpieza aún muestra KeyboardInterrupt dentro de destroy_node del scan fixer:
el supervisor envía SIGINT al grupo del launch y éste vuelve a propagar SIGINT
a sus hijos. Es diferente del doble rclpy.shutdown original. Los tres tests
unitarios no cubren esa segunda señal concurrente; no se oculta esa limitación.

Además, el launch estándar sigue usando timers fijos. El procedimiento por
disponibilidad y limpieza explícita utilizado aquí está en /tmp; todavía no es
un mecanismo persistente y validado del launch estándar para campañas repetidas.
El rerun permite atribuir utilidad al arranque secuenciado, pero no aislar de
forma concluyente carga, primera inferencia y disponibilidad como causa única.

Por tanto: rerun PASS, fase BLOCKED para cierre de robustez/campañas repetidas.
Queda integrar y validar la barrera de disponibilidad y la propagación única
de señales en infraestructura. Se detiene aquí, sin segundo rerun ni campaña.

### Diagnóstico aislado de memory_node (2026-09-30)

Estado: BLOCKED para atribuir y corregir la causa del cierre integrado.
No se ejecutó Gazebo, Nav2 ni un segundo smoke integrado en esta fase.

El log /tmp/bt_lifecycle_iteration_1.log muestra que memory y recommendation
alcanzaron `LIFECYCLE cleanup: complete`. No es correcto situar el bloqueo
observado dentro de executor.shutdown(), destroy_node() o try_shutdown().
Memory siguió vivo: launch escaló a SIGTERM a los 5 s y a SIGKILL 10 s después.
La traza integrada no contiene pilas durante esa espera.

Inspección: el entrypoint gestionado posee SingleThreadedExecutor para memoria.
MemoryNode no crea timers, clientes salientes ni hilos Python propios. La
consulta es síncrona y las pruebas esperan su respuesta antes del SIGINT.
No se llama a store_memory. No se ha demostrado que un recurso concreto de
las bibliotecas de embeddings origine el fallo.

Dos procesos aislados consecutivos reutilizaron el entrypoint gestionado,
OMP_NUM_THREADS=1, MKL_NUM_THREADS=1 y TOKENIZERS_PARALLELISM=false.
El envoltorio temporal registra faulthandler y enumera threads al retornar main.
Ambos hicieron MemoryQuery real: query="navegar evitando la mesa",
U01/salon/navegacion/dormitorio, k=3. Recuperaron M001,M046,M002.
Ambos recibieron un único SIGINT y salieron con código 0, sin SIGTERM/SIGKILL
ni procesos residuales.

- Prueba 1: /tmp/memory_shutdown_diagnostic.log, PID 894996, código 0.
  Duración de cierre no medida con precisión.
- Prueba 2: /tmp/memory_shutdown_isolated_2.log, PID 903737, código 0.
  Cierre: 5.3313 s; /tmp/memory_shutdown_isolated_2_result.log.
- Al retornar main: MainThread y dos monitores tqdm daemon en ambas.
  No se activó el volcado automático a los 10 s.
- Scripts: /tmp/memory_shutdown_diagnostic.py y /tmp/memory_shutdown_isolated.py.

Los 5.3313 s superan el umbral de escalada de launch: este puede interrumpir
una salida que terminaría normalmente. No demuestra por qué el run integrado
llegó a SIGKILL. No se aumentaron timeouts ni se aplicó una corrección
especulativa. Producción, retrieval, ranking, datos y resultados no se modificaron.

Regresiones: colcon test --packages-select wheelchair_memory wheelchair_assistive_bt:
assistive_bt PASS; wheelchair_memory código 5, Ran 0 tests / NO TESTS RAN.
El agregado colcon test-result --verbose indica 39 tests, 0 errors, 0 failures,
2 skipped; no equivale a éxito del comando anterior.
Logs: /tmp/memory_shutdown_regressions.log y /tmp/memory_shutdown_test_results.log.
NavigationRecommendation no se ejercitó en estas reproducciones.
No hubo cambios compilables ni se ejecutó build.

Pendiente: reproducir con launch mínimo de memoria y capturar la espera posterior
al cierre ROS en las condiciones que la provocan. Los dos cierres aislados pasan,
pero todavía no justifican declarar corregido el bloqueo original.

## Memory node shutdown profiling

Clasificación: **BLOCKED / H) UNKNOWN**. No se aplicó corrección funcional.
Las mediciones localizan la demora principalmente después de main, pero no
identifican qué recurso causa la variabilidad del cierre histórico de 5.33 s.
No hay un DESPUÉS de corrección: todos los resultados son con producción intacta.

### Metodología e instrumentación temporal

Se inspeccionaron memory_node, el entrypoint gestionado que usa el launch,
SingleThreadedExecutor, la consulta síncrona y MemoryService. La conexión SQL
se devuelve al pool mediante `with self.engine.connect()` antes de responder.
No hay timers, clientes salientes ni threads propios en MemoryNode, ni cierre
explícito del modelo/pool en finally. El main original de memory_node existe,
pero el launch utiliza managed_memory_process.py y ese es el entrypoint medido.
Launch conserva su escalada SIGINT → SIGTERM, cuyo primer umbral es 5 s.
No se cambiaron timeouts, señales ni recursos funcionales.

En /tmp/memory_profile.py se envolvieron temporalmente las funciones reales
spin, executor.shutdown, Node.destroy_node y rclpy.try_shutdown; se midió el
retorno real de main. Se observaron callbacks atexit registrados después de
instalar el instrumento y GC al salir. No se inventaron cierres de recursos:
las etapas inexistentes figuran como N/A. El instrumento no sustituye handlers
SIGINT. T0 externo es el instante monotónico inmediatamente anterior al envío;
el retorno de spin es el primer efecto observable medido dentro del proceso.
La llamada explícita try_shutdown no representa el cierre previo que el handler
ROS puede realizar: ese tiempo queda incluido en SIGINT → salida de spin.

/tmp/memory_profile_supervisor.py espera servicio y respuesta real usando el
helper de readiness; verifica '#1 M001' antes del único SIGINT. Mide process exit
con wait() y time.monotonic(), con el pequeño retardo de planificación del padre.
OMP_NUM_THREADS=1, MKL_NUM_THREADS=1, TOKENIZERS_PARALLELISM=false.
No se ejecutaron Gazebo, Nav2, BT ni smoke integrado.

La captura preliminar con sys.setprofile dejó de emitir eventos internos durante
la ejecución. Se descartó para la tabla por incompleta y se repitieron dos runs
con wrappers explícitos. Se conservaron sus logs: memory_profile_run1/2 en /tmp.
Sus totales fueron 6878.290 y 3006.162 ms, ambos código 0. El primer wrapper
retornó a los 29.255 ms; hubo ~354 ms de atexit y ~1248 ms de GC, quedando tiempo
posterior sin atribuir. Es evidencia de variación, no una prueba causal de carga.

### Dos mediciones completas, sin corrección

| etapa | run1_ms | run2_ms |
|---|---:|---:|
| SIGINT → spin/executor terminado | 0.825 | 0.654 |
| destroy_node | 8.351 | 7.460 |
| resource cleanup explícito | N/A | N/A |
| PostgreSQL cleanup explícito | N/A | N/A |
| embedding/model cleanup explícito | N/A | N/A |
| rclpy.try_shutdown explícito | 0.056 | 0.035 |
| SIGINT → main/finally terminado | 9.491 | 8.303 |
| main exit → process exit | 1607.105 | 1230.077 |
| SIGINT → process exit TOTAL | 1616.596 | 1238.380 |
| Callbacks atexit observados (intervalo) | 37.532 | 23.840 |
| GC generación 2 observado | 277.034 | 261.154 |
| Fin GC observado → process exit | 1291.410 | 944.715 |

Los tiempos acumulados no deben sumarse a las duraciones individuales.
Las líneas originales incluyen timestamp monotónico; *_timeline.jsonl añade
delta desde el evento anterior y acumulado desde SIGINT para cada evento de salida.

- Run 1: PID 938749, M001, exit code 0, un SIGINT, sin SIGTERM/SIGKILL.
- Run 2: PID 938838, M001, exit code 0, un SIGINT, sin SIGTERM/SIGKILL.
- Antes de consultar: MainThread y tqdm_monitor daemon; 16 threads nativos.
- Al retornar main: MainThread y dos tqdm_monitor daemon; 8 threads nativos.
- No había threads Python no-daemon adicionales al retornar main.
- Los monitores tqdm se cierran en callbacks atexit breves. También se observaron
  weakref.finalize, multiprocessing._exit_function, logging.shutdown, cierre de
  sesión HTTP y callbacks de torch. Su intervalo completo figura en la tabla.
- No se capturaron pilas nativas que permitan asignar el tiempo posterior al GC
  a PyTorch, BLAS, PostgreSQL o un destructor concreto. No se atribuye culpabilidad.
- Ambos procesos desaparecieron de /proc antes de continuar. No se enviaron
  señales adicionales ni se terminaron hilos arbitrariamente.

Evidencia completa: /tmp/memory_timing_run{1,2}.log, .jsonl,
_result.json y _timeline.jsonl. Instrumentación solo en /tmp; producción sin
prints nuevos, cambios de retrieval, ranking, modelo, base de datos ni CSV.
No se insertaron memorias ni se escribieron resultados experimentales.

### Regresiones y conclusión

colcon test --packages-select wheelchair_assistive_bt wheelchair_memory:
wheelchair_assistive_bt PASS; wheelchair_memory: **NO TESTS DISCOVERED**, código 5,
no clasificado como regresión funcional. colcon test-result --verbose:
39 tests, 0 errors, 0 failures, 2 skipped; este agregado no invalida el código 5.
Logs: /tmp/memory_profile_regressions.log y /tmp/memory_profile_test_results.log.
No se necesitó build porque no hubo cambios compilables.

Las dos mediciones completas quedan por debajo de 5 s, pero no demuestran una
corrección: no hubo cambio funcional y la captura preliminar superó 5 s.
Falta identificar el trabajo nativo/finalización posterior a main que explica
la variabilidad antes de proponer una corrección pequeña y medir un DESPUÉS.
Se detiene aquí como BLOCKED / UNKNOWN, sin smoke integrado.


## Python interpreter shutdown investigation

Resultado: **BLOCKED / UNKNOWN**. Se reproduce la demora sin ROS al cargar el
sistema de embeddings, pero no se identifica inequívocamente un recurso o
finalizador que explique su variabilidad. No se modificó código funcional.

### Método y matriz

Scripts diagnósticos: /tmp/exit_isolate_child.py y /tmp/exit_isolate_parent.py.
Cada caso se ejecuta en un proceso nuevo, secuencialmente, con Python del sistema,
los site-packages de memoria y OMP_NUM_THREADS=1, MKL_NUM_THREADS=1,
TOKENIZERS_PARALLELISM=false. El marcador final usa time.monotonic(); el supervisor
mide hasta wait/poll de salida y muestrea /proc cada 10 ms durante ese intervalo.
Las cifras incluyen la latencia de observación del supervisor (~10 ms nominal,
no una cota estricta bajo carga). No son tiempos de importación o carga.
No hubo Gazebo, Nav2, BT, señales de terminación ni escrituras de memorias.
El caso H recuperó M001 mediante la consulta real aprobada, sin ROS.

| Experimento | Recursos cargados | post-main exit ms | Observación |
|---|---|---:|---|
| A | Python mínimo | 4.637 | exit 0 |
| B | rclpy imports, sin nodo | 24.170 | exit 0 |
| C | SQLAlchemy + psycopg2 imports | 35.846 | exit 0 |
| D | SQL SELECT 1 + cierre/dispose | 41.766 | exit 0 |
| E | SentenceTransformer import | 866.005 | exit 0 |
| F | Modelo Qwen cargado | 5451.983 | exit 0 |
| G | Modelo + embedding real | 2140.459 | exit 0 |
| H | MemoryService + retrieval real sin ROS | 5567.424 | exit 0 |
| numpy | numpy import | 15.220 | exit 0 |
| tokenizers | tokenizers import | 4.764 | exit 0 |
| torch | torch import | 311.799 | exit 0 |
| torch | torch import | 317.900 | exit 0 |
| transformers | transformers import | 79.100 | exit 0 |
| sklearn | sklearn import | 156.171 | exit 0 |
| R | Modelo + del + gc.collect antes del fin | 1138.439 | exit 0 |
| F | Modelo Qwen cargado | 1182.952 | exit 0 |
| R | Modelo + del + gc.collect antes del fin | 791.256 | exit 0 |

Los primeros intentos E–H fallaron por instrumentación: un callback nativo
registrado por torch tenía __module__=None. Se corrigió solamente su representación
en el script de /tmp y se repitieron; esos intentos inválidos no figuran en la tabla.
Logs generales: /tmp/exit_isolate_matrix.log, /tmp/exit_isolate_embeddings.log,
/tmp/exit_isolate_bisect.log. Cada stem conserva .log, .events, .end y .result;
este último incluye muestras externas de threads durante el teardown.

### Inventario real de imports y uso

El evento imports del caso H conserva módulos con rutas y aristas de importación
observadas mediante __import__, no un árbol inferido solo de requirements.
Módulos cargados: torch, sentence_transformers, transformers, tokenizers, numpy,
sklearn, sqlalchemy, psycopg2, multiprocessing y concurrent (incluye futures).
No se observó un módulo psycopg separado.

Rutas relevantes observadas:
- memory.memory_service → sentence_transformers y sqlalchemy.
- transformers.models.qwen3.modeling_qwen3 → torch.
- sqlalchemy.dialects.postgresql.psycopg2 → psycopg2.

Uso efectivo: SentenceTransformer carga y ejecuta Qwen mediante transformers/torch;
tokenización y conversión numpy forman parte de encode; SQLAlchemy/psycopg2
realizan la consulta PostgreSQL. sklearn se importa transitivamente: no se ha
medido una operación sklearn necesaria para esta consulta. multiprocessing y
concurrent.futures se importan; eso no demuestra que haya procesos trabajadores
activos ni trabajo pendiente al salir. MemoryNode no crea sus propios pools de
threads ni procesos. No se atribuye causalidad por mera presencia en sys.modules.

### Threads, atexit y tracing

Se envolvieron temporalmente register/unregister antes de importar dependencias,
preservando argumentos y correspondencia de unregister. Cada handler registra
origen/nombre, inicio y fin. Se observaron también callbacks de GC al salir.
Las siguientes cifras son observaciones, no garantía de cobertura de callbacks
registrados directamente desde extensiones nativas ni de destructores C/C++.

- /tmp/exit_isolate_E_20343905916088: threads nativos por etapa [('baseline', 1), ('embedding_imported', 1), ('logical_end_threads', 1)]; durante salida, cantidades [1], wchan ['0']. Handlers más lentos: weakref.finalize._exitfunc 6.106 ms, torch._dynamo.utils.dump_compile_times 0.738 ms.
- /tmp/exit_isolate_F_20358202209792: threads nativos por etapa [('baseline', 1), ('embedding_imported', 1), ('model_loaded', 2), ('logical_end_threads', 2)]; durante salida, cantidades [1], wchan ['0']. Handlers más lentos: weakref.finalize._exitfunc 254.094 ms, huggingface_hub.utils._http.close_session 38.632 ms.
- /tmp/exit_isolate_G_20376823484523: threads nativos por etapa [('baseline', 1), ('embedding_imported', 1), ('model_loaded', 2), ('inference_done', 3), ('logical_end_threads', 3)]; durante salida, cantidades [1], wchan ['0']. Handlers más lentos: weakref.finalize._exitfunc 122.314 ms, huggingface_hub.utils._http.close_session 1.815 ms.
- /tmp/exit_isolate_H_20414980192421: threads nativos por etapa [('baseline', 1), ('model_loaded', 2), ('query_done', 3), ('logical_end_threads', 3)]; durante salida, cantidades [1], wchan ['0']. Handlers más lentos: weakref.finalize._exitfunc 153.576 ms, huggingface_hub.utils._http.close_session 6.373 ms.
- /tmp/exit_isolate_R_20519606394417: threads nativos por etapa [('baseline', 1), ('embedding_imported', 1), ('model_loaded', 2), ('logical_end_threads', 2)]; durante salida, cantidades [1], wchan ['0']. Handlers más lentos: weakref.finalize._exitfunc 6.989 ms, torch._dynamo.utils.dump_compile_times 1.357 ms.
  del model: 0.006 ms; gc.collect: 163.080 ms. Borrar la referencia no demuestra por sí solo destrucción de todos los recursos nativos.
- /tmp/exit_isolate_F_20536984273094: threads nativos por etapa [('baseline', 1), ('embedding_imported', 1), ('model_loaded', 2), ('logical_end_threads', 2)]; durante salida, cantidades [1], wchan ['0']. Handlers más lentos: weakref.finalize._exitfunc 7.315 ms, huggingface_hub.utils._http.close_session 0.667 ms.
- /tmp/exit_isolate_R_20547648665162: threads nativos por etapa [('baseline', 1), ('embedding_imported', 1), ('model_loaded', 2), ('logical_end_threads', 2)]; durante salida, cantidades [1], wchan ['0']. Handlers más lentos: weakref.finalize._exitfunc 7.524 ms, huggingface_hub.utils._http.close_session 0.597 ms.
  del model: 0.011 ms; gc.collect: 167.409 ms. Borrar la referencia no demuestra por sí solo destrucción de todos los recursos nativos.

En los casos con modelo, los threads Python adicionales observados son monitores
tqdm daemon. En las muestras posteriores al marcador queda un solo hilo nativo,
con wchan=0: no se observa una espera bloqueante sostenida ni un join de varios
threads. Esto no equivale a una pila nativa ni descarta esperas entre muestras.
Los nombres /proc son genéricos y no permiten atribuirlos a BLAS/OpenMP/MKL.
Los handlers observados incluyen weakref.finalize, cierre HTTP de Hugging Face,
tqdm, torch, multiprocessing y logging. Sus tiempos no explican por sí solos los
runs >5 s. No se ha demostrado retención por ThreadPoolExecutor, tokenizers,
conexiones PostgreSQL o logging.

strace no está instalado (command -v sin resultado); tampoco se encontraron gdb
ni perf. No se instalaron herramientas ni se modificaron librerías. Se utilizó
/proc/task, comm y wchan como alternativa; falta una pila/traza nativa para
atribuir el trabajo restante del intérprete a un destructor concreto.

### Bisección y conclusión

A–D cuestan decenas de milisegundos. Importar torch solo cuesta ~312/318 ms;
SentenceTransformer sin modelo ~866 ms. Cargar el modelo, sin ROS ni conexión,
reproduce 5452 ms, pero su repetición cuesta 1183 ms. Memoria sin ROS reproduce
5567 ms. Este es el conjunto más reducido probado que reproduce >5 s:
SentenceTransformer + carga Qwen CPU; no se ha demostrado que sea mínimo absoluto.

La liberación anticipada diagnóstica no prueba una corrección: sus salidas de
1138/791 ms se solapan con la repetición sin liberar de 1183 ms. No se puede
separar causalmente liberación de modelo, estado de caché, carga o paginación con
estas medidas. No se elevan esas hipótesis a causa demostrada.

No se propone ni aplica un cambio funcional. Haría falta observación nativa del
tramo posterior a GC, con recursos retenidos identificados, antes de justificar
un cierre explícito. No se usó os._exit, SIGTERM/SIGKILL ni aumento de timeout.
Todos los experimentos válidos salieron normalmente (0); sus procesos finalizaron
antes del siguiente. No se cambiaron BT, retrieval, ranking, embeddings, base de
datos, logging, resultados ni README. No hubo cambios compilables ni motivo para
repetir build/regresiones funcionales en esta fase puramente diagnóstica.
Se detiene aquí con matriz, bisección y evidencia conservadas, sin smoke integrado.


## Persistent memory service / experimental session lifecycle

**Decisión final: BLOCKED.** La persistencia pasa la validación de consultas y
el cierre de sesión; no se completan dos runs integrados independientes porque
el primer N0 falla antes del orquestador, en readiness de Nav2. No se interpreta
este fallo como contaminación de retrieval ni como fallo del cierre de memoria.
No se modificó código funcional, launch estándar ni timeouts.

### Arquitectura revisada y decisión condicionada

El launch N0 actual no arranca memoria. Su orquestador solo crea clientes de
GetState de bt_navigator y NavigateToPose; fija MEMORY_OFF y no tiene clientes
MemoryQuery/NavigationRecommendation ni escrituras de memoria. N1 sí consulta
memoria y recomendación. Su launch actual posee ambos servicios y los cierra al
terminar cada run: no implementa todavía la separación de sesión propuesta.

MemoryNode conserva _retrieval_cache, cuya clave incluye query, user_id,
location, task, goal y k normalizado. La caché contiene resultados completos;
no modifica ranking, pero evita repetir consultas/embeddings y cambia latencia.
Con dataset/configuración congelados es reutilización determinista. Puede crecer
con nuevas claves durante una sesión y no tiene invalidación ni límite propio.
Por tanto, no debe reutilizarse una sesión después de cambiar dataset, modelo,
pesos o protocolo de consultas. No se ha demostrado determinismo universal de
inferencias nuevas ni se ocultan posibles empates de ranking.

NavigationMemoryNode construye cada respuesta y future localmente y selecciona
la primera memoria devuelta; no mantiene historial por usuario/escenario ni
aprendizaje online. Los servicios no invocan store_memory. Esta función existe
en MemoryService, pero su presencia no implica que se ejecute durante los runs.

La arquitectura persistente es compatible con la comparación N0/N1 bajo estas
condiciones: misma memoria residente para ambas condiciones, memoria congelada,
política de calentamiento de consultas declarada y sin medir latencia fría como
si fuera caliente. navigation_time_s comienza al enviar navegación, no incluye
retrieval; aun así, la carga de RAM/CPU compartida debe mantenerse comparable.
La presencia del proceso no cambia N0 a MEMORY_ON: lo define la ausencia de
interacción y de intervención. Una sesión persistente no prueba por sí sola
independencia completa de futuros escenarios o seeds.

### Contrato de estado y reset

| Session state | Run state y reset requerido |
|---|---|
| PostgreSQL/dataset/versionado congelado | run_id único y destino CSV controlado; una fila terminal |
| memory_node, modelo y caché por clave | Nuevo proceso BT: blackboard, goals, futures y flags nuevos |
| navigation_memory_node y clientes ROS | Nueva instancia NavigationMetrics y escritor write_once |
| Configuración de retrieval/modelo fija | Pose inicial y velocidades del robot, world y reloj simulado |
| Política de warm-up explícita | Nav2: lifecycle, AMCL, costmaps, planes, goals y recoveries |
| Supervisor propietario del cierre final | Actores, trayectorias y seeds futuros según protocolo explícito |

Para esta validación se elige reiniciar Gazebo, bridge, TF publisher, scan fixer,
Nav2 y orquestador entre runs. Es un reset completo del estado de navegación,
no se presupone que teletransportar el robot baste. No se implementa reutilización
de Nav2 ni reset parcial del mundo. Los launches existentes restablecen pose
(2,-3), yaw 0 y objetivo (2.5,-3), sin introducir escenarios nuevos.
NavigationMetrics::start borra distancia, plan count y punto anterior; además
cada run nace en un proceso distinto. La independencia dinámica de métricas del
segundo run permanece sin validar porque ese run no llegó a ejecutarse.

### Memory freeze y prueba sin Gazebo

Supervisor temporal: /tmp/persistent_session_supervisor.py. Servicios arrancados
una sola vez como hijos directos, fuera del launch de run. El supervisor es el
único propietario de su SIGINT final. En memoria se impuso
PGOPTIONS='-c default_transaction_read_only=on' sin cambiar PostgreSQL ni dataset.
Se calculó huella de todas las filas de memory_episodes, incluyendo embeddings,
antes y después. Esta protección aplica a las conexiones de memoria de la sesión;
una futura campaña debe bloquear también escritores externos y fijar versiones.

Tres llamadas reales consecutivas A/A/A al mismo PID produjeron respuestas
idénticas completas, incluyendo IDs, textos y scores: M001,M046,M002. La caché
pasó 0→1, 1→1 y 1→1; no se observó crecimiento con la consulta repetida.
Después, recomendación produjo M001/west y reutilizó esa misma entrada.
No hubo inserts, updates ni aprendizaje online en estas rutas.
El wrapper de observación /tmp/persistent_session_memory.py solo registra tamaño
de caché y resultado del callback original; no cambia claves ni respuestas.
Cliente: /tmp/persistent_session_client.py.

PID memory: 1008979; PID recommendation: 1009051.
Scores primera respuesta: semantic=[0.6368106123556561, 0.6274085325715736, 0.6310487377190515], context=[1.0, 1.0, 0.75], final=[0.6731295511200904, 0.6646676793144162, 0.6429438639471463].
Dataset: 50 filas; SHA256 antes=después: `20b92056fa5df658e813bfe0366f9456e41dfb3077d98c19f38cda943634db7e`.

### Validación integrada mínima: intento interrumpido

Tras pasar el preflight se lanzó N0 estándar, con run_id=persistent_session_1,
result_csv=/tmp/persistent_session_N0.csv. Memoria y recomendación siguieron
vivas y separadas del launch. El N1 previsto reutilizaba el launch existente en
una copia temporal /tmp/persistent_session_n1.launch.py, omitiendo únicamente
los procesos/gates de memoria ya disponibles; no se alteró BT ni configuración.
Esa copia no llegó a ejecutarse.

Evidencia de /tmp/persistent_session_N0.log:
- AMCL activado, pose inicial configurada en timestamp ROS 1790752358.319267049.
- Recepción tardía del mapa: 1790752445.766019428.
- 1790752488.838500620: CRITICAL FAILURE: SERVER map_server IS DOWN,
  heartbeat ausente durante 4000 ms; lifecycle_manager apaga y reinicia nodos.
- 1790752498.677136419: el manager vuelve a declarar nodos activos.
- 1790752556.674924173: readiness response failed: /map_server/get_state.
- El gate impide arrancar el orquestador. No hay CSV de N0 ni fila parcial.
- N1 no se lanza. No se valida independencia de run_id/métricas en dos runs.

Hubo cuatro callbacks de memoria en total, todos del preflight (A/A/A y
recomendación), y ninguno durante el intento N0. Esto concuerda con la revisión
estructural MEMORY_OFF, aunque no sustituye una navegación N0 completada.
El supervisor inicialmente registró FileNotFoundError al intentar leer el CSV
inexistente; esa es una consecuencia del gate fallido, no la causa del run.
Se añadió integrated_failure al JSON para distinguir ambos hechos.
No se cambió Nav2, tuning ni timeout para intentar superar el fallo.

### Shutdown final y limitaciones

El launch de N0 cerró sus hijos normalmente, incluido Gazebo. Después el
supervisor envió una sola señal SIGINT a cada servicio, en orden recomendación
→ memoria, y esperó salida normal, sin SIGTERM/SIGKILL ni os._exit.
- PID 1009051: exit 0, 0.702 s, un SIGINT.
- PID 1008979: exit 0, 12.482 s, un SIGINT.

No quedaron procesos residuales y la huella del dataset permaneció idéntica.
Los 12.48 s de memoria son una LIMITACIÓN DEL RUNTIME observada al finalizar
sesión; no forman parte de un reset entre runs. Su causa nativa exacta sigue
UNKNOWN. El supervisor temporal espera de forma ordenada sin la escalada de
5 s de ros2 launch. No se ha cambiado ni validado aún un launch persistente
estándar. Si se implementa, la política de cierre debe ser de sesión, justificada
por estas mediciones, con diagnóstico de bloqueos; no ampliar timeouts por run.

Evidencia: /tmp/persistent_session_result.json, supervisor.log, memory.log,
recommendation.log, cache.jsonl y persistent_session_N0.log. CSV solo previstos
en /tmp; no se escribió experiments/results. No hubo cambios compilables ni
modificaciones de tests, BT, memoria funcional, datasets o README.

Conclusión: persistencia prometedora y consultas congeladas verificadas, cierre
final normal demostrado; **CAMPAIGN ARCHITECTURE READY no demostrado**. El blocker
reproducido es readiness/lifecycle de Nav2 durante N0. Falta completar dos runs
con reset y servicios persistentes; se detiene sin otra prueba integrada.

## Nav2 startup/readiness stability

### Reanudación y diagnóstico, 2026-09-30

WSL se reinició entre fases: al retomar llevaba unos cuatro minutos activo y
los archivos históricos de /tmp ya no existían. El informe anterior conserva
sus resultados, pero sus logs temporales no pudieron releerse. No había stack
ROS/Gazebo anterior. No se atribuye una reparación causal al reinicio de WSL.
El contenedor existente tfm_memory_postgres estaba parado; se arrancó antes de
la sesión final, sin recrearlo ni alterar su volumen/dataset.

El fallo histórico documentado corresponde a pérdida de comunicación/bond
observada por lifecycle_manager (categoría E), después de que map_server se
activara. No demuestra crash del proceso ni identifica por sí solo starvation,
DDS, clock o carga como causa. La causa subyacente sigue sin aislarse.

Se ejecutaron DOS startups limpios sin memoria, consultas, BT ni navegación.
Se reutilizó exactamente el stack existente, con Gazebo headless. Un observador
independiente consultó GetState de los ocho nodos a 1 Hz y registró tópicos,
TF, nombres/namespaces y respuesta lifecycle. En paralelo se ejecutó la barrera
real con un wrapper que contó cada call_async, sin cambiar su comportamiento.
El supervisor registró procesos/PPID/CPU/RSS, RAM, presión de memoria y tiempos
monotónicos. Después de 20 s de estabilidad se cerró únicamente el launch padre
con SIGINT, que propagó una única secuencia de cierre a sus hijos.

Instrumentación desplegada en /tmp/nav_startup_diagnostic.py. No se modificaron
launches estándar, readiness, BT, Nav2 tuning, mapa, robot ni timeouts.

### Timeline y resultados medidos

Tiempos monotónicos relativos al inicio del supervisor; son instantes observados,
no el momento interno exacto de transición. La creación de la entidad Gazebo se
confirma además en el log de ros_gz_sim; la recepción de clock confirma simulación.

| Evento / comprobación | Startup 1 | Startup 2 |
|---|---:|---:|
| Primer /map | 5.46 s | 8.07 s |
| GetState confirma map_server ACTIVE | 5.57 s | 8.73 s |
| Primer /clock | 6.06 s | 10.61 s |
| Primer /odom | 9.81 s | 12.03 s |
| Primer /scan_fixed | 9.82 s | 12.02 s |
| Ocho nodos ACTIVE observados | 14.69 s | 15.96 s |
| Estabilidad posterior verificada | 20 s | 20 s |
| Respuestas GetState de map_server | 29 | 28 |
| Latencia máxima observada de map_server | 51.56 ms | 16.11 ms |
| Estados posteriores a primera activación | ACTIVE | ACTIVE |
| Heartbeat loss | No | No |
| Nodos/namespaces duplicados | No | No |
| Cleanup normal, launch exit 0 | Sí | Sí |
| Procesos residuales | Ninguno | Ninguno |

Los logs registran Creating/Configuring/Activating de map_server. En startup 1:
1790768785.611794 / 1790768785.821380 / 1790768786.951036; entidad Gazebo creada
a 1790768787.950646. En startup 2: 1790768851.618006 / 1790768852.021865 /
1790768852.847781; entidad creada a 1790768853.177419. Estos son timestamps de log,
no se mezclan con los intervalos monotónicos de la tabla. No hubo T9 de fallo.

TF observado: map→odom→base_link, y ruedas. /map usa QoS transient local en el
observador; los otros tópicos se validan por recepción reciente. Hubo una consulta
diagnóstica a planner_server sin respuesta en 3 s durante su activación en cada
startup; luego respondió ACTIVE de forma estable. No fue un fallo de map_server
ni de la barrera real. La RAM disponible mínima fue 2,093,100 / 2,091,996 KiB.
No se observó caída de proceso, manager duplicado ni namespace inesperado.

### Auditoría de la barrera

wait_for_smoke_ready.py crea ocho clientes una vez, ejecuta GetState en serie y
usa spin_until_future_complete con el tiempo restante del límite global de
120 s. No existe un timeout independiente por petición: una respuesta ausente
puede consumir el resto del límite. Espera descubrimiento en pasos de 0.5 s.
Usa el executor global de rclpy; no lanza ros2 CLI en un bucle. No llama a
ChangeState y no compite con el manager por transiciones lifecycle.

spin_once(timeout_sec=0.2) no garantiza 0.2 s entre rondas cuando llegan tópicos.
Se midieron 752 llamadas en 7.492 s y 544 en 7.547 s (~100 y ~72 llamadas/s
totales, distribuidas entre ocho servicios). Es carga adicional demostrada;
no hay evidencia de que causara el fallo histórico: ambos startups pasan con
esa misma barrera. No se altera su frecuencia sin una justificación causal.

Conclusión del diagnóstico: el fallo histórico NO se reprodujo. No se declara
una corrección de código ni una causa identificada por inferencia. Los dos
startups estables habilitaron la única sesión integrada solicitada.

Evidencia: /tmp/nav_startup_{1,2}_stack.log, _gate.log, _gate_calls.jsonl,
_observer.jsonl, _resources.jsonl, _result.json y /tmp/nav_startup_summary.json.

## Persistent session consecutive-run validation

### Sesión única y memoria congelada

Supervisor: /tmp/nav_persistent_session.py. Memoria PID 16482 y recomendación
PID 16697 se iniciaron una sola vez, como procesos de sesión. Preflight A/A/A
produjo respuestas idénticas completas, M001 primero, y recomendación M001/west.
Durante readiness de cada run no se enviaron consultas de memoria. El wrapper
diagnóstico cuenta los callbacks originales de ambos servicios, sin cambiar
retrieval/ranking, claves de caché ni respuestas.

PGOPTIONS=-c default_transaction_read_only=on protege las conexiones del servicio.
Antes, entre runs y al finalizar se verificaron 50 filas y la misma huella del
contenido completo de memory_episodes, incluidos embeddings:
20b92056fa5df658e813bfe0366f9456e41dfb3077d98c19f38cda943634db7e.
No se insertaron experiencias ni se modificó B1-B4. Se mantiene la condición
documentada de impedir escritores externos durante futuras campañas.

### N0, reset, N1

| Comprobación | N0 | N1 |
|---|---|---|
| condition | MEMORY_OFF | MEMORY_ON |
| run_id | persistent_readiness_1 | persistent_readiness_2 |
| MemoryQuery durante run | 0 (contador 4→4) | 2 (4→6) |
| NavigationRecommendation durante run | 0 (1→1) | 1 (1→2) |
| Estrategia | N/A | west, aplicada |
| source_memory | N/A | M001 |
| Waypoint | N/A | (2.250,-3.000), SUCCEEDED |
| Final goal (2.5,-3.0) | SUCCEEDED | SUCCEEDED |
| success | true | true |
| CSV | 1 fila / 35 columnas | 1 fila / 35 columnas |
| navigation_time_s | 3.060 | 2.020 |
| distance_m | 0.265 | 0.264 |
| replanning_count | 2 | 2 |
| Launch exit | 0 | 0 |

CSV: /tmp/nav_persistent_session_N0.csv y /tmp/nav_persistent_session_N1.csv.
Headers idénticos. Todos los campos de memoria/intervención N0 son N/A.
min_clearance_m, context_compliance e intervention_appropriate siguen N/A.
Los valores son validación de infraestructura, no resultados científicos de campaña.

N0 terminó, su launch cerró Gazebo/bridge/TF/scan/Nav2/BT y se comprobó ausencia
de residuos antes de N1. N1 creó procesos nuevos para todo el RUN STATE; se
restablecieron world, robot, reloj, AMCL, costmaps, goals, blackboard, métricas y
writer. AMCL registra pose (2,-3,0) en ambos runs y ros_gz_sim confirma una nueva
entidad. initial_x/y del CSV proceden de odometría y son aproximadamente cero;
no se interpretan como la pose global del mapa ni se cambia la métrica aprobada.
Métricas y writer nacen en cada proceso y NavigationMetrics::start reinicia
distancia, planes y punto anterior; no se acumulan los valores de N0 en N1.

Memoria y recomendación permanecieron vivas con los mismos PID entre ambos runs.
N1 consulta realmente los servicios; la caché calentada devuelve M001,M046,M002.
El primer Goal succeeded de N1 aparece a 1790769163.978207 y el segundo a
1790769165.927945; el blackboard final confirma waypoint y final goal SUCCEEDED.
No se envió el objetivo final antes del éxito del waypoint.

### Cierre y alcance de la validación

Tras N1 se verificó otra vez disponibilidad con consultas reales y se cerró la
sesión: recomendación 0.232 s, memoria 11.199 s, ambos código 0 y un único SIGINT.
No hubo SIGTERM/SIGKILL, doble señal ni procesos ROS/Gazebo residuales.
PostgreSQL queda disponible como infraestructura existente. La demora final de
memoria se registra como limitación del runtime, fuera del ciclo entre runs;
su causa nativa exacta sigue UNKNOWN y no se reabrió su investigación.

El supervisor temporal posee el cierre de los servicios de sesión y espera su
salida normal. N0 usa su launch estándar; N1 usa una copia temporal del launch
actual que omite exclusivamente el arranque/cierre de los servicios de memoria
ya gestionados por la sesión. No se cambió el launch N1 autónomo: no debe usarse
ese launch sin adaptación para una sesión persistente. Esta validación prueba
la arquitectura con el supervisor documentado, no crea un runner de campaña.

### Build, regresiones y decisión

Después de completar la sesión:
- colcon build --symlink-install --executor sequential: 9 paquetes PASS, 7.68 s.
  Python utilizado: /usr/bin/python3; venv no activado para compilación.
- colcon test --executor sequential: ocho paquetes finalizan normalmente;
  wheelchair_memory devuelve 5 por NO TESTS DISCOVERED, no regresión funcional.
- wheelchair_assistive_bt: resolver 10/10, logging N0 8/8, logging N1 11/11,
  lifecycle 7/7 PASS; cuatro entradas CTest PASS.
- colcon test-result --verbose: 39 tests, 0 errors, 0 failures, 2 skipped.
  Este agregado no oculta el código 5 de discovery de wheelchair_memory.
- git diff --check limitado al informe actualizado: PASS.

Logs: /tmp/nav_session_full_build.log, /tmp/nav_session_full_tests.log,
/tmp/nav_session_test_results.log; evidencia de sesión en
/tmp/nav_persistent_session_result.json, _supervisor.log, _memory.log,
_recommendation.log, _memory_calls.jsonl, _recommendation_calls.jsonl,
_N0.log y _N1.log. Los scripts diagnósticos se desplegaron en /tmp; se conservaron
copias de preparación en el directorio temporal de herramientas del host porque
apply_patch no pudo escribir directamente la ruta UNC de WSL.

**CAMPAIGN ARCHITECTURE READY** para el contrato de sesión y reset completo
validado aquí. Dos startups y N0→reset→N1 pasan, con memoria persistente, dataset
congelado, cierre normal y regresiones verificadas. El fallo histórico de
map_server conserva causa subyacente no aislada; esta conclusión se apoya en la
repetición observada, no en una corrección causal de código. No garantiza todos
los estados de carga ni sustituye el preflight de cada futura sesión.
Se detiene sin campaña, escenarios nuevos ni cambios funcionales de producción.
