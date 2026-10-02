from memory.config import memory_database_url
import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy import create_engine, text


MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"



QUERY = (
    "U03 encuentra un obstaculo inesperado "
    "y hay que priorizar la seguridad."
)

USER_ID = "U03"


def main():

    print("=" * 70)
    print("B4 - PRUEBA DE RECUPERACIÓN EPISÓDICA")
    print("=" * 70)

    print("\nConsulta:")
    print(QUERY)

    print("\nUsuario:")
    print(USER_ID)

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
    # Embedding de la consulta
    # --------------------------------------------------------

    print("\nGenerando embedding episódico de la consulta...")

    query_embedding = model.encode(
        QUERY,
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
    # PostgreSQL
    # --------------------------------------------------------

    engine = create_engine(
        memory_database_url(),
        pool_pre_ping=True
    )

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
            observation,
            action,
            outcome,
            preference,

            1 - (
                episodic_embedding
                <=>
                CAST(:query_embedding AS vector)
            ) AS episodic_similarity

        FROM memory_episodes

        WHERE
            episodic_embedding IS NOT NULL
            AND user_id = :user_id

        ORDER BY
            episodic_embedding
            <=>
            CAST(:query_embedding AS vector)

        LIMIT 5;
        """
    )

    print("\n" + "=" * 70)
    print("TOP-5 MEMORIAS POR SIMILITUD EPISÓDICA")
    print("=" * 70)

    with engine.connect() as connection:

        rows = connection.execute(
            sql,
            {
                "query_embedding": vector_string,
                "user_id": USER_ID,
            }
        ).mappings().all()

    for index, row in enumerate(
        rows,
        start=1
    ):

        print(
            f"\n#{index} "
            f"{row['memory_id']} "
            f"| episodic_similarity="
            f"{float(row['episodic_similarity']):.4f}"
        )

        print(
            f"   Usuario: {row['user_id']}"
        )

        print(
            f"   Ubicación: {row['location']}"
        )

        print(
            f"   Tarea: {row['task']}"
        )

        print(
            f"   Objetivo: {row['goal']}"
        )

        print(
            f"   Observation: "
            f"{row['observation']}"
        )

        print(
            f"   Action: "
            f"{row['action']}"
        )

        print(
            f"   Outcome: "
            f"{row['outcome']}"
        )

        print(
            f"   Preference: "
            f"{row['preference']}"
        )

    print("\n" + "=" * 70)
    print("PRUEBA B4 COMPLETADA")
    print("=" * 70)


if __name__ == "__main__":
    main()
