# Validación B1-B4

Fecha: 2026-09-28

## Método

Se auditó B1-B4 sin rediseñar lógica ni datasets. Las cuatro evaluaciones se ejecutaron en el entorno virtual y escribieron primero en /tmp/tfm_retrieval_audit. Los CSV temporales son idénticos byte a byte a los históricos.

PostgreSQL en localhost:5433 estaba detenido y devolvía Connection refused. Se restauró con docker compose up -d postgres. La base efectiva contiene 50 memorias, 50 embeddings semánticos y 50 episódicos, todos de dimensión 1024.

## Datos y dependencias

- Memorias: experiments/data/memory_seed.csv, 50 experiencias M001-M050.
- Consultas: experiments/data/retrieval_queries.csv, 15 consultas Q001-Q015 con relevancia binaria.
- Persistencia: PostgreSQL memory_episodes y pgvector.
- Modelo: Qwen/Qwen3-Embedding-0.6B, normalizado y CPU.
- Dependencias: numpy 2.5.2, pandas 3.0.5, sentence-transformers 6.0.0, SQLAlchemy 2.0.52, psycopg2-binary 2.9.12, torch 2.13.0 y transformers 5.15.1.
- Métricas efectivas: Precision@5, Recall@5 y nDCG@5. MRR está documentado pero no se calcula.

## B1

Script: memory/embedding/evaluate_baseline.py.
Top-5 global por similitud semántica pgvector, sin usuario ni contexto.
Resultado reproducido e histórico: Precision@5 0.4133; Recall@5 0.5959; nDCG@5 0.6239.
Estado: FUNCIONA y REPRODUCIBLE.

## B2

Script: experiments/evaluate_user_filtering.py.
Extrae Uxx y filtra por user_id; sin usuario mantiene búsqueda global.
Resultado reproducido e histórico: Precision@5 0.5600; Recall@5 0.7943; nDCG@5 0.8366.
Estado: FUNCIONA y REPRODUCIBLE.

## B3

Script: experiments/evaluate_context_aware.py.
Combina similitud semántica 0.90 y contexto 0.10, extraído de usuario, ubicación, tarea y objetivo.
Resultado reproducido e histórico: Precision@5 0.5600; Recall@5 0.7981; nDCG@5 0.8441.
La sensibilidad tiene cinco combinaciones y selecciona 0.90/0.10 con nDCG@5 0.8441.
Corrección mínima: optimize_context_weights.py declaraba B3_context_aware_retrieval.csv y podía sobrescribir la evaluación. Ahora escribe B3_context_weight_sensitivity.csv. Compila y reprodujo la selección 0.90/0.10.
Estado: FUNCIONA y REPRODUCIBLE.

## B4

Script: experiments/evaluate_episodic_reranking.py.
Reranking 0.70 semántica y 0.30 episódica; aplica filtro de usuario cuando procede y requiere episodic_embedding.
Resultado reproducido e histórico: Precision@5 0.5333; Recall@5 0.7625; nDCG@5 0.7862.
La sensibilidad histórica B4 contiene 66 configuraciones; la mejor es 0.90 semántica, 0.10 contexto y 0.00 episódica, nDCG@5 0.8441.
Limitación: el evaluador B4 no incorpora score contextual aunque la documentación lo describe como contextual y episódico; además sus pesos no son la mejor fila de sensibilidad. No se alteró para preservar el experimento histórico.
Estado: FUNCIONA y REPRODUCIBLE para el evaluador histórico. El optimizador B4 completo no se reejecutó.

## Resumen

| Experimento | Precision@5 | Recall@5 | nDCG@5 | Validación |
|---|---:|---:|---:|---|
| B1 | 0.4133 | 0.5959 | 0.6239 | CSV idéntico |
| B2 | 0.5600 | 0.7943 | 0.8366 | CSV idéntico |
| B3 | 0.5600 | 0.7981 | 0.8441 | CSV idéntico |
| B4 | 0.5333 | 0.7625 | 0.7862 | CSV idéntico |

## Riesgos

1. Debe arrancarse PostgreSQL antes de ejecutar.
2. Base, modelo, rutas y credenciales están codificados.
3. No hay huella/versionado de la base efectiva ni carga automática del seed.
4. La inferencia CPU es costosa y apareció advertencia de Hugging Face sin token.
5. MRR no está implementado.
6. B4 requiere aclaración metodológica antes de conclusiones sobre contexto y episodicidad.

No se recalculó significancia ni se infirieron mejoras científicas.