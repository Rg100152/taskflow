"""Dark themed popup dialogs: Add / Edit task, GitHub import, Webhook setup."""
from __future__ import annotations

import tkinter as tk
from datetime import date, timedelta
from tkinter import messagebox, ttk
from typing import Any, Callable

from . import theme as T


class _Modal(tk.Toplevel):
    """Base class with consistent dark chrome and centre-on-parent behaviour."""

    def __init__(self, parent: tk.Tk, title: str, width: int = 520, height: int = 520) -> None:
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.configure(bg=T.BG)
        self.transient(parent)
        self.grab_set()
        self.result: Any = None
        self._center(parent, width, height)
        self.bind("<Escape>", lambda _e: self.destroy())

    def _center(self, parent: tk.Tk, width: int, height: int) -> None:
        self.update_idletasks()
        px, py = parent.winfo_x(), parent.winfo_y()
        pw, ph = parent.winfo_width(), parent.winfo_height()
        x = px + max(0, (pw - width) // 2)
        y = py + max(0, (ph - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _label(self, text: str) -> tk.Label:
        return tk.Label(self, text=text, bg=T.BG, fg=T.TEXT_MUTED,
                        font=T.make_font(9, "bold"), anchor="w")

    def _entry(self, textvariable: tk.StringVar) -> tk.Entry:
        return tk.Entry(self, textvariable=textvariable, bg=T.PANEL,
                        fg=T.TEXT, insertbackground=T.ACCENT, relief="flat",
                        font=T.make_font(10), bd=0, highlightthickness=1,
                        highlightbackground=T.BORDER,
                        highlightcolor=T.ACCENT)

    def _footer(self, on_save: Callable[[], None]) -> None:
        bar = tk.Frame(self, bg=T.BG_SOFT, height=58)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        tk.Button(bar, text="Cancel", command=self.destroy, bg=T.PANEL,
                  fg=T.TEXT_MUTED, activebackground=T.PANEL_2, activeforeground=T.TEXT,
                  font=T.make_font(10, "bold"), relief="flat", width=12,
                  cursor="hand2").pack(side="right", padx=(8, 18), pady=12)
        tk.Button(bar, text="Save Task", command=on_save, bg=T.ACCENT,
                  fg=T.BG, activebackground=T.ACCENT_DARK, activeforeground="white",
                  font=T.make_font(10, "bold"), relief="flat", width=14,
                  cursor="hand2").pack(side="right", padx=8, pady=12)


class TaskModal(_Modal):
    """Add a new task or edit an existing one (pass ``task`` to edit)."""

    def __init__(self, parent: tk.Tk, on_save: Callable[[dict[str, Any]], None],
                 task: dict[str, Any] | None = None) -> None:
        editing = task is not None
        super().__init__(parent, "Edit Task" if editing else "New Task",
                         width=540, height=610)
        self._on_save = on_save
        self.task = task or {}
        today = date.today()

        title = tk.Label(self, text=("✎  EDIT TASK" if editing else "＋  CREATE NEW TASK"),
                         bg=T.BG, fg=T.TEXT, font=T.make_font(14, "bold"), anchor="w")
        title.pack(fill="x", padx=22, pady=(20, 4))
        tk.Label(self, text="TaskFlow Pro  •  Project schedule", bg=T.BG,
                 fg=T.TEXT_DIM, font=T.make_font(9),
                 anchor="w").pack(fill="x", padx=22, pady=(0, 14))

        form = tk.Frame(self, bg=T.BG)
        form.pack(fill="both", expand=True, padx=22)

        # Title
        self.v_title = tk.StringVar(value=self.task.get("title", ""))
        self._label("TASK TITLE *").pack(fill="x", pady=(4, 4))
        self._entry(self.v_title).pack(fill="x", ipady=7)

        # Description
        self._label("DESCRIPTION").pack(fill="x", pady=(12, 4))
        desc = tk.Text(self, height=4, bg=T.PANEL, fg=T.TEXT, relief="flat", bd=0,
                       font=T.make_font(9), insertbackground=T.ACCENT,
                       highlightthickness=1, highlightbackground=T.BORDER,
                       highlightcolor=T.ACCENT, wrap="word")
        desc.pack(fill="x")
        desc.insert("1.0", self.task.get("description", ""))
        self.desc = desc

        # Status / priority row
        row = tk.Frame(form, bg=T.BG)
        row.pack(fill="x", pady=(14, 0))
        left = tk.Frame(row, bg=T.BG)
        left.pack(side="left", fill="x", expand=True, padx=(0, 8))
        right = tk.Frame(row, bg=T.BG)
        right.pack(side="right", fill="x", expand=True, padx=(8, 0))

        tk.Label(left, text="STATUS", bg=T.BG, fg=T.TEXT_MUTED,
                 font=T.make_font(9, "bold"), anchor="w").pack(fill="x", pady=(0, 4))
        self.v_status = tk.StringVar(value=self.task.get("status", "To Do"))
        ttk.Combobox(left, textvariable=self.v_status, values=list(T.STATUSES),
                     state="readonly", font=T.make_font(10)).pack(fill="x", ipady=4)

        tk.Label(right, text="PRIORITY", bg=T.BG, fg=T.TEXT_MUTED,
                 font=T.make_font(9, "bold"), anchor="w").pack(fill="x", pady=(0, 4))
        self.v_priority = tk.StringVar(value=self.task.get("priority", "Medium"))
        ttk.Combobox(right, textvariable=self.v_priority, values=list(T.PRIORITIES),
                     state="readonly", font=T.make_font(10)).pack(fill="x", ipady=4)

        # Dates row
        dates = tk.Frame(form, bg=T.BG)
        dates.pack(fill="x", pady=(12, 0))
        left = tk.Frame(dates, bg=T.BG)
        left.pack(side="left", fill="x", expand=True, padx=(0, 8))
        right = tk.Frame(dates, bg=T.BG)
        right.pack(side="right", fill="x", expand=True, padx=(8, 0))
        tk.Label(left, text="START DATE (YYYY-MM-DD)", bg=T.BG, fg=T.TEXT_MUTED,
                 font=T.make_font(9, "bold"), anchor="w").pack(fill="x", pady=(0, 4))
        self.v_start = tk.StringVar(value=self.task.get("start_date", today.isoformat()))
        self._entry(self.v_start).pack(fill="x", ipady=7)
        tk.Label(right, text="END DATE (YYYY-MM-DD)", bg=T.BG, fg=T.TEXT_MUTED,
                 font=T.make_font(9, "bold"), anchor="w").pack(fill="x", pady=(0, 4))
        self.v_end = tk.StringVar(value=self.task.get("end_date", (today + timedelta(days=5)).isoformat()))
        self._entry(self.v_end).pack(fill="x", ipady=7)

        # Assignee + progress
        misc = tk.Frame(form, bg=T.BG)
        misc.pack(fill="x", pady=(12, 0))
        left = tk.Frame(misc, bg=T.BG)
        left.pack(side="left", fill="x", expand=True, padx=(0, 8))
        right = tk.Frame(misc, bg=T.BG)
        right.pack(side="right", fill="x", expand=True, padx=(8, 0))
        tk.Label(left, text="ASSIGNEE", bg=T.BG, fg=T.TEXT_MUTED,
                 font=T.make_font(9, "bold"), anchor="w").pack(fill="x", pady=(0, 4))
        self.v_assignee = tk.StringVar(value=self.task.get("assignee", "Raj Gautam"))
        self._entry(self.v_assignee).pack(fill="x", ipady=7)

        tk.Label(right, text="PROGRESS", bg=T.BG, fg=T.TEXT_MUTED,
                 font=T.make_font(9, "bold"), anchor="w").pack(fill="x", pady=(0, 4))
        self.v_progress = tk.IntVar(value=int(self.task.get("progress", 0)))
        scale = tk.Scale(right, from_=0, to=100, orient="horizontal",
                         variable=self.v_progress, bg=T.BG, fg=T.TEXT,
                         troughcolor=T.PANEL, activebackground=T.ACCENT,
                         highlightthickness=0, showvalue=True, length=210)
        scale.pack(fill="x")

        tk.Label(form,
                 text="Tip: moving a task to Completed automatically sets progress to 100%.",
                 bg=T.BG, fg=T.TEXT_DIM, font=T.make_font(8),
                 anchor="w", wraplength=480, justify="left").pack(fill="x", pady=(12, 4))

        self._footer(self._save)

    def _save(self) -> None:
        title = self.v_title.get().strip()
        if not title:
            messagebox.showwarning("Missing title", "Please enter a task title.", parent=self)
            return
        try:
            start = date.fromisoformat(self.v_start.get().strip()[:10])
            end = date.fromisoformat(self.v_end.get().strip()[:10])
        except ValueError:
            messagebox.showerror("Invalid date", "Use the YYYY-MM-DD format (e.g. 2026-11-22).", parent=self)
            return
        if end < start:
            messagebox.showerror("Invalid range", "End date cannot be before start date.", parent=self)
            return

        self.result = {
            "title": title,
            "description": self.desc.get("1.0", "end").strip(),
            "status": self.v_status.get(),
            "priority": self.v_priority.get(),
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "progress": int(self.v_progress.get()),
            "assignee": self.v_assignee.get().strip() or "Unassigned",
        }
        self._on_save(self.result)
        self.destroy()


class GitHubImportModal(_Modal):
    """Ask for a public repository in owner/repo format."""

    def __init__(self, parent: tk.Tk, on_import: Callable[[str], None]) -> None:
        super().__init__(parent, "Import from GitHub", width=520, height=330)
        self._on_import = on_import

        tk.Label(self, text="🔄  IMPORT GITHUB ISSUES", bg=T.BG, fg=T.TEXT,
                 font=T.make_font(14, "bold"), anchor="w").pack(fill="x", padx=22, pady=(22, 6))
        tk.Label(self, text="Open issues become cards in the To Do column. No API key needed.",
                 bg=T.BG, fg=T.TEXT_MUTED, font=T.make_font(9),
                 anchor="w", wraplength=470, justify="left").pack(fill="x", padx=22)

        tk.Label(self, text="PUBLIC REPOSITORY (owner/repo)", bg=T.BG, fg=T.TEXT_MUTED,
                 font=T.make_font(9, "bold"), anchor="w").pack(fill="x", padx=22, pady=(20, 4))
        self.v_repo = tk.StringVar(value="Rg100152/taskflow")
        entry = self._entry(self.v_repo)
        entry.pack(fill="x", padx=22, ipady=8)
        entry.focus_set()
        entry.bind("<Return>", lambda _e: self._import())

        tk.Label(self, text="Example: Rg100152/taskflow  •  duplicate issues are skipped automatically",
                 bg=T.BG, fg=T.TEXT_DIM, font=T.make_font(8),
                 anchor="w", wraplength=470, justify="left").pack(fill="x", padx=22, pady=(10, 0))

        bar = tk.Frame(self, bg=T.BG_SOFT, height=58)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        tk.Button(bar, text="Cancel", command=self.destroy, bg=T.PANEL, fg=T.TEXT_MUTED,
                  activebackground=T.PANEL_2, activeforeground=T.TEXT, relief="flat",
                  font=T.make_font(10, "bold"), width=12, cursor="hand2").pack(side="right", padx=(8, 18), pady=12)
        tk.Button(bar, text="Import Issues", command=self._import, bg=T.ACCENT, fg=T.BG,
                  activebackground=T.ACCENT_DARK, activeforeground="white", relief="flat",
                  font=T.make_font(10, "bold"), width=15, cursor="hand2").pack(side="right", padx=8, pady=12)

    def _import(self) -> None:
        repo = self.v_repo.get().strip()
        if not repo:
            messagebox.showwarning("Repository required", "Enter a repository such as owner/repo.", parent=self)
            return
        self._on_import(repo)
        self.destroy()


class WebhookModal(_Modal):
    """Configure an optional Discord/Telegram compatible webhook URL."""

    def __init__(self, parent: tk.Tk, current: str, on_save: Callable[[str], None]) -> None:
        super().__init__(parent, "Webhook Alerts", width=540, height=280)
        self._on_save = on_save
        tk.Label(self, text="🔔  COMPLETION WEBHOOK", bg=T.BG, fg=T.TEXT,
                 font=T.make_font(14, "bold"), anchor="w").pack(fill="x", padx=22, pady=(22, 6))
        tk.Label(self,
                 text="When a High-priority task is completed, TaskFlow Pro posts:"
                      "\n“Task Completed by Raj Gautam!” to this URL.",
                 bg=T.BG, fg=T.TEXT_MUTED, font=T.make_font(9),
                 anchor="w", justify="left", wraplength=480).pack(fill="x", padx=22)
        tk.Label(self, text="WEBHOOK URL (leave empty to disable)", bg=T.BG,
                 fg=T.TEXT_MUTED, font=T.make_font(9, "bold"), anchor="w").pack(fill="x", padx=22, pady=(18, 4))
        self.v_url = tk.StringVar(value=current)
        self._entry(self.v_url).pack(fill="x", padx=22, ipady=8)

        bar = tk.Frame(self, bg=T.BG_SOFT, height=58)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        tk.Button(bar, text="Cancel", command=self.destroy, bg=T.PANEL, fg=T.TEXT_MUTED,
                  activebackground=T.PANEL_2, activeforeground=T.TEXT, relief="flat",
                  font=T.make_font(10, "bold"), width=12, cursor="hand2").pack(side="right", padx=(8, 18), pady=12)
        tk.Button(bar, text="Save", command=self._save, bg=T.ACCENT, fg=T.BG,
                  activebackground=T.ACCENT_DARK, activeforeground="white", relief="flat",
                  font=T.make_font(10, "bold"), width=14, cursor="hand2").pack(side="right", padx=8, pady=12)

    def _save(self) -> None:
        self._on_save(self.v_url.get().strip())
        self.destroy()
