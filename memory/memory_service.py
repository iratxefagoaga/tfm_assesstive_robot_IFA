from memory.config import memory_database_url
from datetime import datetime
from typing import Optional

from sentence_transformers import SentenceTransformer
from sqlalchemy import create_engine, text


# ============================================================
# CONFIGURACIÓN
# ============================================================

MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"


SEMANTIC_WEIGHT = 0.90
CONTEXT_WEIGHT = 0.10


# ============================================================
# SERVICIO DE MEMORIA
# ============================================================

class MemoryService:

    def __init__(self):

        print("Inicializando MemoryService...")

        self.model = SentenceTransformer(
            MODEL_NAME,
            device="cpu"
        )

        self.engine = create_engine(
            memory_database_url(),
            pool_pre_ping=True
        )

        dimension = self.model.get_embedding_dimension()

        if dimension != 1024:
            raise ValueError(
                f"Dimensión inesperada: {dimension}. "
                f"Se esperaba 1024."
            )

        print(f"Modelo: {MODEL_NAME}")
        print(f"Dimensión: {dimension}")
        print(
            f"Pesos: semántica={SEMANTIC_WEIGHT}, "
            f"contexto={CONTEXT_WEIGHT}"
        )


    # ========================================================
    # EMBEDDING
    # ========================================================

    def generate_embedding(self, text_value: str):

        return self.model.encode(
            text_value,
            normalize_embeddings=True,
            convert_to_numpy=True
        )


    # ========================================================
    # TEXTO EPISÓDICO
    # ========================================================

    def build_episodic_text(
        self,
        observation: Optional[str],
        action: Optional[str],
        outcome: Optional[str],
        preference: Optional[str]
    ):

        return (
            f"Observation: {observation or ''} "
            f"Action: {action or ''} "
            f"Outcome: {outcome or ''} "
            f"Preference: {preference or ''}"
        )


    # ========================================================
    # GUARDAR MEMORIA
    # ========================================================

    def store_memory(
        self,
        memory_id: str,
        user_id: str,
        location: Optional[str],
        task: Optional[str],
        goal: Optional[str],
        textual_summary: str,
        observation: Optional[str] = None,
        action: Optional[str] = None,
        outcome: Optional[str] = None,
        preference: Optional[str] = None
    ):

        semantic_embedding = self.generate_embedding(
            textual_summary
        )

        episodic_text = self.build_episodic_text(
            observation,
            action,
            outcome,
            preference
        )

        episodic_embedding = self.generate_embedding(
            episodic_text
        )

        semantic_vector = (
            "["
            + ",".join(
                str(float(value))
                for value in semantic_embedding
            )
            + "]"
        )

        episodic_vector = (
            "["
            + ",".join(
                str(float(value))
                for value in episodic_embedding
            )
            + "]"
        )

        sql = text(
            """
            INSERT INTO memory_episodes (
                memory_id,
                user_id,
                timestamp,
                location,
                task,
                goal,
                observation,
                action,
                outcome,
                preference,
                textual_summary,
                embedding,
                episodic_embedding
            )
            VALUES (
                :memory_id,
                :user_id,
                :timestamp,
                :location,
                :task,
                :goal,
                :observation,
                :action,
                :outcome,
                :preference,
                :textual_summary,
                CAST(:embedding AS vector),
                CAST(:episodic_embedding AS vector)
            )
            ON CONFLICT (memory_id)
            DO UPDATE SET
                user_id = EXCLUDED.user_id,
                timestamp = EXCLUDED.timestamp,
                location = EXCLUDED.location,
                task = EXCLUDED.task,
                goal = EXCLUDED.goal,
                observation = EXCLUDED.observation,
                action = EXCLUDED.action,
                outcome = EXCLUDED.outcome,
                preference = EXCLUDED.preference,
                textual_summary = EXCLUDED.textual_summary,
                embedding = EXCLUDED.embedding,
                episodic_embedding = EXCLUDED.episodic_embedding;
            """
        )

        with self.engine.begin() as connection:

            connection.execute(
                sql,
                {
                    "memory_id": memory_id,
                    "user_id": user_id,
                    "timestamp": datetime.now(),
                    "location": location,
                    "task": task,
                    "goal": goal,
                    "observation": observation,
                    "action": action,
                    "outcome": outcome,
                    "preference": preference,
                    "textual_summary": textual_summary,
                    "embedding": semantic_vector,
                    "episodic_embedding": episodic_vector,
                }
            )

        return memory_id


    # ========================================================
    # RETRIEVAL CONTEXT-AWARE
    # ========================================================

    def retrieve_memories(
        self,
        query: str,
        user_id: Optional[str] = None,
        location: Optional[str] = None,
        task: Optional[str] = None,
        goal: Optional[str] = None,
        k: int = 5
    ):

        # ----------------------------------------------------
        # Generar embedding de la consulta
        # ----------------------------------------------------

        query_embedding = self.generate_embedding(
            query
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
        # Consulta con filtro de usuario
        # ----------------------------------------------------

        if user_id is not None:

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
                "user_id": user_id,
            }

        # ----------------------------------------------------
        # Consulta sin filtro de usuario
        # ----------------------------------------------------

        else:

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

        # ----------------------------------------------------
        # Ejecutar consulta
        # ----------------------------------------------------

        with self.engine.connect() as connection:

            rows = connection.execute(
                sql,
                parameters
            ).mappings().all()

        # ----------------------------------------------------
        # Calcular puntuaciones
        # ----------------------------------------------------

        scored = []

        for memory in rows:

            context_values = []

            # ------------------------------------------------
            # Usuario
            # ------------------------------------------------

            if user_id is not None:

                context_values.append(
                    1.0
                    if user_id == memory["user_id"]
                    else 0.0
                )

            # ------------------------------------------------
            # Ubicación
            # ------------------------------------------------

            if location is not None:

                context_values.append(
                    1.0
                    if location == memory["location"]
                    else 0.0
                )

            # ------------------------------------------------
            # Tarea
            # ------------------------------------------------

            if task is not None:

                context_values.append(
                    1.0
                    if task == memory["task"]
                    else 0.0
                )

            # ------------------------------------------------
            # Objetivo
            # ------------------------------------------------

            if goal is not None:

                context_values.append(
                    1.0
                    if goal == memory["goal"]
                    else 0.0
                )

            # ------------------------------------------------
            # Context score
            # ------------------------------------------------

            if context_values:

                context_score = (
                    sum(context_values)
                    / len(context_values)
                )

            else:

                context_score = 0.0

            # ------------------------------------------------
            # Semantic score
            # ------------------------------------------------

            semantic_score = float(
                memory["semantic_similarity"]
            )

            # ------------------------------------------------
            # Final score
            # ------------------------------------------------

            final_score = (
                SEMANTIC_WEIGHT * semantic_score
                +
                CONTEXT_WEIGHT * context_score
            )

            # ------------------------------------------------
            # Resultado enriquecido
            # ------------------------------------------------

            scored.append(
                {
                    "memory_id": memory["memory_id"],
                    "user_id": memory["user_id"],
                    "location": memory["location"],
                    "task": memory["task"],
                    "goal": memory["goal"],

                    "observation": memory["observation"],
                    "action": memory["action"],
                    "outcome": memory["outcome"],
                    "preference": memory["preference"],

                    "textual_summary": memory["textual_summary"],

                    "semantic_similarity": semantic_score,
                    "context_score": context_score,
                    "final_score": final_score,
                }
            )

        # ----------------------------------------------------
        # Ordenar por score final
        # ----------------------------------------------------

        scored.sort(
            key=lambda item: item["final_score"],
            reverse=True
        )

        return scored[:k]