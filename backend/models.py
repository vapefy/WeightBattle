"""
Database models and schema for Weight Battle application.
Uses SQLite with raw SQL for simplicity.
"""

import sqlite3
import os
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
from typing import Optional

# Allow database path to be configured via environment variable for Docker
DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", Path(__file__).parent / "db.sqlite"))

# Default values (used if not configured)
DEFAULT_POT_CONTRIBUTION = 5  # Euros per losing week
DEFAULT_BATTLE_END_DATE = "2026-04-05"  # Easter Sunday


def get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory enabled."""
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")  # Better concurrency
    conn.execute("PRAGMA busy_timeout = 30000")  # Wait up to 30s if locked
    return conn


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize the database with all required tables."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Config table for app settings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                start_weight REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Weigh-ins table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weigh_ins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                week_start DATE NOT NULL,
                weight REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, week_start)
            )
        """)

        # Weekly results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS weekly_results (
                week_start DATE PRIMARY KEY,
                winner_user_id INTEGER,
                loser_user_id INTEGER,
                pot_change INTEGER DEFAULT 0,
                FOREIGN KEY (winner_user_id) REFERENCES users(id),
                FOREIGN KEY (loser_user_id) REFERENCES users(id)
            )
        """)

        # Audit log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity TEXT NOT NULL,
                entity_id INTEGER NOT NULL,
                old_value TEXT,
                new_value TEXT,
                changed_by TEXT NOT NULL,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_weigh_ins_user_id
            ON weigh_ins(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_weigh_ins_week_start
            ON weigh_ins(week_start)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_log_entity
            ON audit_log(entity, entity_id)
        """)


# ============================================================================
# Config Functions
# ============================================================================

def get_config(key: str, default: str = None) -> Optional[str]:
    """Get a config value by key."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row:
            return row["value"]
        return default


def set_config(key: str, value: str) -> None:
    """Set a config value."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)
        """, (key, value))


def get_all_config() -> dict:
    """Get all config values."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT key, value FROM config")
        return {row["key"]: row["value"] for row in cursor.fetchall()}


def is_setup_complete() -> bool:
    """Check if the initial setup has been completed."""
    with get_db() as conn:
        cursor = conn.cursor()
        # Setup is complete if we have at least one user and battle_end_date is set
        cursor.execute("SELECT COUNT(*) as count FROM users")
        user_count = cursor.fetchone()["count"]

        cursor.execute("SELECT value FROM config WHERE key = 'setup_complete'")
        setup_flag = cursor.fetchone()

        return user_count > 0 and setup_flag is not None


def get_pot_contribution() -> int:
    """Get the pot contribution amount per loss."""
    value = get_config("pot_contribution")
    return int(value) if value else DEFAULT_POT_CONTRIBUTION


def get_battle_end_date() -> str:
    """Get the battle end date."""
    return get_config("battle_end_date", DEFAULT_BATTLE_END_DATE)


def get_total_amount() -> int:
    """Get the total amount for the final payment (e.g., dinner)."""
    value = get_config("total_amount")
    return int(value) if value else 100  # Default 100 EUR


# Initialize database on module import
init_db()
