# N1 Contract Unification and Common Experiment Logging - Design

Fecha: 2026-09-29

## HEAD Git inicial

| Repositorio | HEAD |
|---|---|
| /home/iratxefagoaga/workspace/tfm | a2e1705c5324f77580e25044de9851a3cf118e32 |
| /home/iratxefagoaga/workspace/tfm-robot-memory | 4a64e8ee90d29d353b21581abd59edd2ea6abac1 |

## Alcance

Esta fase modifica solamente el paquete ROS2 `wheelchair_assistive_bt` y crea artefactos de smoke test fuera de `experiments/results/`. No modifica `navigation_adapter.py`, servicios de memoria, interfaces, PostgreSQL, pgvector, Nav2, mundos, mapas, escenarios, B1-B4 ni datos.

El BT es el contrato objetivo. El adapter queda intacto como referencia historica, incluida su diferencia de yaw y su anterior parametro `use_strategy_waypoint`.

## Contrato N1 canonico

### Activacion

El parametro `strategy_waypoint_enabled` es explicito y configurable:

- `false`: no se evalua ni aplica waypoint; `strategy_applied=false`, `waypoint_nav2_result=NOT_APPLIED`, y se envia solamente `final_goal`.
- `true`: se valida la configuracion y se evalua la estrategia recuperada.

### Estrategia direct

`retrieved_strategy == direct` nunca aplica waypoint, aunque exista una entrada `direct:dx:dy`. Registra `strategy_applied=false` y `NOT_APPLIED`, y continua a la meta final.

### Offsets

Formato: entradas separadas por coma, cada una `strategy:dx:dy`.

Reglas:

1. todos los campos se recortan para validar;
2. strategy no puede estar vacia;
3. dx/dy deben consumirse completamente como numeros;
4. (0,0) significa no aplicable;
5. la coincidencia es exacta;
6. dos entradas con la misma strategy son configuracion invalida;
7. cualquier entrada malformada es configuracion invalida.

Ante configuracion invalida se detiene N1 antes de enviar un goal: `failure_stage=resolve_strategy_waypoint`, `strategy_applied=false`, `waypoint_nav2_result=NOT_APPLIED` y `final_goal_nav2_result=NOT_SENT`. No se degrada a una ruta directa silenciosa.

### Waypoint y yaw

Para una unica entrada valida, no nula y que coincide con la estrategia:

```text
selected_waypoint.x = final_goal.x + dx
selected_waypoint.y = final_goal.y + dy
selected_waypoint.frame_id = map
selected_waypoint.yaw = final_goal_yaw
```

La politica conserva la orientacion final para ambos goals. El adapter historico crea quaternion identidad y no propaga `goal_yaw`; no se modifica en esta fase.

### Estados Nav2 y barrera

Los estados observables son:

```text
SUCCEEDED, ABORTED, CANCELED, REJECTED, TIMEOUT,
NOT_SENT, NOT_APPLIED, NOT_STARTED
```

Con waypoint aplicado, solamente `SUCCEEDED` permite `NavigateToPose(final_goal)`. Cualquier otro estado deja `final_goal_nav2_result=NOT_SENT`, `success=false` y `failure_stage=navigate_waypoint`. No existe fallback a la rama directa.

## CSV comun N0/N1

Se incorpora un helper C++ compartido para no duplicar la instrumentacion de odometria, /plan y escritura CSV entre orquestadores.

Cada run escribe una fila al parametro explicito `result_csv`. Los smoke tests usaran rutas bajo `/tmp`, nunca `experiments/results/`.

Campos comunes:

```text
timestamp_utc, experiment_id, scenario_id, condition, run_id,
user_id, location, task, goal_label,
initial_x, initial_y, initial_yaw, goal_x, goal_y, goal_yaw,
success, navigation_time_s, distance_m, replanning_count,
min_clearance_m,
memory_ids, source_memory, retrieved_strategy,
strategy_waypoint_enabled, strategy_waypoint_offsets, strategy_applied,
selected_waypoint_x, selected_waypoint_y,
waypoint_nav2_result, final_goal_nav2_result,
nav2_result, failure_stage, failure_reason,
context_compliance, intervention_appropriate
```

N0 usa `N/A` para campos de memoria/intervencion. N1 usa `N/A` cuando el dato no puede existir, por ejemplo antes de una recomendacion.

## Definicion de metricas

- `navigation_time_s`: tiempo monotono desde el envio del primer goal a Nav2 hasta que el run finaliza. Excluye espera de servicios, lifecycle y retrieval. En N1 incluye waypoint y meta final.
- `distance_m`: suma de distancias euclideas entre mensajes consecutivos de `/odom` mientras la navegacion esta activa. Incluye ambos tramos N1.
- `replanning_count`: mensajes `/plan` recibidos durante navegacion menos el primer plan, con minimo cero. Es la definicion ya empleada por runner y adapter.
- `min_clearance_m`: `N/A`. No existe una medicion de clearance validada y comun; scan/costmap requeririan una definicion e instrumentacion adicional.
- `context_compliance` e `intervention_appropriate`: `N/A`. Deben derivarse o anotarse desde escenarios formalmente congelados, no desde campos `expected_*` operacionales.

## Validacion

- Unit/structural tests del resolver: disabled, direct, sin offset, duplicado, malformado y offset valido.
- Smoke N0/N1 con CSV aislados en /tmp.
- Reutilizacion de evidencia existente para waypoint ABORTED; no se forzaran estados peligrosos nuevos.
- Build del paquete y workspace completo.

## README

No se reescribe en esta fase. Despues de declarar BT como camino N1 definitivo deberan actualizarse: arquitectura, requisitos, instalacion, ejecucion N0/N1, memoria, Behavior Tree, resultados y futura seccion de escenarios.
