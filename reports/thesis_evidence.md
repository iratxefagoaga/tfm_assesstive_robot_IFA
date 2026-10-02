# Evidencia técnica y trazabilidad para el TFM

Fecha: 2026-09-28

## Propósito y criterio de lectura

Este documento relaciona el objetivo científico con las hipótesis, la implementación, los experimentos, las métricas y los resultados que existen en el repositorio. Se distingue entre:

- evidencia de implementación: prueba que un componente, interfaz o cadena técnica se ejecutó;
- evidencia experimental descriptiva: mediciones registradas bajo un protocolo;
- evidencia inferencial: prueba estadística aplicada a las observaciones disponibles.

Una prueba funcional no se presenta como evidencia de superioridad. Los resultados de recuperación (B1–B4) y de navegación (N0/N1) no se mezclan, porque miden objetos distintos.

Fuentes revisadas: SPEC.md; docs/00_context.md a docs/09_codex_workflow.md; todos los informes de reports/ existentes al 2026-09-28; y todos los archivos de experiments/results/, incluidos CSV crudos, consolidados, manifiestos, logs y tablas derivadas.

## Trazabilidad del objetivo general

**Objetivo general.** Diseñar, implementar y evaluar una memoria contextual, personalizada y longitudinal integrada en navegación asistiva simulada, para estudiar su efecto frente a un sistema equivalente sin memoria.

| Objetivo específico | Implementación y evidencia técnica | Experimento o artefacto | Métrica disponible | Resultado existente | Alcance de la evidencia |
|---|---|---|---|---|---|
| Representar experiencias | PostgreSQL/pgvector con usuario, contexto, observación, acción, resultado y preferencia | experiments/data/memory_seed.csv y auditoría B1–B4 | Recuento y dimensión de embeddings | 50 memorias M001–M050; 50 embeddings semánticos y 50 episódicos de dimensión 1024 | Infraestructura y datos verificados; no mide por sí misma efecto de navegación |
| Almacenamiento y embeddings | MemoryService, PostgreSQL, pgvector y Qwen/Qwen3-Embedding-0.6B | Auditoría de retrieval | Dimensión y reproducción de resultados | Base efectiva consultada y B1–B4 reproducidos | Evidencia técnica y de reproducibilidad condicionada al estado de la base |
| Recuperación semántica | Ranking top-5 por similitud semántica | B1 | Precision@5, Recall@5, nDCG@5 | 0.4133, 0.5959, 0.6239 | Medición reproducida sobre 15 consultas |
| Personalización por usuario | Filtrado por user_id | B2 | Precision@5, Recall@5, nDCG@5 | 0.5600, 0.7943, 0.8366 | Medición reproducida sobre el mismo conjunto |
| Ranking contextual | Score 0.90 semántico + 0.10 contextual | B3 | Precision@5, Recall@5, nDCG@5 | 0.5600, 0.7981, 0.8441 | Medición reproducida; sin contraste estadístico entre B1 y B3 |
| Información episódica | Embeddings episódicos y reranking histórico | B4 | Precision@5, Recall@5, nDCG@5 | 0.5333, 0.7625, 0.7862 | Medición reproducida, con limitación metodológica |
| Recomendación trazable | /memory/query, /memory/navigation_recommendation y navigation_memory_adapter | Fase 3 Memory ON | IDs, scores, estrategia, waypoint, resultado Nav2 | M001 seleccionada; estrategia west; Nav2 SUCCEEDED | Cadena funcional validada |
| Integración segura con Nav2 | Memoria como recomendación; Nav2 conserva planificación, control y evitación | Fases 2 y 3 | Estado Nav2 y NavigateToPose | Baseline y Memory ON alcanzaron SUCCEEDED en pruebas de aceptación | Integración técnica, no comparación de rendimiento |
| Comparar MEMORY OFF y MEMORY ON | Escenario JSON común, configuración común, lanzadores N0/N1 y automatizador | Fases 4 y 5; protocol_20260928 | Éxito, tiempo, distancia y replanning | Cinco repeticiones solicitadas y artefactos preservados | Comparabilidad declarada y mediciones iniciales; muestra insuficiente para conclusión general |
| Evaluar cuantitativamente | Script de tablas y análisis preservando datos fuente | reports/statistical_analysis.md | Media, mediana, DE, IC, éxito y McNemar | Estadísticos descriptivos e inferencia binaria limitada | No apoya conclusión de superioridad o empeoramiento |

## Hipótesis H1

**Hipótesis.** El sistema de navegación con memoria contextual y personalizada producirá decisiones de navegación más adaptadas al usuario que el baseline sin memoria.

### Objetivo → implementación → experimento → métrica → resultado

| Elemento | Evidencia existente |
|---|---|
| Objetivo relacionado | Objetivos específicos 8 a 12: recomendar, integrar con Nav2, ejecutar simulación, comparar N0/N1 y cuantificar el efecto |
| Implementación | memory_node expone /memory/query; navigation_memory_node expone /memory/navigation_recommendation; el adaptador registra consulta, contexto, IDs, scores, estrategia, waypoint y resultado Nav2. N0 no inicia nodos de memoria; N1 sí los inicia. |
| Experimentos que la evalúan | Infraestructura Fase 4, muestra Fase 5 y, como evidencia principal disponible, protocolo emparejado protocol_20260928 sobre S001_shared_safe_goal. |
| Controles experimentales | Misma pose inicial (2.0, -3.0, 0.0), misma meta (2.5, -3.0), usuario, ubicación, tarea, mundo, mapa, robot, sensores y parámetros Nav2 declarados comunes. El mismo run_id se usa para las dos condiciones de cada repetición. |
| Métricas usadas | success, nav2_result, time_s, distance_m y replanning_events. La documentación también contempla cumplimiento de preferencia y coincidencia de estrategia, pero no hay una métrica observada de cumplimiento geométrico de la preferencia en el lote. |
| Resultados técnicos | En Fase 3, la consulta de U01/salón/navegación/dormitorio recuperó M001 como primera memoria y produjo west, con avoid_obstacle=true y prefer_clearance=true; el objetivo ejecutado (2.5, -3.0) terminó SUCCEEDED. |
| Resultados del protocolo | MEMORY_OFF: 1/5 éxitos; tiempo medio 1.893 s; distancia media 0.104 m; replanning medio 1.000. MEMORY_ON: 4/4 registros con CSV exitosos; tiempo medio 3.404 s; distancia media 0.262 m; replanning medio 2.500. El quinto registro ON quedó como NO_RESULT por timeout y pérdida de heartbeat de planner_server; no se imputó. |
| Comparación inferencial existente | Cuatro parejas completas: tres OFF fallido/ON exitoso, una con éxito en ambas. McNemar exacto bilateral: p=0.250. Para métricas cuantitativas, sólo una pareja tuvo éxito en ambas condiciones; no se calculó prueba ni intervalo emparejado. |

### Limitaciones y estado de evaluación de H1

**Estado: no suficientemente evaluada para confirmarla o rechazarla.**

- Sólo se ejecutó un escenario y se solicitaron cinco repeticiones; existe una ejecución ON sin CSV crudo.
- Las métricas observadas no incluyen una medición directa de adaptación al usuario, cumplimiento de preferencia, clearance lateral, desviación de ruta ni uso efectivo de una ruta oeste.
- En Fase 4 y en la prueba integrada de Fase 3, Memory ON registra west, pero ejecuta el mismo endpoint seguro que el baseline. Esto valida la trazabilidad técnica, no una trayectoria físicamente preferente frente a N0.
- La diferencia de tasa de éxito observada no alcanza significación en la prueba disponible (McNemar p=0.250). Las diferencias de tiempo, distancia y replanning son descriptivas; no se sometieron a contraste inferencial.
- Hay inestabilidad de Nav2 documentada: el registro ON 004 presenta pérdida de heartbeat del planificador. Debe tratarse como riesgo de robustez de la plataforma, no atribuirse a la memoria.
- Las ejecuciones de aceptación anteriores sirven para verificar infraestructura, pero no se agregan al protocolo para evitar mezclar lotes.

Por tanto, existen resultados de navegación registrados y una cadena Memory ON operativa, pero no evidencia experimental suficiente para afirmar que H1 se cumple.

## Hipótesis H2

**Hipótesis.** Incorporar contexto de usuario, ubicación, tarea y objetivo mejorará la relevancia de las memorias recuperadas frente a recuperación exclusivamente semántica.

### Objetivo → implementación → experimento → métrica → resultado

| Elemento | Evidencia existente |
|---|---|
| Objetivo relacionado | Objetivos específicos 4 a 6: recuperación semántica, incorporación de contexto y ranking contextual |
| Implementación | B1 hace top-5 global por similitud semántica. B2 añade filtrado por usuario. B3 combina 0.90 de similitud semántica y 0.10 de relevancia contextual extraída de usuario, ubicación, tarea y objetivo. |
| Experimentos que la evalúan | B1, B2 y B3, ejecutados sobre 50 memorias y 15 consultas Q001–Q015 con relevancia binaria declarada en experiments/data/retrieval_queries.csv. |
| Métricas usadas | Precision@5, Recall@5 y nDCG@5. MRR está documentada como métrica prevista, pero no se calcula en los scripts ni en los CSV existentes. |
| Resultados existentes | B1: P@5=0.4133, R@5=0.5959, nDCG@5=0.6239. B2: 0.5600, 0.7943, 0.8366. B3: 0.5600, 0.7981, 0.8441. La sensibilidad B3 contiene cinco configuraciones y su máximo registrado es 0.90/0.10 con nDCG@5=0.8441. |
| Reproducibilidad | En 2026-09-28 B1–B4 se ejecutaron contra la base efectiva y los CSV temporales fueron idénticos byte a byte a los históricos. PostgreSQL/pgvector, 50 filas y embeddings de 1024 dimensiones se verificaron durante la auditoría. |

### Limitaciones y estado de evaluación de H2

**Estado: evidencia cuantitativa parcial; no suficientemente evaluada para afirmar una mejora estadísticamente demostrada.**

- Las tres métricas observadas son diferentes entre B1 y B3, pero no se calculó intervalo, tamaño de efecto ni prueba estadística para la comparación de retrieval.
- Sólo hay 15 consultas y la relevancia es binaria. No se documenta validación independiente del etiquetado, ni división de entrenamiento/prueba.
- B2 y B3 cambian más de un elemento respecto a B1 si se comparan directamente: B2 incorpora el filtrado de usuario y B3 conserva esa personalización además del score contextual. La contribución aislada de cada campo contextual no está medida.
- El estado efectivo de PostgreSQL no está versionado mediante una huella o carga automática de semilla. La reproducción se verificó sobre la base auditada, no como reproducción independiente desde una base vacía.
- Rutas, credenciales y parámetros están codificados; la inferencia CPU es costosa.
- MRR, porcentaje de recuperación contextual y análisis de relevancia parcial están previstos pero no se han calculado.

Los valores B1/B2/B3 son evidencia observada de rendimiento de recuperación en ese conjunto fijo; no justifican por sí solos una conclusión estadística de mejora general de H2.

## Hipótesis H3

**Hipótesis.** La información episódica de experiencias anteriores permitirá seleccionar estrategias de navegación coherentes con las preferencias del usuario.

### Objetivo → implementación → experimento → métrica → resultado

| Elemento | Evidencia existente |
|---|---|
| Objetivo relacionado | Objetivos específicos 7 y 8: incorporar información episódica y convertir memorias en recomendaciones |
| Implementación | Las memorias incluyen observación, acción, resultado y preferencia; la base contiene episodic_embedding. B4 aplica un reranking histórico de 0.70 semántica + 0.30 episódica y filtra por usuario cuando procede. NavigationRecommendation hace trazable memoria fuente, preferencia y estrategia. |
| Experimentos que la evalúan | B4 evalúa retrieval episódico sobre las mismas 15 consultas. Fase 3 y el protocolo N1 verifican que la recomendación derivada de M001 es west. |
| Métricas usadas | B4: Precision@5, Recall@5, nDCG@5. Navegación: se registra strategy, memory IDs y scores. Las métricas de personalización previstas —preference match, strategy match, consistencia y cumplimiento de preferencia— no tienen una serie experimental calculada. |
| Resultados existentes | B4: P@5=0.5333, R@5=0.7625, nDCG@5=0.7862. Su CSV de sensibilidad contiene 66 configuraciones; la mejor fila histórica tiene 0.90 semántica, 0.10 contexto y 0.00 episódica, con nDCG@5=0.8441. En Fase 3 y en los cuatro N1 con CSV del protocolo, M001 fue la fuente seleccionada y la estrategia registrada fue west. |

### Limitaciones y estado de evaluación de H3

**Estado: no suficientemente evaluada.**

- B4 mide relevancia de retrieval, no la coherencia entre preferencia del usuario y estrategia de navegación ni el cumplimiento de la preferencia durante una trayectoria.
- El evaluador B4 histórico no incorpora score contextual, pese a que la documentación lo describe como contextual y episódico. Además, sus pesos 0.70/0.30 no corresponden a la mejor fila del análisis de sensibilidad. La auditoría preservó ese experimento; no debe reinterpretarse como una ablación completa contexto+episódico.
- La mejor configuración registrada en la sensibilidad B4 asigna peso episódico cero. Este dato no confirma que el componente episódico aporte valor bajo esa métrica y conjunto; tampoco permite una conclusión causal sin contraste estadístico y una metodología B4 alineada.
- La estrategia west fue registrada, pero el waypoint ejecutado permaneció en la meta segura compartida. No se midieron clearance, colisión evitada, coincidencia de estrategia esperada ni preferencia seguida.
- No existe evaluación longitudinal de añadir una experiencia nueva, recuperarla posteriormente y demostrar cambio reproducible de estrategia por usuario.
- La muestra de navegación sólo usa U01 y un escenario, por lo que no permite evaluar consistencia entre usuarios o preferencias.

H3 cuenta con evidencia de representación episódica, recuperación y trazabilidad de una estrategia, pero no con una evaluación experimental suficiente de coherencia de preferencias.

## Inventario de resultados que pueden citarse

| Área | Fuente primaria | Datos que contiene | Uso válido |
|---|---|---|---|
| B1 | experiments/results/B1_semantic_retrieval.csv y baseline_results.csv | 15 consultas, recuperación semántica | Referencia de retrieval semántico |
| B2 | experiments/results/B2_user_filtered_retrieval.csv | 15 consultas, filtrado por usuario | Personalización de retrieval |
| B3 | experiments/results/B3_context_aware_retrieval.csv y B3_context_weight_sensitivity.csv | 15 consultas y cinco pesos | Ranking contextual observado |
| B4 | experiments/results/B4_episodic_reranking.csv y B4_episodic_weight_sensitivity.csv | 15 consultas y 66 configuraciones | Reranking episódico histórico, con limitaciones metodológicas |
| Integración N0 | reports/phase2_baseline.md y experiments/results/baseline_navigation_results.csv | Prueba de aceptación y trazabilidad de fallos previos | Validación del baseline, no estimación de rendimiento |
| Integración N1 | reports/phase3_memory_on.md y experiments/results/memory_on_navigation_results.csv | Query, IDs, scores, estrategia, waypoint y Nav2 | Validación extremo a extremo, no superioridad |
| Comparabilidad | reports/phase4_experiment_infrastructure.md y experiments/results/phase4/ | Escenario, configuración, manifiesto y ejecuciones de aceptación | Evidencia de infraestructura comparable |
| Automatización | reports/phase5_automation.md y experiments/results/phase5/ | Automatización, CSV y manifiestos | Evidencia de que el protocolo puede ejecutarse |
| Navegación analizada | experiments/results/phase5/acceptance_final/ | Lote protocol_20260928, CSV crudos, logs y manifiesto | Único lote usado para estadística de N0/N1 |
| Estadística | reports/statistical_analysis.md y experiments/results/statistical_analysis/ | Descriptivos, IC y McNemar | Descripción del lote; no conclusión general |

## Qué permite afirmar la evidencia

La evidencia permite documentar que el sistema integra recuperación, recomendación y Nav2; que B1–B4 se reprodujeron sobre la base auditada; que N0 y N1 pueden ejecutarse desde un escenario compartido; y que existe un lote de navegación preservado con fallos, éxitos y un resultado faltante.

La evidencia no permite declarar que Memory ON mejora la navegación, que la adaptación al usuario es mayor, que el reranking episódico mejora retrieval, ni que una estrategia west haya cumplido una preferencia espacial durante la navegación. Esas afirmaciones requerirían más escenarios diseñados para preferencias relevantes, más repeticiones completas, estabilidad de Nav2, métricas directas de personalización y un análisis predefinido para las comparaciones.

## Próxima evidencia necesaria, sin alterar las conclusiones actuales

1. Definir varios escenarios donde la preferencia afecte a trayectorias medibles y registrar explícitamente preference_expected, preference_followed, clearance o una métrica equivalente ya especificada.
2. Ejecutar pares completos N0/N1 en cada escenario con un prefijo nuevo, preservando los intentos fallidos y el mismo control de variables.
3. Estabilizar o caracterizar los fallos de heartbeat de Nav2 antes de atribuir resultados a la condición de memoria.
4. Predefinir la comparación estadística y el tamaño de muestra; aplicar pruebas sólo cuando las condiciones y tamaño lo permitan.
5. Alinear metodológicamente B4 con la ablación que se pretenda evaluar y añadir análisis estadístico de retrieval sin sobrescribir los resultados históricos.
6. Versionar o inicializar de forma verificable el estado de la base y documentar la procedencia de los conjuntos de memorias y consultas.
