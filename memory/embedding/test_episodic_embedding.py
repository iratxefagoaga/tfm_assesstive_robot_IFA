from sentence_transformers import SentenceTransformer


MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"


def main():

    print("=" * 70)
    print("B4 - PRUEBA DE EMBEDDING EPISÓDICO")
    print("=" * 70)

    # Datos de M001
    observation = "Paso estrecho junto a la mesa."
    action = "Ruta oeste evitando la mesa."
    outcome = "Navegacion correcta."
    preference = "Prefiere mayor espacio lateral."

    episodic_text = (
        f"Observation: {observation} "
        f"Action: {action} "
        f"Outcome: {outcome} "
        f"Preference: {preference}"
    )

    print("\nMemoria: M001")
    print("\nTexto episódico:")
    print(episodic_text)

    print("\nCargando modelo...")

    model = SentenceTransformer(
        MODEL_NAME,
        device="cpu"
    )

    print("Modelo cargado")

    print("\nGenerando embedding episódico...")

    embedding = model.encode(
        episodic_text,
        normalize_embeddings=True,
        convert_to_numpy=True
    )

    print(
        f"Shape: {embedding.shape}"
    )

    print(
        f"Dimensión: {len(embedding)}"
    )

    print(
        f"Norma: {float((embedding ** 2).sum() ** 0.5):.6f}"
    )

    print("\nPrimeros 10 valores:")

    print(embedding[:10])

    print("\n" + "=" * 70)
    print("PRUEBA B4 COMPLETADA")
    print("=" * 70)


if __name__ == "__main__":
    main()
