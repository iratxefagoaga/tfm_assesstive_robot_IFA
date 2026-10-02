from memory.config import memory_database_url
import re
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy import create_engine, text


# ============================================================
# CONFIGURACIÓN
# ============================================================

MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"


SEMANTIC_WEIGHT = 0.70
CONTEXT_WEIGHT = 0.30


# ============================================================
# EXTRAER CONTEXTO DE LA CONSULTA
# ============================================================

def extract_user_id(query: str) -> Optional[str]:

    match = re.search(
        r"\b(U\d{2})\b",
        query.upper()
    )

    if match:
        return match.group(1)

    return None


def extract_location(query: str) -> Optional[str]:

    locations = [
        "salon",
        "dormitorio",
        "cocina",
        "baño",
        "bano"
    ]

    query_lower = query.lower()

    for location in locations:

        if location in query_lower:

            if location == "bano":
                return "baño"

            return location

    return None


def extract_task(query: str) -> Optional[str]:

    query_lower = query.lower()

    if (
        "navegar" in query_lower
        or "navegacion" in query_lower
        or "navegación" in query_lower
        or "desplazarse" in query_lower
        or "ruta" in query_lower
        or "desvio" in query_lower
        or "desvío" in query_lower
    ):
        return "navegacion"

    if (
        "aproximarse" in query_lower
        or "aproximacion" in query_lower
        or "aproximación" in query_lower
    ):
        return "aproximacion"

    if (
        "localizar" in query_lower
        or "localizar un objeto" in query_lower
    ):
        return "localizacion"

    return None


def extract_goal(query: str) -> Optional[str]:

    query_lower = query.lower()

    goals = [
        "dormitorio",
        "salon",
        "cocina",
        "baño",
        "bano",
        "mesa",
        "objeto",
        "armario"
    ]

    # Para navegación, "al dormitorio",
    # "al salon", etc.
    for goal in goals:

        if (
            f"al {goal}" in query_lower
            or f"al {goal}" in query_lower
        ):

            if goal == "bano":
                return "baño"

            return goal

    # Casos como "aproximarse a una mesa"
    if "mesa" in query_lower:
        return "mesa"

    if "objeto" in query_lower:
        return "objeto"

    if "armario" in query_lower:
        return "armario"

    return None


# ============================================================
# CONTEXT SCORE
# ============================================================

def calculate_context_score(
    query_context,
    memory
):

    comparisons = []

    # Usuario
    if query_context["user_id"] is not None:

        comparisons.append(
            1.0
            if query_context["user_id"]
            == memory["user_id"]
            else 0.0
        )

    # Ubicación
    if query_context["location"] is not None:

        comparisons.append(
            1.0
            if query_context["location"]
            == memory["location"]
            else 0.0
        )

    # Tarea
    if query_context["task"] is not None:

        comparisons.append(
            1.0
            if query_context["task"]
            == memory["task"]
            else 0.0
        )

    # Objetivo
    if query_context["goal"] is not None:

        comparisons.append(
            1.0
            if query_context["goal"]
            == memory["goal"]
            else 0.0
        )

    if not comparisons:
        return 0.0

    return sum(comparisons) / len(comparisons)


# ============================================================
# RETRIEVAL
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
    # B3 mantiene el filtro por usuario de B2
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
            "user_id": query_context["user_id"]
        }

    # --------------------------------------------------------
    # Sin usuario: no aplicar filtro
    # --------------------------------------------------------

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
            "query_embedding": vector_string
        }

    rows = connection.execute(
        sql,
        parameters
    ).mappings().all()

    # --------------------------------------------------------
    # Calcular score contextual y final
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
                "textual_summary": memory[
                    "textual_summary"
                ],
                "semantic_similarity": semantic_score,
                "context_score": context_score,
                "final_score": final_score
            }
        )

    # --------------------------------------------------------
    # Orden final
    # --------------------------------------------------------

    scored.sort(
        key=lambda x: x["final_score"],
        reverse=True
    )

    return scored[:k]


# ============================================================
# PRUEBA Q001
# ============================================================

def main():

    query = (
        "U01 quiere ir del salon al dormitorio "
        "y necesita una ruta con espacio lateral."
    )

    print("=" * 70)
    print("B3 - CONTEXT-AWARE RETRIEVAL")
    print("=" * 70)

    # --------------------------------------------------------
    # Extraer contexto
    # --------------------------------------------------------

    query_context = {
        "user_id": extract_user_id(query),
        "location": extract_location(query),
        "task": extract_task(query),
        "goal": extract_goal(query)
    }

    print("\nConsulta:")
    print(query)

    print("\nContexto extraído:")

    for key, value in query_context.items():

        print(
            f"  {key}: {value}"
        )

    # --------------------------------------------------------
    # Modelo
    # --------------------------------------------------------

    print("\nCargando modelo...")

    model = SentenceTransformer(
        MODEL_NAME,
        device="cpu"
    )

    print(
        f"Dimensión: "
        f"{model.get_embedding_dimension()}"
    )

    # --------------------------------------------------------
    # Embedding
    # --------------------------------------------------------

    print("\nGenerando embedding...")

    query_embedding = model.encode(
        query,
        normalize_embeddings=True,
        convert_to_numpy=True
    )

    print(
        f"Shape: {query_embedding.shape}"
    )

    print(
        f"Norma: "
        f"{np.linalg.norm(query_embedding):.6f}"
    )

    # --------------------------------------------------------
    # DB
    # --------------------------------------------------------

    engine = create_engine(
        memory_database_url(),
        pool_pre_ping=True
    )

    # --------------------------------------------------------
    # Retrieval
    # --------------------------------------------------------

    with engine.connect() as connection:

        results = search_context_aware(
            connection,
            query_embedding,
            query_context,
            k=5
        )

    # --------------------------------------------------------
    # Resultados
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("TOP-5 MEMORIAS")
    print("=" * 70)

    for rank, result in enumerate(
        results,
        start=1
    ):

        print(
            f"\n#{rank} "
            f"{result['memory_id']}"
        )

        print(
            f"   Semantic: "
            f"{result['semantic_similarity']:.4f}"
        )

        print(
            f"   Context:  "
            f"{result['context_score']:.4f}"
        )

        print(
            f"   Final:    "
            f"{result['final_score']:.4f}"
        )

        print(
            f"   Usuario: "
            f"{result['user_id']}"
        )

        print(
            f"   Ubicación: "
            f"{result['location']}"
        )

        print(
            f"   Tarea: "
            f"{result['task']}"
        )

        print(
            f"   Objetivo: "
            f"{result['goal']}"
        )

        print(
            f"   {result['textual_summary']}"
        )

    print("\n" + "=" * 70)
    print("PESOS")
    print("=" * 70)

    print(
        f"Semántica: {SEMANTIC_WEIGHT}"
    )

    print(
        f"Contexto:  {CONTEXT_WEIGHT}"
    )


if __name__ == "__main__":
    main()
