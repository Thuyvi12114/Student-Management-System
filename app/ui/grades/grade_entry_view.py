"""Màn hình Điểm số (nhập & cập nhật) dành cho giảng viên — UI UniCore."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.dao.errors import DataAccessError
from app.models import CourseGradeRow
from app.security.session import Session
from app.service.exceptions import ServiceError
from app.service.grade_service import CourseGradeSheet, GradeService
from app.ui.grades.widgets import configure_table_style, format_score, row_tag, status_label
from app.ui.theme import (
    BACKGROUND,
    BORDER,
    DANGER,
    MUTED,
    PRIMARY,
    PRIMARY_DARK,
    PRIMARY_SOFT,
    SURFACE,
    SUCCESS,
    TEXT,
    font,
    text_field,
)

_PAGE_SIZE = 4

_COLUMNS = [
    ("student_code", "Mã sinh viên",  110, "w"),
    ("student_name", "Họ và tên",     220, "w"),
    ("class_name",   "Lớp",            90, "w"),
    ("grade_id",     "Mã điểm",        90, "center"),
    ("final",        "Điểm",           70, "center"),
    ("status",       "Trạng thái",    110, "center"),
    ("action",       "Thao tác",       90, "center"),
]


class GradeEntryView(tk.Frame):
    """Giảng viên nhập điểm mới hoặc cập nhật điểm cuối kỳ cho sinh viên."""

    def __init__(self, parent: tk.Misc, grade_service: GradeService, session: Session) -> None:
        super().__init__(parent, bg=BACKGROUND)
        self._service  = grade_service
        self._session  = session
        self._courses  = []
        self._course   = None
        self._all_rows: list[CourseGradeRow] = []
        self._rows_by_iid: dict[str, CourseGradeRow] = {}
        self._selected_row: CourseGradeRow | None = None
        self._page = 1
        self._build()
        self._load_courses()

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
        self._breadcrumb = tk.Label(bc,
                                    text="Giảng viên  /  Học phần được phân công",
                                    bg=BACKGROUND, fg=MUTED, font=font(8))
        self._breadcrumb.pack(side="left")

        # ── Title row ─────────────────────────────────────────────────────
        title_row = tk.Frame(page, bg=BACKGROUND)
        title_row.pack(fill="x", pady=(0, 4))
        self._title_label = tk.Label(title_row, text="Điểm số",
                                     bg=BACKGROUND, fg=TEXT,
                                     font=font(20, "bold"), anchor="w")
        self._title_label.pack(side="left")

        back_btn = tk.Button(
            title_row, text="Về học phần của tôi",
            command=self._go_back_to_courses,
            bg=SURFACE, fg=TEXT,
            activebackground=PRIMARY_SOFT, activeforeground=PRIMARY_DARK,
            relief="flat", bd=0,
            highlightbackground=BORDER, highlightthickness=1,
            cursor="hand2", font=font(9),
            padx=16, pady=8,
        )
        back_btn.pack(side="right")

        self._subtitle_label = tk.Label(
            page,
            text="Phụ trách: —",
            bg=BACKGROUND, fg=PRIMARY, font=font(9), anchor="w",
        )
        self._subtitle_label.pack(fill="x", pady=(0, 16))

        # ── Course info card ──────────────────────────────────────────────
        self._info_card = tk.Frame(page, bg=SURFACE,
                                   highlightbackground=BORDER, highlightthickness=1)
        self._info_card.pack(fill="x", pady=(0, 16))
        self._build_info_card(self._info_card)

        # ── Filter bar ────────────────────────────────────────────────────
        filter_row = tk.Frame(page, bg=BACKGROUND)
        filter_row.pack(fill="x", pady=(0, 14))

        # Course selector dropdown
        self._course_var = tk.StringVar()
        course_wrap = tk.Frame(filter_row, bg=SURFACE,
                               highlightbackground=BORDER, highlightthickness=1)
        course_wrap.pack(side="left", padx=(0, 10))
        self._course_combo = ttk.Combobox(
            course_wrap, textvariable=self._course_var,
            state="readonly", width=24, font=font(9),
        )
        self._course_combo.pack(padx=8, pady=7)
        self._course_combo.bind("<<ComboboxSelected>>",
                                lambda _e: self._on_course_change())

        # Search
        search_wrap = tk.Frame(filter_row, bg=SURFACE,
                               highlightbackground=BORDER, highlightthickness=1)
        search_wrap.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self._search_entry = tk.Entry(
            search_wrap, font=font(9),
            relief="flat", bd=0,
            bg=SURFACE, fg="#94A3B8", insertbackground=TEXT, highlightthickness=0,
        )
        self._search_entry.insert(0, "Tìm mã, họ tên hoặc lớp sinh viên...")
        self._search_entry.bind("<FocusIn>",  self._clear_placeholder)
        self._search_entry.bind("<FocusOut>", self._restore_placeholder)
        self._search_entry.bind("<KeyRelease>", lambda _e: self._apply_filter())
        self._search_entry.pack(fill="x", expand=True, padx=12, pady=9)

        # Status dropdown
        self._status_var = tk.StringVar(value="Trạng thái điểm")
        status_wrap = tk.Frame(filter_row, bg=SURFACE,
                               highlightbackground=BORDER, highlightthickness=1)
        status_wrap.pack(side="left", padx=(0, 10))
        status_combo = ttk.Combobox(
            status_wrap, textvariable=self._status_var,
            values=["Trạng thái điểm", "Đã có điểm", "Chưa có điểm"],
            state="readonly", width=16, font=font(9),
        )
        status_combo.pack(padx=8, pady=7)
        status_combo.bind("<<ComboboxSelected>>", lambda _e: self._apply_filter())

        # Clear
        tk.Button(
            filter_row, text="Xóa",
            command=self._clear_filter,
            bg=SURFACE, fg=TEXT,
            activebackground=BACKGROUND,
            relief="flat", bd=0,
            highlightbackground=BORDER, highlightthickness=1,
            cursor="hand2", font=font(9),
            padx=12, pady=7,
        ).pack(side="left")

        # ── Grade table card ──────────────────────────────────────────────
        table_card = tk.Frame(page, bg=SURFACE,
                              highlightbackground=BORDER, highlightthickness=1)
        table_card.pack(fill="x", pady=(0, 16))
        ti = tk.Frame(table_card, bg=SURFACE)
        ti.pack(fill="both", expand=True, padx=20, pady=16)

        # Header
        th = tk.Frame(ti, bg=SURFACE)
        th.pack(fill="x", pady=(0, 4))
        tk.Label(th, text="Điểm cuối kỳ  ·  Thang 0–10",
                 bg=SURFACE, fg=TEXT, font=font(11, "bold"), anchor="w").pack(side="left")

        self._add_btn = tk.Button(
            th, text="+ Ghi điểm mới",
            command=self._open_new_entry,
            bg=PRIMARY, fg="white",
            activebackground="#1E40AF", activeforeground="white",
            relief="flat", bd=0, highlightthickness=0,
            cursor="hand2", font=font(9, "bold"),
            padx=16, pady=8,
        )
        self._add_btn.pack(side="right")

        # Treeview
        configure_table_style(ti)
        self.tree = ttk.Treeview(
            ti,
            columns=[c[0] for c in _COLUMNS],
            show="headings",
            height=_PAGE_SIZE,
            style="Grades.Treeview",
            selectmode="browse",
        )
        for key, label, width, anchor in _COLUMNS:
            self.tree.heading(key, text=label, anchor=anchor)
            self.tree.column(key, width=width, minwidth=40, anchor=anchor, stretch=True)

        self.tree.tag_configure("passed",  foreground="#15803D")
        self.tree.tag_configure("failed",  foreground="#B91C1C")
        self.tree.tag_configure("pending", foreground=MUTED)
        self.tree.bind("<<TreeviewSelect>>", self._on_row_select)
        self.tree.pack(fill="x")

        # Pagination
        pag = tk.Frame(ti, bg=SURFACE)
        pag.pack(fill="x", pady=(10, 0))
        self._page_info = tk.Label(pag, text="", bg=SURFACE, fg=MUTED,
                                   font=font(8), anchor="w")
        self._page_info.pack(side="left")
        pag_right = tk.Frame(pag, bg=SURFACE)
        pag_right.pack(side="right")
        self._prev_btn = self._nav_btn(pag_right, "Trước", self._prev_page)
        self._prev_btn.pack(side="left", padx=(0, 4))
        self._pag_btns = tk.Frame(pag_right, bg=SURFACE)
        self._pag_btns.pack(side="left")
        self._next_btn = self._nav_btn(pag_right, "Sau", self._next_page)
        self._next_btn.pack(side="left", padx=(4, 0))

        # ── Entry form (hidden until row selected) ────────────────────────
        self._form_card = tk.Frame(page, bg=SURFACE,
                                   highlightbackground=BORDER, highlightthickness=1)
        self._form_card.pack(fill="x", pady=(0, 16))
        self._build_form(self._form_card)

        # ── Bottom note ───────────────────────────────────────────────────
        note = tk.Frame(page, bg="#EFF6FF",
                        highlightbackground="#BFDBFE", highlightthickness=1)
        note.pack(fill="x", pady=(0, 24))
        ni = tk.Frame(note, bg="#EFF6FF")
        ni.pack(fill="x", padx=16, pady=12)
        tk.Label(
            ni,
            text="Một sinh viên · Một học phần · Một điểm cuối kỳ",
            bg="#EFF6FF", fg="#1D4ED8", font=font(9, "bold"), anchor="w",
        ).pack(fill="x")
        tk.Label(
            ni,
            text="Chỉ giảng viên đang được phân công mới được ghi hoặc cập nhật điểm. "
                 "Nếu cặp sinh viên–học phần đã có điểm, hãy cập nhật bản ghi hiện có.",
            bg="#EFF6FF", fg="#3B82F6", font=font(8),
            wraplength=800, justify="left", anchor="w",
        ).pack(fill="x", pady=(4, 0))

        self._feedback = tk.Label(page, text="", bg=BACKGROUND,
                                  fg=DANGER, font=font(9), anchor="w", wraplength=860)
        self._feedback.pack(fill="x")

    def _build_info_card(self, parent: tk.Frame) -> None:
        ii = tk.Frame(parent, bg=SURFACE)
        ii.pack(fill="both", expand=True, padx=20, pady=16)

        left = tk.Frame(ii, bg=SURFACE)
        left.pack(side="left", fill="both", expand=True)

        self._info_course_title = tk.Label(
            left, text="—",
            bg=SURFACE, fg=TEXT, font=font(13, "bold"), anchor="w",
        )
        self._info_course_title.pack(fill="x")
        self._info_course_desc = tk.Label(
            left, text="",
            bg=SURFACE, fg=MUTED, font=font(8),
            anchor="w", wraplength=580, justify="left",
        )
        self._info_course_desc.pack(fill="x", pady=(4, 0))

        right = tk.Frame(ii, bg=SURFACE)
        right.pack(side="right", anchor="n")
        self._info_graded = tk.Label(
            right, text="—",
            bg=SURFACE, fg=PRIMARY_DARK, font=font(16, "bold"), anchor="e",
        )
        self._info_graded.pack(anchor="e")
        self._info_graded_sub = tk.Label(
            right, text="",
            bg=SURFACE, fg=MUTED, font=font(8), anchor="e",
        )
        self._info_graded_sub.pack(anchor="e")

    def _build_form(self, parent: tk.Frame) -> None:
        fi = tk.Frame(parent, bg=SURFACE)
        fi.pack(fill="both", expand=True, padx=20, pady=16)

        hdr = tk.Frame(fi, bg=SURFACE)
        hdr.pack(fill="x", pady=(0, 8))
        self._form_title = tk.Label(hdr, text="Nhập điểm cuối kỳ",
                                    bg=SURFACE, fg=TEXT, font=font(10, "bold"), anchor="w")
        self._form_title.pack(side="left")
        self._form_mode = tk.Label(hdr, text="",
                                   bg=PRIMARY_SOFT, fg=PRIMARY_DARK,
                                   font=font(7, "bold"), padx=8, pady=3)
        self._form_mode.pack(side="left", padx=(10, 0))

        self._form_meta = tk.Label(fi, text="Chọn một sinh viên trong bảng để nhập điểm.",
                                   bg=SURFACE, fg=MUTED, font=font(8), anchor="w")
        self._form_meta.pack(fill="x", pady=(0, 12))

        body = tk.Frame(fi, bg=SURFACE)
        body.pack(fill="x")

        # Score field
        field_col = tk.Frame(body, bg=SURFACE)
        field_col.pack(side="left", anchor="n")
        tk.Label(field_col, text="Điểm cuối kỳ (0–10)",
                 bg=SURFACE, fg=TEXT, font=font(8, "bold"), anchor="w").pack(fill="x", pady=(0, 5))
        fw, self._final_entry = text_field(field_col)
        self._final_entry.configure(width=14)
        fw.pack(fill="x")

        # Note
        note_col = tk.Frame(body, bg=SURFACE)
        note_col.pack(side="left", padx=(24, 0), anchor="n")
        tk.Label(note_col,
                 text="Điểm hợp lệ từ 0 đến 10, tối đa 2 chữ số thập phân.",
                 bg=SURFACE, fg=MUTED, font=font(8),
                 wraplength=380, justify="left", anchor="w").pack(fill="x")
        tk.Label(note_col,
                 text="Trạng thái Đạt/Không đạt tự động tính theo ngưỡng 5.0.",
                 bg=SURFACE, fg=MUTED, font=font(8), anchor="w").pack(fill="x", pady=(4, 0))

        # Save / Cancel buttons
        btn_col = tk.Frame(body, bg=SURFACE)
        btn_col.pack(side="right", anchor="n")
        self._save_btn = tk.Button(
            btn_col, text="Lưu điểm",
            command=self._save,
            bg=PRIMARY, fg="white",
            activebackground="#1E40AF", activeforeground="white",
            relief="flat", bd=0, highlightthickness=0,
            cursor="hand2", font=font(9, "bold"),
            padx=18, pady=9,
        )
        self._save_btn.pack()
        tk.Button(
            btn_col, text="Hủy",
            command=self._cancel_form,
            bg=SURFACE, fg=MUTED,
            activebackground=BACKGROUND,
            relief="flat", bd=0,
            highlightbackground=BORDER, highlightthickness=1,
            cursor="hand2", font=font(9),
            padx=18, pady=7,
        ).pack(pady=(6, 0))

    # ------------------------------------------------------------------ nav helpers

    @staticmethod
    def _nav_btn(parent, text, cmd):
        return tk.Button(
            parent, text=text, command=cmd,
            bg=SURFACE, fg=TEXT,
            activebackground=PRIMARY_SOFT, activeforeground=PRIMARY_DARK,
            relief="flat", bd=0,
            highlightbackground=BORDER, highlightthickness=1,
            cursor="hand2", font=font(9),
            padx=12, pady=5,
        )

    def _make_page_btn(self, parent, num):
        is_cur = num == self._page
        btn = tk.Button(
            parent, text=str(num),
            command=lambda n=num: self._goto(n),
            bg=PRIMARY if is_cur else SURFACE,
            fg="white" if is_cur else TEXT,
            activebackground=PRIMARY_SOFT,
            relief="flat", bd=0,
            highlightbackground=BORDER, highlightthickness=1,
            cursor="hand2", font=font(9, "bold" if is_cur else "normal"),
            padx=10, pady=5,
        )
        btn.pack(side="left", padx=2)

    # ------------------------------------------------------------------ data

    def _load_courses(self) -> None:
        try:
            self._courses = self._service.lecturer_courses(self._session)
        except (ServiceError, DataAccessError) as exc:
            self._feedback.configure(text=str(exc))
            return

        if not self._courses:
            self._course_combo.configure(values=[], state="disabled")
            self._feedback.configure(
                text="Bạn chưa được phân công học phần nào.", fg=DANGER)
            return

        labels = [f"{c.course_code}  ·  {c.course_name}" for c in self._courses]
        self._course_combo.configure(values=labels, state="readonly")
        self._course_combo.current(0)
        self._on_course_change()

    def _on_course_change(self) -> None:
        idx = self._course_combo.current()
        if 0 <= idx < len(self._courses):
            self._load_sheet(self._courses[idx].course_id)

    def _load_sheet(self, course_id: int, reselect_student_id: int | None = None) -> None:
        self._rows_by_iid.clear()
        self._selected_row = None
        self._cancel_form()

        try:
            sheet: CourseGradeSheet = self._service.course_grade_sheet(
                self._session, course_id)
        except (ServiceError, DataAccessError) as exc:
            self._feedback.configure(text=str(exc))
            return

        self._course = sheet.course
        self._all_rows = list(sheet.rows)

        # Update breadcrumb and title
        self._breadcrumb.configure(
            text=f"Giảng viên  /  Học phần được phân công  /  {sheet.course.course_code}"
        )
        self._title_label.configure(
            text=f"{sheet.course.course_code}  ·  {sheet.course.course_name}"
        )
        self._subtitle_label.configure(
            text=f"Phụ trách: {sheet.course.lecturer_name or self._session.full_name}"
                 f"  ·  {self._session.username}"
                 f"  ·  Quyền nhập điểm đang hiệu lực"
        )

        # Update info card
        graded = sum(1 for r in sheet.rows if r.final_score is not None)
        total  = len(sheet.rows)
        pending = total - graded
        self._info_course_title.configure(
            text=f"{sheet.course.course_name}  ·  {sheet.course.credits} tín chỉ"
        )
        self._info_graded.configure(text=f"{graded} / {total} đã có điểm")
        self._info_graded_sub.configure(
            text=f"{pending} lượt sinh viên chưa có điểm cuối kỳ"
            if pending else "Tất cả sinh viên đã có điểm"
        )

        # Course combo label
        self._course_var.set(
            f"{sheet.course.course_code}  ·  {sheet.course.course_name}"
        )

        self._page = 1
        self._apply_filter(reselect_student_id=reselect_student_id)

    def _apply_filter(self, reselect_student_id: int | None = None) -> None:
        keyword = self._search_entry.get().strip().lower()
        ph = "tìm mã, họ tên hoặc lớp sinh viên..."
        if keyword == ph:
            keyword = ""

        status_filter = self._status_var.get()
        filtered = []
        for r in self._all_rows:
            if keyword and keyword not in (
                r.student_code + r.student_name
            ).lower():
                continue
            if status_filter == "Đã có điểm" and r.final_score is None:
                continue
            if status_filter == "Chưa có điểm" and r.final_score is not None:
                continue
            filtered.append(r)

        self._filtered_rows = filtered
        self._page = 1
        self._render_page(reselect_student_id=reselect_student_id)

    def _render_page(self, reselect_student_id: int | None = None) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._rows_by_iid.clear()

        total  = len(self._filtered_rows)
        pages  = max(1, (total + _PAGE_SIZE - 1) // _PAGE_SIZE)
        p      = min(self._page, pages)
        self._page = p
        start  = (p - 1) * _PAGE_SIZE
        chunk  = self._filtered_rows[start: start + _PAGE_SIZE]

        for row in chunk:
            iid = f"s-{row.student_id}"
            self._rows_by_iid[iid] = row
            grade_id_str = f"D{row.grade_id:06d}" if row.grade_id else "—"
            action = "Cập nhật" if row.grade_id else "Nhập điểm"
            tag = row_tag(row.status)
            self.tree.insert(
                "", "end", iid=iid,
                values=(
                    row.student_code,
                    row.student_name,
                    "—",
                    grade_id_str,
                    format_score(row.final_score),
                    status_label(row.status),
                    action,
                ),
                tags=tag,
            )

        # Pagination info
        display_start = start + 1 if total else 0
        display_end   = min(start + _PAGE_SIZE, total)
        self._page_info.configure(
            text=f"Hiển thị {display_start}–{display_end} trong {total} sinh viên"
        )

        # Page number buttons
        for w in self._pag_btns.winfo_children():
            w.destroy()
        shown = self._page_range(pages, self._page)
        for pp in shown:
            if pp == "...":
                tk.Label(self._pag_btns, text="...",
                         bg=SURFACE, fg=MUTED, font=font(9)).pack(side="left", padx=2)
            else:
                self._make_page_btn(self._pag_btns, pp)

        self._prev_btn.configure(state="normal" if self._page > 1 else "disabled")
        self._next_btn.configure(state="normal" if self._page < pages else "disabled")

        if reselect_student_id:
            iid = f"s-{reselect_student_id}"
            if iid in self._rows_by_iid:
                self.tree.selection_set(iid)
                self.tree.focus(iid)

    @staticmethod
    def _page_range(total_pages: int, current: int) -> list:
        if total_pages <= 5:
            return list(range(1, total_pages + 1))
        pages = []
        for pp in range(1, total_pages + 1):
            if pp == 1 or pp == total_pages or abs(pp - current) <= 1:
                pages.append(pp)
            elif pages and pages[-1] != "...":
                pages.append("...")
        return pages

    # ------------------------------------------------------------------ interaction

    def _on_row_select(self, _event=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        row = self._rows_by_iid.get(sel[0])
        if row is None:
            return
        self._selected_row = row
        self._open_edit(row)

    def _open_new_entry(self) -> None:
        """Open form in new-entry mode without selecting a row."""
        self._selected_row = None
        self._form_title.configure(text="Ghi điểm mới")
        self._form_mode.configure(text="Thêm mới")
        self._form_meta.configure(
            text="Chọn sinh viên trong bảng để liên kết bản ghi, rồi nhập điểm cuối kỳ."
        )
        self._final_entry.delete(0, "end")
        self._feedback.configure(text="")

    def _open_edit(self, row: CourseGradeRow) -> None:
        is_update = row.grade_id is not None
        self._form_title.configure(text="Cập nhật điểm" if is_update else "Nhập điểm mới")
        self._form_mode.configure(text="Cập nhật" if is_update else "Nhập mới")
        self._form_meta.configure(
            text=f"{row.student_code}  ·  {row.student_name}"
        )
        self._final_entry.delete(0, "end")
        if row.final_score is not None:
            self._final_entry.insert(0, f"{row.final_score:.2f}")
        self._feedback.configure(text="")

    def _save(self) -> None:
        if self._course is None:
            self._feedback.configure(text="Vui lòng chọn học phần.", fg=DANGER)
            return
        if self._selected_row is None:
            self._feedback.configure(
                text="Vui lòng chọn sinh viên trong bảng trước khi lưu.", fg=DANGER)
            return

        try:
            self._service.save_grade(
                self._session,
                self._course.course_id,
                self._selected_row.student_id,
                (
                    str(self._selected_row.process_score)
                    if self._selected_row.process_score is not None
                    else ""
                ),
                self._final_entry.get(),
                self._selected_row.grade_id,
            )
        except (ServiceError, DataAccessError) as exc:
            self._feedback.configure(text=str(exc), fg=DANGER)
            return

        student_id = self._selected_row.student_id
        self._load_sheet(self._course.course_id, reselect_student_id=student_id)
        self._feedback.configure(text="Đã lưu điểm thành công.", fg=SUCCESS)

    def _cancel_form(self) -> None:
        self._selected_row = None
        self._form_title.configure(text="Nhập điểm cuối kỳ")
        self._form_mode.configure(text="")
        self._form_meta.configure(text="Chọn một sinh viên trong bảng để nhập điểm.")
        self._final_entry.delete(0, "end")
        self._feedback.configure(text="")

    def _go_back_to_courses(self) -> None:
        self._feedback.configure(
            text="Dùng menu bên trái → \"Học phần được phân công\" để quay lại.",
            fg=MUTED,
        )

    def _clear_filter(self) -> None:
        self._search_entry.delete(0, "end")
        self._search_entry.insert(0, "Tìm mã, họ tên hoặc lớp sinh viên...")
        self._search_entry.configure(fg="#94A3B8")
        self._status_var.set("Trạng thái điểm")
        self._apply_filter()

    def _clear_placeholder(self, _e=None) -> None:
        if self._search_entry.get() == "Tìm mã, họ tên hoặc lớp sinh viên...":
            self._search_entry.delete(0, "end")
            self._search_entry.configure(fg=TEXT)

    def _restore_placeholder(self, _e=None) -> None:
        if not self._search_entry.get():
            self._search_entry.insert(0, "Tìm mã, họ tên hoặc lớp sinh viên...")
            self._search_entry.configure(fg="#94A3B8")

    def _prev_page(self) -> None:
        if self._page > 1:
            self._page -= 1
            self._render_page()

    def _next_page(self) -> None:
        total = len(self._filtered_rows)
        pages = max(1, (total + _PAGE_SIZE - 1) // _PAGE_SIZE)
        if self._page < pages:
            self._page += 1
            self._render_page()

    def _goto(self, num: int) -> None:
        self._page = num
        self._render_page()

    @property
    def _filtered_rows(self):
        return getattr(self, "_filtered_rows_data", [])

    @_filtered_rows.setter
    def _filtered_rows(self, v):
        self._filtered_rows_data = v
