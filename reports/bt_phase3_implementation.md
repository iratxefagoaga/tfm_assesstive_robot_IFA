# BT Phase 3 - Implementacion

Fecha: 2026-09-29

## Alcance

Se implemento unicamente la orquestacion N1 con estrategia de memoria mediante un waypoint relativo a la meta final. No se modificaron N0, Nav2, PostgreSQL/pgvector, las interfaces ROS, el modelo de embeddings, el mundo, el mapa, los escenarios ni los resultados experimentales.

La ruta N1 implementada es:

```text
MemoryQuery -> NavigationRecommendation -> ResolveStrategyWaypoint
-> [si aplicable] NavigateToPose(waypoint) -> NavigateToPose(meta final)
-> FinalizeExperiment
```

Si no existe una estrategia aplicable, N1 conserva la ruta directa a la misma meta final. Si la navegacion al waypoint falla, no se envia la meta final.

## Archivos modificados o anadidos

| Archivo | Cambio |
|---|---|
| `/home/iratxefagoaga/workspace/tfm/ros2/src/wheelchair_assistive_bt/src/memory_observation_orchestrator.cpp` | Anade resolucion general de estrategia a waypoint, condiciones de rama, navegacion por etapas y trazabilidad de blackboard. |
| `/home/iratxefagoaga/workspace/tfm/ros2/src/wheelchair_assistive_bt/behavior_trees/n1_memory_strategy_navigation.xml` | Nuevo arbol N1: consulta memoria, recomienda, resuelve waypoint y ejecuta waypoint antes de la meta final cuando procede. |
| `/home/iratxefagoaga/workspace/tfm/ros2/src/wheelchair_assistive_bt/launch/bt_n1_phase3_smoke.launch.py` | Launch de smoke test aislado para N1 Phase 3. No modifica los launch experimentales. |

## Diseno aplicado

`ResolveStrategyWaypoint` consume desde el blackboard:

- `retrieved_strategy`
- `strategy_waypoint_offsets`
- `final_goal`

`strategy_waypoint_offsets` usa entradas declarativas separadas por comas:

```text
estrategia:desplazamiento_x:desplazamiento_y
```

La coincidencia es exacta por nombre de estrategia y el desplazamiento se suma a la meta final en el frame `map`. Las entradas mal formadas, sin coincidencia o con desplazamiento `0,0` no aplican estrategia. No contiene reglas especificas para M001, S001, `west`, `central` u otro escenario.

Al aplicar una estrategia se escriben:

- `strategy_applied=true`
- `selected_waypoint`
- `waypoint_nav2_result`

`NavigateNav2` ahora recibe `goal` y `stage`:

- En `stage=waypoint`, un error registra el resultado, marca `final_goal_nav2_result=NOT_SENT` y falla el arbol.
- En `stage=final_goal`, conserva el registro de resultado final.
- Solo se acepta `waypoint` o `final_goal`; otros valores fallan explicitamente.

El arbol emplea dos condiciones complementarias. `WaypointApplicable` permite la secuencia waypoint->meta final solo cuando el waypoint fue resuelto. `WaypointNotApplicable` permite la ruta directa solo cuando no se aplico estrategia. Por ello un fallo posterior de navegacion al waypoint no puede caer a la rama directa.

## Conservacion de responsabilidades

La memoria selecciona una recomendacion y, opcionalmente, un waypoint. Cada desplazamiento se manda como `NavigateToPose` a Nav2. Nav2 continua siendo responsable de planificacion, costmaps, control, evitacion, recuperaciones y del resultado de cada navegacion. La memoria no publica `cmd_vel` ni sustituye componentes de Nav2.

## Trazabilidad anadida

El resumen final de blackboard registra:

- estrategia recuperada;
- offsets usados;
- si la estrategia fue aplicada;
- waypoint seleccionado;
- resultado Nav2 del waypoint;
- meta final comun;
- resultado Nav2 de la meta final;
- resultado global, exito y etapa/motivo de fallo.

## Limites

Esta fase anade la mecanica de orquestacion y sus smoke tests. No ejecuta campanas experimentales, no altera los escenarios definitivos y no escribe experiencias nuevas en la base de memoria.
