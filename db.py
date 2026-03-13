import os
import sqlite3
from typing import List, Dict

class Database:

    def __init__(self, db_path: str = os.getenv("DB_PATH")):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        cursor = self.conn.cursor()

        # Access tokens table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS access_tokens (
            access_token TEXT,
            expiry INTEGER,
            refresh_token TEXT
        )
        """)

        # Messages table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            message_id TEXT PRIMARY KEY,
            chat_id TEXT,
            timestamp INTEGER,
            role TEXT CHECK(role IN ('user','assistant')),
            content TEXT
        )
        """)

        self.conn.commit()

    # -------------------------
    # Access Token Methods
    # -------------------------

    def fetch_access_token(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT access_token, expiry, refresh_token FROM access_tokens LIMIT 1")
        row = cursor.fetchone()

        if not row:
            return None

        return {
            "accessToken": row["access_token"],
            "accessTokenExpiry": row["expiry"],
            "refreshToken": row["refresh_token"]
        }

    def update_access_token(self, access_token: str, access_token_expiry: int, refresh_token: str):
        cursor = self.conn.cursor()

        # Replace existing token
        cursor.execute("DELETE FROM access_tokens")

        cursor.execute("""
        INSERT INTO access_tokens (access_token, expiry, refresh_token)
        VALUES (?, ?, ?)
        """, (access_token, access_token_expiry, refresh_token))

        self.conn.commit()

    # -------------------------
    # Message Methods
    # -------------------------

    def list_last_messages(self, chat_id: str, limit: int = 10) -> List[Dict]:
        cursor = self.conn.cursor()

        cursor.execute("""
        SELECT message_id, chat_id, timestamp, role, content
        FROM messages
        WHERE chat_id = ?
        ORDER BY timestamp DESC
        LIMIT ?
        """, (chat_id, limit))

        rows = cursor.fetchall()

        return [
            {
                "message_id": r["message_id"],
                "chat_id": r["chat_id"],
                "timestamp": r["timestamp"],
                "role": r["role"],
                "content": r["content"]
            }
            for r in rows
        ]

    def append_messages(self, messages: List[Dict]):
        """
        messages format:
        [
            {
                "message_id": "...",
                "chat_id": "...",
                "timestamp": 123456,
                "role": "user",
                "content": "hello"
            }
        ]
        """

        cursor = self.conn.cursor()

        cursor.executemany("""
        INSERT OR IGNORE INTO messages
        (message_id, chat_id, timestamp, role, content)
        VALUES (?, ?, ?, ?, ?)
        """, [
            (
                m["message_id"],
                m["chat_id"],
                m["timestamp"],
                m["role"],
                m["content"]
            )
            for m in messages
        ])

        self.conn.commit()

    def close(self):
        self.conn.close()