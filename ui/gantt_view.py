"""Canvas-driven interactive Gantt timeline - no plotting libraries required."""
from __future__ import annotations

import tkinter as tk
from datetime import date, timedelta
from typing import Any, Callable

from database.db_manager import DatabaseManager
from . import theme as T

LEFT_W = 264
HEADER_H = 62
ROW_H = 48
DAY_W = 30
BAR_H = 22
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
WEEKDAYS = ["M", "T", "W", "T", "F", "S", "S"]


def _parse(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


class GanttView(tk.Frame):
    """Left task list + horizontally scrollable Canvas timeline."""

    def __init__(self, parent: tk.Misc, db: DatabaseManager,
                 on_edit: Callable[[dict[str, Any]], None] | None = None) -> None:
        super().__init__(parent, bg=T.BG)
        self.db = db
        self.on_edit = on_edit
        self._tooltip: tk.Toplevel | None = None
        self._bar_map: dict[int, dict[str, Any]] = {}
        self._build()

    # ------------------------------------------------------------------ #
    # Layout
    # ------------------------------------------------------------------ #
    def _build(self) -> None:
        # Legend / instruction strip
        legend = tk.Frame(self, bg=T.BG_SOFT, height=44)
        legend.pack(fill="x", padx=18, pady=(10, 0))
        legend.pack_propagate(False)
        tk.Label(legend, text="📊  GANTT TIMELINE", bg=T.BG_SOFT, fg=T.TEXT,
                 font=T.make_font(10, "bold")).pack(side="left", padx=(14, 18))
        for status in ("To Do", "In Progress", "Completed"):
            color = T.STATUS_COLORS[status]
            tk.Label(legend, text="●", bg=T.BG_SOFT, fg=color,
                     font=T.make_font(11)).pack(side="left", padx=(4, 0))
            tk.Label(legend, text=status, bg=T.BG_SOFT, fg=T.TEXT_MUTED,
                     font=T.make_font(8)).pack(side="left", padx=(2, 14))
        tk.Label(legend, text="Scroll ↔ to navigate  •  hover a bar for details  •  double-click to edit",
                 bg=T.BG_SOFT, fg=T.TEXT_DIM, font=T.make_font(8)).pack(side="right", padx=14)

        chart = tk.Frame(self, bg=T.BG_SOFT, highlightthickness=1,
                         highlightbackground=T.BORDER_SOFT)
        chart.pack(fill="both", expand=True, padx=18, pady=(8, 18))

        left_holder = tk.Frame(chart, bg=T.BG_SOFT, width=LEFT_W)
        left_holder.pack(side="left", fill="y")
        left_holder.pack_propagate(False)

        right_holder = tk.Frame(chart, bg=T.BG_SOFT)
        right_holder.pack(side="left", fill="both", expand=True)

        self.left = tk.Canvas(left_holder, bg=T.BG_SOFT, width=LEFT_W,
                              highlightthickness=0, bd=0)
        self.left.pack(fill="both", expand=True)

        self.vbar = tk.Scrollbar(chart, orient="vertical", command=self._scroll_y,
                                 width=9, bg=T.BG_SOFT, troughcolor=T.BG_SOFT,
                                 activebackground=T.BORDER, relief="flat")
        self.vbar.pack(side="right", fill="y")

        self.hbar = tk.Scrollbar(right_holder, orient="horizontal",
                                 width=9, bg=T.BG_SOFT, troughcolor=T.BG_SOFT,
                                 activebackground=T.BORDER, relief="flat")

        self.right = tk.Canvas(right_holder, bg=T.BG_SOFT, highlightthickness=0, bd=0,
                               xscrollcommand=self.hbar.set,
                               yscrollcommand=self._report_y)
        self.right.pack(fill="both", expand=True, side="top")
        self.hbar.configure(command=self.right.xview)
        self.hbar.pack(side="bottom", fill="x")

        self.right.bind("<MouseWheel>", lambda e: self.right.xview_scroll(-e.delta // 120, "units"))
        self.right.bind("<Shift-MouseWheel>", lambda e: self._scroll_y("scroll", -e.delta // 120, "units"))
        self.right.bind("<Button-4>", lambda e: self.right.xview_scroll(-1, "units"))
        self.right.bind("<Button-5>", lambda e: self.right.xview_scroll(1, "units"))

    def _report_y(self, first: str, last: str) -> None:
        self.vbar.set(first, last)
        self.left.yview_moveto(float(first))

    def _scroll_y(self, *args: Any) -> None:
        self.right.yview(*args)
        self.left.yview(*args)

    # ------------------------------------------------------------------ #
    # Rendering
    # ------------------------------------------------------------------ #
    def refresh(self, search: str = "") -> None:
        tasks = [t for t in self.db.get_all_tasks(search=search)
                 if _parse(t.get("start_date")) and _parse(t.get("end_date"))]
        self.left.delete("all")
        self.right.delete("all")
        self._bar_map.clear()
        self._hide_tooltip()

        if not tasks:
            self.left.create_text(LEFT_W // 2, 140, text="No tasks to display",
                                  fill=T.TEXT_DIM, font=T.make_font(10))
            self.right.create_text(400, 140, text="Add a task to see it on the timeline",
                                   fill=T.TEXT_DIM, font=T.make_font(10))
            self._set_scrollregions(0, 0)
            return

        starts = [_parse(t["start_date"]) for t in tasks]
        ends = [_parse(t["end_date"]) for t in tasks]
        assert starts and ends
        range_start = min(starts) - timedelta(days=2)
        range_end = max(ends) + timedelta(days=3)
        total_days = max(14, (range_end - range_start).days + 1)
        timeline_w = 24 + total_days * DAY_W + 40
        content_h = HEADER_H + len(tasks) * ROW_H + 20
        self._timeline_w, self._content_h = timeline_w, content_h
        self._set_scrollregions(timeline_w, content_h)

        self._draw_header(range_start, total_days)

        for index, task in enumerate(tasks):
            y = HEADER_H + index * ROW_H
            self._draw_row(task, index, y, range_start)

        # Today marker drawn last so it sits above the bars
        today = date.today()
        if range_start <= today <= range_start + timedelta(days=total_days - 1):
            x = self._x(today, range_start)
            self.right.create_line(x, HEADER_H - 8, x, content_h,
                                   fill=T.RED, width=1, dash=(4, 4))
            T.round_rect(self.right, x - 22, 34, x + 22, 52, radius=6,
                         fill=T.RED, outline="")
            self.right.create_text(x, 43, text="TODAY", fill="white",
                                   font=T.make_font(7, "bold"))

        self.right.bind("<Motion>", self._on_motion)
        self.right.bind("<Leave>", lambda _e: self._hide_tooltip())
        self.right.bind("<Double-Button-1>", self._on_double_click)

    def _set_scrollregions(self, width: int, height: int) -> None:
        self.right.configure(scrollregion=(0, 0, max(width, 600), max(height, 300)))
        self.left.configure(scrollregion=(0, 0, LEFT_W, max(height, 300)))

    def _x(self, day: date, start: date) -> int:
        return 24 + (day - start).days * DAY_W

    def _draw_header(self, start: date, total_days: int) -> None:
        c = self.right
        c.create_rectangle(0, 0, self._timeline_w, HEADER_H, fill=T.PANEL, outline="")
        c.create_line(0, HEADER_H, self._timeline_w, HEADER_H, fill=T.BORDER, width=1)

        month_start = 0
        for i in range(total_days + 1):
            day = start + timedelta(days=i)
            x = self._x(day, start)
            weekend = day.weekday() >= 5
            if i < total_days:
                if weekend:
                    c.create_rectangle(x, HEADER_H, x + DAY_W, self._content_h,
                                       fill=T.with_alpha(T.BG_SOFT, 0.55, T.PANEL), outline="")
                c.create_line(x, HEADER_H - 12, x, HEADER_H, fill=T.BORDER, width=1)
                c.create_text(x + DAY_W // 2, HEADER_H - 26, text=str(day.day),
                              fill=T.TEXT_DIM if weekend else T.TEXT,
                              font=T.make_font(8, "bold"))
                c.create_text(x + DAY_W // 2, HEADER_H - 9, text=WEEKDAYS[day.weekday()],
                              fill=T.TEXT_DIM if weekend else T.TEXT_MUTED,
                              font=T.make_font(7))
            if i == total_days or day.month != (start + timedelta(days=month_start)).month:
                label = f"{MONTHS[(start + timedelta(days=month_start)).month - 1]} {(start + timedelta(days=month_start)).year}"
                c.create_text(self._x(start + timedelta(days=month_start), start) + 8, 16,
                              anchor="w", text=label, fill=T.ACCENT,
                              font=T.make_font(9, "bold"))
                month_start = i

    def _draw_row(self, task: dict[str, Any], index: int, y: int, start: date) -> None:
        left, c = self.left, self.right
        bg = T.PANEL if index % 2 == 0 else T.BG_SOFT
        left.create_rectangle(0, y, LEFT_W, y + ROW_H, fill=bg, outline="")
        c.create_rectangle(0, y, self._timeline_w, y + ROW_H, fill=bg, outline="")
        c.create_line(0, y + ROW_H, self._timeline_w, y + ROW_H,
                      fill=T.with_alpha(T.BORDER, 0.4, bg), width=1)
        left.create_line(0, y + ROW_H, LEFT_W, y + ROW_H,
                         fill=T.with_alpha(T.BORDER, 0.4, bg), width=1)

        pcolor = T.PRIORITY_COLORS.get(task.get("priority", "Medium"), T.ACCENT)
        scolor = T.STATUS_COLORS.get(task.get("status", "To Do"), T.ACCENT)
        title = str(task.get("title", "Untitled"))
        short = title if len(title) <= 32 else title[:30] + "…"
        left.create_oval(10, y + 14, 18, y + 22, fill=pcolor, outline="")
        left.create_text(26, y + 17, anchor="nw", text=short, fill=T.TEXT,
                         font=T.make_font(9, "bold"))
        left.create_text(26, y + 33, anchor="nw",
                         text=f"{(task.get('assignee') or 'Unassigned')[:22]}  •  {task.get('priority')}",
                         fill=T.TEXT_DIM, font=T.make_font(7))

        s, e = _parse(task["start_date"]), _parse(task["end_date"])
        if not s or not e or e < s:
            return
        x1 = self._x(s, start)
        x2 = self._x(e, start) + DAY_W
        bar_w = max(DAY_W, x2 - x1 - 4)
        top = y + (ROW_H - BAR_H) // 2

        T.round_rect(c, x1, top, x1 + bar_w, top + BAR_H, radius=7,
                     fill=T.with_alpha(scolor, 0.28, bg), outline=scolor, width=1)
        pct = max(0, min(100, int(task.get("progress", 0) or 0)))
        if pct:
            T.round_rect(c, x1 + 1, top + 1, x1 + max(6, bar_w * pct / 100) - 1,
                         top + BAR_H - 1, radius=6, fill=scolor, outline="")
        text_color = T.BG if pct >= 45 else T.TEXT
        label = f"{short[:max(4, int(bar_w / 7))]}  {pct}%" if bar_w > 70 else f"{pct}%"
        c.create_text(x1 + 9, top + BAR_H // 2, anchor="w", text=label,
                      fill=text_color, font=T.make_font(8, "bold"))

        c.create_text(x2 + 8, top + BAR_H // 2, anchor="w",
                      text=e.strftime("%d %b"), fill=T.TEXT_DIM, font=T.make_font(7))
        # Map an oversized invisible hit area to this task for hover/click.
        hit = c.create_rectangle(x1, top - 4, x1 + bar_w + 30, top + BAR_H + 4,
                                 fill="", outline="", tags=("bar",))
        self._bar_map[hit] = {"task": task, "x": x1, "y": top,
                              "w": bar_w, "h": BAR_H}

    # ------------------------------------------------------------------ #
    # Interaction
    # ------------------------------------------------------------------ #
    def _hit_at(self, event: tk.Event) -> dict[str, Any] | None:
        # find_overlapping is canvas coordinates and respects scroll offset.
        x, y = self.right.canvasx(event.x), self.right.canvasy(event.y)
        overlaps = self.right.find_overlapping(x, y, x, y)
        for item in reversed(overlaps):
            if item in self._bar_map:
                return self._bar_map[item]
        return None

    def _on_motion(self, event: tk.Event) -> None:
        hit = self._hit_at(event)
        if not hit:
            self._hide_tooltip()
            self.right.config(cursor="")
            return
        self.right.config(cursor="hand2")
        task = hit["task"]
        text = (
            f"{task['title']}\n"
            f"Status: {task['status']}   Priority: {task['priority']}\n"
            f"{task['start_date']} → {task['end_date']}   Progress: {task['progress']}%\n"
            f"Assignee: {task.get('assignee', 'Unassigned')}"
        )
        if self._tooltip:
            self._tooltip.destroy()
        tip = tk.Toplevel(self)
        tip.withdraw()
        tip.overrideredirect(True)
        tip.configure(bg=T.BORDER)
        tk.Label(tip, text=text, bg=T.PANEL, fg=T.TEXT, justify="left",
                 font=T.make_font(8), padx=10, pady=8).pack()
        tip.update_idletasks()
        tx = self.winfo_rootx() + event.x + 18
        ty = self.winfo_rooty() + event.y + 20
        tip.geometry(f"+{tx}+{ty}")
        tip.deiconify()
        self._tooltip = tip

    def _hide_tooltip(self) -> None:
        if self._tooltip:
            self._tooltip.destroy()
            self._tooltip = None

    def _on_double_click(self, event: tk.Event) -> None:
        hit = self._hit_at(event)
        if hit and self.on_edit:
            self.on_edit(hit["task"])
