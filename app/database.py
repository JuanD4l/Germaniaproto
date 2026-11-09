import sqlite3
import pymysql
from pymysql.cursors import DictCursor
from flask import g, current_app

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False


def dict_factory(cursor, row):
    """Convierte filas de SQLite en diccionarios."""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


def get_db():
    """
    Retorna la conexión activa a la base de datos dentro del contexto de Flask.
    Soporta PostgreSQL (Render), MariaDB/MySQL y SQLite (desarrollo/testing).
    """
    if "db" not in g:
        config = current_app.config
        db_type = config.get("DB_TYPE", "sqlite")

        if config.get("TESTING"):
            db_path = config.get("TEST_DB_PATH", ":memory:")
            g.db = sqlite3.connect(db_path)
            g.db.row_factory = dict_factory
            g.db.execute("PRAGMA foreign_keys = ON;")
        elif db_type == "postgres" and config.get("DATABASE_URL") and HAS_PSYCOPG2:
            g.db = psycopg2.connect(
                config["DATABASE_URL"],
                cursor_factory=RealDictCursor
            )
        elif db_type == "mysql":
            g.db = pymysql.connect(
                host=config["DB_HOST"],
                port=config["DB_PORT"],
                user=config["DB_USER"],
                password=config["DB_PASSWORD"],
                database=config["DB_NAME"],
                charset="utf8mb4",
                cursorclass=DictCursor,
                autocommit=False,
            )
        else:
            # Fallback a SQLite local para máxima portabilidad
            db_path = config.get("SQLITE_DB_PATH", "germania_local.db")
            g.db = sqlite3.connect(db_path)
            g.db.row_factory = dict_factory
            g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db


def close_db(e=None):
    """Cierra la conexión al finalizar la petición."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _format_query(db, query: str) -> str:
    """Adapta transparentemente la sintaxis de placeholders (%s vs ?) según el motor."""
    if isinstance(db, sqlite3.Connection):
        return query.replace("%s", "?")
    return query


def query_db(query, args=(), one=False):
    """
    Ejecuta consultas de selección (SELECT) de forma parametrizada y segura.
    Retorna una lista de diccionarios o un diccionario individual si one=True.
    """
    db = get_db()
    formatted_query = _format_query(db, query)
    cursor = db.cursor()
    cursor.execute(formatted_query, args)
    rv = cursor.fetchall()
    cursor.close()
    return (rv[0] if rv else None) if one else rv


def execute_db(query, args=(), commit=True):
    """
    Ejecuta sentencias DML (INSERT, UPDATE, DELETE) de forma parametrizada.
    Retorna el ID autoincremental generado y la cantidad de filas afectadas.
    """
    db = get_db()
    formatted_query = _format_query(db, query)
    cursor = db.cursor()
    cursor.execute(formatted_query, args)

    last_id = None
    if hasattr(cursor, "lastrowid"):
        last_id = cursor.lastrowid

    row_count = cursor.rowcount
    if commit:
        db.commit()
    cursor.close()
    return {"lastrowid": last_id, "rowcount": row_count}
