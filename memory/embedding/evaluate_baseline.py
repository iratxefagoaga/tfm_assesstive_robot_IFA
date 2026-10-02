from memory.config import memory_database_url
from pathlib import Path
import time

import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy import create_engine, text


# ============================================================
# CONFIGURACIÓN
# ============================================================

MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"


PROJECT_ROOT = Path(__file__).resolve().parents[2]

QUERIES_PATH = (
    PROJECT_ROOT
    / "experiments"
    / "data"
    / "retrieval_queries.csv"
)

RESULTS_DIR = (
    PROJECT_ROOT
    / "experiments"
    / "results"
)

RESULTS_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ============================================================
# MÉTRICAS
# ============================================================

def precision_at_k(retrieved, relevant, k):
    """
    Precision@K:
    proporción de resultados recuperados que son relevantes.
    """

    retrieved_k = retrieved[:k]

    if not retrieved_k:
        return 0.0

    relevant_set = set(relevant)

    hits = sum(
        1
        for memory_id in retrieved_k
        if memory_id in relevant_set
    )

    return hits / k


def recall_at_k(retrieved, relevant, k):
    """
    Recall@K:
    proporción de memorias relevantes recuperadas.
    """

    if not relevant:
        return 0.0

    retrieved_k = retrieved[:k]

    relevant_set = set(relevant)

    hits = sum(
        1
        for memory_id in retrieved_k
        if memory_id in relevant_set
    )

    return hits / len(relevant_set)


def ndcg_at_k(retrieved, relevant, k):
    """
    nDCG@K utilizando relevancia binaria.
    """

    retrieved_k = retrieved[:k]
    relevant_set = set(relevant)

    dcg = 0.0

    for rank, memory_id in enumerate(
        retrieved_k,
        start=1
    ):

        relevance = (
            1
            if memory_id in relevant_set
            else 0
        )

        dcg += (
            relevance
            / np.log2(rank + 1)
        )

    ideal_relevances = [
        1
        for _ in range(
            min(k, len(relevant_set))
        )
    ]

    idcg = 0.0

    for rank, relevance in enumerate(
        ideal_relevances,
        start=1
    ):

        idcg += (
            relevance
            / np.log2(rank + 1)
        )

    if idcg == 0:
        return 0.0

    return dcg / idcg


# ============================================================
# CARGAR MODELO
# ============================================================

def load_model():

    print("Cargando modelo...")

    start = time.perf_counter()

    model = SentenceTransformer(
        MODEL_NAME,
        device="cpu"
    )

    elapsed = time.perf_counter() - start

    print(
        f"Modelo cargado en "
        f"{elapsed:.2f} segundos"
    )

    print(
        f"Dimensión: "
        f"{model.get_embedding_dimension()}"
    )

    return model


# ============================================================
# CONEXIÓN
# ============================================================

def create_engine_connection():

    return create_engine(
        memory_database_url(),
        pool_pre_ping=True
    )


# ============================================================
# BÚSQUEDA
# ============================================================

def search_memory(
    connection,
    query_embedding,
    k=5
):

    vector_string = (
        "["
        + ",".join(
            str(float(value))
            for value in query_embedding
        )
        + "]"
    )

    sql = text(
        """
        SELECT
            memory_id,
            user_id,
            location,
            task,
            1 - (
                embedding
                <=>
                CAST(:query_embedding AS vector)
            ) AS similarity

        FROM memory_episodes

        WHERE embedding IS NOT NULL

        ORDER BY
            embedding
            <=>
            CAST(:query_embedding AS vector)

        LIMIT :k;
        """
    )

    result = connection.execute(
        sql,
        {
            "query_embedding": vector_string,
            "k": k
        }
    )

    return list(result)


# ============================================================
# EVALUACIÓN
# ============================================================

def evaluate():

    print("=" * 70)
    print("TFM - EVALUACIÓN DEL BASELINE")
    print("=" * 70)

    # --------------------------------------------------------
    # Cargar queries
    # --------------------------------------------------------

    if not QUERIES_PATH.exists():

        raise FileNotFoundError(
            f"No existe: {QUERIES_PATH}"
        )

    queries = pd.read_csv(
        QUERIES_PATH
    )

    print(
        f"\nConsultas: {len(queries)}"
    )

    # --------------------------------------------------------
    # Modelo
    # --------------------------------------------------------

    model = load_model()

    # --------------------------------------------------------
    # PostgreSQL
    # --------------------------------------------------------

    engine = create_engine_connection()

    results = []

    # --------------------------------------------------------
    # Evaluar consultas
    # --------------------------------------------------------

    for index, row in queries.iterrows():

        query_id = row["query_id"]
        query = row["query"]

        relevant = (
            row["expected_memories"]
            .split(";")
        )

        print("\n" + "-" * 70)

        print(
            f"{query_id} "
            f"({index + 1}/{len(queries)})"
        )

        print(
            f"Query: {query}"
        )

        # --------------------------------------------
        # Embedding
        # --------------------------------------------

        query_embedding = model.encode(
            query,
            normalize_embeddings=True,
            convert_to_numpy=True
        )

        # --------------------------------------------
        # Retrieval
        # --------------------------------------------

        with engine.connect() as connection:

            retrieved_rows = search_memory(
                connection,
                query_embedding,
                k=5
            )

        retrieved_ids = [
            row.memory_id
            for row in retrieved_rows
        ]

        similarities = [
            float(row.similarity)
            for row in retrieved_rows
        ]

        # --------------------------------------------
        # Métricas
        # --------------------------------------------

        precision = precision_at_k(
            retrieved_ids,
            relevant,
            5
        )

        recall = recall_at_k(
            retrieved_ids,
            relevant,
            5
        )

        ndcg = ndcg_at_k(
            retrieved_ids,
            relevant,
            5
        )

        print(
            f"Retrieved: "
            f"{', '.join(retrieved_ids)}"
        )

        print(
            f"Relevant:  "
            f"{', '.join(relevant)}"
        )

        print(
            f"Precision@5: {precision:.4f}"
        )

        print(
            f"Recall@5:    {recall:.4f}"
        )

        print(
            f"nDCG@5:      {ndcg:.4f}"
        )

        # --------------------------------------------
        # Guardar resultado
        # --------------------------------------------

        results.append(
            {
                "query_id": query_id,
                "query": query,
                "relevant_memories": ";".join(
                    relevant
                ),
                "retrieved_memories": ";".join(
                    retrieved_ids
                ),
                "similarities": ";".join(
                    f"{value:.6f}"
                    for value in similarities
                ),
                "precision_at_5": precision,
                "recall_at_5": recall,
                "ndcg_at_5": ndcg
            }
        )

    # ========================================================
    # RESULTADOS
    # ========================================================

    results_df = pd.DataFrame(
        results
    )

    output_path = (
        RESULTS_DIR
        / "baseline_results.csv"
    )

    results_df.to_csv(
        output_path,
        index=False
    )

    # --------------------------------------------------------
    # Media
    # --------------------------------------------------------

    mean_precision = (
        results_df[
            "precision_at_5"
        ].mean()
    )

    mean_recall = (
        results_df[
            "recall_at_5"
        ].mean()
    )

    mean_ndcg = (
        results_df[
            "ndcg_at_5"
        ].mean()
    )

    print("\n" + "=" * 70)
    print("RESULTADOS DEL BASELINE")
    print("=" * 70)

    print(
        f"\nPrecision@5 media: "
        f"{mean_precision:.4f}"
    )

    print(
        f"Recall@5 medio:    "
        f"{mean_recall:.4f}"
    )

    print(
        f"nDCG@5 medio:      "
        f"{mean_ndcg:.4f}"
    )

    print(
        f"\nResultados guardados en:"
    )

    print(output_path)

    print("\n" + "=" * 70)
    print("EVALUACIÓN COMPLETADA")
    print("=" * 70)


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    evaluate()
