# Fase 3 - Memory ON

Fecha de cierre: 2026-09-22.

## Objetivo y alcance

Se validó una ejecución reproducible sin cambiar PostgreSQL, pgvector, el modelo Qwen/Qwen3-Embedding-0.6B, Nav2 ni el VLA:

query -> /memory/query -> retrieval -> /memory/navigation_recommendation -> navigation_memory_adapter -> /navigate_to_pose -> resultado.

## Interfaces y grafo verificados

- /memory/query: wheelchair_interfaces/srv/MemoryQuery.
- /memory/navigation_recommendation: wheelchair_interfaces/srv/NavigationRecommendation.
- /navigate_to_pose: nav2_msgs/action/NavigateToPose.
- Nodos presentes: memory_node, navigation_memory_node, map_server, amcl, planner_server, controller_server y bt_navigator.
- El gestor de ciclo de vida informó todos los nodos Nav2 como active.

## Correcciones mínimas de estabilidad

- Se añadió el lanzador memory_on.launch.py.
- El adaptador registra query, user, location, task, goal, memory IDs, scores semantic/context/final, strategy, waypoint y resultado Nav2 en CSV.
- El adaptador espera a que bt_navigator esté active antes de enviar el goal.
- La primera consulta usa Qwen + PostgreSQL + pgvector; la consulta idéntica requerida por la recomendación reutiliza el resultado sólo en memoria del proceso.
- El modelo se calienta antes del arranque de Nav2. Esto evita que la carga inicial de embeddings interrumpa heartbeats de Nav2. Los parámetros de Nav2 no se modificaron.

## Prueba integrada real exitosa

Consulta: U01 quiere ir del salon al dormitorio y necesita una ruta con espacio lateral.

| Campo | Resultado |
|---|---|
| user / location / task / goal | U01 / salon / navegacion / dormitorio |
| memory IDs | M001, M046, M015, M007, M009 |
| memoria seleccionada | M001 |
| semantic / context / final | 0.7510414032 / 1.0000000000 / 0.7759372629 |
| strategy | west |
| waypoint ejecutado | (2.500, -3.000), frame map |
| Nav2 | SUCCEEDED |
| CSV | 2026-09-22T14:28:39.529587+00:00 |

La traza muestra: recuperación M001 -> recomendación west -> goal aceptado -> resultado SUCCEEDED. El CSV persistido es experiments/results/memory_on_navigation_results.csv.

## Intentos previos y diagnóstico

- El waypoint (1.500, -3.000) produjo ABORTED por colisión detectada por el controlador; no se usa como evidencia de éxito.
- Un objetivo fue rechazado durante un reinicio del ciclo de vida provocado por la carga inicial del modelo.
- Ambos problemas se resolvieron separando el calentamiento de embeddings del arranque de Nav2 y esperando explícitamente el estado active.

## Estado

- Retrieval y scores: FUNCIONA.
- Recommendation M001 -> west: FUNCIONA.
- Navigation adapter y persistencia: FUNCIONAN.
- Nav2 NavigateToPose bajo Memory ON: FUNCIONA.
- Flujo extremo a extremo Memory ON: FUNCIONA.
- Efecto experimental de una ruta físicamente oeste frente al baseline: NO PROBADO. El endpoint exitoso reutiliza el objetivo seguro del baseline para validar la integración; un waypoint oeste seguro para el footprint debe validarse como experimento posterior.
