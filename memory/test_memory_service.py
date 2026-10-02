from memory_service import MemoryService


def main():

    service = MemoryService()

    query = (
        "U01 quiere ir del salon al dormitorio "
        "y necesita una ruta con espacio lateral."
    )

    results = service.retrieve_memories(
        query=query,
        user_id="U01",
        location="salon",
        task="navegacion",
        goal="dormitorio",
        k=5
    )

    print("\n" + "=" * 70)
    print("TEST MEMORY SERVICE")
    print("=" * 70)

    for rank, result in enumerate(
        results,
        start=1
    ):

        print(
            f"\n#{rank} {result['memory_id']}"
        )

        print(
            f"   Semantic: "
            f"{result['semantic_similarity']:.4f}"
        )

        print(
            f"   Context:  "
            f"{result['context_score']:.4f}"
        )

        print(
            f"   Final:    "
            f"{result['final_score']:.4f}"
        )

        print(
            f"   {result['textual_summary']}"
        )


if __name__ == "__main__":
    main()
