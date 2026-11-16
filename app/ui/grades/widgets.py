"""Thành phần dùng chung cho các màn hình điểm."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.ui.theme import (
    BACKGROUND,
    BORDER,
    DANGER,
    MUTED,
    PRIMARY_DARK,
    PRIMARY_SOFT,
    SUCCESS,
    SURFACE,
    TEXT,
    font,
)

_STATUS_LABELS = {
    "PASSED": "Đạt",
    "FAILED": "Không đạt",
    "PENDING": "Chưa đủ điểm",
}


def page_header(parent: tk.Misc, title: str, subtitle: str) -> tk.Frame:
    frame = tk.Frame(parent, bg=BACKGROUND)
    frame.pack(fill="x")
    tk.Label(
        frame,
        text=title,
        bg=BACKGROUND,
        fg=TEXT,
        font=font(20, "bold"),
        anchor="w",
    ).pack(fill="x")
    tk.Label(
        frame,
        text=subtitle,
        bg=BACKGROUND,
        fg=MUTED,
        font=font(9),
        anchor="w",
        justify="left",
        wraplength=860,
    ).pack(fill="x", pady=(6, 0))
    return frame


def configure_table_style(widget: tk.Misc) -> None:
    style = ttk.Style(widget)
    style.configure(
        "Grades.Treeview",
        background=SURFACE,
        fieldbackground=SURFACE,
        foreground=TEXT,
        rowheight=28,
        font=font(9),
        borderwidth=0,
    )
    style.configure(
        "Grades.Treeview.Heading",
        background=BACKGROUND,
        foreground=MUTED,
        font=font(8, "bold"),
        relief="flat",
        padding=(8, 6),
    )
    style.map(
        "Grades.Treeview",
        background=[("selected", PRIMARY_SOFT)],
        foreground=[("selected", PRIMARY_DARK)],
    )


def create_table(
    parent: tk.Misc,
    columns: list[tuple[str, str, int, str]],
    height: int = 11,
) -> tuple[tk.Frame, ttk.Treeview]:
    """Tạo bảng chỉ đọc có thanh cuộn; columns = (key, label, width, anchor)."""
    configure_table_style(parent)
    frame = tk.Frame(parent, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
    tree = ttk.Treeview(
        frame,
        columns=[column[0] for column in columns],
        show="headings",
        height=height,
        style="Grades.Treeview",
        selectmode="browse",
    )
    for key, label, width, anchor in columns:
        tree.heading(key, text=label)
        tree.column(key, width=width, minwidth=50, anchor=anchor, stretch=True)

    scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side="left", fill="both", expand=True, padx=(1, 0), pady=1)
    scrollbar.pack(side="right", fill="y")

    tree.tag_configure("passed", foreground=SUCCESS)
    tree.tag_configure("failed", foreground=DANGER)
    tree.tag_configure("pending", foreground=MUTED)
    return frame, tree


def stat_card(parent: tk.Misc, label: str) -> tuple[tk.Frame, tk.Label]:
    card = tk.Frame(parent, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
    inner = tk.Frame(card, bg=SURFACE)
    inner.pack(fill="both", expand=True, padx=18, pady=14)
    tk.Label(
        inner,
        text=label,
        bg=SURFACE,
        fg=MUTED,
        font=font(8),
        anchor="w",
    ).pack(fill="x")
    value = tk.Label(
        inner,
        text="—",
        bg=SURFACE,
        fg=PRIMARY_DARK,
        font=font(18, "bold"),
        anchor="w",
    )
    value.pack(fill="x", pady=(4, 0))
    return card, value


def format_score(value) -> str:
    return "—" if value is None else f"{value:.2f}"


def status_label(status: str | None) -> str:
    if not status:
        return "Chưa nhập điểm"
    return _STATUS_LABELS.get(status.upper(), status)


def status_chip_label(status: str | None) -> str:
    """Nhãn trạng thái dùng cho cột bảng điểm sinh viên."""
    if not status:
        return "Chưa có điểm"
    mapping = {
        "PASSED": "Đã có điểm",
        "FAILED": "Không đạt",
        "PENDING": "Chưa có điểm",
    }
    return mapping.get(status.upper(), status)


def row_tag(status: str | None) -> tuple[str, ...]:
    if not status:
        return ("pending",)
    normalized = status.lower()
    return (normalized,) if normalized in ("passed", "failed", "pending") else ()
