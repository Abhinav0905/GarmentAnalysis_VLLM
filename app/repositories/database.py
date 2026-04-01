from __future__ import annotations

import sqlite3
from pathlib import Path


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON;")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS garments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_path TEXT NOT NULL,
                    original_filename TEXT NOT NULL,
                    designer TEXT,
                    captured_at TEXT,
                    year INTEGER,
                    month INTEGER,
                    location_hint TEXT,
                    description TEXT NOT NULL,
                    garment_type TEXT,
                    style TEXT,
                    material TEXT,
                    color_palette TEXT NOT NULL,
                    pattern TEXT,
                    season TEXT,
                    occasion TEXT,
                    consumer_profile TEXT,
                    trend_notes TEXT NOT NULL,
                    continent TEXT,
                    country TEXT,
                    city TEXT,
                    ai_tags TEXT NOT NULL,
                    raw_model_output TEXT NOT NULL,
                    token_estimate INTEGER NOT NULL,
                    model_name TEXT,
                    token_source TEXT NOT NULL DEFAULT 'estimate',
                    input_tokens INTEGER NOT NULL DEFAULT 0,
                    output_tokens INTEGER NOT NULL DEFAULT 0,
                    total_tokens INTEGER NOT NULL DEFAULT 0,
                    cached_input_tokens INTEGER NOT NULL DEFAULT 0,
                    input_cost_usd REAL,
                    output_cost_usd REAL,
                    total_cost_usd REAL,
                    trace_id TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS annotations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    garment_id INTEGER NOT NULL REFERENCES garments(id) ON DELETE CASCADE,
                    note TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE VIRTUAL TABLE IF NOT EXISTS garment_search USING fts5(
                    garment_id UNINDEXED,
                    description,
                    trend_notes,
                    ai_tags,
                    user_annotations,
                    location_text,
                    tokenize='unicode61'
                );
                """
            )
            self._ensure_column(connection, "garments", "model_name", "TEXT")
            self._ensure_column(connection, "garments", "token_source", "TEXT NOT NULL DEFAULT 'estimate'")
            self._ensure_column(connection, "garments", "input_tokens", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(connection, "garments", "output_tokens", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(connection, "garments", "total_tokens", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(connection, "garments", "cached_input_tokens", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(connection, "garments", "input_cost_usd", "REAL")
            self._ensure_column(connection, "garments", "output_cost_usd", "REAL")
            self._ensure_column(connection, "garments", "total_cost_usd", "REAL")
            connection.execute(
                """
                UPDATE garments
                SET total_tokens = token_estimate,
                    token_source = 'estimate'
                WHERE total_tokens = 0
                  AND token_estimate > 0
                """
            )

    def _ensure_column(self, connection: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
        columns = {
            row["name"]
            for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        if column_name in columns:
            return
        connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")
