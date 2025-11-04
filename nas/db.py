from __future__ import annotations
from contextlib import contextmanager
from typing import Any, Dict, Iterable, Optional

import mysql.connector
from flask import current_app, g


def init_app(app):
    app.teardown_appcontext(close_db)
    app.logger.debug("Database helpers initialized")


def get_connection():
    if "db_conn" not in g:
        config = current_app.config
        g.db_conn = mysql.connector.connect(
            host=config["DB_HOST"],
            user=config["DB_USER"],
            password=config["DB_PASS"],
            database=config["DB_NAME"],
            autocommit=True,
        )
    return g.db_conn


def close_db(exception=None):
    conn = g.pop("db_conn", None)
    if conn is not None:
        conn.close()


@contextmanager
def cursor(dictionary: bool = True):
    conn = get_connection()
    cur = conn.cursor(dictionary=dictionary)
    try:
        yield cur
    finally:
        cur.close()


def query(sql: str, params: Optional[Iterable[Any]] = None, *, fetchone=False):
    with cursor() as cur:
        current_app.logger.debug("Executing SQL: %s params=%s", sql, params)
        cur.execute(sql, params or ())
        if cur.with_rows:
            return cur.fetchone() if fetchone else cur.fetchall()
        return None


def execute(sql: str, params: Optional[Iterable[Any]] = None):
    with cursor(dictionary=False) as cur:
        current_app.logger.debug("Executing SQL: %s params=%s", sql, params)
        cur.execute(sql, params or ())
        return cur.lastrowid


def init_db_schema(app):
    from pathlib import Path

    schema_path = Path(app.root_path).parent / "db" / "schema.sql"
    sql = schema_path.read_text()
    with cursor(dictionary=False) as cur:
        for statement in filter(None, sql.split(";")):
            stmt = statement.strip()
            if stmt:
                app.logger.debug("Running schema statement: %s", stmt[:100])
                cur.execute(stmt)


__all__ = [
    "init_app",
    "query",
    "execute",
    "init_db_schema",
]
