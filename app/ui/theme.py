"""Bảng màu, font và widget dùng chung cho giao diện."""

from __future__ import annotations

import tkinter as tk

from app.models import Role

PRIMARY = "#1D4ED8"
PRIMARY_DARK = "#1E3A8A"
PRIMARY_SOFT = "#E8EFFC"
BACKGROUND = "#F3F5FA"
SURFACE = "#FFFFFF"
TEXT = "#0F172A"
MUTED = "#64748B"
BORDER = "#E2E8F0"
DANGER = "#B91C1C"
SUCCESS = "#15803D"
DISABLED = "#93A8DE"

FONT_FAMILY = "Segoe UI"


def font(size: int, weight: str = "normal") -> tuple[str, int, str]:
    return (FONT_FAMILY, size, weight)


def primary_button(parent: tk.Misc, text: str, command) -> tk.Button:
    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=PRIMARY,
        fg="white",
        activebackground="#1E40AF",
        activeforeground="white",
        relief="flat",
        bd=0,
        highlightthickness=0,
        cursor="hand2",
        font=font(10, "bold"),
        padx=18,
        pady=10,
    )


def secondary_button(parent: tk.Misc, text: str, command) -> tk.Button:
    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=SURFACE,
        fg=PRIMARY,
        activebackground=PRIMARY_SOFT,
        activeforeground=PRIMARY,
        relief="flat",
        bd=0,
        highlightbackground=BORDER,
        highlightcolor=BORDER,
        highlightthickness=1,
        cursor="hand2",
        font=font(10, "bold"),
        padx=16,
        pady=8,
    )


def subtle_button(parent: tk.Misc, text: str, command, foreground: str = DANGER) -> tk.Button:
    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=BACKGROUND,
        fg=foreground,
        activebackground=BORDER,
        activeforeground=foreground,
        relief="flat",
        bd=0,
        highlightthickness=0,
        cursor="hand2",
        font=font(10, "bold"),
        padx=16,
        pady=9,
    )


def text_field(parent: tk.Misc, *, show: str | None = None) -> tuple[tk.Frame, tk.Entry]:
    """Trả về (khung viền, entry) để có giao diện ô nhập đồng nhất."""
    wrapper = tk.Frame(
        parent,
        bg=SURFACE,
        highlightbackground=BORDER,
        highlightcolor=PRIMARY,
        highlightthickness=1,
    )
    entry = tk.Entry(
        wrapper,
        font=font(11),
        relief="flat",
        bd=0,
        bg=SURFACE,
        fg=TEXT,
        insertbackground=TEXT,
        highlightthickness=0,
        show=show,
    )
    entry.pack(fill="x", padx=12, pady=9)
    return wrapper, entry


def role_colors(role: Role) -> tuple[str, str]:
    if role is Role.ADMIN:
        return "#DBEAFE", "#1D4ED8"
    if role is Role.LECTURER:
        return "#DCFCE7", "#15803D"
    return "#FEF3C7", "#B45309"


def role_chip(parent: tk.Misc, role: Role) -> tk.Label:
    background, foreground = role_colors(role)
    return tk.Label(
        parent,
        text=role.label,
        bg=background,
        fg=foreground,
        font=font(8, "bold"),
        padx=8,
        pady=3,
    )
