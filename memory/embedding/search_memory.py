from memory.config import memory_database_url
import time

import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy import create_engine, text


# ============================================================
# CONFIGURACIÓN
# ============================================================

MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"



# ============================================================
# CONSULTA
# ============================================================

QUERY = (
    "U01 quiere ir del salon al dormitorio "
    "y necesita una ruta con espacio lateral."
)


# ============================================================
# MODELO
# ============================================================

print("Cargando modelo...")

model = SentenceTransformer(
    MODEL_NAME,
    device="cpu"
)

print(
    f"Dimension: "
    f"{model.get_embedding_dimension()}"
)


# ============================================================
# GENERAR EMBEDDING DE LA CONSULTA
# ============================================================

print("\nGenerando embedding de la consulta...")

start = time.perf_counter()

query_embedding = model.encode(
    QUERY,
    normalize_embeddings=True,
    convert_to_numpy=True
)

elapsed = time.perf_counter() - start

print(
    f"Tiempo: {elapsed:.4f} segundos"
)

print(
    f"Shape: {query_embedding.shape}"
)

print(
    f"Norma: "
    f"{np.linalg.norm(query_embedding):.6f}"
)


# ============================================================
# CONEXIÓN
# ============================================================

engine = create_engine(
    memory_database_url(),
    pool_pre_ping=True
)


# ============================================================
# BÚSQUEDA VECTORIAL
# ============================================================

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
            embedding <=> CAST(:query_embedding AS vector)
        ) AS similarity

    FROM memory_episodes

    WHERE embedding IS NOT NULL

    ORDER BY embedding <=> CAST(:query_embedding AS vector)

    LIMIT 5;
    """
)


print("\n" + "=" * 70)
print("TOP-5 MEMORIAS RECUPERADAS")
print("=" * 70)

with engine.connect() as connection:

    results = connection.execute(
        sql,
        {
            "query_embedding": vector_string
        }
    )

    for rank, row in enumerate(results, start=1):

        print(
            f"\n#{rank} "
            f"{row.memory_id} "
            f"| similarity={row.similarity:.4f}"
        )

        print(
            f"   Usuario: {row.user_id}"
        )

        print(
            f"   Ubicacion: {row.location}"
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
