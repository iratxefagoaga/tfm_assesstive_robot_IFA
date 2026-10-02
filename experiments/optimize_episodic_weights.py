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
    / "B4_episodic_weight_sensitivity.csv"
)


# ============================================================
# EXTRACCIÓN DE CONTEXTO
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

    if query_context["user_id"] is not None:

        scores.append(
            1.0
            if query_context["user_id"]
            == memory["user_id"]
            else 0.0
        )

    if query_context["location"] is not None:

        scores.append(
            1.0
            if query_context["location"]
            == memory["location"]
            else 0.0
        )

    if query_context["task"] is not None:

        scores.append(
            1.0
            if query_context["task"]
            == memory["task"]
            else 0.0
        )

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
# RECUPERACIÓN DE CANDIDATOS
# ============================================================

def retrieve_candidates(
    connection,
    query_embedding,
    query_context
):

    vector_string = (
        "["
        + ",".join(
            str(float(value))
            for value in query_embedding
        )
        + "]"
    )

    if query_context["user_id"] is not None:

        sql = text(
            """
            SELECT
                memory_id,
                user_id,
                location,
                task,
                goal,

                1 - (
                    embedding
                    <=>
                    CAST(:query_embedding AS vector)
                ) AS semantic_similarity,

                1 - (
                    episodic_embedding
                    <=>
                    CAST(:query_embedding AS vector)
                ) AS episodic_similarity

            FROM memory_episodes

            WHERE
                embedding IS NOT NULL
                AND episodic_embedding IS NOT NULL
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

                1 - (
                    embedding
                    <=>
                    CAST(:query_embedding AS vector)
                ) AS semantic_similarity,

                1 - (
                    episodic_embedding
                    <=>
                    CAST(:query_embedding AS vector)
                ) AS episodic_similarity

            FROM memory_episodes

            WHERE
                embedding IS NOT NULL
                AND episodic_embedding IS NOT NULL

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

    return rows


# ============================================================
# MÉTRICAS
# ============================================================

def precision_at_k(
    retrieved,
    relevant,
    k=5
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
    k=5
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
    k=5
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
# GENERAR CONFIGURACIONES DE PESOS
# ============================================================

def generate_weight_configurations(
    step=0.10
):

    configurations = []

    values = np.arange(
        0.0,
        1.0 + step / 2,
        step
    )

    for semantic_weight in values:

        for context_weight in values:

            episodic_weight = (
                1.0
                - semantic_weight
                - context_weight
            )

            if episodic_weight < -1e-9:
                continue

            episodic_weight = round(
                episodic_weight,
                10
            )

            configurations.append(
                (
                    round(semantic_weight, 2),
                    round(context_weight, 2),
                    round(episodic_weight, 2),
                )
            )

    return configurations


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print(
        "B4 - OPTIMIZACIÓN DE PESOS "
        "SEMÁNTICA/CONTEXTO/EPISÓDICO"
    )
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
    # Configuraciones
    # --------------------------------------------------------

    configurations = (
        generate_weight_configurations(
            step=0.10
        )
    )

    print(
        f"Configuraciones de pesos: "
        f"{len(configurations)}"
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

    elapsed = (
        time.perf_counter()
        - start
    )

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

    # --------------------------------------------------------
    # Precalcular candidatos
    # --------------------------------------------------------

    print(
        "\nPrecalculando candidatos..."
    )

    query_data = []

    for index, row in queries.iterrows():

        query_id = row["query_id"]
        query = row["query"]

        relevant = [
            value.strip()
            for value in
            row["expected_memories"].split(";")
        ]

        query_context = {
            "user_id":
                extract_user_id(query),

            "location":
                extract_location(query),

            "task":
                extract_task(query),

            "goal":
                extract_goal(query),
        }

        print(
            f"  {query_id} "
            f"({index + 1}/{len(queries)})"
        )

        query_embedding = model.encode(
            query,
            normalize_embeddings=True,
            convert_to_numpy=True
        )

        with engine.connect() as connection:

            candidates = retrieve_candidates(
                connection,
                query_embedding,
                query_context
            )

        prepared_candidates = []

        for memory in candidates:

            context_score = (
                calculate_context_score(
                    query_context,
                    memory
                )
            )

            prepared_candidates.append(
                {
                    "memory_id":
                        memory["memory_id"],

                    "semantic_similarity":
                        float(
                            memory[
                                "semantic_similarity"
                            ]
                        ),

                    "context_score":
                        float(
                            context_score
                        ),

                    "episodic_similarity":
                        float(
                            memory[
                                "episodic_similarity"
                            ]
                        ),
                }
            )

        query_data.append(
            {
                "query_id":
                    query_id,

                "query":
                    query,

                "relevant":
                    relevant,

                "context":
                    query_context,

                "candidates":
                    prepared_candidates,
            }
        )

    # ========================================================
    # EVALUAR CONFIGURACIONES
    # ========================================================

    all_results = []

    for config_index, (
        semantic_weight,
        context_weight,
        episodic_weight,
    ) in enumerate(
        configurations,
        start=1
    ):

        print("\n" + "=" * 70)

        print(
            f"CONFIGURACIÓN "
            f"{config_index}/{len(configurations)}"
        )

        print(
            f"Semántica={semantic_weight:.2f} | "
            f"Contexto={context_weight:.2f} | "
            f"Episódico={episodic_weight:.2f}"
        )

        precisions = []
        recalls = []
        ndcgs = []

        for item in query_data:

            scored = []

            for memory in item["candidates"]:

                final_score = (
                    semantic_weight
                    * memory[
                        "semantic_similarity"
                    ]
                    +
                    context_weight
                    * memory[
                        "context_score"
                    ]
                    +
                    episodic_weight
                    * memory[
                        "episodic_similarity"
                    ]
                )

                scored.append(
                    {
                        "memory_id":
                            memory["memory_id"],

                        "final_score":
                            final_score,
                    }
                )

            scored.sort(
                key=lambda x:
                    x["final_score"],
                reverse=True
            )

            retrieved = [
                item["memory_id"]
                for item in scored[:5]
            ]

            precision = precision_at_k(
                retrieved,
                item["relevant"],
                5
            )

            recall = recall_at_k(
                retrieved,
                item["relevant"],
                5
            )

            ndcg = ndcg_at_k(
                retrieved,
                item["relevant"],
                5
            )

            precisions.append(
                precision
            )

            recalls.append(
                recall
            )

            ndcgs.append(
                ndcg
            )

        mean_precision = np.mean(
            precisions
        )

        mean_recall = np.mean(
            recalls
        )

        mean_ndcg = np.mean(
            ndcgs
        )

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

        all_results.append(
            {
                "semantic_weight":
                    semantic_weight,

                "context_weight":
                    context_weight,

                "episodic_weight":
                    episodic_weight,

                "precision_at_5":
                    mean_precision,

                "recall_at_5":
                    mean_recall,

                "ndcg_at_5":
                    mean_ndcg,
            }
        )

    # ========================================================
    # RESULTADOS
    # ========================================================

    results_df = pd.DataFrame(
        all_results
    )

    results_df = results_df.sort_values(
        by="ndcg_at_5",
        ascending=False
    ).reset_index(
        drop=True
    )

    results_df.to_csv(
        OUTPUT_PATH,
        index=False
    )

    # ========================================================
    # MEJOR CONFIGURACIÓN
    # ========================================================

    best = results_df.iloc[0]

    print("\n" + "=" * 70)
    print(
        "RESULTADOS OPTIMIZACIÓN B4"
    )
    print("=" * 70)

    print(
        "\nMejor configuración "
        "según nDCG@5:"
    )

    print(
        f"Semántica: "
        f"{best['semantic_weight']:.2f}"
    )

    print(
        f"Contexto:  "
        f"{best['context_weight']:.2f}"
    )

    print(
        f"Episódico: "
        f"{best['episodic_weight']:.2f}"
    )

    print(
        f"\nPrecision@5: "
        f"{best['precision_at_5']:.4f}"
    )

    print(
        f"Recall@5:    "
        f"{best['recall_at_5']:.4f}"
    )

    print(
        f"nDCG@5:      "
        f"{best['ndcg_at_5']:.4f}"
    )

    print(
        "\nTop 10 configuraciones:"
    )

    print(
        results_df.head(10).to_string(
            index=False
        )
    )

    print(
        "\nResultados guardados en:"
    )

    print(
        OUTPUT_PATH
    )

    print("\n" + "=" * 70)
    print(
        "OPTIMIZACIÓN B4 COMPLETADA"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()
