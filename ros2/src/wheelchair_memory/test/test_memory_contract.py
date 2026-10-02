"""Contracts exercised with the production callbacks and controlled backend."""
import importlib
import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest
import rclpy
from rclpy.node import Node
from wheelchair_interfaces.srv import MemoryQuery, NavigationRecommendation


@pytest.fixture
def modules(monkeypatch):
    # No model loading, PostgreSQL connections or experimental data access.
    encoder = types.ModuleType("sentence_transformers")
    encoder.SentenceTransformer = MagicMock()
    sqlalchemy = types.ModuleType("sqlalchemy")
    sqlalchemy.create_engine = MagicMock()
    sqlalchemy.text = lambda sql: sql
    monkeypatch.setitem(sys.modules, "sentence_transformers", encoder)
    monkeypatch.setitem(sys.modules, "sqlalchemy", sqlalchemy)
    backend = importlib.import_module("memory.memory_service")
    node = importlib.import_module("wheelchair_memory.memory_node")
    recommendation = importlib.import_module(
        "wheelchair_memory.navigation_memory_node"
    )
    return backend, node, recommendation


@pytest.fixture
def row():
    return dict(
        memory_id="M001", textual_summary="Fixture controlled",
        observation="Paso estrecho junto a la mesa.",
        action="Ruta oeste evitando la mesa.",
        outcome="Navegacion correcta.",
        preference="Prefiere mayor espacio lateral.",
        semantic_similarity=0.75, context_score=1.0, final_score=0.775,
        user_id="U01", location="salon", task="navegacion", goal="dormitorio",
    )


@pytest.fixture
def memory_node(modules, monkeypatch, row):
    backend = MagicMock()
    backend.retrieve_memories.return_value = [row]
    monkeypatch.setattr(modules[1], "MemoryService", lambda: backend)
    rclpy.init()
    node = modules[1].MemoryNode()
    yield node, backend
    node.destroy_node()
    rclpy.try_shutdown()


def request(k=3):
    return MemoryQuery.Request(
        query="navegar evitando la mesa", user_id="U01",
        location="salon", task="navegacion", goal="dormitorio", k=k,
    )


def query(node, k=3):
    return node.handle_memory_query(request(k), MemoryQuery.Response())


def test_node_construction(memory_node):
    node, backend = memory_node
    assert node.get_name() == "memory_node"
    assert node.service.srv_name == "/memory/query"
    backend.retrieve_memories.assert_not_called()


def test_valid_query(memory_node):
    node, backend = memory_node
    response = query(node)
    assert response.success and response.memory_ids == ["M001"]
    assert list(response.final_scores) == [0.775]
    backend.retrieve_memories.assert_called_once_with(
        query="navegar evitando la mesa", user_id="U01",
        location="salon", task="navegacion", goal="dormitorio", k=3,
    )


@pytest.mark.parametrize("k", [0, -1])
def test_invalid_k_uses_existing_default(memory_node, k):
    node, backend = memory_node
    assert query(node, k).success
    assert backend.retrieve_memories.call_args.kwargs["k"] == 5


def test_backend_failure(memory_node):
    node, backend = memory_node
    backend.retrieve_memories.side_effect = RuntimeError("controlled failure")
    response = query(node)
    assert not response.success
    assert response.message == "controlled failure"
    assert not response.memory_ids


def test_identical_query_cache(memory_node):
    node, backend = memory_node
    first, second = query(node), query(node)
    assert first.memory_ids == second.memory_ids
    assert first.final_scores == second.final_scores
    backend.retrieve_memories.assert_called_once()


def test_context_and_k_have_separate_cache(memory_node):
    node, backend = memory_node
    query(node, 3)
    query(node, 5)
    req = request()
    req.location = "cocina"
    node.handle_memory_query(req, MemoryQuery.Response())
    assert backend.retrieve_memories.call_count == 3


def test_failed_query_is_not_cached(memory_node):
    node, backend = memory_node
    backend.retrieve_memories.side_effect = [
        RuntimeError("controlled failure"), backend.retrieve_memories.return_value
    ]
    assert not query(node).success
    assert query(node).success
    assert backend.retrieve_memories.call_count == 2


def test_west_recommendation(memory_node, modules):
    response = query(memory_node[0])
    # Exercise the actual recommendation method, which uses no node state.
    recommendation = modules[2].NavigationMemoryNode.build_navigation_recommendation(
        None, response
    )
    assert recommendation["success"]
    assert recommendation["source_memory"] == "M001"
    assert recommendation["strategy"] == "west"
    assert recommendation["avoid_obstacle"]
    assert recommendation["prefer_clearance"]


def test_no_applicable_strategy(memory_node, modules):
    response = query(memory_node[0])
    response.actions = ["Llegada correcta"]
    response.observations = [""]
    response.preferences = [""]
    recommendation = modules[2].NavigationMemoryNode.build_navigation_recommendation(
        None, response
    )
    assert recommendation["strategy"] == "direct"
    assert not recommendation["avoid_obstacle"]
    assert not recommendation["prefer_clearance"]


@pytest.mark.parametrize("success", [False, True])
def test_recommendation_error_and_empty(modules, success):
    response = MemoryQuery.Response(success=success, message="controlled error")
    result = modules[2].NavigationMemoryNode.build_navigation_recommendation(
        None, response
    )
    assert not result["success"]


def test_navigation_node_construction(memory_node, modules):
    # The real query service exists in the same ROS context.
    node = modules[2].NavigationMemoryNode()
    try:
        assert node.recommendation_service.srv_name == "/memory/navigation_recommendation"
    finally:
        node.destroy_node()


def test_light_shutdown_and_idempotent_context():
    rclpy.init()
    node = Node("isolated_shutdown")
    node.destroy_node()
    rclpy.try_shutdown()
    rclpy.try_shutdown()
    assert not rclpy.ok()


def test_real_ros_services_with_controlled_backend(memory_node, modules):
    import threading
    from rclpy.executors import MultiThreadedExecutor
    node, backend = memory_node
    recommendation = modules[2].NavigationMemoryNode()
    client_node = Node("contract_client")
    executor = MultiThreadedExecutor(num_threads=3)
    for item in (node, recommendation, client_node):
        executor.add_node(item)
    thread = threading.Thread(target=executor.spin, daemon=True)
    thread.start()
    try:
        for service_type, name in (
            (MemoryQuery, "/memory/query"),
            (NavigationRecommendation, "/memory/navigation_recommendation"),
        ):
            client = client_node.create_client(service_type, name)
            assert client.wait_for_service(timeout_sec=5)
            req = service_type.Request(
                query="navegar evitando la mesa", user_id="U01",
                location="salon", task="navegacion", goal="dormitorio", k=3,
            )
            done = threading.Event()
            future = client.call_async(req)
            future.add_done_callback(lambda result: done.set())
            assert done.wait(5), "Controlled service did not reply"
            response = future.result()
            assert response.success
            if service_type is MemoryQuery:
                assert response.memory_ids == ["M001"]
            else:
                assert response.source_memory == "M001"
                assert response.strategy == "west"
            client_node.destroy_client(client)
    finally:
        executor.shutdown(timeout_sec=5)
        thread.join(timeout=5)
        assert not thread.is_alive()
        client_node.destroy_node()
        recommendation.destroy_node()


@pytest.mark.parametrize("iteration", [1, 2])
def test_single_sigint_exits_normally(tmp_path, iteration):
    import os
    import signal
    import subprocess
    import time

    script = Path(__file__).resolve().parents[2] / (
        "wheelchair_assistive_bt/scripts/managed_memory_process.py"
    )
    program = """
import importlib.util
import sys
import types
from types import SimpleNamespace
from rclpy.executors import SingleThreadedExecutor

backend = types.ModuleType("memory.memory_service")
backend.MemoryService = lambda: SimpleNamespace(retrieve_memories=lambda **kwargs: [])
sys.modules["memory.memory_service"] = backend
from wheelchair_memory.memory_node import MemoryNode

spec = importlib.util.spec_from_file_location("managed_lifecycle", sys.argv[1])
managed = importlib.util.module_from_spec(spec)
spec.loader.exec_module(managed)
def factory():
    node = MemoryNode()
    print("LIGHT_NODE_READY", flush=True)
    return node
managed.run_node(factory, SingleThreadedExecutor)
"""
    log = tmp_path / "shutdown.log"
    with log.open("w") as output:
        process = subprocess.Popen(
            [sys.executable, "-c", program, str(script)],
            stdout=output, stderr=subprocess.STDOUT,
        )
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if process.poll() is not None:
                break
            if "LIGHT_NODE_READY" in log.read_text():
                break
            time.sleep(0.05)
        assert "LIGHT_NODE_READY" in log.read_text()
        process.send_signal(signal.SIGINT)
        assert process.wait(timeout=20) == 0
    text = log.read_text()
    assert text.count("LIFECYCLE cleanup: complete") == 1
    assert "Traceback" not in text
