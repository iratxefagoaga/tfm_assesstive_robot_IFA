# BT Phase 3 - Validacion

Fecha: 2026-09-29

## Alcance de la validacion

Se ejecutaron smoke tests reales, no una campana experimental. Todos usaron Nav2 y Gazebo mediante los launch de humo. Los resultados de esta seccion proceden de logs ROS conservados bajo `/home/iratxefagoaga/.ros/log/`.

## Compilacion

| Prueba | Resultado | Evidencia |
|---|---|---|
| `colcon build --packages-select wheelchair_assistive_bt --symlink-install` | PASS | Paquete compilado correctamente. |
| `colcon build --symlink-install` | PASS | 9 paquetes completados: `wheelchair_interfaces`, `wheelchair_description`, `wheelchair_gazebo`, `wheelchair_navigation`, `wheelchair_api`, `wheelchair_vla`, `wheelchair_memory`, `wheelchair_assistive_bt`, `wheelchair_bringup`. |

La compilacion se realizo con `/usr/bin/python3` tras cargar ROS Jazzy, sin activar el entorno virtual de memoria.

## Smoke tests N1

### 1. Estrategia aplicable: waypoint y meta final

Configuracion relevante:

```text
condition=MEMORY_ON
user_id=U01
query=navegar evitando la mesa
final_goal=(2.500, -3.000)
strategy_waypoint_offsets=west:-0.25:0.0
```

Resultado: PASS.

Log: `/home/iratxefagoaga/.ros/log/memory_observation_bt_orchestrator_329960_1790703804039.log`

Evidencia observada:

```text
strategy 'west' resolved to waypoint (2.250, -3.000)
waypoint sent to /navigate_to_pose
final_goal sent to /navigate_to_pose
strategy_applied=true
selected_waypoint=(2.250,-3.000)
waypoint_nav2_result=SUCCEEDED
final_goal=(2.500,-3.000)
final_goal_nav2_result=SUCCEEDED
nav2_result=SUCCEEDED
success=true
```

Esta ejecucion demuestra que una estrategia recuperada de memoria se aplico realmente mediante Nav2 y que, tras completarla, Nav2 recibio la misma meta final.

### 2. Estrategia no aplicable: ruta directa

Configuracion relevante:

```text
retrieved_strategy=west
strategy_waypoint_offsets=central:-0.25:0.0
```

Resultado: PASS.

Log: `/home/iratxefagoaga/.ros/log/memory_observation_bt_orchestrator_330537_1790703969783.log`

Evidencia observada:

```text
strategy_applied=false
selected_waypoint=(0.000,0.000)
waypoint_nav2_result=NOT_APPLIED
final_goal=(2.500,-3.000)
final_goal_nav2_result=SUCCEEDED
nav2_result=SUCCEEDED
success=true
```

El log no contiene envio de waypoint. La falta de una correspondencia declarada produce una unica navegacion a la meta final.

### 3. Barrera de fallo del waypoint

Configuracion controlada:

```text
strategy_waypoint_offsets=west:100.0:0.0
final_goal=(2.500,-3.000)
selected_waypoint=(102.500,-3.000)
```

Resultado: PASS (fallo esperado y explicito).

Log: `/home/iratxefagoaga/.ros/log/memory_observation_bt_orchestrator_331131_1790704250349.log`

Evidencia observada:

```text
strategy_applied=true
selected_waypoint=(102.500,-3.000)
waypoint_nav2_result=ABORTED
final_goal_nav2_result=NOT_SENT
nav2_result=ABORTED
success=false
failure_stage=navigate_waypoint
failure_reason=ABORTED
```

El log contiene el envio del waypoint y no contiene un envio posterior de `final_goal`. Esto valida que el arbol no oculta un fallo ni degrada a navegacion directa.

### 4. Fallo de memoria

Se ejecuto el orquestador N1 sin los servicios de memoria disponibles y con espera de un segundo.

Resultado: PASS (barrera de fallo esperada).

Evidencia observada:

```text
memory_query_result=TIMEOUT
recommendation_result=NOT_STARTED
strategy_applied=false
waypoint_nav2_result=NOT_APPLIED
final_goal_nav2_result=NOT_SENT
nav2_result=NOT_STARTED
success=false
failure_stage=query_memory
failure_reason=TIMEOUT waiting for /memory/query
```

No se envio waypoint ni meta final cuando falla la consulta de memoria.

## Regresion N0

Se ejecuto `bt_n0_smoke.launch.py` con:

```text
experiment_id=bt_phase3_n0_regression
scenario_id=S001_shared_safe_goal
condition=MEMORY_OFF
run_id=n0_phase3_001
```

Resultado: PASS.

Log: `/home/iratxefagoaga/.ros/log/assistive_bt_orchestrator_331569_1790704449121.log`

Evidencia observada:

```text
Assistive BT N0 XML loaded: .../n0_assistive_navigation.xml
Assistive BT N0: final_goal sent to /navigate_to_pose.
nav2_result=SUCCEEDED
final_goal_nav2_result=SUCCEEDED
success=true
```

N0 no consulta memoria y sigue navegando directamente a la meta final.

## Criterios de aceptacion

| Criterio | Estado |
|---|---|
| N0 continua sin memoria | PASS |
| N1 obtiene recomendacion | PASS |
| Una estrategia aplicable marca `strategy_applied=true` | PASS |
| Nav2 recibe el waypoint | PASS |
| Tras waypoint exitoso Nav2 recibe la misma meta final | PASS |
| Fallo del waypoint no envia meta final | PASS |
| Fallo de memoria no envia navegacion | PASS |
| El log separa decision de memoria y ejecucion Nav2 | PASS |
| No se registran experiencias nuevas durante los smoke tests | PASS (inspeccion de alcance: solo consulta/recomendacion; no se invoco escritura de memoria) |

## Incidencias restantes

Despues de cada lanzamiento de humo se terminaron los procesos Gazebo residuales antes del siguiente test. Esto es una incidencia de ciclo de vida del launch/simulador ya conocida y no altera la evidencia de los resultados Nav2 anteriores; no se modifico en esta fase.

No se han ejecutado escenarios ni repeticiones experimentales definitivas. Es necesario mantener esa separacion antes de la campana final.
