# Diseño de resolución — Blocker 1

Fecha: 2026-09-28  
Alcance: exclusivamente que N1 ejecute mediante Nav2 una intervención de memoria trazable. No se modifican B1–B4, escenarios finales, mundo, robot, mapa, parámetros Nav2 ni la lógica de recuperación.

## Comportamiento actual auditado

- navigation_memory_node recibe NavigationRecommendation, consulta internamente /memory/query y selecciona la primera memoria, ya ordenada por final_score. Interpreta texto de action con reglas reproducibles: "ruta oeste" → west; "ruta central" → central; "alternativa/desvío" → alternative; si no, direct.
- NavigationRecommendation no incluye un waypoint. Devuelve una estrategia de alto nivel, memoria fuente, razón, flags de preferencia/evitación y scores.
- No existe un memory_on_runner independiente: el ejecutable navigation_adapter de wheelchair_memory realiza el rol de runner/adapter de N1.
- navigation_adapter llama primero a MemoryQuery y después a NavigationRecommendation; registra IDs y scores y envía un único NavigateToPose.
- use_strategy_waypoint es un parámetro booleano del adapter. Si es false, select_waypoint ignora la estrategia y devuelve goal_x/goal_y. Si es true, sólo west devuelve west_waypoint_x/y; central, alternative y direct devuelven direct_waypoint_x/y, por defecto la meta final.
- memory_on_experiment.launch.py fuerza use_strategy_waypoint=false. Por eso N1 registra west, pero manda exactamente la meta final común, igual que N0.

## Problema experimental

N1 tiene acceso a memoria pero no ejecuta una decisión que altere la navegación. No puede atribuirse una trayectoria, éxito, fallo o cumplimiento de preferencia a la recomendación. El mapeo anterior tampoco es general: usa coordenadas absolutas para west y no define intervenciones para central/alternative.

## Diseño propuesto

1. Mantener NavigationRecommendation sin cambios: estrategia es una recomendación de alto nivel; no se incorpora geometría de mapa a la interfaz de memoria.
2. El adapter acepta una lista declarativa strategy_waypoint_offsets con entradas strategy:dx:dy. Un offset se suma a la meta final en frame map. La política queda configurable por launch/configuración y no depende de M001, una query concreta ni coordenadas absolutas de S001.
3. Si la estrategia recuperada tiene un offset configurado distinto de (0,0), el adapter marca strategy_applied=true y envía un primer NavigateToPose al waypoint resultante.
4. Sólo si Nav2 termina el waypoint con SUCCEEDED, el adapter envía un segundo NavigateToPose a la meta final común goal_x/goal_y. N0 sigue enviando únicamente esa misma meta final y no consulta memoria.
5. Si no existe waypoint aplicable, strategy_applied=false y N1 envía directamente la meta final, registrando waypoint_nav2_result=NOT_APPLIED. Si Nav2 rechaza, aborta o cancela el waypoint, el adapter termina explícitamente con final_goal_nav2_result=NOT_SENT; no oculta el fallo ni continúa hacia la meta.
6. La seguridad permanece en Nav2: la memoria sólo selecciona una preferencia/waypoint. Planner, controller, costmaps, recovery, velocity smoother y Gazebo deciden si el waypoint es alcanzable y ejecutan el movimiento.

## Archivos a modificar

- wheelchair_memory/wheelchair_memory/navigation_adapter.py: mapeo declarativo, máquina de dos goals Nav2 y trazabilidad.
- wheelchair_bringup/launch/memory_on_experiment.launch.py: habilitar la política y exponer el parámetro declarativo.
- wheelchair_bringup/scripts/baseline_runner.py: añadir campos vacíos al esquema común, únicamente por compatibilidad CSV.
- experiments/scripts/run_navigation_scenario.py: conservar los nuevos campos en el CSV consolidado y validarlos para N1.
- reports/implementation_log.md: registro de esta corrección.

## Comportamiento esperado

Para una estrategia configurada, por ejemplo west:
current pose → Nav2 waypoint derivado de west → Nav2 meta final común.

El resultado contiene strategy/retrieved_strategy, strategy_applied, waypoint seleccionado, waypoint_nav2_result, final_goal_x/y y final_goal_nav2_result. Un fallo de waypoint queda visible y no se presenta como llegada a la meta.

## Riesgos

- Un offset declarado puede producir una celda ocupada o un pasillo incompatible con footprint/costmaps. Es un resultado explícito de Nav2, no se sustituye por movimiento directo.
- La estrategia textual no contiene por sí misma geometría universal; por ello el mapeo debe estar declarado por configuración y ser validado por escenarios posteriores, no inferido ni entrenado para favorecer N1.
- La secuencia añade un segundo goal sólo después de un waypoint exitoso; tiempo/distancia/replanning agregados reflejarán toda la navegación N1.

## Preservación de N0 y de Nav2

N0 no inicia memoria, no consulta servicios y conserva una única meta final. La única diferencia N1 es el acceso a memoria y, si hay una estrategia configurada aplicable, el waypoint de alto nivel. Nav2 sigue planificando ambos segmentos y conserva el derecho de abortar el waypoint.
