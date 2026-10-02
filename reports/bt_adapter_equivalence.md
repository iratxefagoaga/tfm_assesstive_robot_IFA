# Equivalencia semantica: navigation_adapter y Behavior Tree N1

Fecha de auditoria: 2026-09-29

## Resultado final

**BLOCKED**

Las implementaciones son equivalentes para los smoke tests canonicos ya validados: estrategia aplicable, estrategia sin offset, y waypoint que Nav2 aborta. Sin embargo, existen diferencias semanticas en entradas y estados admitidos por los dos caminos. Conforme al criterio de esta auditoria, no se debe migrar el camino experimental N1 al Behavior Tree hasta decidir y unificar esos contratos.

No se modifico codigo, launch, Nav2, mundo, mapa, memoria, datasets, escenarios ni resultados. No se ejecutaron smoke tests nuevos ni una campana experimental. Este informe es el unico artefacto creado en esta fase.

## HEAD Git iniciales

| Repositorio | Branch | HEAD |
|---|---|---|
| `/home/iratxefagoaga/workspace/tfm/ros2` | `nav2_rebuild` | `a2e1705c5324f77580e25044de9851a3cf118e32` |
| `/home/iratxefagoaga/workspace/tfm-robot-memory` | `main` | `4a64e8ee90d29d353b21581abd59edd2ea6abac1` |

No se ejecutaron operaciones Git de escritura.

## Implementaciones comparadas

- Referencia validada: `/home/iratxefagoaga/workspace/tfm/ros2/src/wheelchair_memory/wheelchair_memory/navigation_adapter.py`.
- Behavior Tree: `/home/iratxefagoaga/workspace/tfm/ros2/src/wheelchair_assistive_bt/src/memory_observation_orchestrator.cpp` y `/home/iratxefagoaga/workspace/tfm/ros2/src/wheelchair_assistive_bt/behavior_trees/n1_memory_strategy_navigation.xml`.

Ambas usan `/memory/query`, `/memory/navigation_recommendation` y el action `/navigate_to_pose`. Ninguna sustituye planner, controller, costmaps, recovery ni publica `cmd_vel`.

## Tabla de equivalencia

| Aspecto | navigation_adapter | Behavior Tree | Equivalente |
|---|---|---|---|
| `retrieved_strategy` | Copia `response.strategy` tras `NavigationRecommendation`. | Guarda `response.strategy` en blackboard. | Si, para respuestas validas. |
| Parsing de offsets canonicos | Busca `estrategia:dx:dy`, coincidencia exacta y offset no nulo. | Busca los tres campos, coincidencia exacta y offset no nulo. | Si, para una configuracion canonica sin duplicados. |
| `selected_waypoint` | `final_goal + (dx,dy)`. | Copia `final_goal` y suma `(dx,dy)`. | Si. |
| `strategy_applied` | Verdadero si se obtiene waypoint. | Verdadero si `ResolveStrategyWaypoint` encuentra offset valido. | Si, en el contrato canonico. |
| Sin estrategia aplicable | `NOT_APPLIED` y prepara directamente la meta final. | `WaypointNotApplicable` permite directamente la meta final. | Si, salvo reglas especiales descritas abajo. |
| Orden de goals | Envia waypoint; solo su callback `SUCCEEDED` llama a `prepare_final_goal`. | La secuencia XML envia waypoint antes de la meta final. | Si. |
| Puerta de exito del waypoint | Solo `SUCCEEDED` programa final goal. | Solo el exito de `NavigateNav2(stage=waypoint)` habilita la siguiente leaf. | Si. |
| Barrera de fallo del waypoint | Para `ABORTED/CANCELED`, registra resultado y termina sin meta final. | Para `ABORTED/CANCELED/REJECTED/TIMEOUT`, registra fallo y no puede entrar en la rama directa. | Parcial: vease diferencia semantica de `REJECTED`. |
| Meta final | Usa `goal_x, goal_y`. | Usa el mismo `final_goal` de blackboard. | Si, para `goal_yaw=0`. |
| Autoridad de Nav2 | Cada pose se envia como `NavigateToPose`. | Cada pose se envia como `NavigateToPose`. | Si. |
| Escrituras en memoria | No inserta ni actualiza PostgreSQL/pgvector. | No inserta ni actualiza PostgreSQL/pgvector. | Si. |
| Resultado experimental | Anade una fila CSV con metricas y traza. | Phase 3 deja traza de blackboard en log; no anade la fila CSV del adapter. | No, diferencia logging-only para esta auditoria; impide sustitucion experimental sin integrar logging. |

## CASE A - Estrategia aplicable

Configuracion canonica usada en la evidencia BT:

```text
retrieved_strategy=west
final_goal=(2.500, -3.000)
strategy_waypoint_offsets=west:-0.25:0.0
```

Resultado estructural:

- Adapter: `select_strategy_waypoint` devuelve `(2.250,-3.000)`, marca `strategy_applied=true`, envia waypoint y despues prepara la meta final solo si Nav2 responde `SUCCEEDED`.
- BT: `ResolveStrategyWaypoint` produjo `(2.250,-3.000)`; el XML envio `NavigateNav2(selected_waypoint, waypoint)` antes de `NavigateNav2(final_goal, final_goal)`.

Evidencia real reutilizada del BT: `reports/bt_phase3_validation.md` registra `strategy_applied=true`, `waypoint_nav2_result=SUCCEEDED`, `final_goal_nav2_result=SUCCEEDED` y ambos envios a `/navigate_to_pose`.

Evidencia previa del adapter: `reports/blocker1_validation.md` documenta la misma politica waypoint antes de final goal para la integracion validada.

**CASE A: PASS para configuracion canonica.**

## CASE B - Estrategia no aplicable

Configuracion BT previamente validada:

```text
retrieved_strategy=west
strategy_waypoint_offsets=central:-0.25:0.0
```

Resultado estructural:

- Adapter: no encuentra entrada con nombre `west`, conserva `waypoint_nav2_result=NOT_APPLIED` y prepara un unico final goal.
- BT: resuelve `strategy_applied=false`; `WaypointApplicable` falla y `WaypointNotApplicable` habilita un unico final goal.

Evidencia real reutilizada del BT: `reports/bt_phase3_validation.md` registra `strategy_applied=false`, `waypoint_nav2_result=NOT_APPLIED` y `final_goal_nav2_result=SUCCEEDED`, sin envio de waypoint.

**CASE B: PASS para configuracion canonica.**

## CASE C - Fallo del waypoint

Para una respuesta Nav2 `ABORTED` o `CANCELED`:

- Adapter: escribe `waypoint_nav2_result=<resultado>`, mantiene `final_goal_nav2_result=NOT_SENT`, llama a `finish` y no programa final goal.
- BT: `NavigateNav2(stage=waypoint)` escribe el resultado, fija `final_goal_nav2_result=NOT_SENT`, falla la secuencia; la rama directa no puede ejecutarse porque `WaypointNotApplicable` es falsa cuando `strategy_applied=true`.

Evidencia real reutilizada del BT: con `west:100.0:0.0`, `reports/bt_phase3_validation.md` registra `waypoint_nav2_result=ABORTED`, `final_goal_nav2_result=NOT_SENT`, `success=false` y ausencia de envio posterior de final goal.

La evidencia previa del adapter para Blocker 1 establece la misma barrera para fallo de waypoint.

**CASE C: PARTIAL.** La barrera de ejecucion es equivalente para `ABORTED/CANCELED`, pero no lo es para la trazabilidad de un goal `REJECTED`: el adapter entra por `on_goal_response`, llama a `finish('NAV2_REJECTED')` sin actualizar `waypoint_nav2_result` ni etiquetar la etapa. El BT registra `REJECTED` como resultado de waypoint y conserva la barrera. Ambos evitan la meta final, pero no preservan la misma semantica observable del resultado de waypoint.

## Diferencias encontradas

| Diferencia | Clasificacion | Impacto |
|---|---|---|
| `use_strategy_waypoint=false` en adapter desactiva toda intervencion; el BT Phase 3 no tiene parametro equivalente. | semantic | Con los mismos offsets, el adapter puede ir directo y el BT aplicar waypoint. |
| Adapter trata `strategy == 'direct'` como no aplicable aun si existe `direct:dx:dy`; el BT trata cualquier estrategia, incluido `direct`, de forma generica. | semantic | Misma entrada puede producir distinto `strategy_applied` y distinto numero de goals. |
| Con offsets duplicados, adapter termina al primer match (incluido `0,0`); BT puede ignorar un primer `0,0` y aplicar un match posterior. | semantic | Configuracion ambigua produce distinta decision. |
| Python `float()` rechaza sufijos no numericos; `std::stod` puede aceptar prefijos numericos con sufijo. | semantic | Una entrada malformada puede ignorarse en adapter y aplicarse en BT. |
| En rechazo inicial del goal waypoint, adapter no actualiza `waypoint_nav2_result` aunque no envia final goal; BT si lo actualiza. | semantic | La barrera se conserva, pero la traza requerida del resultado waypoint no es equivalente. |
| Adapter fuerza orientacion identidad en cada `make_goal`; BT conserva `goal_yaw` para final y waypoint. | semantic fuera de los smoke tests actuales, que usan yaw cero | Una configuracion con yaw no nulo no envia la misma pose Nav2. |
| Adapter persiste CSV con tiempo, distancia y replanning; BT Phase 3 emite log de blackboard. | logging-only | No cambia la decision ni la autoridad Nav2, pero el BT no puede sustituir aun el camino experimental que exige resultados CSV. |
| Espera de servicios y timeouts difieren antes de la intervencion. | implementation-only para CASE A/B/C; semantic en disponibilidad/fallo de infraestructura | Adapter puede esperar indefinidamente durante arranque; BT termina por timeout configurado. |

## Recomendacion

El BT **no debe sustituir todavia** al adapter como camino N1 experimental.

Para declararlo sustituto deben resolverse por decision explicita y validacion posterior las diferencias semantic de politica de activacion, estrategia `direct`, configuraciones duplicadas/malformadas, estado `REJECTED` y yaw. Ademas, debe existir registro experimental equivalente de resultados; esta ultima diferencia es logging-only, pero es necesaria para una campana reproducible.

La recomendacion no implica cambiar nada en esta fase. El adapter permanece intacto y los launch experimentales no se migran.
