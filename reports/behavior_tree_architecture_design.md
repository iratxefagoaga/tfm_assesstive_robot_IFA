# Diseño de arquitectura Behavior Tree para navegación asistiva con memoria

Fecha: 2026-09-29  
Estado: diseño solamente. No se ha modificado código, configuración, escenarios, datos ni resultados; no se han ejecutado experimentos.

## 1. Estado actual de Behavior Trees en Nav2

El paquete `wheelchair_navigation` inicia `nav2_bt_navigator` junto con planner, controller, costmaps, behavior server, waypoint follower y velocity smoother. La configuración actual de `bt_navigator` declara dos navegadores estándar:

- `navigate_to_pose` → `nav2_bt_navigator::NavigateToPoseNavigator`
- `navigate_through_poses` → `nav2_bt_navigator::NavigateThroughPosesNavigator`

No define `default_nav_to_pose_bt_xml`, `default_nav_through_poses_bt_xml` ni `plugin_lib_names`. Por omisión de Nav2 Jazzy, `NavigateToPose` carga:

`nav2_bt_navigator/behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml`

El XML instalado contiene:

- `PipelineSequence` de `ComputePathToPose` y `FollowPath`;
- replanning a 1 Hz;
- `PlannerSelector` y `ControllerSelector`;
- recuperación por limpieza de costmaps;
- `Spin`, `Wait` y `BackUp`;
- hasta seis reintentos en `NavigateRecovery`.

Por tanto, Nav2 ya usa BehaviorTree.CPP internamente para planificar, controlar y recuperar. La configuración del proyecto conserva el footprint 0,72 x 0,68 m, inflation radius 0,70 m y `/scan_fixed`; nada de ello debe trasladarse a la memoria.

BehaviorTree.CPP 4.9.0 y las cabeceras/biblioteca necesarias están instaladas en `/opt/ros/jazzy`. No existe un XML BT propio ni un paquete BT propio en los workspaces auditados.

## 2. Arquitectura actual

```text
N0:
BaselineRunner
  └─ NavigateToPose(final_goal)
       └─ Nav2 BT estándar
            ├─ ComputePathToPose / planner
            ├─ FollowPath / controller
            └─ recovery + costmaps + velocity smoother

N1:
NavigationMemoryAdapter (máquina de estados Python)
  ├─ MemoryQuery
  ├─ NavigationRecommendation
  ├─ resolver strategy_waypoint_offsets
  ├─ NavigateToPose(waypoint), si estrategia aplicable
  └─ NavigateToPose(final_goal), sólo si waypoint=SUCCEEDED
       └─ Nav2 BT estándar
```

`memory_node` es el adaptador ROS de `MemoryService`, PostgreSQL, pgvector y embeddings, y expone `/memory/query`. `navigation_memory_node` consume esa respuesta y expone `/memory/navigation_recommendation`; interpreta la acción de la memoria como `west`, `central`, `alternative` o `direct`. Las interfaces `MemoryQuery` y `NavigationRecommendation` ya contienen toda la trazabilidad semántica/episódica requerida.

## 3. Problema de integración

La orquestación de N1 no es visible como árbol: está repartida en callbacks de `navigation_adapter.py`:

- espera de servicios y de lifecycle active;
- query y recommendation;
- copia de IDs y scores al registro;
- resolución de offset de estrategia;
- decisión entre waypoint o meta directa;
- envío secuencial de goals Nav2;
- regla de fallo del waypoint;
- métricas de odometría/replanning y persistencia CSV.

Esa implementación fue validada para Blocker 1, pero una máquina de estados por callbacks dificulta inspeccionar de forma declarativa las bifurcaciones experimentales y el tratamiento del fallo. Además, la acción estándar `NavigateToPose` sólo aporta una pose: no transporta `query`, usuario, contexto ni policy offsets. Por ello, sustituir únicamente el XML de Nav2 no resuelve cómo llega el contexto de memoria al árbol.

## 4. Alternativas

| Opción | Complejidad | Reutilización | Integración Nav2 | Trazabilidad/reproducibilidad | Riesgo | Adecuación |
|---|---|---|---|---|---|---|
| A. Extender directamente el XML de `bt_navigator` | Media/alta | Reutiliza nodos BT internos | Muy estrecha | Buena si se resuelve el contexto | Alta: requiere custom BT plugins y un canal seguro por goal para metadata | Insuficiente por sí sola; `NavigateToPose` no lleva el contexto experimental |
| B. BT asistivo de alto nivel que invoque Nav2 | Media | Máxima: conserva servicios, recommendation, offsets, CSV y BT Nav2 actual | Dos niveles de BT: asistivo → `NavigateToPose` → BT Nav2 | Muy alta: un XML explícito refleja condiciones y cada leaf registra evidencia | Bajo/medio: no cambia planner/controller/costmaps ni el XML Nav2 validado | **Recomendada** |
| C. Navigator plugin + acción asistiva personalizada | Alta | Reutiliza Nav2 BT, pero requiere C++, action nueva, pluginlib y lifecycle | Máxima, un único BT dentro de `bt_navigator` | Muy buena | Alta: nueva interfaz de navegación y mayor superficie de regresión | Fase futura si se necesita API interactiva unificada |
| A + C | Muy alta | Parcial | Máxima | Muy buena | Muy alta | No justificada para este TFM en la fase actual |

### Decisión propuesta

Adoptar **B** como solución mínima y defendible: un BT asistivo de alto nivel, implementado con BehaviorTree.CPP, que llama a los dos servicios existentes y a la acción estándar `/navigate_to_pose`. El BT de Nav2 permanece intacto y anidado. Esto satisface que el BT orqueste memoria, decisión y navegación sin reimplementar Nav2.

No se recomienda por ahora un Navigator plugin personalizado. Es técnicamente viable —`nav2_core::BehaviorTreeNavigator<ActionT>` permite plugins con `goalReceived`, blackboard y `goalCompleted`—, pero obligaría a definir una acción asistiva nueva para transportar contexto, registrar feedback y preservar compatibilidad. Es desproporcionado antes de cerrar estabilidad, escenarios y métricas.

## 5. Arquitectura BT propuesta

Un nuevo ejecutable C++ `assistive_bt_orchestrator` alojaría un árbol BehaviorTree.CPP externo. Sería un cliente de:

- `/memory/query`;
- `/memory/navigation_recommendation`;
- `/navigate_to_pose`;
- `/bt_navigator/get_state`;
- `/odom` y `/plan` para la instrumentación que ya usa el adapter.

No publicaría `cmd_vel`, no llama directamente a planner/controller ni modifica costmaps. Cada leaf `NavigateNav2` sólo entrega una pose a Nav2; el BT interno de Nav2 sigue realizando `ComputePathToPose`, `FollowPath` y recoveries.

```text
                         Request / parámetros de escenario
                                      |
                                      v
                      Assistive BT Orchestrator (BT.CPP)
                                      |
        +-----------------------------+----------------------------+
        |                                                          |
        v                                                          v
  N0: Memory OFF                                             N1: Memory ON
  StartRun                                                   StartRun
  NavigateNav2(final_goal)                                   QueryMemory
  RecordFinalResult                                          RecommendNavigation
  FinalizeRun                                                ResolveStrategyWaypoint
                                                             |
                                                             +-- no waypoint --> NavigateNav2(final_goal)
                                                             |
                                                             +-- waypoint --> NavigateNav2(waypoint)
                                                                  | failure --> RecordWaypointFailure
                                                                  |            FinalNotSent
                                                                  |            FinalizeRun(FAILURE)
                                                                  v success
                                                               NavigateNav2(final_goal)
                                                               RecordFinalResult
                                                               FinalizeRun
                                      |
                                      v
                      /navigate_to_pose (Nav2 BT estándar)
                                      |
                         planner / controller / costmaps /
                         recoveries / velocity smoother / Gazebo
```

## 6. Nodos BT necesarios

Los nodos deben ser pocos y tener responsabilidades acotadas.

| Nodo propuesto | Tipo | Responsabilidad | Reutilización |
|---|---|---|---|
| `WaitForNav2Active` | Condition/Stateful action | Comprueba lifecycle de `bt_navigator` antes de cualquier goal | lógica actual del adapter/runner |
| `QueryMemory` | Stateful action | Llama `MemoryQuery`; guarda listas y scores | servicio existente |
| `GetNavigationRecommendation` | Stateful action | Llama `NavigationRecommendation`; guarda estrategia, memoria fuente, flags y razón | servicio existente |
| `ResolveStrategyWaypoint` | Synchronous action | Aplica los offsets declarativos por escenario; no valida ni mueve el robot | `select_strategy_waypoint` actual |
| `WaypointApplicable` | Condition | Verdadero sólo si existe offset distinto de cero | regla actual |
| `NavigateNav2` | Stateful action | Cliente de `NavigateToPose`; informa `SUCCEEDED/ABORTED/CANCELED/REJECTED` | acciones actuales, Nav2 interno |
| `RecordEvent` / `FinalizeExperiment` | Synchronous action | Escribe un evento estructurado y finalmente el CSV común | esquema actual del adapter/baseline |
| `BuildDeferredExperience` | Synchronous action, desactivado por defecto | Genera candidato de experiencia fuera de la DB | nueva fase, no activa en campaña |

No son necesarios nodos que repliquen `ComputePathToPose`, `FollowPath`, costmaps, recovery, AMCL o Gazebo: ya son nodos/servidores de Nav2. Tampoco son necesarios nodos de embedding, PostgreSQL o pgvector.

## 7. Blackboard

El blackboard pertenece a una ejecución identificada por `experiment_id/scenario_id/condition/run_id`; no debe compartir estado mutable entre runs.

### Entrada inmutable

```text
experiment_id, scenario_id, condition, run_id
query, user_id, location, task, goal_label, k
initial_pose, final_goal
strategy_waypoint_offsets
results_path
```

### Estado de memoria

```text
memory_ids, summaries, observations, actions, outcomes, preferences
semantic_scores, context_scores, final_scores
source_memory, recommendation_reason
retrieved_strategy, avoid_obstacle, prefer_clearance
```

### Estado de decisión/navegación

```text
strategy_applied
selected_waypoint (PoseStamped o vacío)
waypoint_nav2_result
final_goal_nav2_result
nav2_result, success
time_s, distance_m, replanning_events
failure_stage, failure_reason
```

Las listas de memorias y la recomendación se almacenan como datos trazables; el nodo `ResolveStrategyWaypoint` únicamente usa `retrieved_strategy`, `final_goal` y la política declarativa. Ningún `expected_*` de escenario entra al blackboard operacional: es ground truth para análisis, no una orden al sistema.

## 8. Flujo N0: Memory OFF

```xml
<Sequence>
  <StartRun condition="MEMORY_OFF"/>
  <WaitForNav2Active/>
  <NavigateNav2 goal="{final_goal}" result="{final_goal_nav2_result}"/>
  <FinalizeExperiment status="from_final_goal"/>
</Sequence>
```

N0 no instancia clientes de `MemoryQuery` ni `NavigationRecommendation`; sus campos de memoria permanecen vacíos. El árbol alto nivel sólo formaliza la misma secuencia que realiza `baseline_runner.py`. Así, N0 y N1 comparten la leaf `NavigateNav2`, métricas, formato CSV, condiciones de lifecycle y meta final.

## 9. Flujo N1: Memory ON

Pseudoxml conceptual:

```xml
<Sequence>
  <StartRun condition="MEMORY_ON"/>
  <WaitForNav2Active/>
  <QueryMemory .../>
  <GetNavigationRecommendation .../>
  <ResolveStrategyWaypoint .../>

  <Fallback>
    <Sequence>
      <WaypointApplicable/>
      <NavigateNav2 goal="{selected_waypoint}" result="{waypoint_nav2_result}"/>
      <NavigateNav2 goal="{final_goal}" result="{final_goal_nav2_result}"/>
    </Sequence>
    <Sequence>
      <NoWaypointApplicable/>
      <NavigateNav2 goal="{final_goal}" result="{final_goal_nav2_result}"/>
    </Sequence>
  </Fallback>

  <FinalizeExperiment status="from_final_goal"/>
</Sequence>
```

El XML final debe estructurarse para que un `NavigateNav2(waypoint)` que falle no pueda caer a la rama sin waypoint. La condición `NoWaypointApplicable` será verdadera sólo cuando `strategy_applied=false`, nunca cuando existe waypoint y su navegación falla.

## 10. Manejo de fallos y seguridad

| Evento | Estado BT | Registro | ¿Se envía final goal? |
|---|---|---|---|
| MemoryQuery o recommendation falla | FAILURE | `MEMORY_QUERY_* / RECOMMENDATION_*`, stage y razón | No |
| No hay estrategia aplicable | SUCCESS de resolución | `strategy_applied=false`, `NOT_APPLIED` | Sí, meta final común |
| Waypoint rechazado/abortado/cancelado | FAILURE | `waypoint_nav2_result`, `WAYPOINT_<resultado>`, `final_goal_nav2_result=NOT_SENT` | **No** |
| Waypoint succeeds | SUCCESS | resultado waypoint | Sí |
| Final goal falla | FAILURE | resultado Nav2 final | Ya fue enviado; se conserva resultado |
| Final goal succeeds | SUCCESS | `SUCCEEDED` | No aplica |

Se conserva íntegramente la política validada del Blocker 1. Los recoveries que Nav2 aplique dentro de cada `NavigateNav2` siguen siendo de Nav2. El BT asistivo no convierte una recomendación en `cmd_vel`, no altera el footprint ni relaja la seguridad de mapa/costmap.

## 11. Relación con navigation_adapter existente

No se elimina `navigation_adapter`.

Fase de migración propuesta:

1. Mantenerlo como implementación de referencia y smoke-test validado de N1.
2. Extraer/duplicar inicialmente, con tests de equivalencia, tres contratos puros: serialización de offsets, esquema CSV y mapeo de estados de Nav2.
3. Implementar el orquestador BT como alternativa de lanzamiento experimental, sin cambiar los servicios de memoria.
4. Comparar un smoke test del adapter y uno del BT con el mismo request: deben conservar request, memoria, estrategia, waypoint, política de fallo, meta final y campos CSV.
5. Sólo tras esa equivalencia, hacer que el launch N1 experimental seleccione el orquestador BT; el adapter queda disponible como fallback técnico, no como condición experimental distinta.

El problema de doble consulta actual se preserva al comienzo por compatibilidad: `QueryMemory` registra la respuesta y `GetNavigationRecommendation` usa el servicio existente, que internamente consulta memoria. La caché de `memory_node` evita repetir retrieval idéntico durante el proceso. Optimizar la interfaz para una sola consulta es una mejora separada y no forma parte de la integración BT inicial.

## 12. Cambios necesarios por paquete

| Paquete/área | Cambio futuro mínimo | No cambiar en la primera iteración |
|---|---|---|
| Nuevo `wheelchair_assistive_bt` (ament_cmake) | ejecutable C++ BT.CPP, XML y plugins/leaf nodes; dependencias `rclcpp`, `rclcpp_action`, `behaviortree_cpp`, `nav2_msgs`, `geometry_msgs`, `nav_msgs`, `lifecycle_msgs`, `wheelchair_interfaces` | planner/controller/costmaps |
| `wheelchair_memory` | conservar nodos y adapter; opcionalmente compartir nombres de campos/CSV | PostgreSQL, pgvector, embeddings, ranking y reglas de recommendation |
| `wheelchair_interfaces` | sin cambio inicial | no crear action nueva aún |
| `wheelchair_navigation` | sin cambio inicial: mantener XML default y params actuales | no sustituir XML Nav2 ni plugins internos |
| `wheelchair_bringup` | launch alternativo que arranque el orquestador BT en N0/N1 con el mismo stack Nav2 | no tocar mundo, robot, sensores ni Nav2 |
| `experiments/scripts` | elegir launcher BT y registrar versión/XML en manifiesto cuando se implemente | no alterar escenarios ni resultados existentes |

Un `AssistedNavigate.action` y un Navigator plugin (opción C) sólo se evaluarían después si se necesita exponer a RViz/usuarios una acción única con contexto completo. No son requisitos del diseño mínimo.

## 13. Logging experimental

El orquestador debe conservar el CSV común y añadir, sin borrar campos existentes, una traza de eventos por run (CSV/JSONL separado) con:

```text
timestamp_utc, experiment_id, scenario_id, condition, run_id
bt_xml_id, bt_node, bt_status, failure_stage
memory_ids, source_memory, semantic/context/final score
retrieved_strategy, strategy_applied, selected_waypoint
waypoint_nav2_result, final_goal, final_goal_nav2_result
nav2_result, success, time_s, distance_m, replanning_events
```

La fila agregada se emite una sola vez al final. Los eventos permiten demostrar qué decisión fue de memoria y qué resultado ejecutó Nav2. La referencia/version/hash del XML debe quedar en el manifiesto antes de la campaña para evitar ambigüedad de configuración.

## 14. Experiencia resultante sin contaminar experimentos

Durante la campaña experimental, `BuildDeferredExperience` debe estar deshabilitado y no debe hacer `INSERT` en PostgreSQL. Esto garantiza que una repetición no cambie el corpus de la siguiente.

Como salida opcional, el orquestador puede producir un artefacto inmutable por run —por ejemplo `candidate_experience.json`— con input, decisión, resultados y referencias de configuración. Tras terminar **toda** la campaña, una fase separada, con corpus congelado y aprobación explícita, podrá revisar/deduplicar/ingestar candidatos en una base nueva o snapshot posterior. Esa ingesta no forma parte de N0/N1 ni de las hipótesis actuales.

## 15. Riesgos

1. Añadir BT.CPP C++ crea un segundo lenguaje frente a los nodos Python; se justifica porque `py_trees` no está instalado ni en Python ROS ni en el venv de memoria, y BT.CPP es la biblioteca ya instalada por Nav2.
2. Un BT externo introduce dos niveles de árboles. Es intencional y trazable: el alto nivel decide la secuencia asistiva; Nav2 decide la navegación segura.
3. El uso concurrente de varios stacks de Gazebo/clock observado en la validación de Blocker 2 puede invalidar smoke tests BT; se exigirá un único stack por prueba.
4. Servicios de memoria lentos o no disponibles deben terminar N1 explícitamente, no usar una estrategia inventada ni degradar silenciosamente a N0.
5. Duplicar temporalmente la lógica del adapter puede divergir; los tests de equivalencia y el adapter preservado reducen ese riesgo.
6. No se debe interpretar una ruta más larga de N1 como mejora: sólo métricas y ground truth predefinidos permitirán análisis posterior.

## 16. Plan incremental de implementación

1. Congelar el diseño: nombres de nodos, schema de blackboard, XML y política de fallo.
2. Crear el paquete C++ y un BT N0 mínimo que sólo llame `NavigateNav2(final_goal)`; verificar que no consulta memoria y que produce el CSV compatible.
3. Añadir `WaitForNav2Active`, métricas y `FinalizeExperiment`; validar lifecycle y resultados.
4. Añadir `QueryMemory` y `GetNavigationRecommendation` sin aplicar waypoint; comparar con la trazabilidad del adapter.
5. Añadir `ResolveStrategyWaypoint`, dos-goals y la barrera estricta `waypoint failure → final NOT_SENT`.
6. Ejecutar smoke tests aislados N0/N1 con un único stack, sin campaña ni cambios de escenarios.
7. Añadir la traza de eventos y versión de XML al manifiesto.
8. Sólo después revisar la necesidad de un Navigator plugin personalizado. No iniciar la campaña hasta cerrar los blockers de escenarios, métricas, congelación y reproducibilidad.

## 17. Criterios de validación

1. Build de paquetes BT con `/usr/bin/python3` para el workspace ROS; ninguna dependencia de embeddings entra en CMake.
2. El árbol N0 no crea clientes ni llamadas a servicios de memoria.
3. El árbol N1 completa `query → recommendation → strategy → waypoint si procede → Nav2 → final goal`.
4. El blackboard y CSV muestran IDs, scores, estrategia, waypoint, resultados de ambos goals y resultado final.
5. Se demuestra en una ejecución real que Nav2 recibe el waypoint y, sólo tras `SUCCEEDED`, la misma meta final que N0.
6. Se demuestra que waypoint `ABORTED/REJECTED/CANCELED` termina el run con `final_goal_nav2_result=NOT_SENT`.
7. Planner, controller, costmaps, recovery, `cmd_vel` pipeline, mapa, robot y sensores permanecen iguales N0/N1.
8. Un único Gazebo/clock está activo durante cada smoke test.
9. Las ejecuciones de validación se escriben fuera de `experiments/results/` o en un lote explícitamente no definitivo.
10. No se insertan experiencias nuevas en la base de datos durante repeticiones experimentales.
