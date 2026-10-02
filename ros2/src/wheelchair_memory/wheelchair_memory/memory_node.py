import rclpy
from rclpy.node import Node

from memory.memory_service import MemoryService
from wheelchair_interfaces.srv import MemoryQuery


# ============================================================
# NODO ROS 2
# ============================================================

class MemoryNode(Node):

    def __init__(self):

        super().__init__("memory_node")

        self.get_logger().info(
            "Inicializando MemoryNode..."
        )

        # ----------------------------------------------------
        # Servicio de memoria
        # ----------------------------------------------------

        self.memory_service = MemoryService()

        # Reutiliza resultados idénticos durante esta ejecución.
        self._retrieval_cache = {}

        self.get_logger().info(
            "MemoryService inicializado correctamente."
        )

        # ----------------------------------------------------
        # Servicio ROS
        # ----------------------------------------------------

        self.service = self.create_service(
            MemoryQuery,
            "/memory/query",
            self.handle_memory_query,
        )

        self.get_logger().info(
            "Servicio /memory/query disponible."
        )

    # ========================================================
    # CALLBACK
    # ========================================================

    def handle_memory_query(
        self,
        request,
        response,
    ):

        self.get_logger().info(
            "Consulta de memoria recibida."
        )

        self.get_logger().info(
            f"query={request.query}"
        )

        self.get_logger().info(
            f"user_id={request.user_id}"
        )

        self.get_logger().info(
            f"location={request.location}"
        )

        self.get_logger().info(
            f"task={request.task}"
        )

        self.get_logger().info(
            f"goal={request.goal}"
        )

        # ----------------------------------------------------
        # Parámetros opcionales
        # ----------------------------------------------------

        user_id = request.user_id or None
        location = request.location or None
        task = request.task or None
        goal = request.goal or None

        k = request.k

        if k <= 0:
            k = 5

        # ----------------------------------------------------
        # Recuperación
        # ----------------------------------------------------

        cache_key = (
            request.query,
            user_id,
            location,
            task,
            goal,
            k,
        )

        try:

            if cache_key in self._retrieval_cache:
                results = self._retrieval_cache[cache_key]
                self.get_logger().info(
                    "Resultado de memoria reutilizado para solicitud idéntica."
                )
            else:
                results = self.memory_service.retrieve_memories(
                    query=request.query,
                    user_id=user_id,
                    location=location,
                    task=task,
                    goal=goal,
                    k=k,
                )
                self._retrieval_cache[cache_key] = results

        except Exception as error:

            self.get_logger().error(
                f"Error recuperando memoria: {error}"
            )

            response.success = False
            response.message = str(error)

            return response

        # ----------------------------------------------------
        # Respuesta básica
        # ----------------------------------------------------

        response.success = True

        response.message = (
            f"{len(results)} memorias recuperadas"
        )

        # ----------------------------------------------------
        # Rellenar resultados
        # ----------------------------------------------------

        for result in results:

            response.memory_ids.append(
                str(result["memory_id"])
            )

            response.summaries.append(
                str(result["textual_summary"] or "")
            )

            response.observations.append(
                str(result["observation"] or "")
            )

            response.actions.append(
                str(result["action"] or "")
            )

            response.outcomes.append(
                str(result["outcome"] or "")
            )

            response.preferences.append(
                str(result["preference"] or "")
            )

            response.semantic_scores.append(
                float(result["semantic_similarity"])
            )

            response.context_scores.append(
                float(result["context_score"])
            )

            response.final_scores.append(
                float(result["final_score"])
            )

        # ----------------------------------------------------
        # Logging
        # ----------------------------------------------------

        self.get_logger().info(
            f"Memorias recuperadas: {len(results)}"
        )

        for rank, result in enumerate(
            results,
            start=1,
        ):

            self.get_logger().info(
                f"#{rank} "
                f"{result['memory_id']} | "
                f"semantic="
                f"{result['semantic_similarity']:.4f} | "
                f"context="
                f"{result['context_score']:.4f} | "
                f"final="
                f"{result['final_score']:.4f}"
            )

            self.get_logger().info(
                f"   action="
                f"{result['action'] or ''}"
            )

            self.get_logger().info(
                f"   preference="
                f"{result['preference'] or ''}"
            )

        return response


# ============================================================
# MAIN
# ============================================================

def main(args=None):

    rclpy.init(args=args)

    node = MemoryNode()

    try:

        rclpy.spin(node)

    except KeyboardInterrupt:

        pass

    finally:

        node.destroy_node()

        rclpy.shutdown()


if __name__ == "__main__":
    main()
