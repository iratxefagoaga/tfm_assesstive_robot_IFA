from memory.config import memory_database_url
import time
import numpy as np
import pandas as pd

from sentence_transformers import SentenceTransformer
from sqlalchemy import create_engine, text


# ============================================================
# CONFIGURACIÓN
# ============================================================

MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"


SEMANTIC_WEIGHT = 0.70
EPISODIC_WEIGHT = 0.30

QUERIES_PATH = "experiments/data/retrieval_queries.csv"

OUTPUT_PATH = (
    "experiments/results/B4_episodic_reranking.csv"
)


# ============================================================
# MÉTRICAS
# ============================================================

def precision_at_k(retrieved, relevant, k=5):

    retrieved_k = retrieved[:k]
    relevant_set = set(relevant)

    if not retrieved_k:
        return 0.0

    hits = sum(
        memory_id in relevant_set
        for memory_id in retrieved_k
    )

    return hits / k


def recall_at_k(retrieved, relevant, k=5):

    relevant_set = set(relevant)

    if not relevant_set:
        return 0.0

    retrieved_k = retrieved[:k]

    hits = sum(
        memory_id in relevant_set
        for memory_id in retrieved_k
    )

    return hits / len(relevant_set)


def ndcg_at_k(retrieved, relevant, k=5):

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
# USUARIO
# ============================================================

def extract_user_id(query):

    import re

    match = re.search(
        r"\b(U\d{2})\b",
        query.upper()
    )

    if match:
        return match.group(1)

    return None


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("B4 - EVALUACIÓN EPISODIC RERANKING")
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

    elapsed = time.perf_counter() - start

    print(
        f"Modelo cargado en "
        f"{elapsed:.2f}s"
    )

    print(
        f"Dimensión: "
        f"{model.get_embedding_dimension()}"
    )

    # --------------------------------------------------------
    # PostgreSQL
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

        relevant = [
            value.strip()
            for value in
            row["expected_memories"].split(";")
        ]

        user_id = extract_user_id(query)

        print("\n" + "-" * 70)

        print(
            f"{query_id} "
            f"({index + 1}/{len(queries)})"
        )

        print(
            f"Query: {query}"
        )

        print(
            f"Usuario: "
            f"{user_id if user_id else 'no especificado'}"
        )

        # ----------------------------------------------------
        # Embedding de la consulta
        # ----------------------------------------------------

        query_embedding = model.encode(
            query,
            normalize_embeddings=True,
            convert_to_numpy=True
        )

        vector_string = (
            "["
            + ",".join(
                str(float(value))
                for value in query_embedding
            )
            + "]"
        )

        # ----------------------------------------------------
        # Recuperar candidatos
        # ----------------------------------------------------

        if user_id is not None:

            sql = text(
                """
                SELECT
                    memory_id,
                    user_id,

                    1 - (
                        embedding
                        <=>
                        CAST(
                            :query_embedding
                            AS vector
                        )
                    ) AS semantic_similarity,

                    1 - (
                        episodic_embedding
                        <=>
                        CAST(
                            :query_embedding
                            AS vector
                        )
                    ) AS episodic_similarity

                FROM memory_episodes

                WHERE
                    embedding IS NOT NULL
                    AND episodic_embedding IS NOT NULL
                    AND user_id = :user_id

                ORDER BY
                    embedding
                    <=>
                    CAST(
                        :query_embedding
                        AS vector
                    )

                LIMIT 50;
                """
            )

            parameters = {
                "query_embedding": vector_string,
                "user_id": user_id,
            }

        else:

            sql = text(
                """
                SELECT
                    memory_id,
                    user_id,

                    1 - (
                        embedding
                        <=>
                        CAST(
                            :query_embedding
                            AS vector
                        )
                    ) AS semantic_similarity,

                    1 - (
                        episodic_embedding
                        <=>
                        CAST(
                            :query_embedding
                            AS vector
                        )
                    ) AS episodic_similarity

                FROM memory_episodes

                WHERE
                    embedding IS NOT NULL
                    AND episodic_embedding IS NOT NULL

                ORDER BY
                    embedding
                    <=>
                    CAST(
                        :query_embedding
                        AS vector
                    )

                LIMIT 50;
                """
            )

            parameters = {
                "query_embedding": vector_string,
            }

        with engine.connect() as connection:

            rows = connection.execute(
                sql,
                parameters
            ).mappings().all()

        # ----------------------------------------------------
        # Reranking
        # ----------------------------------------------------

        scored = []

        for memory in rows:

            semantic = float(
                memory["semantic_similarity"]
            )

            episodic = float(
                memory["episodic_similarity"]
            )

            final_score = (
                SEMANTIC_WEIGHT * semantic
                +
                EPISODIC_WEIGHT * episodic
            )

            scored.append(
                {
                    "memory_id":
                        memory["memory_id"],

                    "semantic_similarity":
                        semantic,

                    "episodic_similarity":
                        episodic,

                    "final_score":
                        final_score,
                }
            )

        scored.sort(
            key=lambda item:
                item["final_score"],
            reverse=True
        )

        top5 = scored[:5]

        retrieved = [
            item["memory_id"]
            for item in top5
        ]

        # ----------------------------------------------------
        # Métricas
        # ----------------------------------------------------

        precision = precision_at_k(
            retrieved,
            relevant,
            5
        )

        recall = recall_at_k(
            retrieved,
            relevant,
            5
        )

        ndcg = ndcg_at_k(
            retrieved,
            relevant,
            5
        )

        print(
            f"Retrieved: "
            f"{', '.join(retrieved)}"
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
                "query_id":
                    query_id,

                "query":
                    query,

                "user_id":
                    user_id,

                "relevant_memories":
                    ";".join(relevant),

                "retrieved_memories":
                    ";".join(retrieved),

                "semantic_scores":
                    ";".join(
                        f"{item['semantic_similarity']:.6f}"
                        for item in top5
                    ),

                "episodic_scores":
                    ";".join(
                        f"{item['episodic_similarity']:.6f}"
                        for item in top5
                    ),

                "final_scores":
                    ";".join(
                        f"{item['final_score']:.6f}"
                        for item in top5
                    ),

                "precision_at_5":
                    precision,

                "recall_at_5":
                    recall,

                "ndcg_at_5":
                    ndcg,
            }
        )

    # ========================================================
    # GUARDAR
    # ========================================================

    results_df = pd.DataFrame(
        results
    )

    results_df.to_csv(
        OUTPUT_PATH,
        index=False
    )

    # ========================================================
    # RESULTADOS GLOBALES
    # ========================================================

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
    print("RESULTADOS B4")
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

    print("\nPesos:")

    print(
        f"Semántica: "
        f"{SEMANTIC_WEIGHT}"
    )

    print(
        f"Episódica: "
        f"{EPISODIC_WEIGHT}"
    )

    print(
        "\nResultados guardados en:"
    )

    print(
        OUTPUT_PATH
    )

    print("\n" + "=" * 70)
    print("B4 COMPLETADO")
    print("=" * 70)


if __name__ == "__main__":
    main()
