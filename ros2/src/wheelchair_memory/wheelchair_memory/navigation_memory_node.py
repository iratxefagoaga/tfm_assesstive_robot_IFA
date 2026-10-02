import time
import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor

from wheelchair_interfaces.srv import (
    MemoryQuery,
    NavigationRecommendation,
)


class NavigationMemoryNode(Node):

    def __init__(self):

        super().__init__(
            "navigation_memory_node"
        )

        self.get_logger().info(
            "Inicializando NavigationMemoryNode..."
        )

        # ====================================================
        # CALLBACK GROUP
        # ====================================================

        self.callback_group = ReentrantCallbackGroup()

        # ====================================================
        # CLIENTE DE MEMORIA
        # ====================================================

        self.memory_client = self.create_client(
            MemoryQuery,
            "/memory/query",
            callback_group=self.callback_group,
        )

        self.get_logger().info(
            "Esperando servicio /memory/query..."
        )

        while not self.memory_client.wait_for_service(
            timeout_sec=1.0
        ):
            self.get_logger().info(
                "Servicio /memory/query todavía "
                "no disponible..."
            )

        self.get_logger().info(
            "Servicio /memory/query disponible."
        )

        # ====================================================
        # SERVICIO DE RECOMENDACIÓN
        # ====================================================

        self.recommendation_service = (
            self.create_service(
                NavigationRecommendation,
                "/memory/navigation_recommendation",
                self.handle_recommendation,
                callback_group=self.callback_group,
            )
        )

        self.get_logger().info(
            "Servicio "
            "/memory/navigation_recommendation "
            "disponible."
        )

    # ========================================================
    # CONSTRUIR RECOMENDACIÓN
    # ========================================================

    def build_navigation_recommendation(
        self,
        response,
    ):

        if not response.success:

            return {
                "success": False,
                "message": response.message,
            }

        if not response.memory_ids:

            return {
                "success": False,
                "message": (
                    "No se recuperaron memorias."
                ),
            }

        # ----------------------------------------------------
        # Seleccionar la memoria con mayor puntuación
        #
        # /memory/query ya devuelve las memorias ordenadas
        # por final_score, por lo que la primera es la mejor.
        # ----------------------------------------------------

        index = 0

        memory_id = response.memory_ids[index]

        action = response.actions[index]

        preference = response.preferences[index]

        observation = response.observations[index]

        outcome = response.outcomes[index]

        semantic_score = (
            response.semantic_scores[index]
        )

        context_score = (
            response.context_scores[index]
        )

        final_score = (
            response.final_scores[index]
        )

        action_lower = (
            action or ""
        ).lower()

        preference_lower = (
            preference or ""
        ).lower()

        observation_lower = (
            observation or ""
        ).lower()

        # ----------------------------------------------------
        # Valores por defecto
        # ----------------------------------------------------

        strategy = "direct"

        avoid_obstacle = False

        prefer_clearance = False

        # ----------------------------------------------------
        # Estrategia
        # ----------------------------------------------------

        if "ruta oeste" in action_lower:

            strategy = "west"

        elif "ruta central" in action_lower:

            strategy = "central"

        elif (
            "alternativa" in action_lower
            or "desvio" in action_lower
            or "desvío" in action_lower
        ):

            strategy = "alternative"

        # ----------------------------------------------------
        # Obstáculos
        # ----------------------------------------------------

        obstacle_terms = [
            "evitando",
            "evita",
            "obstaculo",
            "obstáculo",
            "mesa",
        ]

        if any(
            term in action_lower
            for term in obstacle_terms
        ):

            avoid_obstacle = True

        if (
            "obstaculo" in observation_lower
            or "obstáculo" in observation_lower
            or "mesa" in observation_lower
        ):

            avoid_obstacle = True

        # ----------------------------------------------------
        # Espacio lateral
        # ----------------------------------------------------

        clearance_terms = [
            "espacio lateral",
            "espacio",
            "lateral",
        ]

        if any(
            term in preference_lower
            for term in clearance_terms
        ):

            prefer_clearance = True

        # ----------------------------------------------------
        # Razón
        # ----------------------------------------------------

        reason = (
            f"Memoria {memory_id}: "
            f"{action}"
        )

        if preference:

            reason += (
                f" Preferencia: {preference}"
            )

        return {
            "success": True,
            "message": (
                "Recomendación generada "
                "a partir de memoria."
            ),
            "strategy": strategy,
            "avoid_obstacle": avoid_obstacle,
            "prefer_clearance": prefer_clearance,
            "source_memory": memory_id,
            "reason": reason,
            "observation": observation,
            "action": action,
            "outcome": outcome,
            "preference": preference,
            "semantic_score": semantic_score,
            "context_score": context_score,
            "final_score": final_score,
        }

    # ========================================================
    # RELLENAR RESPUESTA
    # ========================================================

    def fill_response(
        self,
        response,
        memory_response,
    ):

        recommendation = (
            self.build_navigation_recommendation(
                memory_response
            )
        )

        if not recommendation["success"]:

            response.success = False

            response.message = (
                recommendation["message"]
            )

            return

        response.success = True

        response.message = (
            recommendation["message"]
        )

        response.strategy = (
            recommendation["strategy"]
        )

        response.avoid_obstacle = (
            recommendation["avoid_obstacle"]
        )

        response.prefer_clearance = (
            recommendation["prefer_clearance"]
        )

        response.source_memory = (
            recommendation["source_memory"]
        )

        response.reason = (
            recommendation["reason"]
        )

        response.observation = (
            recommendation["observation"]
        )

        response.action = (
            recommendation["action"]
        )

        response.outcome = (
            recommendation["outcome"]
        )

        response.preference = (
            recommendation["preference"]
        )

        response.semantic_score = (
            recommendation["semantic_score"]
        )

        response.context_score = (
            recommendation["context_score"]
        )

        response.final_score = (
            recommendation["final_score"]
        )

    # ========================================================
    # CALLBACK DEL SERVICIO
    # ========================================================

    def handle_recommendation(
        self,
        request,
        response,
    ):

        self.get_logger().info(
            ""
        )

        self.get_logger().info(
            "=" * 70
        )

        self.get_logger().info(
            "NUEVA PETICIÓN DE RECOMENDACIÓN"
        )

        self.get_logger().info(
            "=" * 70
        )

        self.get_logger().info(
            f"Query: {request.query}"
        )

        self.get_logger().info(
            f"Usuario: {request.user_id}"
        )

        self.get_logger().info(
            f"Ubicación: {request.location}"
        )

        self.get_logger().info(
            f"Tarea: {request.task}"
        )

        self.get_logger().info(
            f"Objetivo: {request.goal}"
        )

        # ----------------------------------------------------
        # Crear petición interna
        # ----------------------------------------------------

        memory_request = MemoryQuery.Request()

        memory_request.query = request.query

        memory_request.user_id = (
            request.user_id or ""
        )

        memory_request.location = (
            request.location or ""
        )

        memory_request.task = (
            request.task or ""
        )

        memory_request.goal = (
            request.goal or ""
        )

        memory_request.k = (
            request.k
            if request.k > 0
            else 5
        )

        # ----------------------------------------------------
        # Lanzar consulta asíncrona
        # ----------------------------------------------------

        self.get_logger().info(
            "Consultando /memory/query..."
        )

        future = self.memory_client.call_async(
            memory_request
        )

        # ----------------------------------------------------
        # Esperar a que termine la consulta
        #
        # El callback group es Reentrant y el executor
        # principal es MultiThreadedExecutor.
        # ----------------------------------------------------

        while rclpy.ok() and not future.done():

            time.sleep(0.05)

        # ----------------------------------------------------
        # Comprobar resultado
        # ----------------------------------------------------

        if not future.done():

            response.success = False

            response.message = (
                "La consulta de memoria no terminó."
            )

            return response

        try:

            memory_response = (
                future.result()
            )

            # ------------------------------------------------
            # Construir recomendación
            # ------------------------------------------------

            self.fill_response(
                response,
                memory_response,
            )

            self.get_logger().info(
                "Recomendación generada."
            )

            self.get_logger().info(
                f"Strategy: "
                f"{response.strategy}"
            )

            self.get_logger().info(
                f"Avoid obstacle: "
                f"{response.avoid_obstacle}"
            )

            self.get_logger().info(
                f"Prefer clearance: "
                f"{response.prefer_clearance}"
            )

            self.get_logger().info(
                f"Source memory: "
                f"{response.source_memory}"
            )

            self.get_logger().info(
                f"Final score: "
                f"{response.final_score:.4f}"
            )

        except Exception as error:

            response.success = False

            response.message = (
                f"Error consultando memoria: "
                f"{error}"
            )

            self.get_logger().error(
                response.message
            )

        return response


# ============================================================
# MAIN
# ============================================================

def main(args=None):

    rclpy.init(args=args)

    node = NavigationMemoryNode()

    executor = MultiThreadedExecutor(
        num_threads=2
    )

    executor.add_node(node)

    try:

        executor.spin()

    except KeyboardInterrupt:

        pass

    finally:

        executor.shutdown()

        node.destroy_node()

        rclpy.shutdown()


if __name__ == "__main__":
    main()
