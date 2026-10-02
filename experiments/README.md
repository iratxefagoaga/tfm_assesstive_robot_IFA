# Experimentos de evaluación

## B1 — Recuperación semántica

Script:
`evaluate_semantic_retrieval.py`

Objetivo:
Establecer el baseline de recuperación basado exclusivamente en similitud semántica.

Resultado:
- Precision@5: 0.4133
- Recall@5: 0.5959
- nDCG@5: 0.6239

---

## B2 — Filtrado por usuario

Script:
`evaluate_user_filtering.py`

Objetivo:
Evaluar el efecto de restringir la recuperación a las experiencias asociadas al usuario de la consulta.

Resultado:
- Precision@5: 0.5600
- Recall@5: 0.7943
- nDCG@5: 0.8366

---

## B3 — Context-aware retrieval

Script:
`evaluate_context_aware.py`

Objetivo:
Incorporar información contextual de la consulta al ranking semántico.

Optimización:
`optimize_context_weights.py`

Pesos seleccionados:
- Semántica: 0.90
- Contexto: 0.10

Resultado:
- Precision@5: 0.5600
- Recall@5: 0.7981
- nDCG@5: 0.8441

---

## B4 — Reranking episódico

Script:
`evaluate_episodic_reranking.py`

Objetivo:
Evaluar la incorporación de similitud episódica al proceso de recuperación.

Optimización:
`optimize_episodic_weights.py`

Resultado de la búsqueda de pesos:
- Semántica: 0.90
- Contexto: 0.10
- Episódico: 0.00

Conclusión:
La incorporación del componente episódico no mejora el rendimiento del modelo context-aware en el conjunto experimental utilizado.

---

## Dataset de evaluación

Número de consultas:
15

Número de memorias:
50

Métricas:
- Precision@5
- Recall@5
- nDCG@5

## Fase 4 - Infraestructura de escenarios comparables

Artefactos:

- Escenarios JSON: `experiments/scenarios/`.
- Configuración de condiciones: `experiments/configs/navigation_conditions.json`.
- Ejecutor: `experiments/scripts/run_navigation_scenario.py`.
- Resultados crudos y manifiesto: `experiments/results/phase4/`.

Ejemplo:

`/usr/bin/python3 experiments/scripts/run_navigation_scenario.py --scenario experiments/scenarios/S001_shared_safe_goal.json --condition both --run-id <id_unico>`

El ejecutor usa la misma pose, meta, usuario y contexto en N0/N1. Durante Fase 4, Memory ON registra la estrategia recuperada pero ejecuta el mismo objetivo final del escenario. No se realiza análisis de resultados en esta fase.
