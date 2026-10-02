import os
from pathlib import Path
import time

import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy import create_engine, text


# ============================================================
# CONFIGURACIÓN
# ============================================================

MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"

DB_USER = os.environ["MEMORY_DB_USER"]
DB_PASSWORD = os.environ["MEMORY_DB_PASSWORD"]
DB_HOST = os.environ.get("MEMORY_DB_HOST", "localhost")
DB_PORT = os.environ.get("MEMORY_DB_PORT", "5433")
DB_NAME = os.environ.get("MEMORY_DB_NAME", "memory")

DATABASE_URL = (
    f"postgresql+psycopg2://"
    f"{DB_USER}:{DB_PASSWORD}@"
    f"{DB_HOST}:{DB_PORT}/{DB_NAME}"
)


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

    print(f"Modelo cargado en {elapsed:.2f} segundos")
    print(
        f"Dimensión: "
        f"{model.get_embedding_dimension()}"
    )

    return model


# ============================================================
# CONEXIÓN
# ============================================================

def create_db_engine():

    print("\nConectando con PostgreSQL...")

    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True
    )

    with engine.connect() as connection:

        result = connection.execute(
            text(
                """
                SELECT current_database();
                """
            )
        )

        database = result.scalar()

        print(f"Base de datos: {database}")

    return engine


# ============================================================
# OBTENER MEMORIAS
# ============================================================

def get_memories(engine):

    with engine.connect() as connection:

        result = connection.execute(
            text(
                """
                SELECT
                    memory_id,
                    textual_summary
                FROM memory_episodes
                ORDER BY memory_id;
                """
            )
        )

        memories = result.fetchall()

    print(f"\nMemorias encontradas: {len(memories)}")

    if not memories:
        raise RuntimeError(
            "No hay memorias en memory_episodes."
        )

    return memories


# ============================================================
# GENERAR EMBEDDINGS
# ============================================================

def generate_embeddings(model, memories):

    texts = [
        memory.textual_summary
        for memory in memories
    ]

    print("\nGenerando embeddings...")

    start = time.perf_counter()

    embeddings = model.encode(
        texts,
        batch_size=4,
        normalize_embeddings=True,
        show_progress_bar=True,
        convert_to_numpy=True
    )

    elapsed = time.perf_counter() - start

    print(
        f"\nTiempo total: {elapsed:.2f} segundos"
    )

    print(
        f"Tiempo medio por memoria: "
        f"{elapsed / len(memories):.4f} segundos"
    )

    print(
        f"Shape: {embeddings.shape}"
    )

    print(
        f"Dimensión: {embeddings.shape[1]}"
    )

    print(
        f"Norma media: "
        f"{np.linalg.norm(embeddings, axis=1).mean():.6f}"
    )

    return embeddings


# ============================================================
# GUARDAR EN PGVECTOR
# ============================================================

def update_embeddings(engine, memories, embeddings):

    print("\nGuardando embeddings en PostgreSQL...")

    update_sql = text(
        """
        UPDATE memory_episodes
        SET embedding = CAST(:embedding AS vector)
        WHERE memory_id = :memory_id;
        """
    )

    records = []

    for memory, embedding in zip(
        memories,
        embeddings
    ):

        vector_string = (
            "["
            + ",".join(
                str(float(value))
                for value in embedding
            )
            + "]"
        )

        records.append(
            {
                "memory_id": memory.memory_id,
                "embedding": vector_string
            }
        )

    with engine.begin() as connection:

        connection.execute(
            update_sql,
            records
        )

    print(
        f"Embeddings almacenados: "
        f"{len(records)}"
    )


# ============================================================
# VALIDACIÓN
# ============================================================

def validate_embeddings(engine):

    print("\nValidando embeddings...")

    with engine.connect() as connection:

        result = connection.execute(
            text(
                """
                SELECT
                    COUNT(*) AS total,
                    COUNT(embedding) AS with_embedding
                FROM memory_episodes;
                """
            )
        )

        row = result.fetchone()

        print(
            f"Memorias totales: {row.total}"
        )

        print(
            f"Memorias con embedding: "
            f"{row.with_embedding}"
        )

        if row.total != row.with_embedding:

            raise RuntimeError(
                "No todas las memorias tienen embedding."
            )

        result = connection.execute(
            text(
                """
                SELECT
                    memory_id,
                    vector_dims(embedding) AS dimensions
                FROM memory_episodes
                ORDER BY memory_id
                LIMIT 5;
                """
            )
        )

        print("\nDimensiones de los primeros embeddings:")

        for row in result:

            print(
                f"{row.memory_id}: "
                f"{row.dimensions}"
            )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("TFM - GENERACIÓN DE EMBEDDINGS")
    print("=" * 60)

    model = load_model()

    engine = create_db_engine()

    memories = get_memories(engine)

    embeddings = generate_embeddings(
        model,
        memories
    )

    if embeddings.shape[1] != 1024:

        raise RuntimeError(
            f"Dimensión inesperada: "
            f"{embeddings.shape[1]}"
        )

    update_embeddings(
        engine,
        memories,
        embeddings
    )

    validate_embeddings(engine)

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETADO CORRECTAMENTE")
    print("=" * 60)


if __name__ == "__main__":
    main()
