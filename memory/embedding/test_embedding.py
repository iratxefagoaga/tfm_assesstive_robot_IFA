from pathlib import Path
import time

import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer


# ============================================================
# CONFIGURACIÓN
# ============================================================

MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = PROJECT_ROOT / "experiments" / "data" / "memory_seed.csv"


# ============================================================
# CARGAR MODELO
# ============================================================

print("=" * 60)
print("TFM - PRUEBA DEL MODELO DE EMBEDDINGS")
print("=" * 60)

print(f"\nModelo: {MODEL_NAME}")

start = time.perf_counter()

model = SentenceTransformer(
    MODEL_NAME,
    device="cpu"
)

load_time = time.perf_counter() - start

print(f"Modelo cargado en: {load_time:.2f} segundos")

print(
    f"Dimensión del embedding: "
    f"{model.get_embedding_dimension()}"
)


# ============================================================
# PRUEBA 1 - UN EMBEDDING
# ============================================================

text = (
    "User U01. "
    "Location: salon. "
    "Task: navegacion. "
    "Goal: dormitorio. "
    "Observation: Paso estrecho junto a la mesa. "
    "Action: Ruta oeste evitando la mesa. "
    "Outcome: Navegacion correcta. "
    "Preference: Prefiere mayor espacio lateral."
)

print("\n" + "-" * 60)
print("PRUEBA 1 - EMBEDDING INDIVIDUAL")
print("-" * 60)

start = time.perf_counter()

embedding = model.encode(
    text,
    normalize_embeddings=True
)

elapsed = time.perf_counter() - start

print(f"Tiempo: {elapsed:.4f} segundos")
print(f"Shape: {embedding.shape}")
print(f"Norma: {np.linalg.norm(embedding):.6f}")

print("\nPrimeros 10 valores:")
print(embedding[:10])


# ============================================================
# PRUEBA 2 - SIMILITUD SEMÁNTICA
# ============================================================

print("\n" + "-" * 60)
print("PRUEBA 2 - SIMILITUD SEMÁNTICA")
print("-" * 60)

texts = [
    (
        "U01 tiene dificultades para pasar cerca de la mesa "
        "y prefiere una ruta con espacio lateral."
    ),
    (
        "U01 tuvo problemas de espacio al pasar junto a la mesa."
    ),
    (
        "U02 prefiere aproximaciones frontales a la mesa."
    ),
]

embeddings = model.encode(
    texts,
    normalize_embeddings=True
)

similarity = np.matmul(
    embeddings,
    embeddings.T
)

print("\nMatriz de similitud:")

for i in range(len(texts)):
    for j in range(len(texts)):
        print(
            f"Texto {i + 1} vs Texto {j + 1}: "
            f"{similarity[i][j]:.4f}"
        )


# ============================================================
# PRUEBA 3 - 50 MEMORIAS
# ============================================================

print("\n" + "-" * 60)
print("PRUEBA 3 - EMBEDDINGS DEL DATASET")
print("-" * 60)

if not CSV_PATH.exists():
    raise FileNotFoundError(
        f"No se encuentra: {CSV_PATH}"
    )

df = pd.read_csv(CSV_PATH)

print(f"Memorias: {len(df)}")

start = time.perf_counter()

dataset_embeddings = model.encode(
    df["textual_summary"].tolist(),
    normalize_embeddings=True,
    batch_size=4,
    show_progress_bar=True
)

elapsed = time.perf_counter() - start

print(f"\nTiempo total: {elapsed:.2f} segundos")
print(
    f"Tiempo medio por memoria: "
    f"{elapsed / len(df):.4f} segundos"
)

print(
    f"Shape final: "
    f"{dataset_embeddings.shape}"
)

print("\n" + "=" * 60)
print("PRUEBAS COMPLETADAS")
print("=" * 60)
