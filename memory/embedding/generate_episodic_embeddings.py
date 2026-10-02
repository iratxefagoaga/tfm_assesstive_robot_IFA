from memory.config import memory_database_url
import time

import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy import create_engine, text


# ============================================================
# CONFIGURACIÓN
# ============================================================

MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"


BATCH_SIZE = 4


# ============================================================
# CONSTRUCCIÓN DEL TEXTO EPISÓDICO
# ============================================================

def build_episodic_text(memory):
    return (
        f"Observation: {memory['observation'] or ''} "
        f"Action: {memory['action'] or ''} "
        f"Outcome: {memory['outcome'] or ''} "
        f"Preference: {memory['preference'] or ''}"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("TFM - GENERACIÓN DE EMBEDDINGS EPISÓDICOS")
    print("=" * 70)

    # --------------------------------------------------------
    # Cargar modelo
    # --------------------------------------------------------

    print("\nCargando modelo...")

    start = time.perf_counter()

    model = SentenceTransformer(
        MODEL_NAME,
        device="cpu"
    )

    model_load_time = time.perf_counter() - start

    print(
        f"Modelo cargado en "
        f"{model_load_time:.2f} segundos"
    )

    dimension = model.get_embedding_dimension()

    print(
        f"Dimensión: {dimension}"
    )

    if dimension != 1024:
        raise ValueError(
            f"Dimensión inesperada: {dimension}. "
            f"Se esperaba 1024."
        )

    # --------------------------------------------------------
    # Conectar PostgreSQL
    # --------------------------------------------------------

    print("\nConectando con PostgreSQL...")

    engine = create_engine(
        memory_database_url(),
        pool_pre_ping=True
    )

    # --------------------------------------------------------
    # Obtener memorias
    # --------------------------------------------------------

    with engine.connect() as connection:

        rows = connection.execute(
            text(
                """
                SELECT
                    memory_id,
                    user_id,
                    observation,
                    action,
                    outcome,
                    preference
                FROM memory_episodes
                ORDER BY memory_id;
                """
            )
        ).mappings().all()

    print(
        f"Memorias encontradas: {len(rows)}"
    )

    if not rows:
        raise ValueError(
            "No se encontraron memorias."
        )

    # --------------------------------------------------------
    # Construir textos episódicos
    # --------------------------------------------------------

    print("\nConstruyendo textos episódicos...")

    episodic_texts = []

    for memory in rows:

        episodic_text = build_episodic_text(
            memory
        )

        episodic_texts.append(
            episodic_text
        )

    # Mostrar una muestra
    print("\nEjemplo M001:")

    first_memory = rows[0]

    print(
        build_episodic_text(first_memory)
    )

    # --------------------------------------------------------
    # Generar embeddings
    # --------------------------------------------------------

    print("\nGenerando embeddings episódicos...")

    start = time.perf_counter()

    embeddings = model.encode(
        episodic_texts,
        batch_size=BATCH_SIZE,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=True
    )

    elapsed = time.perf_counter() - start

    print(
        f"\nTiempo total: {elapsed:.2f} segundos"
    )

    print(
        f"Tiempo medio por memoria: "
        f"{elapsed / len(rows):.4f} segundos"
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

    # --------------------------------------------------------
    # Validaciones
    # --------------------------------------------------------

    if embeddings.shape != (
        len(rows),
        1024
    ):
        raise ValueError(
            "Shape de embeddings inesperado: "
            f"{embeddings.shape}"
        )

    norms = np.linalg.norm(
        embeddings,
        axis=1
    )

    if not np.allclose(
        norms,
        1.0,
        atol=0.01
    ):
        raise ValueError(
            "Se encontraron embeddings "
            "con normas fuera del rango esperado."
        )

    # --------------------------------------------------------
    # Guardar en PostgreSQL
    # --------------------------------------------------------

    print(
        "\nGuardando embeddings episódicos "
        "en PostgreSQL..."
    )

    update_sql = text(
        """
        UPDATE memory_episodes
        SET episodic_embedding =
            CAST(:embedding AS vector)
        WHERE memory_id = :memory_id;
        """
    )

    stored = 0

    with engine.begin() as connection:

        for memory, embedding in zip(
            rows,
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

            connection.execute(
                update_sql,
                {
                    "memory_id": memory["memory_id"],
                    "embedding": vector_string,
                }
            )

            stored += 1

    print(
        f"Embeddings episódicos almacenados: "
        f"{stored}"
    )

    # --------------------------------------------------------
    # Validación en PostgreSQL
    # --------------------------------------------------------

    print(
        "\nValidando embeddings episódicos..."
    )

    with engine.connect() as connection:

        total = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM memory_episodes;
                """
            )
        ).scalar()

        with_embedding = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM memory_episodes
                WHERE episodic_embedding IS NOT NULL;
                """
            )
        ).scalar()

        dimensions = connection.execute(
            text(
                """
                SELECT
                    memory_id,
                    vector_dims(episodic_embedding)
                        AS dimension
                FROM memory_episodes
                WHERE episodic_embedding IS NOT NULL
                ORDER BY memory_id
                LIMIT 5;
                """
            )
        ).mappings().all()

    print(
        f"Memorias totales: {total}"
    )

    print(
        f"Memorias con embedding episódico: "
        f"{with_embedding}"
    )

    print(
        "\nDimensiones de los primeros "
        "embeddings episódicos:"
    )

    for row in dimensions:

        print(
            f"{row['memory_id']}: "
            f"{row['dimension']}"
        )

    # --------------------------------------------------------
    # Resultado final
    # --------------------------------------------------------

    if (
        total != len(rows)
        or with_embedding != len(rows)
    ):
        raise RuntimeError(
            "No todas las memorias tienen "
            "embedding episódico."
        )

    print("\n" + "=" * 70)
    print("PIPELINE DE EMBEDDINGS EPISÓDICOS COMPLETADO")
    print("=" * 70)


if __name__ == "__main__":
    main()
