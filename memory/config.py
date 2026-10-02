import os
from urllib.parse import quote_plus


_REQUIRED = (
    "MEMORY_DB_HOST",
    "MEMORY_DB_PORT",
    "MEMORY_DB_NAME",
    "MEMORY_DB_USER",
    "MEMORY_DB_PASSWORD",
)


def _required(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing required memory configuration variable: {name}"
        )
    return value


def memory_database_url():
    host = _required("MEMORY_DB_HOST")
    port = _required("MEMORY_DB_PORT")
    database = _required("MEMORY_DB_NAME")
    user = _required("MEMORY_DB_USER")
    password = _required("MEMORY_DB_PASSWORD")

    return (
        f"postgresql://{quote_plus(user)}:{quote_plus(password)}"
        f"@{host}:{port}/{database}"
    )
