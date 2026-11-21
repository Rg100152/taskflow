"""SQLite3 persistence layer for TaskFlow Pro.

Stores the full project schedule locally in ``taskflow.db`` next to main.py.
Auto-creates the schema and seeds six realistic developer tasks on first run.
Only Python's built-in ``sqlite3`` is used.
"""
from __future__ import annotations

import os
import sqlite3
import threading
from contextlib import closing
from datetime import date, timedelta
from typing import Any, Iterable

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "taskflow.db")

STATUSES = ("To Do", "In Progress", "Completed")
PRIORITIES = ("High", "Medium", "Low")


class DatabaseManager:
    """Thin, thread-safe-enough CRUD wrapper around one SQLite connection."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or DEFAULT_DB_PATH
        self._write_lock = threading.Lock()
        self._init_schema()
        if self.count_tasks() == 0:
            self.seed_sample_tasks()

    # ------------------------------------------------------------------ #
    # Connection helpers
    # ------------------------------------------------------------------ #
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_schema(self) -> None:
        with closing(self._connect()) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    title       TEXT    NOT NULL,
                    description TEXT    NOT NULL DEFAULT '',
                    status      TEXT    NOT NULL DEFAULT 'To Do'
                                CHECK (status IN ('To Do','In Progress','Completed')),
                    priority    TEXT    NOT NULL DEFAULT 'Medium'
                                CHECK (priority IN ('High','Medium','Low')),
                    start_date  TEXT    NOT NULL,
                    end_date    TEXT    NOT NULL,
                    progress    INTEGER NOT NULL DEFAULT 0
                                CHECK (progress BETWEEN 0 AND 100),
                    assignee    TEXT    NOT NULL DEFAULT '',
                    source      TEXT    NOT NULL DEFAULT 'local',
                    github_id   TEXT,
                    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                    updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_tasks_github_id "
                "ON tasks(github_id) WHERE github_id IS NOT NULL"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)"
            )
            conn.commit()

    # ------------------------------------------------------------------ #
    # Row conversion
    # ------------------------------------------------------------------ #
    @staticmethod
    def _as_dict(row: sqlite3.Row) -> dict[str, Any]:
        return dict(row)

    # ------------------------------------------------------------------ #
    # READ
    # ------------------------------------------------------------------ #
    def get_all_tasks(self, search: str = "", status: str | None = None) -> list[dict[str, Any]]:
        """Return tasks ordered by status, priority then due date.

        ``search`` filters across title / description / assignee.
        """
        query = "SELECT * FROM tasks WHERE 1=1"
        params: list[Any] = []
        if search:
            query += " AND (title LIKE ? OR description LIKE ? OR assignee LIKE ?)"
            term = f"%{search}%"
            params.extend([term, term, term])
        if status:
            query += " AND status = ?"
            params.append(status)
        query += (
            " ORDER BY CASE status WHEN 'To Do' THEN 0 WHEN 'In Progress' THEN 1 ELSE 2 END,"
            " CASE priority WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 ELSE 2 END,"
            " end_date ASC, id ASC"
        )
        with closing(self._connect()) as conn:
            return [self._as_dict(r) for r in conn.execute(query, params).fetchall()]

    def get_task(self, task_id: int) -> dict[str, Any] | None:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            return self._as_dict(row) if row else None

    def count_tasks(self) -> int:
        with closing(self._connect()) as conn:
            return int(conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0])

    def github_issue_exists(self, github_id: str) -> bool:
        with closing(self._connect()) as conn:
            return conn.execute(
                "SELECT 1 FROM tasks WHERE github_id = ?", (str(github_id),)
            ).fetchone() is not None

    def get_stats(self) -> dict[str, Any]:
        """Live KPI values used by the dashboard header."""
        today = date.today().isoformat()
        with closing(self._connect()) as conn:
            totals = conn.execute(
                """
                SELECT
                  COUNT(*)                                                   AS total,
                  SUM(status = 'To Do')                                      AS todo,
                  SUM(status = 'In Progress')                                AS in_progress,
                  SUM(status = 'Completed')                                  AS completed,
                  SUM(priority = 'High' AND status != 'Completed')            AS high_open,
                  SUM(status != 'Completed' AND end_date < ?)                 AS overdue
                FROM tasks
                """,
                (today,),
            ).fetchone()
        total = int(totals["total"] or 0)
        done = int(totals["completed"] or 0)
        return {
            "total": total,
            "todo": int(totals["todo"] or 0),
            "in_progress": int(totals["in_progress"] or 0),
            "completed": done,
            "completion_pct": round((done / total) * 100) if total else 0,
            "overdue": int(totals["overdue"] or 0),
            "high_open": int(totals["high_open"] or 0),
        }

    # ------------------------------------------------------------------ #
    # WRITE
    # ------------------------------------------------------------------ #
    def add_task(self, *, title: str, description: str = "", status: str = "To Do",
                 priority: str = "Medium", start_date: str | None = None,
                 end_date: str | None = None, progress: int = 0,
                 assignee: str = "Raj Gautam", source: str = "local",
                 github_id: str | None = None) -> int:
        today = date.today().isoformat()
        start_date = start_date or today
        end_date = end_date or (date.today() + timedelta(days=5)).isoformat()
        if status not in STATUSES:
            status = "To Do"
        if priority not in PRIORITIES:
            priority = "Medium"
        if status == "Completed":
            progress = 100
        progress = max(0, min(100, int(progress)))

        with self._write_lock, closing(self._connect()) as conn:
            cur = conn.execute(
                """
                INSERT INTO tasks
                  (title, description, status, priority, start_date, end_date,
                   progress, assignee, source, github_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (title.strip(), description.strip(), status, priority, start_date,
                 end_date, progress, assignee.strip() or "Unassigned", source, github_id),
            )
            conn.commit()
            return int(cur.lastrowid)

    def update_task(self, task_id: int, **fields: Any) -> bool:
        """Update any subset of editable columns (whitelisted)."""
        allowed = {
            "title", "description", "status", "priority", "start_date",
            "end_date", "progress", "assignee",
        }
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return False
        if "status" in updates and updates["status"] not in STATUSES:
            updates.pop("status")
        if "priority" in updates and updates["priority"] not in PRIORITIES:
            updates.pop("priority")
        if "progress" in updates:
            updates["progress"] = max(0, min(100, int(updates["progress"])))
        if updates.get("status") == "Completed":
            updates["progress"] = 100
        if not updates:
            return False

        assignments = ", ".join(f"{key} = ?" for key in updates)
        params = list(updates.values()) + [task_id]
        with self._write_lock, closing(self._connect()) as conn:
            conn.execute(
                f"UPDATE tasks SET {assignments}, updated_at = datetime('now') WHERE id = ?",
                params,
            )
            conn.commit()
            return True

    def move_task(self, task_id: int, status: str) -> bool:
        """Move a task to an explicit Kanban column."""
        return self.update_task(task_id, status=status)

    def shift_task(self, task_id: int, direction: int) -> bool:
        """Move a task one column left (-1) or right (+1). Returns False at edges."""
        task = self.get_task(task_id)
        if not task:
            return False
        current = STATUSES.index(task["status"]) if task["status"] in STATUSES else 0
        target = current + direction
        if target < 0 or target >= len(STATUSES):
            return False
        return self.move_task(task_id, STATUSES[target])

    def delete_task(self, task_id: int) -> bool:
        with self._write_lock, closing(self._connect()) as conn:
            cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
            conn.commit()
            return cur.rowcount > 0

    def bulk_add(self, tasks: Iterable[dict[str, Any]]) -> int:
        """Insert many tasks at once (used by the GitHub importer). Skips duplicates."""
        added = 0
        for task in tasks:
            gid = task.get("github_id")
            if gid and self.github_issue_exists(str(gid)):
                continue
            self.add_task(**task)
            added += 1
        return added

    # ------------------------------------------------------------------ #
    # Seeder
    # ------------------------------------------------------------------ #
    def seed_sample_tasks(self) -> None:
        """Six realistic developer tasks spread across the three columns."""
        t = date.today()
        samples = [
            dict(title="Design SQLite schema & CRUD layer",
                 description="Define tasks table, indexes and the DatabaseManager API used by all views.",
                 status="Completed", priority="High",
                 start_date=(t - timedelta(days=6)).isoformat(),
                 end_date=(t - timedelta(days=3)).isoformat(),
                 progress=100, assignee="Raj Gautam"),
            dict(title="Build dark-themed Kanban board",
                 description="Three columns with priority badges, one-click stage moves and delete controls.",
                 status="Completed", priority="High",
                 start_date=(t - timedelta(days=5)).isoformat(),
                 end_date=(t - timedelta(days=1)).isoformat(),
                 progress=100, assignee="Raj Gautam"),
            dict(title="Render interactive Gantt timeline",
                 description="Canvas-driven timeline bars with progress fill, date grid and today marker.",
                 status="In Progress", priority="High",
                 start_date=(t - timedelta(days=2)).isoformat(),
                 end_date=(t + timedelta(days=3)).isoformat(),
                 progress=65, assignee="Raj Gautam"),
            dict(title="Wire GitHub Issues import API",
                 description="Fetch open issues from a public repository with urllib in a background thread.",
                 status="In Progress", priority="Medium",
                 start_date=t.isoformat(),
                 end_date=(t + timedelta(days=4)).isoformat(),
                 progress=40, assignee="Raj Gautam"),
            dict(title="Add CSV report exporter",
                 description="Export tasks, timeline dates and status into a clean shareable CSV file.",
                 status="To Do", priority="Medium",
                 start_date=(t + timedelta(days=2)).isoformat(),
                 end_date=(t + timedelta(days=6)).isoformat(),
                 progress=0, assignee="Raj Gautam"),
            dict(title="Write README & publish to GitHub",
                 description="Add logo, downloaded banner, screenshot, Mermaid DFD and developer credits.",
                 status="To Do", priority="Low",
                 start_date=(t + timedelta(days=5)).isoformat(),
                 end_date=(t + timedelta(days=9)).isoformat(),
                 progress=0, assignee="Raj Gautam"),
        ]
        with self._write_lock, closing(self._connect()) as conn:
            for s in samples:
                conn.execute(
                    """
                    INSERT INTO tasks
                      (title, description, status, priority, start_date, end_date,
                       progress, assignee)
                    VALUES (:title, :description, :status, :priority, :start_date,
                            :end_date, :progress, :assignee)
                    """,
                    s,
                )
            conn.commit()
