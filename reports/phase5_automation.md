# Fase 5 — Automatización de experimentos

Fecha: 2026-09-22

## Alcance

El automatizador ejecuta escenarios declarados con MEMORY_OFF, MEMORY_ON o ambas condiciones. Recibe scenario, condition y number_of_runs. Con condition=both usa el mismo run_id para las dos condiciones de cada repetición y no sobrescribe artefactos existentes.

## Artefactos

- Configuración: experiments/configs/phase5_automated_navigation.json
- Escenario: experiments/scenarios/S001_shared_safe_goal.json
- Ejecutor: experiments/scripts/run_navigation_scenario.py
- Muestra válida: experiments/results/phase5/acceptance_final/

## Registro y validación

navigation_results.csv contiene timestamp_utc, experiment_id, scenario_id, condition, run_id, contexto, meta, nav2_result, success, time_s, distance_m, replanning_events, memory_ids, scores, strategy y waypoint. run_manifest.csv contiene la configuración declarada, rutas a artefactos, timeout y estado Nav2.

La validación exige identidad, resultado, tiempo, distancia y replanning. En MEMORY_ON exige IDs, scores y estrategia; en MEMORY_OFF exige que los campos de memoria permanezcan vacíos.

## Prueba pequeña real

Comando ejecutado:

/usr/bin/python3 experiments/scripts/run_navigation_scenario.py --scenario experiments/scenarios/S001_shared_safe_goal.json --condition both --number-of-runs 1 --run-prefix phase5_final --config experiments/configs/phase5_automated_navigation.json

Resultados de phase5_final_001:

- MEMORY_OFF: SUCCEEDED, success=true, time_s=2.522, distance_m=0.263, replanning_events=2; campos de memoria vacíos por diseño.
- MEMORY_ON: SUCCEEDED, success=true, time_s=3.654, distance_m=0.266, replanning_events=3; memory_ids=M001|M046|M015|M007|M009, strategy=west, scores registrados.

Se verificaron cabecera, dos filas del consolidado, dos filas del manifiesto y trazabilidad de M001. No se realiza análisis comparativo.

## Cómo ampliar

Para cinco repeticiones emparejadas:

/usr/bin/python3 experiments/scripts/run_navigation_scenario.py --scenario experiments/scenarios/S001_shared_safe_goal.json --condition both --number-of-runs 5 --run-prefix phase5_s001 --config experiments/configs/phase5_automated_navigation.json

El lote genera phase5_s001_001 a phase5_s001_005 para ambas condiciones. Use un prefijo nuevo para cada lote. Para una sola condición, use condition=memory_off o condition=memory_on.

No se han ejecutado lotes masivos ni se han generado resultados artificiales.