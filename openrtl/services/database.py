import json
import sqlite3
from pathlib import Path

from openrtl.config import config
from openrtl.exceptions import DatabaseError
from openrtl.logging import get_logger

log = get_logger("database")


class DatabaseService:
    """SQLite-backed persistence for project metadata."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self._db_path = str(db_path or config.db_path)
        self._init_db()

    def _init_db(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS projects (
                    project_name TEXT PRIMARY KEY,
                    folder_structure TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )"""
            )

    def _connect(self) -> sqlite3.Connection:
        try:
            conn = sqlite3.connect(self._db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            raise DatabaseError(f"Failed to connect to database: {e}") from e

    def save_project(self, project_name: str, structure: dict) -> None:
        with self._connect() as conn:
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO projects (project_name, folder_structure) VALUES (?, ?)",
                    (project_name, json.dumps(structure)),
                )
                conn.commit()
            except sqlite3.Error as e:
                raise DatabaseError(f"Failed to save project '{project_name}': {e}") from e

    def get_project(self, project_name: str) -> dict | None:
        with self._connect() as conn:
            try:
                row = conn.execute(
                    "SELECT folder_structure FROM projects WHERE project_name = ?",
                    (project_name,),
                ).fetchone()
                if row is None:
                    return None
                return json.loads(row["folder_structure"])
            except (sqlite3.Error, json.JSONDecodeError) as e:
                raise DatabaseError(f"Failed to get project '{project_name}': {e}") from e

    def list_projects(self) -> list[str]:
        with self._connect() as conn:
            try:
                rows = conn.execute(
                    "SELECT project_name FROM projects ORDER BY created_at DESC"
                ).fetchall()
                return [r["project_name"] for r in rows]
            except sqlite3.Error as e:
                raise DatabaseError(f"Failed to list projects: {e}") from e

    def delete_project(self, project_name: str) -> None:
        with self._connect() as conn:
            try:
                conn.execute(
                    "DELETE FROM projects WHERE project_name = ?",
                    (project_name,),
                )
                conn.commit()
            except sqlite3.Error as e:
                raise DatabaseError(f"Failed to delete project '{project_name}': {e}") from e
