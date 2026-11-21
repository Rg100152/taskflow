"""Interactive 3-column Kanban board with Canvas-rendered task cards."""
from __future__ import annotations

import tkinter as tk
from datetime import date
from typing import Any, Callable

from database.db_manager import DatabaseManager
from . import theme as T


class TaskCard(tk.Frame):
    """A crisp, rounded, Canvas-drawn task card with inline controls."""

    CARD_W = 300
    PAD = 16

    def __init__(self, parent: tk.Misc, task: dict[str, Any], column_index: int,
                 on_move: Callable[[int, int], None],
                 on_delete: Callable[[int], None],
                 on_edit: Callable[[dict[str, Any]], None]) -> None:
        super().__init__(parent, bg=T.BG)
        self.task = task
        self.on_move = on_move
        self.on_delete = on_delete
        self.on_edit = on_edit

        title = T.wrap_text(task.get("title", "Untitled"), width=36)
        lines = len(title.split("\n"))
        y_title = self.PAD - 2
        title_h = lines * 16
        y_badge = y_title + title_h + 10
        y_meta = y_badge + 30
        y_progress = y_meta + 24
        y_buttons = y_progress + 24
        height = y_buttons + 32

        self.canvas = tk.Canvas(
            self, width=self.CARD_W, height=height, bg=T.BG,
            highlightthickness=0, bd=0, cursor="hand2",
        )
        self.canvas.pack()
        c = self.canvas
        priority = task.get("priority", "Medium")
        pcolor = T.PRIORITY_COLORS.get(priority, T.ACCENT)
        status = task.get("status", "To Do")
        accent = T.STATUS_COLORS.get(status, T.ACCENT)

        try:
            end = date.fromisoformat(str(task.get("end_date", ""))[:10])
            overdue = end < date.today() and status != "Completed"
            due_text = f"📅  Due {end.strftime('%d %b %Y')}"
        except (ValueError, TypeError):
            overdue, due_text = False, "📅  No due date"

        # Card body + subtle top status accent
        self.outline_id = T.round_rect(c, 2, 2, self.CARD_W - 2, height - 2, radius=11,
                                       fill=T.PANEL, outline=T.BORDER, width=1)
        c.create_rectangle(14, 2, self.CARD_W - 14, 5, fill=accent, outline="")
        T.round_rect(c, 4, 14, 8, height - 14, radius=2, fill=pcolor, outline="")

        # Title
        c.create_text(self.PAD, y_title, anchor="nw", text=title, fill=T.TEXT,
                      font=T.make_font(10, "bold"), width=self.CARD_W - 2 * self.PAD)

        # Priority pill
        label = priority.upper()
        pill_w = 22 + 8 * len(label)
        T.round_rect(c, self.PAD, y_badge, self.PAD + pill_w, y_badge + 20,
                     radius=10, fill=T.with_alpha(pcolor, 0.22), outline=pcolor)
        c.create_text(self.PAD + pill_w // 2, y_badge + 10, text=label,
                      fill=pcolor, font=T.make_font(8, "bold"))
        c.create_text(self.PAD + pill_w + 12, y_badge + 10, anchor="w",
                      text=f"👤 {(task.get('assignee') or 'Unassigned')[:20]}",
                      fill=T.TEXT_MUTED, font=T.make_font(8))

        # Due date + source hint
        c.create_text(self.PAD, y_meta + 6, anchor="w", text=due_text,
                      fill=T.RED if overdue else T.TEXT_DIM, font=T.make_font(8))
        if task.get("source") == "github":
            c.create_text(self.CARD_W - self.PAD, y_meta + 6, anchor="e",
                          text="GitHub", fill=T.ACCENT, font=T.make_font(8, "bold"))

        # Progress bar
        pct = max(0, min(100, int(task.get("progress", 0) or 0)))
        track_x2 = self.CARD_W - self.PAD
        T.round_rect(c, self.PAD, y_progress, track_x2, y_progress + 8,
                     radius=4, fill=T.BORDER, outline="")
        if pct:
            T.round_rect(c, self.PAD, y_progress,
                         self.PAD + max(8, (track_x2 - self.PAD) * pct / 100),
                         y_progress + 8, radius=4, fill=pcolor, outline="")
        c.create_text(track_x2, y_progress + 4, anchor="e", text=f"{pct}%",
                      fill=T.TEXT, font=T.make_font(7, "bold"))

        # Controls
        controls = [
            ("←", lambda: self.on_move(task["id"], -1), column_index == 0, "Move left"),
            ("→", lambda: self.on_move(task["id"], 1), column_index == 2, "Move right"),
            ("✎", lambda: self.on_edit(task), False, "Edit task"),
            ("✕", lambda: self.on_delete(task["id"]), False, "Delete task"),
        ]
        x = self.PAD
        for symbol, command, disabled, tip in controls:
            btn = tk.Button(
                c, text=symbol, command=command, width=3, height=1,
                bg=T.PANEL_2 if not disabled else T.BG_SOFT,
                fg=T.TEXT_MUTED if not disabled else T.TEXT_DIM,
                activebackground=T.ACCENT,
                activeforeground=T.BG,
                font=T.make_font(9, "bold"), relief="flat", bd=0,
                cursor="hand2" if not disabled else "arrow",
                state="disabled" if disabled else "normal",
            )
            c.create_window(x, y_buttons + 1, window=btn, anchor="nw")
            x += 38

        c.bind("<Double-Button-1>", lambda _e: self.on_edit(task))
        c.bind("<Enter>", lambda _e: c.itemconfig(self.outline_id, outline=T.with_alpha(accent, 0.6)))
        c.bind("<Leave>", lambda _e: c.itemconfig(self.outline_id, outline=T.BORDER))


class KanbanView(tk.Frame):
    """Three scrollable columns backed by the SQLite task table."""

    COLUMNS = [
        ("To Do", T.RED, "▢"),
        ("In Progress", T.AMBER, "◐"),
        ("Completed", T.EMERALD, "✓"),
    ]

    def __init__(self, parent: tk.Misc, db: DatabaseManager,
                 on_change: Callable[[], None],
                 on_edit: Callable[[dict[str, Any]], None],
                 on_notify: Callable[[dict[str, Any]], None] | None = None) -> None:
        super().__init__(parent, bg=T.BG)
        self.db = db
        self.on_change = on_change
        self.on_edit = on_edit
        self.on_notify = on_notify
        self._columns: list[tk.Frame] = []
        self._counts: list[tk.Label] = []
        self._build_columns()

    def _build_columns(self) -> None:
        wrapper = tk.Frame(self, bg=T.BG)
        wrapper.pack(fill="both", expand=True, padx=18, pady=(10, 18))

        for index, (name, color, icon) in enumerate(self.COLUMNS):
            col = tk.Frame(wrapper, bg=T.BG_SOFT, highlightthickness=1,
                           highlightbackground=T.BORDER_SOFT)
            col.pack(side="left", fill="both", expand=True, padx=(0, 12))

            header = tk.Frame(col, bg=T.BG_SOFT, height=54)
            header.pack(fill="x")
            header.pack_propagate(False)
            tk.Frame(header, bg=color, height=3).pack(fill="x", side="top")
            tk.Label(header, text=f" {icon}  {name.upper()}", bg=T.BG_SOFT,
                     fg=T.TEXT, font=T.make_font(10, "bold")).pack(side="left", padx=(12, 6), pady=12)
            count = tk.Label(header, text="0", bg=T.with_alpha(color, 0.18),
                             fg=color, font=T.make_font(9, "bold"),
                             padx=9, pady=2, relief="flat")
            count.pack(side="right", padx=12)
            self._counts.append(count)

            body = tk.Frame(col, bg=T.BG_SOFT)
            body.pack(fill="both", expand=True)
            canvas = tk.Canvas(body, bg=T.BG_SOFT, highlightthickness=0, bd=0)
            scroll = tk.Scrollbar(body, orient="vertical", command=canvas.yview,
                                  width=8, bg=T.BG_SOFT, troughcolor=T.BG_SOFT,
                                  activebackground=T.BORDER, relief="flat")
            inner = tk.Frame(canvas, bg=T.BG_SOFT)
            inner.bind("<Configure>", lambda e, cv=canvas: cv.configure(scrollregion=cv.bbox("all")))
            canvas.create_window((0, 0), window=inner, anchor="nw")
            canvas.configure(yscrollcommand=scroll.set)
            canvas.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=6)
            scroll.pack(side="right", fill="y", pady=6)

            def _wheel(event: tk.Event, cv: tk.Canvas = canvas) -> None:
                cv.yview_scroll(-1 if event.delta > 0 else 1, "units")

            canvas.bind("<MouseWheel>", _wheel)
            inner.bind("<MouseWheel>", _wheel)
            canvas.bind("<Button-4>", lambda e, cv=canvas: cv.yview_scroll(-1, "units"))
            canvas.bind("<Button-5>", lambda e, cv=canvas: cv.yview_scroll(1, "units"))

            self._columns.append(inner)

    def refresh(self, search: str = "") -> None:
        tasks = self.db.get_all_tasks(search=search)
        for index, inner in enumerate(self._columns):
            for widget in inner.winfo_children():
                widget.destroy()
            status = self.COLUMNS[index][0]
            column_tasks = [t for t in tasks if t["status"] == status]
            self._counts[index].config(text=str(len(column_tasks)))
            if not column_tasks:
                tk.Label(inner, text="No tasks here yet", bg=T.BG_SOFT,
                         fg=T.TEXT_DIM, font=T.make_font(9), pady=20).pack()
                continue
            for task in column_tasks:
                card = TaskCard(
                    inner, task, index,
                    on_move=self._move,
                    on_delete=self._delete,
                    on_edit=self.on_edit,
                )
                card.pack(pady=(0, 10), padx=4)

    # ------------------------------------------------------------------ #
    # Card actions
    # ------------------------------------------------------------------ #
    def _move(self, task_id: int, direction: int) -> None:
        before = self.db.get_task(task_id)
        if not before or not self.db.shift_task(task_id, direction):
            return
        after = self.db.get_task(task_id)
        if (before.get("priority") == "High" and after
                and after.get("status") == "Completed" and self.on_notify):
            self.on_notify(after)
        self.on_change()

    def _delete(self, task_id: int) -> None:
        from tkinter import messagebox
        task = self.db.get_task(task_id)
        if not task:
            return
        if messagebox.askyesno("Delete task", f"Delete “{task['title']}” permanently?", parent=self):
            self.db.delete_task(task_id)
            self.on_change()
