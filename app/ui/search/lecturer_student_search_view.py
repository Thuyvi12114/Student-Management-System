"""UI 1.18 - Giảng viên tra cứu sinh viên (UC-01): chỉ thấy mã sinh viên, họ tên, lớp."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.dao.errors import DataAccessError
from app.models import LecturerStudentSearchResult
from app.security.session import Session
from app.service.exceptions import ServiceError
from app.service.student_search_service import StudentSearchService
from app.ui.management.widgets import configure_management_table, run_in_background
from app.ui.theme import (
    BACKGROUND, BORDER, DANGER, MUTED, PRIMARY_DARK, SURFACE, TEXT,
    font, secondary_button,
)

_PAGE_SIZE = 10
_ALL_CLASSES = "Tất cả lớp"


class LecturerStudentSearchView(tk.Frame):
    def __init__(self, parent: tk.Misc, service: StudentSearchService, session: Session) -> None:
        super().__init__(parent, bg=BACKGROUND)
        self._service = service
        self._session = session
        self._page = 1
        self._pages = 0
        self._loading = False
        self._after_id: str | None = None
        self._build()
        self._load(refresh_classes=True)

    def _build(self) -> None:
        page = tk.Frame(self, bg=BACKGROUND)
        page.pack(fill="both", expand=True, padx=32, pady=24)
        tk.Label(page, text="Tra cứu sinh viên", bg=BACKGROUND, fg=TEXT, font=font(20, "bold"), anchor="w").pack(fill="x")
        tk.Label(
            page,
            text="Tìm theo mã sinh viên, họ tên hoặc lớp (khớp một phần, không phân biệt hoa thường). "
                 "Chỉ hiển thị mã sinh viên, họ tên và lớp.",
            bg=BACKGROUND, fg=MUTED, font=font(9), anchor="w", wraplength=860, justify="left",
        ).pack(fill="x", pady=(5, 14))

        filters = tk.Frame(page, bg=BACKGROUND)
        filters.pack(fill="x", pady=(0, 14))
        wrap = tk.Frame(filters, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        wrap.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self._keyword = tk.StringVar()
        self._entry = ttk.Entry(wrap, textvariable=self._keyword, font=font(9))
        self._entry.pack(fill="x", padx=10, pady=8)
        self._entry.bind("<KeyRelease>", self._schedule)
        self._class_var = tk.StringVar(value=_ALL_CLASSES)
        self._class_combo = ttk.Combobox(filters, textvariable=self._class_var, values=[_ALL_CLASSES],
                                         state="readonly", width=18, font=font(9))
        self._class_combo.pack(side="left", padx=(0, 10), ipady=5)
        self._class_combo.bind("<<ComboboxSelected>>", self._changed)
        secondary_button(filters, "Xóa bộ lọc", self._clear).pack(side="left")

        card = tk.Frame(page, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="both", expand=True)
        inner = tk.Frame(card, bg=SURFACE)
        inner.pack(fill="both", expand=True, padx=18, pady=16)
        head = tk.Frame(inner, bg=SURFACE)
        head.pack(fill="x", pady=(0, 10))
        tk.Label(head, text="Danh sách sinh viên", bg=SURFACE, fg=TEXT, font=font(11, "bold")).pack(side="left")
        self._summary = tk.Label(head, text="Đang tải...", bg=SURFACE, fg=MUTED, font=font(8))
        self._summary.pack(side="right")

        configure_management_table(inner)
        self._tree = ttk.Treeview(inner, columns=("id", "name", "class"), show="headings", height=_PAGE_SIZE,
                                  style="Management.Treeview", selectmode="browse")
        for key, label, width in (("id", "Mã sinh viên", 160), ("name", "Họ và tên", 360), ("class", "Lớp", 200)):
            self._tree.heading(key, text=label, anchor="w")
            self._tree.column(key, width=width, minwidth=80, anchor="w")
        self._tree.tag_configure("odd", background="#F8FAFC")
        self._tree.pack(fill="both", expand=True)
        self._empty = tk.Label(inner, text="", bg=SURFACE, fg=MUTED, font=font(9), pady=10)
        self._empty.pack(fill="x")

        foot = tk.Frame(inner, bg=SURFACE)
        foot.pack(fill="x", pady=(8, 0))
        self._range = tk.Label(foot, text="", bg=SURFACE, fg=MUTED, font=font(8))
        self._range.pack(side="left")
        controls = tk.Frame(foot, bg=SURFACE)
        controls.pack(side="right")
        self._prev = secondary_button(controls, "Trước", self._previous)
        self._prev.pack(side="left", padx=(0, 6))
        self._page_label = tk.Label(controls, text="Trang 0 / 0", bg=SURFACE, fg=PRIMARY_DARK, font=font(8, "bold"), padx=8)
        self._page_label.pack(side="left")
        self._next = secondary_button(controls, "Sau", self._next_page)
        self._next.pack(side="left", padx=(6, 0))
        self._feedback = tk.Label(page, text="", bg=BACKGROUND, fg=DANGER, font=font(9), anchor="w")
        self._feedback.pack(fill="x", pady=(8, 0))

    def _schedule(self, _e=None) -> None:
        if self._after_id is not None:
            self.after_cancel(self._after_id)
        self._after_id = self.after(250, self._changed)

    def _changed(self, _e=None) -> None:
        self._page = 1
        self._load()

    def _clear(self) -> None:
        self._keyword.set("")
        self._class_var.set(_ALL_CLASSES)
        self._changed()

    def _previous(self) -> None:
        if self._page > 1:
            self._page -= 1
            self._load()

    def _next_page(self) -> None:
        if self._page < self._pages:
            self._page += 1
            self._load()

    def _load(self, *, refresh_classes: bool = False) -> None:
        if self._loading:
            return
        self._loading = True
        selected = self._class_var.get()
        class_name = None if selected == _ALL_CLASSES else selected
        keyword, page = self._keyword.get(), self._page

        def fetch():
            result = self._service.search_students_basic(
                self._session, keyword, page=page, page_size=_PAGE_SIZE, class_name=class_name)
            classes = self._service.class_names(self._session) if refresh_classes else None
            return result, classes

        run_in_background(self, fetch, self._loaded, self._failed)

    def _loaded(self, data: tuple[LecturerStudentSearchResult, list[str] | None]) -> None:
        result, classes = data
        self._loading = False
        self._page, self._pages = result.page, result.total_pages
        self._feedback.configure(text="")
        self._tree.delete(*self._tree.get_children())
        for index, item in enumerate(result.items):
            self._tree.insert("", "end", iid=item.student_id, values=(item.student_id, item.full_name, item.class_name),
                              tags=("odd",) if index % 2 else ())
        total = result.total_count
        start = (result.page - 1) * result.page_size + 1 if total else 0
        end = min(result.page * result.page_size, total)
        self._summary.configure(text=f"{total} sinh viên")
        self._range.configure(text=f"Hiển thị {start}–{end} trong {total} bản ghi")
        self._page_label.configure(text=f"Trang {result.page} / {result.total_pages or 1}")
        self._empty.configure(text="" if result.items else "Không có sinh viên phù hợp.")
        self._prev.configure(state="normal" if result.page > 1 else "disabled")
        self._next.configure(state="normal" if result.page < result.total_pages else "disabled")
        if classes is not None:
            self._class_combo.configure(values=[_ALL_CLASSES, *classes])

    def _failed(self, error: BaseException) -> None:
        self._loading = False
        self._feedback.configure(text=str(error) if isinstance(error, (ServiceError, DataAccessError)) else f"Lỗi: {error}")
