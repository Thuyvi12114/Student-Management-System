"""Màn hình Điểm số dành cho Admin (chỉ đọc) — UI thiết kế UniCore."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.dao.errors import DataAccessError
from app.security.session import Session
from app.service.exceptions import ServiceError
from app.service.grade_service import GradeService
from app.ui.grades.widgets import (
    configure_table_style,
    format_score,
    row_tag,
    status_label,
    status_of,
)
from app.ui.theme import (
    BACKGROUND,
    BORDER,
    DANGER,
    MUTED,
    PRIMARY,
    PRIMARY_DARK,
    PRIMARY_SOFT,
    SURFACE,
    TEXT,
    font,
)

_PAGE_SIZE = 6

_COLUMNS = [
    ("grade_id",     "Mã ghi danh", 100, "w"),
    ("student",      "Sinh viên",   260, "w"),
    ("course",       "Học phần",    240, "w"),
    ("final",        "Điểm cuối kỳ", 110, "center"),
    ("action",       "Thao tác",     90, "center"),
]

_ALL_COURSES  = "Tất cả học phần"
_ALL_STATUS   = "Trang thái điểm"
_STATUS_OPTS  = [_ALL_STATUS, "Đã có điểm", "Chưa có điểm"]


class AdminGradesView(tk.Frame):
    """Admin xem toàn bộ điểm, lọc/tìm kiếm, xem chi tiết từng bản ghi."""

    def __init__(self, parent: tk.Misc, grade_service: GradeService, session: Session) -> None:
        super().__init__(parent, bg=BACKGROUND)
        self._service   = grade_service
        self._session   = session
        self._students  = []
        self._courses   = []
        self._all_rows: list = []        # toàn bộ GradeEntry sau lọc
        self._page      = 1
        self._detail_grade = None        # GradeEntry đang xem chi tiết
        self._build()
        self._load_options()

    # ------------------------------------------------------------------ build

    def _build(self) -> None:
        # Outer scrollable canvas
        outer = tk.Frame(self, bg=BACKGROUND)
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, bg=BACKGROUND, highlightthickness=0)
        sb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        self._sf = tk.Frame(canvas, bg=BACKGROUND)
        self._sf.bind("<Configure>",
                      lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        _win = canvas.create_window((0, 0), window=self._sf, anchor="nw")
        canvas.configure(yscrollcommand=sb.set)
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(_win, width=e.width))
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        canvas.bind("<Enter>",
                    lambda e: canvas.bind_all(
                        "<MouseWheel>",
                        lambda ev: canvas.yview_scroll(-1*(ev.delta//120), "units")))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        page = tk.Frame(self._sf, bg=BACKGROUND)
        page.pack(fill="both", expand=True, padx=32, pady=24)

        # ── Breadcrumb ────────────────────────────────────────────────────
        bc = tk.Frame(page, bg=BACKGROUND)
        bc.pack(fill="x", pady=(0, 8))
        tk.Label(bc, text="Quản trị  /  Điểm số",
                 bg=BACKGROUND, fg=MUTED, font=font(8)).pack(side="left")

        # ── Title ─────────────────────────────────────────────────────────
        tk.Label(page, text="Điểm số",
                 bg=BACKGROUND, fg=TEXT, font=font(20, "bold"), anchor="w").pack(fill="x")
        tk.Label(page,
                 text="Tra cứu điểm cuối kỳ theo sinh viên hoặc học phần. "
                      "Quản trị viên chỉ có quyền xem.",
                 bg=BACKGROUND, fg=MUTED, font=font(9), anchor="w", justify="left").pack(
            fill="x", pady=(4, 18))

        # ── Search bar ────────────────────────────────────────────────────
        search_row = tk.Frame(page, bg=BACKGROUND)
        search_row.pack(fill="x", pady=(0, 16))

        # Search field
        search_wrap = tk.Frame(search_row, bg=SURFACE,
                               highlightbackground=BORDER, highlightthickness=1)
        search_wrap.pack(side="left", fill="x", expand=True, padx=(0, 10))
        tk.Label(search_wrap, text="🔍", bg=SURFACE, fg=MUTED,
                 font=font(10)).pack(side="left", padx=(10, 0))
        self._search_var = tk.StringVar()
        self._search_entry = tk.Entry(
            search_wrap, textvariable=self._search_var,
            font=font(9), relief="flat", bd=0,
            bg=SURFACE, fg=TEXT, insertbackground=TEXT, highlightthickness=0,
        )
        self._search_entry.insert(0, "Tìm mã hoặc tên sinh viên...")
        self._search_entry.configure(fg="#94A3B8")
        self._search_entry.bind("<FocusIn>",  self._clear_placeholder)
        self._search_entry.bind("<FocusOut>", self._restore_placeholder)
        self._search_entry.bind("<KeyRelease>", lambda _e: self._apply_filter())
        self._search_entry.pack(side="left", fill="x", expand=True, padx=8, pady=9)

        # Course combobox
        self._course_var = tk.StringVar(value=_ALL_COURSES)
        course_wrap = tk.Frame(search_row, bg=SURFACE,
                               highlightbackground=BORDER, highlightthickness=1)
        course_wrap.pack(side="left", padx=(0, 10))
        self._course_combo = ttk.Combobox(course_wrap, textvariable=self._course_var,
                                          state="readonly", width=20, font=font(9))
        self._course_combo.pack(padx=8, pady=7)
        self._course_combo.bind("<<ComboboxSelected>>", lambda _e: self._apply_filter())

        # Status combobox
        self._status_var = tk.StringVar(value=_ALL_STATUS)
        status_wrap = tk.Frame(search_row, bg=SURFACE,
                               highlightbackground=BORDER, highlightthickness=1)
        status_wrap.pack(side="left", padx=(0, 10))
        self._status_combo = ttk.Combobox(
            status_wrap, textvariable=self._status_var,
            values=_STATUS_OPTS, state="readonly", width=18, font=font(9))
        self._status_combo.pack(padx=8, pady=7)
        self._status_combo.bind("<<ComboboxSelected>>", lambda _e: self._apply_filter())

        # Clear button
        clear_btn = tk.Button(
            search_row, text="Xóa tìm kiếm",
            command=self._clear_filter,
            bg=SURFACE, fg=TEXT,
            activebackground=BACKGROUND, activeforeground=TEXT,
            relief="flat", bd=0,
            highlightbackground=BORDER, highlightthickness=1,
            cursor="hand2", font=font(9),
            padx=14, pady=7,
        )
        clear_btn.pack(side="left")

        # ── Result table card ─────────────────────────────────────────────
        table_card = tk.Frame(page, bg=SURFACE,
                              highlightbackground=BORDER, highlightthickness=1)
        table_card.pack(fill="x", pady=(0, 16))
        ti = tk.Frame(table_card, bg=SURFACE)
        ti.pack(fill="both", expand=True, padx=20, pady=16)

        # Card header
        ch = tk.Frame(ti, bg=SURFACE)
        ch.pack(fill="x", pady=(0, 4))
        tk.Label(ch, text="Kết quả theo ghi danh",
                 bg=SURFACE, fg=TEXT, font=font(11, "bold"), anchor="w").pack(side="left")
        self._badge = tk.Label(ch, text="Thang điểm 0–10",
                               bg=PRIMARY_SOFT, fg=PRIMARY_DARK,
                               font=font(7, "bold"), padx=8, pady=3)
        self._badge.pack(side="right")

        self._summary_label = tk.Label(ti, text="",
                                       bg=SURFACE, fg=MUTED, font=font(8), anchor="w")
        self._summary_label.pack(fill="x", pady=(0, 10))

        # Treeview table
        configure_table_style(ti)
        self.tree = ttk.Treeview(
            ti, columns=[c[0] for c in _COLUMNS],
            show="headings", height=_PAGE_SIZE,
            style="Grades.Treeview", selectmode="browse",
        )
        for key, label, width, anchor in _COLUMNS:
            self.tree.heading(key, text=label, anchor=anchor)
            self.tree.column(key, width=width, minwidth=50, anchor=anchor, stretch=True)

        self.tree.tag_configure("passed",  foreground="#15803D")
        self.tree.tag_configure("failed",  foreground="#B91C1C")
        self.tree.tag_configure("pending", foreground="#B45309", background="#FFFBEB")
        self.tree.bind("<<TreeviewSelect>>", self._on_row_select)
        self.tree.pack(fill="x")

        # Pagination row
        pag_row = tk.Frame(ti, bg=SURFACE)
        pag_row.pack(fill="x", pady=(12, 0))

        self._page_info = tk.Label(pag_row, text="",
                                   bg=SURFACE, fg=MUTED, font=font(8), anchor="w")
        self._page_info.pack(side="left")

        pag_right = tk.Frame(pag_row, bg=SURFACE)
        pag_right.pack(side="right")

        self._prev_btn = self._page_btn(pag_right, "Trước", self._prev_page)
        self._prev_btn.pack(side="left", padx=(0, 4))
        self._page_btns_frame = tk.Frame(pag_right, bg=SURFACE)
        self._page_btns_frame.pack(side="left")
        self._next_btn = self._page_btn(pag_right, "Sau", self._next_page)
        self._next_btn.pack(side="left", padx=(4, 0))

        # ── Detail card ───────────────────────────────────────────────────
        self._detail_card = tk.Frame(page, bg=SURFACE,
                                     highlightbackground=BORDER, highlightthickness=1)
        self._detail_card.pack(fill="x", pady=(0, 24))
        self._build_detail_panel(self._detail_card)

        self.feedback = tk.Label(page, text="",
                                 bg=BACKGROUND, fg=DANGER, font=font(9),
                                 anchor="w", wraplength=860)
        self.feedback.pack(fill="x")

    def _build_detail_panel(self, parent: tk.Frame) -> None:
        di = tk.Frame(parent, bg=SURFACE)
        di.pack(fill="both", expand=True, padx=20, pady=16)

        hdr = tk.Frame(di, bg=SURFACE)
        hdr.pack(fill="x", pady=(0, 4))
        tk.Label(hdr, text="Chi tiết điểm cuối kỳ  ·  Chỉ xem",
                 bg=SURFACE, fg=TEXT, font=font(11, "bold"), anchor="w").pack(side="left")

        self._detail_meta = tk.Label(di, text="Chọn một dòng trong bảng để xem chi tiết.",
                                     bg=SURFACE, fg=MUTED, font=font(8), anchor="w")
        self._detail_meta.pack(fill="x", pady=(0, 14))

        body = tk.Frame(di, bg=SURFACE)
        body.pack(fill="x")

        # Score field (read-only)
        field_col = tk.Frame(body, bg=SURFACE)
        field_col.pack(side="left", anchor="n")
        tk.Label(field_col, text="Điểm cuối kỳ (0–10)",
                 bg=SURFACE, fg=TEXT, font=font(8, "bold"), anchor="w").pack(fill="x", pady=(0, 5))
        score_wrap = tk.Frame(field_col, bg=SURFACE,
                              highlightbackground=BORDER, highlightthickness=1,
                              width=200)
        score_wrap.pack(fill="x")
        score_wrap.pack_propagate(False)
        self._detail_score = tk.Label(score_wrap, text="Chưa có điểm",
                                      bg=SURFACE, fg=MUTED,
                                      font=font(10), anchor="w")
        self._detail_score.pack(padx=12, pady=10, anchor="w")

        # Note column
        note_col = tk.Frame(body, bg=SURFACE)
        note_col.pack(side="left", padx=(24, 0), anchor="n")
        tk.Label(note_col,
                 text="Chỉ giảng viên phụ trách học phần mới được nhập hoặc cập nhật điểm.",
                 bg=SURFACE, fg=MUTED, font=font(8),
                 wraplength=400, justify="left", anchor="w").pack(fill="x")
        tk.Label(note_col,
                 text="Quản trị viên không được thêm, sửa hoặc xóa điểm.",
                 bg=SURFACE, fg=MUTED, font=font(8), anchor="w").pack(fill="x", pady=(4, 0))

        # Close button
        btn_col = tk.Frame(body, bg=SURFACE)
        btn_col.pack(side="right", anchor="n")
        self._close_btn = tk.Button(
            btn_col, text="✓  Đóng",
            command=self._close_detail,
            bg=PRIMARY, fg="white",
            activebackground="#1E40AF", activeforeground="white",
            relief="flat", bd=0, highlightthickness=0,
            cursor="hand2", font=font(9, "bold"),
            padx=18, pady=9,
        )
        self._close_btn.pack()

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _page_btn(parent: tk.Frame, text: str, cmd) -> tk.Button:
        return tk.Button(
            parent, text=text, command=cmd,
            bg=SURFACE, fg=TEXT,
            activebackground=PRIMARY_SOFT, activeforeground=PRIMARY_DARK,
            relief="flat", bd=0,
            highlightbackground=BORDER, highlightthickness=1,
            cursor="hand2", font=font(9),
            padx=12, pady=5,
        )

    def _make_page_number_btn(self, parent: tk.Frame, num: int) -> tk.Button:
        is_current = (num == self._page)
        btn = tk.Button(
            parent, text=str(num),
            command=lambda n=num: self._goto_page(n),
            bg=PRIMARY if is_current else SURFACE,
            fg="white" if is_current else TEXT,
            activebackground=PRIMARY_SOFT,
            relief="flat", bd=0,
            highlightbackground=BORDER, highlightthickness=1,
            cursor="hand2", font=font(9, "bold" if is_current else "normal"),
            padx=10, pady=5,
        )
        btn.pack(side="left", padx=2)
        return btn

    # ------------------------------------------------------------------ data

    def _load_options(self) -> None:
        try:
            self._students, self._courses = self._service.list_filter_options(self._session)
        except (ServiceError, DataAccessError) as exc:
            self.feedback.configure(text=str(exc))
            return

        self._course_combo.configure(
            values=[_ALL_COURSES]
            + [f"{c.course_code} - {c.course_name}" for c in self._courses]
        )
        self._course_combo.current(0)
        self._search()

    def _search(self) -> None:
        idx = self._course_combo.current()
        course_id = self._courses[idx - 1].course_id if idx > 0 else None

        try:
            rows = self._service.admin_search(self._session, None, course_id)
        except (ServiceError, DataAccessError) as exc:
            self.feedback.configure(text=str(exc))
            return

        self.feedback.configure(text="")
        self._raw_rows = rows
        self._apply_filter()

    def _apply_filter(self) -> None:
        keyword = self._search_var.get().strip().lower()
        placeholder = "tìm mã hoặc tên sinh viên..."
        if keyword == placeholder:
            keyword = ""

        status_filter = self._status_var.get()

        filtered = []
        for g in self._raw_rows:
            # Keyword filter (mã SV, tên SV, mã HP, tên HP)
            if keyword and keyword not in (
                (g.student_code + g.student_name + g.course_code + g.course_name).lower()
            ):
                continue
            # Status filter
            if status_filter == "Đã có điểm" and g.grade_value is None:
                continue
            if status_filter == "Chưa có điểm" and g.grade_value is not None:
                continue
            filtered.append(g)

        self._all_rows = filtered
        self._page = 1
        self._render_page()

    def _render_page(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        total  = len(self._all_rows)
        pages  = max(1, (total + _PAGE_SIZE - 1) // _PAGE_SIZE)
        start  = (_page := min(self._page, pages)) - 1
        end    = min(start + _PAGE_SIZE, total)
        self._page = _page
        chunk  = self._all_rows[start * _PAGE_SIZE: end]

        # Pending count for summary
        pending_count = sum(1 for g in self._all_rows if g.grade_value is None)
        self._summary_label.configure(
            text=f"{total} lượt ghi danh  ·  {pending_count} chưa có điểm"
        )

        for grade in chunk:
            grade_id_str = f"GD{grade.grade_id:06d}"
            sv_str = f"{grade.student_code} · {grade.student_name}"
            hp_str = f"{grade.course_code} · {grade.course_name}"
            score  = format_score(grade.grade_value)
            tag    = row_tag(status_of(grade.grade_value))

            self.tree.insert(
                "", "end",
                iid=str(grade.grade_id),
                values=(grade_id_str, sv_str, hp_str, score, "Xem chi tiết"),
                tags=tag,
            )

        # Pagination info
        display_start = start * _PAGE_SIZE + 1 if total > 0 else 0
        self.feedback.configure(text="")
        self._page_info.configure(
            text=f"Hiển thị {display_start}–{end} trong {total} bản ghi"
        )

        # Rebuild page number buttons
        for w in self._page_btns_frame.winfo_children():
            w.destroy()
        shown_pages = self._page_range(pages, self._page)
        for p in shown_pages:
            if p == "...":
                tk.Label(self._page_btns_frame, text="...",
                         bg=SURFACE, fg=MUTED, font=font(9)).pack(side="left", padx=2)
            else:
                self._make_page_number_btn(self._page_btns_frame, p)

        self._prev_btn.configure(state="normal" if self._page > 1 else "disabled")
        self._next_btn.configure(state="normal" if self._page < pages else "disabled")

    @staticmethod
    def _page_range(total_pages: int, current: int) -> list:
        if total_pages <= 5:
            return list(range(1, total_pages + 1))
        pages = []
        for p in range(1, total_pages + 1):
            if p == 1 or p == total_pages or abs(p - current) <= 1:
                pages.append(p)
            elif pages and pages[-1] != "...":
                pages.append("...")
        return pages

    # ------------------------------------------------------------------ interaction

    def _on_row_select(self, _event=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        grade_id = int(sel[0])
        grade = next((g for g in self._all_rows if g.grade_id == grade_id), None)
        if grade is None:
            return
        self._detail_grade = grade

        self._detail_meta.configure(
            text=f"GD{grade.grade_id:06d}  ·  {grade.student_name}  ·  "
                 f"{grade.course_code} — {grade.course_name}"
        )
        if grade.grade_value is not None:
            self._detail_score.configure(text=format_score(grade.grade_value), fg="#0F172A")
        else:
            self._detail_score.configure(text="Chưa có điểm", fg=MUTED)

    def _close_detail(self) -> None:
        self._detail_grade = None
        self._detail_meta.configure(text="Chọn một dòng trong bảng để xem chi tiết.")
        self._detail_score.configure(text="Chưa có điểm", fg=MUTED)
        self.tree.selection_remove(*self.tree.selection())

    def _clear_filter(self) -> None:
        self._restore_placeholder()
        self._course_combo.current(0)
        self._status_combo.current(0)
        self._search()

    def _clear_placeholder(self, _event=None) -> None:
        if self._search_entry.get() == "Tìm mã hoặc tên sinh viên...":
            self._search_entry.delete(0, "end")
            self._search_entry.configure(fg=TEXT)

    def _restore_placeholder(self, _event=None) -> None:
        if not self._search_entry.get():
            self._search_entry.insert(0, "Tìm mã hoặc tên sinh viên...")
            self._search_entry.configure(fg="#94A3B8")

    def _prev_page(self) -> None:
        if self._page > 1:
            self._page -= 1
            self._render_page()

    def _next_page(self) -> None:
        total  = len(self._all_rows)
        pages  = max(1, (total + _PAGE_SIZE - 1) // _PAGE_SIZE)
        if self._page < pages:
            self._page += 1
            self._render_page()

    def _goto_page(self, num: int) -> None:
        self._page = num
        self._render_page()

    # ------------------------------------------------------------------ init

    @property
    def _raw_rows(self):
        return getattr(self, "_raw_rows_data", [])

    @_raw_rows.setter
    def _raw_rows(self, value):
        self._raw_rows_data = value
