"""TaskFlow Pro - Centralized dark theme tokens and small drawing helpers.

Every color used by the UI lives here so the whole application can be
re-themed from a single place. Pure stdlib (tkinter) - no external packages.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont


# --------------------------------------------------------------------------- #
# Palette (Deep Slate / Tailwind-inspired dark UI)
# --------------------------------------------------------------------------- #
BG = "#0F172A"            # app background (deep slate 900)
BG_SOFT = "#111C33"       # slightly lighter panel background
PANEL = "#1E293B"         # card / panel surface (slate 800)
PANEL_2 = "#243249"       # raised surface / hover
BORDER = "#334155"        # subtle borders (slate 700)
BORDER_SOFT = "#2A3A52"

TEXT = "#F8FAFC"          # primary text (slate 50)
TEXT_MUTED = "#94A3B8"    # secondary text (slate 400)
TEXT_DIM = "#64748B"      # tertiary text (slate 500)

ACCENT = "#38BDF8"        # sky blue brand accent
ACCENT_DARK = "#0284C7"
RED = "#EF4444"           # To Do / High
AMBER = "#F59E0B"         # In Progress / Medium
EMERALD = "#10B981"       # Completed / Low
VIOLET = "#8B5CF6"

STATUS_COLORS = {
    "To Do": RED,
    "In Progress": AMBER,
    "Completed": EMERALD,
}
PRIORITY_COLORS = {
    "High": RED,
    "Medium": AMBER,
    "Low": EMERALD,
}
STATUSES = ("To Do", "In Progress", "Completed")
PRIORITIES = ("High", "Medium", "Low")

FONT_FAMILY = "Segoe UI"  # falls back gracefully on Linux (Pop!_OS -> DejaVu Sans)


def make_font(size: int = 10, weight: str = "normal", family: str = FONT_FAMILY) -> tkfont.Font:
    """Return a tkfont.Font. Safe to call before a Tk root exists."""
    return tkfont.Font(family=family, size=size, weight=weight)


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def mix(color_a: str, color_b: str, ratio: float = 0.5) -> str:
    """Blend two hex colors. ratio=0 -> color_a, ratio=1 -> color_b."""
    a, b = hex_to_rgb(color_a), hex_to_rgb(color_b)
    return "#%02x%02x%02x" % tuple(
        round(a[i] + (b[i] - a[i]) * ratio) for i in range(3)
    )


def with_alpha(color: str, factor: float, background: str = PANEL) -> str:
    """Approximate alpha by mixing a color into a background."""
    return mix(background, color, factor)


def round_rect(canvas: tk.Canvas, x1: float, y1: float, x2: float, y2: float,
               radius: float = 10, **kwargs) -> int:
    """Draw a smooth rounded rectangle on a tkinter Canvas (native, no PIL)."""
    x1, y1, x2, y2 = map(float, (x1, y1, x2, y2))
    r = min(radius, (x2 - x1) / 2, (y2 - y1) / 2)
    points = [
        x1 + r, y1, x2 - r, y1,
        x2, y1, x2, y1 + r,
        x2, y2 - r, x2, y2,
        x2 - r, y2, x1 + r, y2,
        x1, y2, x1, y2 - r,
        x1, y1 + r, x1, y1,
    ]
    return canvas.create_polygon(points, smooth=True, splinesteps=12, **kwargs)


def wrap_text(text: str, width: int = 34) -> str:
    """Simple word wrapping used by Canvas-drawn task cards."""
    lines: list[str] = []
    for paragraph in str(text).split("\n"):
        words = paragraph.split()
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if len(candidate) <= width or not current:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return "\n".join(lines)
