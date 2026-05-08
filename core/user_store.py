"""SQLite-backed user store for RBAC - persistent across restarts."""
import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "data/users.db"


class SQLiteUserStore:
    """SQLite-backed user storage - survives restarts."""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.getenv("USER_STORE_PATH", DEFAULT_DB_PATH)
        self._init_db()
    
    def _init_db(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    roles TEXT NOT NULL,
                    permissions TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    last_login REAL,
                    active INTEGER NOT NULL DEFAULT 1
                )
            """)
            conn.commit()
    
    def get(self, user_id: str) -> Optional[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
            if row:
                return dict(row)
        return None
    
    def get_by_email(self, email: str) -> Optional[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM users WHERE email = ?", (email,)
            ).fetchone()
            if row:
                return dict(row)
        return None
    
    def save(self, user: dict) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO users 
                (user_id, email, password_hash, roles, permissions, created_at, last_login, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user["user_id"],
                user["email"],
                user["password_hash"],
                json.dumps(user.get("roles", [])),
                json.dumps(user.get("permissions", [])),
                user.get("created_at", 0.0),
                user.get("last_login"),
                1 if user.get("active", True) else 0,
            ))
            conn.commit()
    
    def delete(self, user_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM users WHERE user_id = ?", (user_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    def list_users(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM users").fetchall()
            return [dict(row) for row in rows]


_store: Optional[SQLiteUserStore] = None


def get_user_store() -> SQLiteUserStore:
    global _store
    if _store is None:
        _store = SQLiteUserStore()
    return _store


__all__ = ["SQLiteUserStore", "get_user_store"]
