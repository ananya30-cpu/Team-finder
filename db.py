"""
db.py — MySQL connection helpers for College Project Team Finder.

Uses a connection pool for the application database user.
"""

import os
from decimal import Decimal
from datetime import date, datetime
from dotenv import load_dotenv
import mysql.connector
from mysql.connector import pooling

# Load backend/.env (passwords live here, never in source code)
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# --- Config from environment ---
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "college_team_finder")


# Connection pool so we do not open a new TCP connection on every request
_pool = pooling.MySQLConnectionPool(
    pool_name="team_finder_pool",
    pool_size=5,
    host=DB_HOST,
    port=DB_PORT,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME,
    ssl_disabled=False,
    autocommit=False,
)


def get_connection():
    """Borrow a connection from the main (read-write) pool."""
    return _pool.get_connection()


def make_json_safe(value):
    """Convert MySQL types (Decimal, date, datetime) into JSON-friendly values."""
    if value is None:
        return None
    if isinstance(value, Decimal):
        # Keep one decimal place look for averages, else float
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def rows_to_dicts(cursor):
    """Turn cursor.fetchall() into a list of plain dicts (JSON-safe)."""
    columns = [col[0] for col in cursor.description] if cursor.description else []
    result = []
    for row in cursor.fetchall():
        item = {}
        for i, col in enumerate(columns):
            item[col] = make_json_safe(row[i])
        result.append(item)
    return result


def fetch_all(sql, params=None):
    """Run a SELECT with parameters and return list of dicts."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params or ())
        data = rows_to_dicts(cursor)
        cursor.close()
        return data
    finally:
        conn.close()


def fetch_one(sql, params=None):
    """Run a SELECT and return one dict, or None."""
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


def execute_write(sql, params=None):
    """
    Run INSERT / UPDATE / DELETE / CALL.
    Returns (affected_rows, lastrowid).
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params or ())
        conn.commit()
        affected = cursor.rowcount
        last_id = cursor.lastrowid
        cursor.close()
        return affected, last_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def call_procedure(name, args):
    """
    CALL a stored procedure with arguments.
    Raises mysql.connector.Error on SIGNAL / SQL errors (message preserved).
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        # Build CALL name(%s, %s, ...) with placeholders
        placeholders = ", ".join(["%s"] * len(args))
        cursor.execute(f"CALL {name}({placeholders})", tuple(args))
        conn.commit()
        cursor.close()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# Proficiency ENUM → number (MySQL ENUM index order: BEGINNER=1 ... EXPERT=4)
PROFICIENCY_RANK = {
    "BEGINNER": 1,
    "INTERMEDIATE": 2,
    "ADVANCED": 3,
    "EXPERT": 4,
}


def proficiency_to_int(level):
    """Map proficiency ENUM string to 1–4 for comparisons."""
    if level is None:
        return 0
    return PROFICIENCY_RANK.get(str(level).upper(), 0)
