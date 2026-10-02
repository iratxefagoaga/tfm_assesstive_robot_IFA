"""canonical_memory_fingerprint_v2: explicit, read-only memory snapshot.

Historical fingerprint is a different, unrecovered procedure.
Logical content and embeddings are hashed separately. Neither is computed
against the experimental DB during G2a.
"""
import hashlib
import json

METHOD = "canonical_memory_fingerprint_v2"
LOGICAL_COLUMNS = (
    "memory_id", "user_id", "timestamp", "location", "task", "goal",
    "observation", "action", "outcome", "preference", "memory_type",
    "importance", "confidence", "textual_summary", "metadata",
)
VECTOR_COLUMNS = ("memory_id", "embedding", "episodic_embedding")
SELECT_SQL = """
SELECT memory_id, user_id,
       to_char(timestamp, 'YYYY-MM-DD"T"HH24:MI:SS.US') AS timestamp,
       location, task, goal, observation, action, outcome, preference,
       memory_type, importance::text AS importance,
       confidence::text AS confidence, textual_summary, metadata::text AS metadata,
       embedding::text AS embedding, episodic_embedding::text AS episodic_embedding
FROM memory_episodes
ORDER BY memory_id COLLATE "C"
"""


def _digest(rows, columns, component):
    payload = {
        "method": METHOD, "component": component,
        "columns": list(columns),
        "rows": [[row[column] for column in columns] for row in rows],
    }
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def fingerprint_rows(rows):
    rows = sorted(rows, key=lambda row: row["memory_id"].encode("utf-8"))
    ids = [row["memory_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate memory_id")
    return {
        "method": METHOD,
        "row_count": len(rows),
        "logical_sha256": _digest(rows, LOGICAL_COLUMNS, "logical"),
        "embeddings_sha256": _digest(rows, VECTOR_COLUMNS, "embeddings"),
    }


def main():
    # Runtime imports are lazy; fixture tests never need a PostgreSQL connection.
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from memory.config import memory_database_url
    connection = None
    try:
        connection = psycopg2.connect(memory_database_url())
        connection.set_session(readonly=True, isolation_level="REPEATABLE READ")
        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(SELECT_SQL)
            result = fingerprint_rows(cursor.fetchall())
        connection.rollback()
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception as error:
        # Drivers may embed DSNs in error messages: report only the exception type.
        print(json.dumps({"method": METHOD, "error_type": type(error).__name__}))
        return 1
    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
