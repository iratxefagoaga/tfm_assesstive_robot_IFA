"""Production retrieval exercised with fixtures and no model/database."""
import importlib
import sys
import types
from unittest.mock import MagicMock
import pytest
from memory.config import memory_database_url


def test_missing_config_is_explicit(monkeypatch):
    monkeypatch.delenv("MEMORY_DB_HOST", raising=False)
    with pytest.raises(RuntimeError, match="MEMORY_DB_HOST") as caught:
        memory_database_url()
    assert "postgresql://" not in str(caught.value)


def test_config_encodes_credentials(monkeypatch):
    for key, value in dict(HOST="localhost", PORT="5433", NAME="fixture",
                           USER="fixture", PASSWORD="synthetic@:/").items():
        monkeypatch.setenv("MEMORY_DB_" + key, value)
    result = memory_database_url()
    assert "synthetic%40%3A%2F" in result
    assert result.endswith("@localhost:5433/fixture")


@pytest.fixture
def service(monkeypatch):
    encoder = types.ModuleType("sentence_transformers")
    encoder.SentenceTransformer = MagicMock()
    database = types.ModuleType("sqlalchemy")
    database.create_engine = MagicMock()
    database.text = lambda query: query
    monkeypatch.setitem(sys.modules, "sentence_transformers", encoder)
    monkeypatch.setitem(sys.modules, "sqlalchemy", database)
    module = importlib.import_module("memory.memory_service")
    node = object.__new__(module.MemoryService)
    node.generate_embedding = MagicMock(return_value=[0.1, 0.2])
    node.engine = MagicMock()
    connection = node.engine.connect.return_value.__enter__.return_value
    rows = [
        dict(memory_id="M002", user_id="U01", location="cocina",
             task="navegacion", goal="otro", semantic_similarity=0.76,
             textual_summary="Other fixture", observation="", action="",
             outcome="", preference=""),
        dict(memory_id="M001", user_id="U01", location="salon",
             task="navegacion", goal="dormitorio", semantic_similarity=0.75,
             textual_summary="Equivalent fixture", observation="mesa",
             action="Ruta oeste evitando la mesa", outcome="correcto",
             preference="mayor espacio lateral"),
    ]
    connection.execute.return_value.mappings.return_value.all.return_value = rows
    return node, connection


def retrieve(node, k=3):
    return node.retrieve_memories(
        query="controlled query", user_id="U01", location="salon",
        task="navegacion", goal="dormitorio", k=k,
    )


def test_real_retrieval_deterministic(service):
    node, connection = service
    first, second = retrieve(node), retrieve(node)
    assert first == second
    assert [row["memory_id"] for row in first] == ["M001", "M002"]
    assert first[0]["final_score"] == pytest.approx(0.775)
    assert first[0]["context_score"] == 1.0


def test_retrieval_k_limit(service):
    assert [r["memory_id"] for r in retrieve(service[0], 1)] == ["M001"]


def test_retrieval_parameterizes_user(service):
    node, connection = service
    retrieve(node)
    sql, parameters = connection.execute.call_args.args
    assert ":user_id" in sql
    assert parameters["user_id"] == "U01"
    assert parameters["query_embedding"] == "[0.1,0.2]"


def test_retrieval_error_propagates(service):
    node, connection = service
    connection.execute.side_effect = RuntimeError("controlled database error")
    with pytest.raises(RuntimeError, match="controlled database error"):
        retrieve(node)


def test_empty_retrieval(service):
    node, connection = service
    connection.execute.return_value.mappings.return_value.all.return_value = []
    assert retrieve(node) == []


def test_episodic_text_uses_production_method(service):
    result = service[0].build_episodic_text(None, "route", None, "space")
    assert result == "Observation:  Action: route Outcome:  Preference: space"
