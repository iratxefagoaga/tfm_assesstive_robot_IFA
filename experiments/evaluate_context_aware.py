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


SEMANTIC_WEIGHT = 0.90
CONTEXT_WEIGHT = 0.10

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
    / "B3_context_aware_retrieval.csv"
)


# ============================================================
# CONTEXTO DE LA CONSULTA
# ============================================================

def extract_user_id(query):

    match = re.search(
        r"\b(U\d{2})\b",
        query.upper()
    )

    if match:
        return match.group(1)

    return None

def extract_location(query):

    query_lower = query.lower()

    locations = [
        ("salon", "salon"),
        ("dormitorio", "dormitorio"),
        ("cocina", "cocina"),
        ("baño", "baño"),
        ("bano", "baño"),
    ]

    # Casos donde la consulta expresa explícitamente
    # el origen: "del salon al dormitorio",
    # "desde el salon", etc.

    origin_patterns = [
        r"del\s+(salon|dormitorio|cocina|baño|bano)",
        r"desde\s+(el\s+|la\s+)?(salon|dormitorio|cocina|baño|bano)",
        r"partiendo\s+(del\s+|de\s+la\s+)?(salon|dormitorio|cocina|baño|bano)",
    ]

    for pattern in origin_patterns:

        match = re.search(
            pattern,
            query_lower
        )

        if match:

            location = match.groups()[-1]

            if location == "bano":
                return "baño"

            return location

    # Casos explícitos de posición actual:
    # "está en el salon", "se encuentra en el salon"

    current_patterns = [
        r"está\s+en\s+(el\s+|la\s+)?(salon|dormitorio|cocina|baño|bano)",
        r"esta\s+en\s+(el\s+|la\s+)?(salon|dormitorio|cocina|baño|bano)",
        r"se\s+encuentra\s+en\s+(el\s+|la\s+)?(salon|dormitorio|cocina|baño|bano)",
    ]

    for pattern in current_patterns:

        match = re.search(
            pattern,
            query_lower
        )

        if match:

            location = match.groups()[-1]

            if location == "bano":
                return "baño"

            return location

    return None

def extract_task(query):

    query_lower = query.lower()

    # Primero comprobamos expresiones negativas.
    # Ejemplo:
    # "no de navegar" NO debe clasificarse como navegación.

    negative_navigation = [
        "no de navegar",
        "no de navegación",
        "no de navegacion",
        "no es navegar",
        "no es navegación",
        "no es navegacion",
    ]

    if any(
        phrase in query_lower
        for phrase in negative_navigation
    ):

        if (
            "localizar" in query_lower
            or "localización" in query_lower
            or "localizacion" in query_lower
        ):
            return "localizacion"

        return None

    if any(
        phrase in query_lower
        for phrase in [
            "navegar",
            "navegacion",
            "navegación",
            "desplazarse",
            "ruta",
            "desvio",
            "desvío",
            "obstaculo",
            "obstáculo",
        ]
    ):
        return "navegacion"

    if any(
        phrase in query_lower
        for phrase in [
            "aproximarse",
            "aproximacion",
            "aproximación",
        ]
    ):
        return "aproximacion"

    if any(
        phrase in query_lower
        for phrase in [
            "localizar",
            "localización",
            "localizacion",
        ]
    ):
        return "localizacion"

    return None

def extract_goal(query):

    query_lower = query.lower()

    # Destinos explícitos
    destinations = [
        ("dormitorio", "dormitorio"),
        ("salon", "salon"),
        ("cocina", "cocina"),
        ("baño", "baño"),
        ("bano", "baño"),
    ]

    for text_value, normalized_value in destinations:

        if (
            f"al {text_value}" in query_lower
            or f"a {text_value}" in query_lower
        ):
            return normalized_value

    # Objetos
    if "mesa" in query_lower:
        return "mesa"

    if "armario" in query_lower:
        return "armario"

    if "objeto" in query_lower:
        return "objeto"

    return None


# ============================================================
# SCORE CONTEXTUAL
# ============================================================

def calculate_context_score(
    query_context,
    memory
):

    scores = []

    # Usuario
    if query_context["user_id"] is not None:

        scores.append(
            1.0
            if query_context["user_id"]
            == memory["user_id"]
            else 0.0
        )

    # Ubicación
    if query_context["location"] is not None:

        scores.append(
            1.0
            if query_context["location"]
            == memory["location"]
            else 0.0
        )

    # Tarea
    if query_context["task"] is not None:

        scores.append(
            1.0
            if query_context["task"]
            == memory["task"]
            else 0.0
        )

    # Objetivo
    if query_context["goal"] is not None:

        scores.append(
            1.0
            if query_context["goal"]
            == memory["goal"]
            else 0.0
        )

    if not scores:
        return 0.0

    return sum(scores) / len(scores)


# ============================================================
# RETRIEVAL CONTEXT-AWARE
# ============================================================

def search_context_aware(
    connection,
    query_embedding,
    query_context,
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
    # Si conocemos el usuario, mantenemos el filtro de B2
    # --------------------------------------------------------

    if query_context["user_id"] is not None:

        sql = text(
            """
            SELECT
                memory_id,
                user_id,
                location,
                task,
                goal,
                textual_summary,

                1 - (
                    embedding
                    <=>
                    CAST(:query_embedding AS vector)
                ) AS semantic_similarity

            FROM memory_episodes

            WHERE
                embedding IS NOT NULL
                AND user_id = :user_id

            ORDER BY
                embedding
                <=>
                CAST(:query_embedding AS vector)

            LIMIT 50;
            """
        )

        parameters = {
            "query_embedding": vector_string,
            "user_id": query_context["user_id"],
        }

    else:

        sql = text(
            """
            SELECT
                memory_id,
                user_id,
                location,
                task,
                goal,
                textual_summary,

                1 - (
                    embedding
                    <=>
                    CAST(:query_embedding AS vector)
                ) AS semantic_similarity

            FROM memory_episodes

            WHERE embedding IS NOT NULL

            ORDER BY
                embedding
                <=>
                CAST(:query_embedding AS vector)

            LIMIT 50;
            """
        )

        parameters = {
            "query_embedding": vector_string,
        }

    rows = connection.execute(
        sql,
        parameters
    ).mappings().all()

    # --------------------------------------------------------
    # Calcular scores
    # --------------------------------------------------------

    scored = []

    for memory in rows:

        semantic_score = float(
            memory["semantic_similarity"]
        )

        context_score = calculate_context_score(
            query_context,
            memory
        )

        final_score = (
            SEMANTIC_WEIGHT * semantic_score
            +
            CONTEXT_WEIGHT * context_score
        )

        scored.append(
            {
                "memory_id": memory["memory_id"],
                "user_id": memory["user_id"],
                "location": memory["location"],
                "task": memory["task"],
                "goal": memory["goal"],
                "semantic_similarity": semantic_score,
                "context_score": context_score,
                "final_score": final_score,
            }
        )

    scored.sort(
        key=lambda x: x["final_score"],
        reverse=True
    )

    return scored[:k]


# ============================================================
# MÉTRICAS
# ============================================================

def precision_at_k(
    retrieved,
    relevant,
    k
):

    retrieved_k = retrieved[:k]

    if not retrieved_k:
        return 0.0

    relevant_set = set(relevant)

    hits = sum(
        memory_id in relevant_set
        for memory_id in retrieved_k
    )

    return hits / k


def recall_at_k(
    retrieved,
    relevant,
    k
):

    if not relevant:
        return 0.0

    retrieved_k = retrieved[:k]

    relevant_set = set(relevant)

    hits = sum(
        memory_id in relevant_set
        for memory_id in retrieved_k
    )

    return hits / len(relevant_set)


def ndcg_at_k(
    retrieved,
    relevant,
    k
):

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
# EVALUACIÓN
# ============================================================

def main():

    print("=" * 70)
    print("B3 - EVALUACIÓN CONTEXT-AWARE RETRIEVAL")
    print("=" * 70)

    # --------------------------------------------------------
    # Consultas
    # --------------------------------------------------------

    queries = pd.read_csv(
        QUERIES_PATH
    )

    print(
        f"\nConsultas: {len(queries)}"
    )

    # --------------------------------------------------------
    # Modelo
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
    # DB
    # --------------------------------------------------------

    engine = create_engine(
        memory_database_url(),
        pool_pre_ping=True
    )

    results = []

    # ========================================================
    # CONSULTAS
    # ========================================================

    for index, row in queries.iterrows():

        query_id = row["query_id"]
        query = row["query"]

        relevant = (
            row["expected_memories"]
            .split(";")
        )

        # ----------------------------------------------------
        # Contexto
        # ----------------------------------------------------

        query_context = {
            "user_id": extract_user_id(query),
            "location": extract_location(query),
            "task": extract_task(query),
            "goal": extract_goal(query),
        }

        print("\n" + "-" * 70)

        print(
            f"{query_id} "
            f"({index + 1}/{len(queries)})"
        )

        print(
            f"Query: {query}"
        )

        print(
            f"Contexto: "
            f"user={query_context['user_id']}, "
            f"location={query_context['location']}, "
            f"task={query_context['task']}, "
            f"goal={query_context['goal']}"
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

            retrieved_rows = search_context_aware(
                connection,
                query_embedding,
                query_context,
                k=5
            )

        retrieved_ids = [
            result["memory_id"]
            for result in retrieved_rows
        ]

        # ----------------------------------------------------
        # Scores
        # ----------------------------------------------------

        semantic_scores = [
            result["semantic_similarity"]
            for result in retrieved_rows
        ]

        context_scores = [
            result["context_score"]
            for result in retrieved_rows
        ]

        final_scores = [
            result["final_score"]
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
        # Guardar
        # ----------------------------------------------------

        results.append(
            {
                "query_id": query_id,
                "query": query,
                "user_id": query_context["user_id"],
                "location": query_context["location"],
                "task": query_context["task"],
                "goal": query_context["goal"],
                "relevant_memories": ";".join(
                    relevant
                ),
                "retrieved_memories": ";".join(
                    retrieved_ids
                ),
                "semantic_scores": ";".join(
                    f"{value:.6f}"
                    for value in semantic_scores
                ),
                "context_scores": ";".join(
                    f"{value:.6f}"
                    for value in context_scores
                ),
                "final_scores": ";".join(
                    f"{value:.6f}"
                    for value in final_scores
                ),
                "precision_at_5": precision,
                "recall_at_5": recall,
                "ndcg_at_5": ndcg,
            }
        )

    # ========================================================
    # GUARDAR RESULTADOS
    # ========================================================

    results_df = pd.DataFrame(
        results
    )

    results_df.to_csv(
        OUTPUT_PATH,
        index=False
    )

    # ========================================================
    # MEDIAS
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
    print("RESULTADOS B3")
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
        "\nPesos utilizados:"
    )

    print(
        f"Semántica: {SEMANTIC_WEIGHT}"
    )

    print(
        f"Contexto:  {CONTEXT_WEIGHT}"
    )

    print(
        "\nResultados guardados en:"
    )

    print(
        OUTPUT_PATH
    )

    print("\n" + "=" * 70)
    print("B3 COMPLETADO")
    print("=" * 70)

if __name__ == "__main__":
    main()
