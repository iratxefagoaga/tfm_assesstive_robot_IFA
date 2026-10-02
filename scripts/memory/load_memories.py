import os
from pathlib import Path
import json

import pandas as pd
from sqlalchemy import create_engine, text


# ============================================================
# CONFIGURACIÓN
# ============================================================

DB_USER = os.environ["MEMORY_DB_USER"]
DB_PASSWORD = os.environ["MEMORY_DB_PASSWORD"]
DB_HOST = os.environ.get("MEMORY_DB_HOST", "localhost")
DB_PORT = os.environ.get("MEMORY_DB_PORT", "5433")
DB_NAME = os.environ.get("MEMORY_DB_NAME", "memory")

DATABASE_URL = (
    f"postgresql+psycopg2://"
    f"{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "experiments" / "data" / "memory_seed.csv"


# ============================================================
# CARGA DEL DATASET
# ============================================================

def load_dataset() -> pd.DataFrame:
    """Carga el dataset sintético de memorias."""

    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"No se encuentra el dataset: {CSV_PATH}"
        )

    df = pd.read_csv(CSV_PATH)

    print(f"Dataset encontrado: {CSV_PATH}")
    print(f"Memorias leídas: {len(df)}")

    return df


# ============================================================
# PREPARACIÓN
# ============================================================

def prepare_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Prepara los datos para PostgreSQL."""

    required_columns = [
        "memory_id",
        "user_id",
        "timestamp",
        "location",
        "task",
        "goal",
        "observation",
        "action",
        "outcome",
        "preference",
        "memory_type",
        "importance",
        "confidence",
        "textual_summary",
        "metadata",
    ]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Faltan columnas en el CSV: {missing}"
        )

    # Convertimos la fecha a datetime
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # PostgreSQL TEXT[] espera una lista de valores.
    df["memory_type"] = df["memory_type"].apply(
        lambda value: value.split(";")
        if isinstance(value, str)
        else []
    )

    # Convertimos metadata "{}" a un diccionario Python.
    df["metadata"] = df["metadata"].apply(
    	lambda value: json.dumps({})
    	if pd.isna(value) or value == "{}"
    	else json.dumps(value) if isinstance(value, dict) else value
    )

    return df


# ============================================================
# CONEXIÓN
# ============================================================

def create_db_engine():
    """Crea la conexión con PostgreSQL."""

    print("Conectando con PostgreSQL...")

    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
    )

    # Comprobamos conexión
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT current_database(), version();")
        )

        database, version = result.fetchone()

        print(f"Base de datos: {database}")
        print(f"PostgreSQL: {version.split(',')[0]}")

    return engine


# ============================================================
# INSERCIÓN
# ============================================================

def insert_memories(engine, df: pd.DataFrame):
    """Inserta las memorias en PostgreSQL."""

    insert_sql = text(
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
            memory_type,
            importance,
            confidence,
            textual_summary,
            metadata
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
            :memory_type,
            :importance,
            :confidence,
            :textual_summary,
            CAST(:metadata AS jsonb)
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
            memory_type = EXCLUDED.memory_type,
            importance = EXCLUDED.importance,
            confidence = EXCLUDED.confidence,
            textual_summary = EXCLUDED.textual_summary,
            metadata = EXCLUDED.metadata;
        """
    )

    records = df.to_dict(orient="records")

    with engine.begin() as connection:
        connection.execute(insert_sql, records)

    print(f"Memorias insertadas/actualizadas: {len(records)}")


# ============================================================
# VALIDACIÓN
# ============================================================

def validate_database(engine):
    """Comprueba que los datos se han insertado correctamente."""

    with engine.connect() as connection:

        result = connection.execute(
            text(
                """
                SELECT COUNT(*)
                FROM memory_episodes;
                """
            )
        )

        total = result.scalar()

        print(f"\nTotal de memorias en PostgreSQL: {total}")

        result = connection.execute(
            text(
                """
                SELECT
                    user_id,
                    COUNT(*) AS total
                FROM memory_episodes
                GROUP BY user_id
                ORDER BY user_id;
                """
            )
        )

        print("\nMemorias por usuario:")

        for row in result:
            print(
                f"  {row.user_id}: {row.total}"
            )

        result = connection.execute(
            text(
                """
                SELECT
                    memory_id,
                    user_id,
                    location,
                    task,
                    goal
                FROM memory_episodes
                ORDER BY memory_id
                LIMIT 5;
                """
            )
        )

        print("\nPrimeras memorias:")

        for row in result:
            print(
                f"  {row.memory_id} | "
                f"{row.user_id} | "
                f"{row.location} | "
                f"{row.task} | "
                f"{row.goal}"
            )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print("TFM - CARGA DE MEMORIAS")
    print("=" * 60)

    try:
        # 1. Leer CSV
        df = load_dataset()

        # 2. Preparar datos
        df = prepare_dataset(df)

        # 3. Conectar con PostgreSQL
        engine = create_db_engine()

        # 4. Insertar
        insert_memories(engine, df)

        # 5. Validar
        validate_database(engine)

        print("\n" + "=" * 60)
        print("Carga completada correctamente.")
        print("=" * 60)

    except Exception as error:

        print("\nERROR durante la carga:")
        print(error)

        raise


if __name__ == "__main__":
    main()
