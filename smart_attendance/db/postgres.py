import os

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - exercised only when dependency is missing
    psycopg = None
    dict_row = None


def is_database_enabled():
    return psycopg is not None and bool(os.getenv("DATABASE_URL"))


def get_connection():
    if not is_database_enabled():
        raise RuntimeError("DATABASE_URL is not configured or psycopg is not installed.")

    return psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row)
