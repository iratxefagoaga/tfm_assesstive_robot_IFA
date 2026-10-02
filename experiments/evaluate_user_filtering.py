from memory.config import memory_database_url
from pathlib import Path
import re
import time

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sqlalchemy import create_engine, text


# ============================================================
# CONFIGURACIÓN
# ============================================================

MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"


PROJECT_ROOT = Path(__file__).resolve().parents[1]

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

OUTPUT_PATH = (
    RESULTS_DIR
    / "B2_user_filtered_retrieval.csv"
)


# ============================================================
# MÉTRICAS
# ============================================================

def precision_at_k(retrieved, relevant, k):

    retrieved_k = retrieved[:k]

    if not retrieved_k:
        return 0.0

    relevant_set = set(relevant)

    hits = sum(
        memory_id in relevant_set
        for memory_id in retrieved_k
    )

    return hits / k


def recall_at_k(retrieved, relevant, k):

    if not relevant:
        return 0.0

    retrieved_k = retrieved[:k]

    relevant_set = set(relevant)

    hits = sum(
        memory_id in relevant_set
        for memory_id in retrieved_k
    )

    return hits / len(relevant_set)


def ndcg_at_k(retrieved, relevant, k):

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

    ideal_count = min(
        k,
        len(relevant_set)
    )

    if ideal_count == 0:
        return 0.0

    idcg = sum(
        1 / np.log2(rank + 1)
        for rank in range(
            1,
            ideal_count + 1
        )
    )

    return dcg / idcg


# ============================================================
# EXTRAER USUARIO
# ============================================================

def extract_user_id(query):

    match = re.search(
        r"\b(U\d{2})\b",
        query.upper()
    )

    if match:
        return match.group(1)

    return None


# ============================================================
# BÚSQUEDA
# ============================================================

def search_memory(
    connection,
    query_embedding,
    user_id=None,
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

    # --------------------------------------------------------
    # Con usuario: aplicar filtro
    # --------------------------------------------------------

    if user_id is not None:

        sql = text(
            """
            SELECT
                memory_id,

                1 - (
                    embedding
                    <=>
                    CAST(:query_embedding AS vector)
                ) AS similarity

            FROM memory_episodes

            WHERE
                embedding IS NOT NULL
                AND user_id = :user_id

            ORDER BY
                embedding
                <=>
                CAST(:query_embedding AS vector)

            LIMIT :k;
            """
        )

        parameters = {
            "query_embedding": vector_string,
            "user_id": user_id,
            "k": k
        }

    # --------------------------------------------------------
    # Sin usuario: no aplicar filtro
    # --------------------------------------------------------

    else:

        sql = text(
            """
            SELECT
                memory_id,

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

        parameters = {
            "query_embedding": vector_string,
            "k": k
        }

    result = connection.execute(
        sql,
        parameters
    )

    return list(result)


# ============================================================
# EVALUACIÓN
# ============================================================

def main():

    print("=" * 70)
    print("B2 - EVALUACIÓN USER FILTERED RETRIEVAL")
    print("=" * 70)

    # --------------------------------------------------------
    # Cargar consultas
    # --------------------------------------------------------

    queries = pd.read_csv(
        QUERIES_PATH
    )

    print(
        f"\nConsultas: {len(queries)}"
    )

    # --------------------------------------------------------
    # Cargar modelo
    # --------------------------------------------------------

    print("\nCargando modelo...")

    start = time.perf_counter()

    model = SentenceTransformer(
        MODEL_NAME,
        device="cpu"
    )

    print(
        f"Modelo cargado en "
        f"{time.perf_counter() - start:.2f}s"
    )

    print(
        f"Dimensión: "
        f"{model.get_embedding_dimension()}"
    )

    # --------------------------------------------------------
    # Conexión
    # --------------------------------------------------------

    engine = create_engine(
        memory_database_url(),
        pool_pre_ping=True
    )

    results = []

    # ========================================================
    # EVALUAR CONSULTAS
    # ========================================================

    for index, row in queries.iterrows():

        query_id = row["query_id"]
        query = row["query"]

        user_id = extract_user_id(
            query
        )

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

        if user_id is None:

            print(
                "Usuario: no especificado"
            )

            print(
                "Filtro de usuario: "
                "NO APLICADO"
            )

        else:

            print(
                f"Usuario: {user_id}"
            )

            print(
                f"Filtro de usuario: "
                f"{user_id}"
            )

        # ----------------------------------------------------
        # Embedding
        # ----------------------------------------------------

        query_embedding = model.encode(
            query,
            normalize_embeddings=True,
            convert_to_numpy=True
        )

        # ----------------------------------------------------
        # Retrieval
        # ----------------------------------------------------

        with engine.connect() as connection:

            retrieved_rows = search_memory(
                connection,
                query_embedding,
                user_id,
                k=5
            )

        retrieved_ids = [
            result.memory_id
            for result in retrieved_rows
        ]

        similarities = [
            float(result.similarity)
            for result in retrieved_rows
        ]

        # ----------------------------------------------------
        # Métricas
        # ----------------------------------------------------

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
            f"Precision@5: "
            f"{precision:.4f}"
        )

        print(
            f"Recall@5:    "
            f"{recall:.4f}"
        )

        print(
            f"nDCG@5:      "
            f"{ndcg:.4f}"
        )

        # ----------------------------------------------------
        # Guardar resultado
        # ----------------------------------------------------

        results.append(
            {
                "query_id": query_id,
                "query": query,
                "user_id": user_id,
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

    results_df.to_csv(
        OUTPUT_PATH,
        index=False
    )

    # --------------------------------------------------------
    # Medias
    # --------------------------------------------------------

    mean_precision = results_df[
        "precision_at_5"
    ].mean()

    mean_recall = results_df[
        "recall_at_5"
    ].mean()

    mean_ndcg = results_df[
        "ndcg_at_5"
    ].mean()

    print("\n" + "=" * 70)
    print("RESULTADOS B2")
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
        "\nResultados guardados en:"
    )

    print(
        OUTPUT_PATH
    )

    print("\n" + "=" * 70)
    print("B2 COMPLETADO")
    print("=" * 70)


if __name__ == "__main__":
    main()
