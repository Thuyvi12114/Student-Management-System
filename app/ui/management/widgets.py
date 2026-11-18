"""Shared, theme-aligned management page widgets."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from collections.abc import Callable
from threading import Event
from typing import TypeVar
from tkinter import ttk

from app.ui.theme import (
    BACKGROUND,
    BORDER,
    MUTED,
    PRIMARY_DARK,
    PRIMARY_SOFT,
    SURFACE,
    TEXT,
    font,
)

T = TypeVar("T")


def create_stat_card(parent: tk.Misc, title: str) -> tuple[tk.Frame, tk.Label]:
    card = tk.Frame(parent, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
    inner = tk.Frame(card, bg=SURFACE)
    inner.pack(fill="both", expand=True, padx=16, pady=12)
    tk.Label(
        inner,
        text=title,
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
        font=font(19, "bold"),
        anchor="w",
    )
    value.pack(fill="x", pady=(5, 0))
    return card, value


def configure_management_table(widget: tk.Misc) -> None:
    style = ttk.Style(widget)
    style.configure(
        "Management.Treeview",
        background=SURFACE,
        fieldbackground=SURFACE,
        foreground=TEXT,
        rowheight=32,
        font=font(9),
        borderwidth=0,
    )
    style.configure(
        "Management.Treeview.Heading",
        background=BACKGROUND,
        foreground=MUTED,
        font=font(8, "bold"),
        relief="flat",
        padding=(8, 7),
    )
    style.map(
        "Management.Treeview",
        background=[("selected", PRIMARY_SOFT)],
        foreground=[("selected", PRIMARY_DARK)],
    )


def run_in_background(
    widget: tk.Misc,
    operation: Callable[[], T],
    on_success: Callable[[T], None],
    on_error: Callable[[BaseException], None],
) -> None:
    """Run blocking work off the UI thread and deliver its result on the Tk thread."""
    result_queue: queue.Queue[T] = queue.Queue(maxsize=1)
    error_queue: queue.Queue[BaseException] = queue.Queue(maxsize=1)
    completed = Event()

    def worker() -> None:
        try:
            result_queue.put(operation())
        except Exception as exc:
            error_queue.put(exc)
        finally:
            completed.set()

    def poll() -> None:
        if not completed.is_set():
            try:
                widget.after(40, poll)
            except tk.TclError:
                return
            return

        try:
            error = error_queue.get_nowait()
        except queue.Empty:
            on_success(result_queue.get_nowait())
        else:
            on_error(error)

    threading.Thread(target=worker, daemon=True).start()
    widget.after(40, poll)
