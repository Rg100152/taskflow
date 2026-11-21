"""CSV report exporter for TaskFlow Pro (built-in ``csv`` module only)."""
from __future__ import annotations

import csv
import os
from datetime import date, datetime
from typing import Any

from database.db_manager import DatabaseManager

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HEADERS = [
    "ID", "Task", "Description", "Status", "Priority",
    "Start Date", "End Date", "Progress %", "Assignee", "Source",
    "Days Remaining", "Created At",
]


class CSVExporter:
    """Turns the task table into a clean, shareable timeline report."""

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def export(self, tasks: list[dict[str, Any]] | None = None,
               path: str | None = None) -> str:
        """Write a CSV and return the saved file path.

        If ``path`` is omitted a timestamped file is created next to main.py.
        """
        rows = tasks if tasks is not None else self.db.get_all_tasks()
        if not path:
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(BASE_DIR, f"taskflow_report_{stamp}.csv")

        today = date.today()
        with open(path, "w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.writer(handle)
            writer.writerow(["TaskFlow Pro — Project Progress Report"])
            writer.writerow(["Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
            writer.writerow(["Developer", "Raj Gautam"])
            writer.writerow([])
            writer.writerow(HEADERS)
            for task in rows:
                try:
                    end = date.fromisoformat(str(task.get("end_date", ""))[:10])
                    remaining = (end - today).days
                except (ValueError, TypeError):
                    remaining = ""
                writer.writerow([
                    task.get("id", ""),
                    task.get("title", ""),
                    (task.get("description", "") or "").replace("\n", " "),
                    task.get("status", ""),
                    task.get("priority", ""),
                    task.get("start_date", ""),
                    task.get("end_date", ""),
                    task.get("progress", 0),
                    task.get("assignee", ""),
                    task.get("source", "local"),
                    remaining,
                    task.get("created_at", ""),
                ])
            stats = self.db.get_stats()
            writer.writerow([])
            writer.writerow(["SUMMARY", "Total", stats["total"], "Completed", stats["completed"],
                             "Completion %", stats["completion_pct"], "Overdue", stats["overdue"]])
        return path
