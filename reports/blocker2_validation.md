# Validación — Blocker 2: escenarios comparables

Fecha: 2026-09-29  
Alcance: smoke tests de geometría, configuración y Nav2. No se ejecutó una campaña N0/N1, no se modificaron B1--B4, el mundo ni el mapa, y no se sobrescribieron resultados de experimentos.

## Resultado

**BLOCKER 2: NO RESUELTO.**

Se han diseñado y declarado escenarios comparables, y la política de waypoint ya se transmite desde cada escenario al launch de N1. Sin embargo, ninguno se clasifica como VALID porque no se pudo obtener una comprobación `ComputePathToPose` aislada y reproducible del stack real después de evitar interferencias de `/clock`. La evidencia estática no sustituye ese requisito.

## Cambios realizados

- Creado `reports/blocker2_scenario_design.md`.
- Creados, sin modificar `S001_shared_safe_goal.json`:
  - `experiments/scenarios/S002_control_direct_u02.json`
  - `experiments/scenarios/S003_table_clearance_u01.json`
  - `experiments/scenarios/S004_table_personalization_u02.json`
  - `experiments/scenarios/S005_table_alternative_u03.json`
- Cambio mínimo en `experiments/scripts/run_navigation_scenario.py`: para N1 serializa el objeto `strategy_waypoint_offsets` del escenario como argumento del launch y lo registra en el manifiesto. No cambia retrieval, recommendation, Nav2, mapa ni comportamiento de Blocker 1.

## Evidencia estática

El PGM fue comprobado contra la geometría SDF y el footprint configurado (x +/-0,36 m; y +/-0,34 m). Las celdas candidatas son libres y no solapan el footprint estático:

| Elemento | Coordenadas | Celda PGM libre | Footprint estático libre | Distancia mínima a ocupación |
|---|---:|---|---|---:|
| S002 inicio | (2,00, -3,00) | sí | sí | 0,72 m |
| S002 meta | (2,50, -3,00) | sí | sí | 0,60 m |
| S003/S004/S005 inicio | (-4,00, 0,80) | sí | sí | 1,85 m |
| S003/S004/S005 meta | (2,50, 0,00) | sí | sí | 1,05 m |
| west | (-2,00, -0,70) | sí | sí | 1,12 m |
| alternative | (-2,00, 3,00) | sí | sí | >1,0 m |

La mesa ocupa aproximadamente x [-1,80, -0,55], y [0,45, 1,20]. La recta desde (-4,00, 0,80) a (2,50, 0,00) la atraviesa; por ello west y alternative representan dos rutas geométricas distintas alrededor de la mesa. Nav2 conserva la autoridad para aceptar o rechazar esos segmentos.

La sintaxis fue verificada con:

```text
/usr/bin/python3 -m py_compile experiments/scripts/run_navigation_scenario.py
/usr/bin/python3 <carga de JSON + launch_arguments>
```

Resultado: los cuatro JSON nuevos se cargan correctamente y N1 recibe exactamente:

| Escenario | Argumento `strategy_waypoint_offsets` |
|---|---|
| S002 | `direct:0:0,central:0:0` |
| S003 | `direct:0:0,west:-4.5:-0.7,alternative:-4.5:3` |
| S004 | `direct:0:0,central:0:0,west:-4.5:-0.7,alternative:-4.5:3` |
| S005 | `direct:0:0,west:-4.5:-0.7,alternative:-4.5:3` |

Para la meta común (2,50; 0,00), los offsets generan west = (-2,00; -0,70) y alternative = (-2,00; 3,00), sin hardcodear una memoria o una ejecución.

## Resultado por escenario

| Escenario | Estado | Evidencia | Motivo |
|---|---|---|---|
| S001_shared_safe_goal | PARTIAL | Escenario histórico preservado; inicio/meta libres por PGM. | No se revalidó ComputePath en un stack aislado. No es control tras Blocker 1 porque U01 puede aplicar west. |
| S002_control_direct_u02 | PARTIAL | JSON/argumentos correctos; puntos libres y fuera del footprint. N0/N1 comparten meta (2,50; -3,00). | Falta `ComputePathToPose` aislado y smoke Nav2 actual. |
| S003_table_clearance_u01 | PARTIAL | Inicio/meta/west libres; línea directa interseca mesa; política N1 serializada correctamente. Un smoke N0 temporal terminó `ABORTED` tras 48,828 s, 1,259 m y 23 eventos de replanning. | Ese intento coexistió con varios Gazebo/Nav2 temporales y generó saltos `TF_OLD_DATA`/clock; no es evidencia limpia para invalidar la geometría ni para validarla. Falta path aislado y prueba waypoint → meta. |
| S004_table_personalization_u02 | PARTIAL | Misma pose/meta/obstáculo de S003; contexto U02 y estrategia esperada direct independientes; argumentos correctos. | Falta `ComputePathToPose` aislado. La comparabilidad está declarada, no demostrada en ejecución real. |
| S005_table_alternative_u03 | PARTIAL | Inicio/meta/waypoint norte libres; offset `alternative` produce (-2,00; 3,00); M037 es experiencia episódica relevante. | Falta `ComputePathToPose` para inicio → alternative y alternative → meta, y smoke N1 real. |

## Pruebas reales y problema encontrado

Se inició temporalmente Gazebo, bridge, robot, scan-frame fixer y Nav2 para ejecutar un smoke N0 de S003 y acciones `ComputePathToPose`. Durante los intentos coexistieron más de un proceso temporal de Gazebo, lo cual provocó reinicios de simulación y mensajes repetidos de AMCL:

```text
TF_OLD_DATA ignoring data from the past
Detected jump back in time. Clearing TF buffer.
```

El CSV temporal `/tmp/blocker2_s003_n0_smoke.csv` contiene una ejecución real de N0 con:

```text
nav2_result=ABORTED
success=false
time_s=48.828
distance_m=1.259
replanning_events=23
```

No se guardó en `experiments/results/` y no se usa como resultado definitivo. Los procesos temporales identificados se detuvieron para no dejar interferencia en futuros tests.

## Condiciones comparables declaradas

Para cada par N0/N1 quedan constantes robot, SDF, PGM, obstáculos estáticos, Nav2, sensores, pose inicial, meta final, usuario/contexto del escenario y run_id. N1 recibe además query/retrieval/recommendation y, sólo ante estrategia con offset distinto de cero, el waypoint de memoria. N0 no recibe ningún parámetro de memoria.

S003 y S004 comparten exactamente la geometría de mesa para contrastar U01 (west/clearance esperado) frente a U02 (direct/minimizar desvíos esperado). S005 comparte la misma geometría para aislar una experiencia episódica de U03 que expresa `alternative`.

## Tests exactos pendientes

1. Lanzar **un único** stack Gazebo/Nav2, sin otro `gz sim`, confirmar `/clock` monótono y lifecycle active.
2. Ejecutar y conservar la respuesta de `ComputePathToPose` para S002 inicio→meta.
3. Ejecutar `ComputePathToPose` para S003/S004 inicio→west y west→meta.
4. Ejecutar `ComputePathToPose` para S005 inicio→alternative y alternative→meta.
5. Ejecutar un smoke N0 limpio de S003 y un smoke N1 limpio que recupere una estrategia aplicable, llegue al waypoint y después a la misma meta final, conservando CSV/log temporal.
6. Sólo después de esos tests, cambiar los estados PARTIAL a VALID. No iniciar repeticiones ni campaña definitiva como parte de la validación.

## Limitación científica preservada

El mundo carece de segmentación física de habitaciones. Los nombres de destino son contexto existente del dataset, no una afirmación de que el SDF modele cocina/dormitorio/baño. Los escenarios permiten probar una decisión de ruta contextual/personalizada alrededor de la mesa; no permiten concluir semantic grounding de habitaciones ni comportamiento ante obstáculos dinámicos.
