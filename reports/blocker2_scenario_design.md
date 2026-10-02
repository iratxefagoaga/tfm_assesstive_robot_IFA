# Diseño de escenarios — Blocker 2

Fecha: 2026-09-29  
Alcance: definición declarativa y validación geométrica de escenarios comparables N0/N1. No se han modificado mundo, robot, mapa, Nav2, B1--B4 ni los resultados históricos.

## 1. Análisis del entorno

### Fuentes inspeccionadas

- Mundo: `wheelchair_gazebo/models/apartment/model.sdf` y `worlds/apartment.world`.
- Mapa Nav2: `wheelchair_navigation/maps/apartment.pgm`, 240 x 200 celdas, resolución 0,05 m, origen (-6,0; -5,0).
- Configuración Nav2: footprint rectangular x = +/-0,36 m, y = +/-0,34 m; inflation radius = 0,70 m; costmaps con `/scan_fixed`.
- Dataset: las 50 filas de `experiments/data/memory_seed.csv` y `experiments/data/retrieval_queries.csv`.

El mundo consta de un rectángulo navegable de aproximadamente 12 x 10 m, cerrado por paredes perimetrales. No incluye paredes ni puertas internas. Los obstáculos estáticos que coinciden con el PGM son:

| Objeto | Huella aproximada (m) |
|---|---|
| Mesa | x [-1,80, -0,55], y [0,45, 1,20] |
| Sofá | x [1,20, 2,85], y [1,40, 2,20] |
| Cama | x [2,40, 4,20], y [-2,40, -1,00] |
| Armario | x [-3,65, -2,35], y [-2,25, -1,75] |
| Planta | centro aproximado (-3,80, 3,00), radio 0,30 m |

La mesa es el único obstáculo que permite operacionalizar de modo controlado dos itinerarios alrededor de una misma obstrucción entre el oeste y el este. El paso no es un “pasillo” arquitectónico: es una zona abierta. Por rigor, el informe se refiere a rutas norte/sur alrededor de la mesa, no a habitaciones o pasillos inexistentes.

Las etiquetas `salon`, `cocina`, `dormitorio` y `baño` proceden del dataset y son contexto semántico del retrieval; el mundo actual no asigna esas etiquetas a regiones geométricas. Esto limita cualquier conclusión sobre grounding semántico de habitaciones, pero no impide evaluar la intervención de estrategia en la misma geometría física.

### Poses y seguridad estática

La comprobación de PGM usó ocupación < 128 y el rectángulo del footprint, sin sustituir a los costmaps ni a Nav2. Los siguientes puntos son celdas libres y no solapan el footprint estático:

| Punto | Coordenadas | Distancia estática mínima a ocupación |
|---|---:|---:|
| inicio de mesa | (-4,00, 0,80) | 1,85 m |
| meta este | (2,50, 0,00) | 1,05 m |
| waypoint sur-oeste | (-2,00, -0,70) | 1,12 m |
| waypoint norte-oeste | (-2,00, 3,00) | > 1,0 m |
| S001 inicio | (2,00, -3,00) | 0,72 m |
| S001 meta | (2,50, -3,00) | 0,60 m |

La distancia estática no equivale a clearance durante la ejecución: la aceptación final de cada waypoint queda condicionada a `ComputePathToPose`, costmaps y, si es necesario, un smoke test `NavigateToPose`.

## 2. Memorias relevantes

Las memorias utilizables con la geometría actual son las que contienen acciones explícitas de navegación alrededor de la mesa:

| Usuario | Memorias relevantes | Preferencia/experiencia representada |
|---|---|---|
| U01 | M002, M013, M015 | ruta oeste ante mesa o espacio reducido; M002/M015 son episódicas |
| U02 | M017 | ruta directa y minimizar desvíos cuando está despejada |
| U03 | M032, M037, M040 | evitar mesa; estrategia west o alternativa; M032/M037 son episódicas |

M001, M009, M016, M031 y otras memorias son también semánticamente próximas, pero no se usan como único ground truth: `expected_relevant_memories` expresa una lista relevante, no fuerza el ranking ni la recomendación. Las memorias que describen sofá temporal, silla temporal, velocidad o aproximación a objetos no se operacionalizan, porque el mundo no contiene esos cambios dinámicos ni la interfaz actual aplica esas acciones a Nav2.

## 3. Diseño experimental propuesto

Se proponen cuatro escenarios nuevos, además de preservar S001 como smoke histórico. Cada ejecución N0/N1 comparte literalmente pose inicial, meta final, mundo, mapa, robot, sensores y configuración Nav2. En N0 el request llega directamente a Nav2. En N1 la única intervención adicional es retrieval/recommendation y, cuando la estrategia tiene offset no nulo, el waypoint ejecutado por Nav2.

| Escenario | Categoría | H | Geometría y decisión esperada |
|---|---|---|---|
| S002_control_direct_u02 | Control | H1 | Trayecto corto ya usado en S001. U02 pide ruta directa. La estrategia esperada es `direct`; no debe introducirse waypoint. Comprueba ausencia de intervención innecesaria. |
| S003_table_clearance_u01 | Clearance / ruta alternativa | H1, H3 | De (-4,00, 0,80) a (2,50, 0,00), la recta corta intersecta la mesa. La ruta `west` se operacionaliza mediante (-2,00, -0,70), al sur y oeste de la mesa, con más separación que intentar cruzarla. |
| S004_table_personalization_u02 | Personalización comparable | H1 | Misma geometría, pose y meta que S003, con U02 y una solicitud de mínimo desvío. Permite observar una recomendación distinta sin cambiar Nav2 ni el entorno. La estrategia esperada es `direct`; no debe inducir waypoint. |
| S005_table_alternative_u03 | Episódico / rutas alternativas | H3, H1 | Misma pose y meta que S003, pero U03 pide evitar la mesa para el contexto `baño`. `alternative` se operacionaliza como waypoint (-2,00, 3,00), norte y oeste de la mesa. M037 contiene acción alternativa y resultado de llegada; N1 debe decidir independientemente si la recupera. |

S001 no se modifica ni se reclasifica como escenario final: conserva su función de smoke histórico. Tras Blocker 1, su query U01 puede recuperar `west`, por lo que no es un control de no-intervención.

## 4. Formalización y offsets

Los nuevos JSON contienen al menos los campos requeridos y campos explícitos de trazabilidad:

- `expected_relevant_memories`, `expected_preference` y `expected_strategy` son ground truth para análisis posterior. No se pasan a MemoryQuery, NavigationRecommendation ni Nav2.
- `available_strategies` describe las opciones que la política declarativa permite para esa geometría.
- `strategy_waypoint_offsets` se expresa relativo a la meta, tal como exige el adapter de Blocker 1. Para la meta (2,50; 0,00): `west:-4.5:-0.7` genera (-2,00; -0,70), y `alternative:-4.5:3.0` genera (-2,00; 3,00). `direct:0:0` no genera waypoint.
- El offset no está asociado a un ID de memoria; es una política declarativa por geometría de escenario.

## 5. Variables y métricas

Controladas: robot, mundo, PGM, pose, meta final, obstáculos estáticos, sensores, Nav2, configuración del lanzamiento y run_id dentro de cada par N0/N1.

Variable experimental: acceso a memoria y, si la recomendación recuperada dispone de offset aplicable, el waypoint de estrategia antes de la misma meta final.

Las métricas ya registradas que se podrán comparar son éxito, tiempo, distancia, replanning, Nav2 result, estrategia, memoria y resultados de waypoint/meta. Para H1/H3 se requerirá además, en el blocker de métricas, preference/strategy match y clearance o equivalente calculado sobre trayectoria. Este diseño no presupone que Memory ON obtenga mejores valores.

## 6. Riesgos y confounders

1. Nav2 puede escoger por sí mismo una ruta alrededor de la mesa en N0; el efecto de N1 será una decisión trazable de waypoint, no una garantía de superioridad.
2. Los nombres de destino del dataset no están anclados a habitaciones físicas del mundo actual. Las conclusiones deben limitarse a contexto de retrieval y estrategia geométrica, no a conocimiento semántico del plano.
3. El mapa contiene obstáculos estáticos; no permite validar memorias sobre silla/sofá temporal, espera o velocidad reducida sin introducir cambios de mundo, que quedan fuera de este blocker.
4. Un waypoint libre en PGM puede ser rechazado por costmaps o Nav2. Cualquier rechazo se conservará como resultado explícito y el escenario no se declarará VALID sin evidencia de path.
5. S003/S004/S005 comparten geometría deliberadamente para aislar preferencia y contexto. Esto no sustituye a escenarios futuros con otros obstáculos si el mundo se amplía mediante una decisión de diseño independiente.

## 7. Criterio de aceptación

Un escenario sólo será VALID tras comprobar en el stack real: pose y meta navegables, waypoint si aplica dentro de mapa y libre para footprint, `ComputePathToPose` a los segmentos pertinentes y preservación de la misma meta final N0/N1. Los smoke tests no son la campaña experimental definitiva ni producen repetición estadística.
