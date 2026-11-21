#!/usr/bin/env python3
"""TaskFlow Pro - Desktop Project Management Tool.

Developed by Raj Gautam  •  graj13099@gmail.com  •  @linuxuser.raj

A zero-dependency (stdlib only) Tkinter application featuring a dark Kanban
board, a Canvas-based interactive Gantt chart, SQLite persistence, CSV export
and live GitHub issue / quote / webhook integrations.

Run:  python3 main.py
"""
from __future__ import annotations

import os
import tkinter as tk
from datetime import date
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

from database.db_manager import DatabaseManager
from services.github_api import GitHubService, WebhookNotifier
from ui import theme as T
from ui.gantt_view import GanttView
from ui.kanban_view import KanbanView
from ui.modals import GitHubImportModal, TaskModal, WebhookModal
from utils.exporter import CSVExporter

APP_VERSION = "1.0.0"
MIN_WIDTH, MIN_HEIGHT = 1120, 720


class TaskFlowPro(tk.Tk):
    """Main application window / UI shell."""

    def __init__(self) -> None:
        super().__init__()
        self.title(f"TaskFlow Pro v{APP_VERSION}  —  Project Management Suite  |  Raj Gautam")
        self.configure(bg=T.BG)
        self.minsize(MIN_WIDTH, MIN_HEIGHT)
        self.geometry(self._startup_geometry(1480, 930))
        self.attributes("-alpha", 0.99)

        self.db = DatabaseManager()
        self.github = GitHubService(root=self)
        self.notifier = WebhookNotifier(root=self)

        self._configure_ttk()
        self._build_ui()
        self.refresh_all()
        self.github.fetch_quote_async(on_success=self._show_quote)

    # ------------------------------------------------------------------ #
    # Window helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _startup_geometry(width: int, height: int) -> str:
        return f"{width}x{height}+80+50"

    def _configure_ttk(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TNotebook", background=T.BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=T.PANEL, foreground=T.TEXT_MUTED,
                        padding=(20, 9), borderwidth=0,
                        font=T.make_font(10, "bold"))
        style.map("TNotebook.Tab",
                  background=[("selected", T.BG_SOFT)],
                  foreground=[("selected", T.ACCENT)])
        style.configure("TCombobox", fieldbackground=T.PANEL, background=T.PANEL,
                        foreground=T.TEXT, arrowcolor=T.TEXT_MUTED,
                        bordercolor=T.BORDER, lightcolor=T.PANEL, darkcolor=T.PANEL,
                        font=T.make_font(9))
        style.map("TCombobox", fieldbackground=[("readonly", T.PANEL)])

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #
    def _build_ui(self) -> None:
        self._build_navbar()
        self._build_kpis()
        self._build_toolbar()
        self._build_tabs()
        self._build_statusbar()

    def _build_navbar(self) -> None:
        nav = tk.Frame(self, bg=T.BG, height=72)
        nav.pack(fill="x", side="top")
        nav.pack_propagate(False)
        tk.Frame(nav, bg=T.BORDER_SOFT, height=1).pack(fill="x", side="bottom")

        self._draw_logo(nav).pack(side="left", padx=(22, 10), pady=12)

        title_box = tk.Frame(nav, bg=T.BG)
        title_box.pack(side="left", padx=(4, 20))
        tk.Label(title_box, text="PROJECT COMMAND CENTER", bg=T.BG, fg=T.ACCENT,
                 font=T.make_font(8, "bold")).pack(anchor="w", pady=(12, 0))
        tk.Label(title_box, text="Plan • Track • Ship", bg=T.BG, fg=T.TEXT_DIM,
                 font=T.make_font(8)).pack(anchor="w")

        self.quote_var = tk.StringVar(value="“Loading today's motivation…”")
        quote = tk.Label(nav, textvariable=self.quote_var, bg=T.BG, fg=T.TEXT_MUTED,
                         font=T.make_font(8), wraplength=430, justify="right", anchor="e")
        quote.pack(side="right", padx=(20, 24), fill="y", expand=True)

        self._button(nav, "⚙  Webhook", T.VIOLET, self._open_webhook).pack(side="right", pady=18)

    def _draw_logo(self, parent: tk.Misc) -> tk.Canvas:
        """Vector-style logo drawn directly on a Canvas (no image files)."""
        logo = tk.Canvas(parent, width=250, height=48, bg=T.BG, highlightthickness=0)
        T.round_rect(logo, 2, 3, 42, 45, radius=10, fill=T.PANEL, outline=T.ACCENT, width=1.6)
        T.round_rect(logo, 6, 7, 38, 41, radius=7, fill=T.BG_SOFT, outline="")
        logo.create_rectangle(11, 13, 22, 17, fill=T.RED, outline="")
        logo.create_rectangle(14, 22, 31, 26, fill=T.AMBER, outline="")
        logo.create_rectangle(11, 31, 34, 35, fill=T.EMERALD, outline="")

        font_main = T.make_font(17, "bold")
        logo.create_text(50, 23, anchor="w", text="TaskFlow", fill=T.TEXT, font=font_main)
        x_pro = 50 + font_main.measure("TaskFlow") + 2
        logo.create_text(x_pro, 23, anchor="w", text="Pro", fill=T.ACCENT, font=font_main)
        logo.create_text(51, 39, anchor="w", text="DESKTOP PROJECT MANAGER",
                         fill=T.TEXT_DIM, font=T.make_font(6, "bold"))
        return logo

    def _build_kpis(self) -> None:
        bar = tk.Frame(self, bg=T.BG_SOFT)
        bar.pack(fill="x", padx=18, pady=(14, 4))

        specs = [
            ("total", "TOTAL TASKS", T.ACCENT, "▦"),
            ("in_progress", "IN PROGRESS", T.AMBER, "◐"),
            ("completion_pct", "COMPLETED", T.EMERALD, "✓"),
            ("overdue", "OVERDUE", T.RED, "⚠"),
            ("high_open", "HIGH PRIORITY", T.VIOLET, "▲"),
        ]
        self.kpi_labels: dict[str, tk.Label] = {}
        for key, caption, color, icon in specs:
            card = tk.Frame(bar, bg=T.PANEL, highlightthickness=1,
                            highlightbackground=T.BORDER_SOFT)
            card.pack(side="left", fill="both", expand=True, padx=(0, 10))
            tk.Frame(card, bg=color, height=3).pack(fill="x", side="top")
            inner = tk.Frame(card, bg=T.PANEL)
            inner.pack(fill="both", expand=True, padx=14, pady=10)
            tk.Label(inner, text=icon, bg=T.PANEL, fg=color,
                     font=T.make_font(13, "bold")).pack(side="left", padx=(0, 10))
            value = tk.Label(inner, text="0", bg=T.PANEL, fg=T.TEXT,
                             font=T.make_font(20, "bold"))
            value.pack(side="left")
            self.kpi_labels[key] = value
            suffix = "%" if key == "completion_pct" else ""
            tk.Label(inner, text=suffix, bg=T.PANEL, fg=color,
                     font=T.make_font(10, "bold")).pack(side="left", padx=(2, 0))
            tk.Label(card, text=caption, bg=T.PANEL, fg=T.TEXT_MUTED,
                     font=T.make_font(8, "bold"), anchor="w").pack(fill="x", padx=14, pady=(0, 10))

    def _build_toolbar(self) -> None:
        bar = tk.Frame(self, bg=T.BG, height=58)
        bar.pack(fill="x", padx=18, pady=(10, 0))
        bar.pack_propagate(False)

        search_wrap = tk.Frame(bar, bg=T.PANEL, highlightthickness=1,
                               highlightbackground=T.BORDER)
        search_wrap.pack(side="left", fill="y", padx=(0, 10), ipadx=4)
        tk.Label(search_wrap, text="🔍", bg=T.PANEL, fg=T.TEXT_MUTED,
                 font=T.make_font(10)).pack(side="left", padx=(10, 4))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh_all())
        entry = tk.Entry(search_wrap, textvariable=self.search_var, bg=T.PANEL, fg=T.TEXT,
                         insertbackground=T.ACCENT, relief="flat", bd=0,
                         font=T.make_font(10), width=34, highlightthickness=0)
        entry.pack(side="left", fill="y", padx=(0, 8))
        entry.insert(0, "")
        tk.Label(search_wrap, text="Search tasks, assignees…", bg=T.PANEL,
                 fg=T.TEXT_DIM, font=T.make_font(8)).pack(side="left", padx=(0, 12))

        self._button(bar, "＋  Add Task", T.ACCENT, self._open_add_task, width=14).pack(side="right", padx=6)
        self._button(bar, "🔄  Import GitHub", T.VIOLET, self._open_import, width=17).pack(side="right", padx=6)
        self._button(bar, "📥  Export CSV", T.EMERALD, self._export_csv, width=15).pack(side="right", padx=6)

    def _build_tabs(self) -> None:
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=18, pady=(12, 4))

        self.kanban = KanbanView(
            self.notebook, self.db,
            on_change=self.refresh_all,
            on_edit=self._open_edit_task,
            on_notify=self._notify_completion,
        )
        self.gantt = GanttView(self.notebook, self.db, on_edit=self._open_edit_task)

        self.notebook.add(self.kanban, text="▦  Kanban Board")
        self.notebook.add(self.gantt, text="▤  Gantt Timeline")
        self.notebook.bind("<<NotebookTabChanged>>", lambda _e: self.refresh_all())

    def _build_statusbar(self) -> None:
        bar = tk.Frame(self, bg=T.BG_SOFT, height=34)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        tk.Frame(bar, bg=T.BORDER_SOFT, height=1).pack(fill="x", side="top")
        self.status_var = tk.StringVar(value="Ready  •  SQLite: taskflow.db")
        tk.Label(bar, textvariable=self.status_var, bg=T.BG_SOFT, fg=T.TEXT_DIM,
                 font=T.make_font(8), anchor="w").pack(side="left", padx=18)
        tk.Label(bar, text="Developed by Raj Gautam  •  graj13099@gmail.com  •  @linuxuser.raj",
                 bg=T.BG_SOFT, fg=T.TEXT_DIM, font=T.make_font(8)).pack(side="right", padx=18)

    # ------------------------------------------------------------------ #
    # Generic helpers
    # ------------------------------------------------------------------ #
    def _button(self, parent: tk.Misc, text: str, color: str,
                command: object, width: int = 12) -> tk.Button:
        return tk.Button(
            parent, text=text, command=command, bg=color, fg=T.BG,
            activebackground=T.mix(color, T.TEXT, 0.18), activeforeground=T.BG,
            font=T.make_font(9, "bold"), relief="flat", bd=0,
            width=width, cursor="hand2", pady=2,
        )

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)
        self.update_idletasks()

    def _show_quote(self, quote: str) -> None:
        self.quote_var.set(quote)

    def refresh_all(self) -> None:
        """Re-render both views and every KPI from the current DB state."""
        term = self.search_var.get().strip() if hasattr(self, "search_var") else ""
        self.kanban.refresh(term)
        self.gantt.refresh(term)
        stats = self.db.get_stats()
        for key, label in self.kpi_labels.items():
            label.config(text=str(stats.get(key, 0)))

    # ------------------------------------------------------------------ #
    # Actions
    # ------------------------------------------------------------------ #
    def _open_add_task(self) -> None:
        TaskModal(self, self._save_new_task)

    def _save_new_task(self, data: dict[str, object]) -> None:
        self.db.add_task(**data)
        self.refresh_all()
        self._set_status(f"Created task: {data['title']}")

    def _open_edit_task(self, task: dict[str, object]) -> None:
        TaskModal(self, lambda data, tid=int(task["id"]): self._save_edit(tid, data), task=task)

    def _save_edit(self, task_id: int, data: dict[str, object]) -> None:
        self.db.update_task(task_id, **data)
        self.refresh_all()
        self._set_status(f"Updated task #{task_id}: {data['title']}")

    def _open_import(self) -> None:
        GitHubImportModal(self, self._start_import)

    def _start_import(self, repo: str) -> None:
        self._set_status(f"Fetching open issues from GitHub: {repo} …")
        self.github.fetch_open_issues_async(
            repo,
            on_success=self._finish_import,
            on_error=lambda err: (
                self._set_status(f"Import failed: {err}"),
                messagebox.showerror("GitHub Import Failed", err, parent=self),
            ),
        )

    def _finish_import(self, tasks: list[dict[str, object]], repo: str) -> None:
        added = self.db.bulk_add(tasks)
        self.refresh_all()
        self._set_status(f"Imported {added} new issue(s) from {repo}")
        messagebox.showinfo(
            "GitHub Import Complete",
            f"Fetched {len(tasks)} open issue(s) from {repo}.\n"
            f"Added {added} new task(s) to To Do. Duplicates were skipped.",
            parent=self,
        )

    def _export_csv(self) -> None:
        initial = f"taskflow_report_{date.today().isoformat()}.csv"
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Save TaskFlow Pro Report",
            defaultextension=".csv",
            initialfile=initial,
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            saved = CSVExporter(self.db).export(self.db.get_all_tasks(self.search_var.get().strip()), path)
            self._set_status(f"Report exported: {saved}")
            messagebox.showinfo("Export Successful", f"CSV report saved to:\n{saved}", parent=self)
        except OSError as exc:
            messagebox.showerror("Export Failed", str(exc), parent=self)

    def _open_webhook(self) -> None:
        WebhookModal(self, self.notifier.webhook_url, self._save_webhook)

    def _save_webhook(self, url: str) -> None:
        self.notifier.set_url(url)
        self._set_status("Webhook alerts enabled" if url else "Webhook alerts disabled")

    def _notify_completion(self, task: dict[str, object]) -> None:
        self.notifier.notify_high_priority_completion(str(task.get("title", "Task")))
        self._set_status(f"High-priority task completed: {task.get('title', '')}")


def main() -> None:
    app = TaskFlowPro()
    app.mainloop()


if __name__ == "__main__":
    main()
