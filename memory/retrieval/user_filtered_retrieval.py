from memory.config import memory_database_url
import re
from typing import Optional

import numpy as np
from sqlalchemy import create_engine, text
from sentence_transformers import SentenceTransformer


# ============================================================
# CONFIGURACIÓN
# ============================================================

MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"



# ============================================================
# EXTRAER USUARIO
# ============================================================

def extract_user_id(query: str) -> Optional[str]:
    """
    Extrae U01, U02 o U03 de la consulta.
    """

    match = re.search(
        r"\b(U\d{2})\b",
        query.upper()
    )

    if match:
        return match.group(1)

    return None


# ============================================================
# GENERAR EMBEDDING
# ============================================================

def generate_query_embedding(model, query: str):

    embedding = model.encode(
        query,
        normalize_embeddings=True,
        convert_to_numpy=True
    )

    return embedding


# ============================================================
# BÚSQUEDA CONTEXTUAL POR USUARIO
# ============================================================

def search_user_filtered(
    connection,
    query_embedding,
    user_id: str,
    k: int = 5
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
            goal,
            textual_summary,

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

    result = connection.execute(
        sql,
        {
            "query_embedding": vector_string,
            "user_id": user_id,
            "k": k
        }
    )

    return list(result)


# ============================================================
# EJEMPLO
# ============================================================

def main():

    query = (
        "U01 quiere ir del salon al dormitorio "
        "y necesita una ruta con espacio lateral."
    )

    print("=" * 70)
    print("B2 - USER FILTERED RETRIEVAL")
    print("=" * 70)

    # --------------------------------------------------------
    # Usuario
    # --------------------------------------------------------

    user_id = extract_user_id(query)

    if user_id is None:

        raise ValueError(
            "No se ha podido identificar el usuario."
        )

    print(f"\nUsuario identificado: {user_id}")

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

    query_embedding = generate_query_embedding(
        model,
        query
    )

    print(
        f"Shape: {query_embedding.shape}"
    )

    print(
        f"Norma: "
        f"{np.linalg.norm(query_embedding):.6f}"
    )

    # --------------------------------------------------------
    # PostgreSQL
    # --------------------------------------------------------

    engine = create_engine(
        memory_database_url(),
        pool_pre_ping=True
    )

    # --------------------------------------------------------
    # Retrieval
    # --------------------------------------------------------

    with engine.connect() as connection:

        results = search_user_filtered(
            connection,
            query_embedding,
            user_id,
            k=5
        )

    # --------------------------------------------------------
    # Mostrar
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("TOP-5 MEMORIAS RECUPERADAS")
    print("=" * 70)

    for rank, row in enumerate(
        results,
        start=1
    ):

        print(
            f"\n#{rank} "
            f"{row.memory_id} "
            f"| similarity={row.similarity:.4f}"
        )

        print(
            f"   Usuario: {row.user_id}"
        )

        print(
            f"   Ubicación: {row.location}"
        )

        print(
            f"   Tarea: {row.task}"
        )

        print(
            f"   Objetivo: {row.goal}"
        )

        print(
            f"   {row.textual_summary}"
        )


if __name__ == "__main__":
    main()
