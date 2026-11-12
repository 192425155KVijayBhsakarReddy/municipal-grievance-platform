import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from flask import has_app_context, current_app
from backend.config import Config

def get_connection(db_path=None):
    if db_path is None:
        if has_app_context():
            db_path = current_app.config.get("DATABASE_PATH", Config.DATABASE_PATH)
        else:
            db_path = Config.DATABASE_PATH
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@contextmanager
def db_session(db_path=None):
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db(db_path=None):
    """Initializes tables for grievances, audit logs, and citizen feedback."""
    with db_session(db_path) as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tracking_id TEXT UNIQUE NOT NULL,
                citizen_name TEXT NOT NULL,
                citizen_phone TEXT NOT NULL,
                category TEXT NOT NULL,
                ward TEXT NOT NULL,
                location TEXT NOT NULL,
                description TEXT NOT NULL,
                photo_url TEXT,
                priority TEXT NOT NULL DEFAULT 'Medium',
                status TEXT NOT NULL DEFAULT 'SUBMITTED',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                sla_deadline TEXT NOT NULL,
                assigned_engineer TEXT,
                resolution_notes TEXT,
                resolution_proof TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tracking_id TEXT NOT NULL,
                action TEXT NOT NULL,
                from_status TEXT,
                to_status TEXT,
                performed_by TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                notes TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tracking_id TEXT UNIQUE NOT NULL,
                rating INTEGER NOT NULL,
                comments TEXT,
                submitted_at TEXT NOT NULL
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracking ON complaints(tracking_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON complaints(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ward ON complaints(ward)")
