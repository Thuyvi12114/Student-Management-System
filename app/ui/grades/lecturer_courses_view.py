"""Màn hình Học phần & điểm dành cho giảng viên — UI UniCore."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

from app.dao.errors import DataAccessError
from app.models import CourseGradeRow, CourseOption
from app.security.session import Session
from app.service.exceptions import ServiceError
from app.service.grade_service import CourseGradeSheet, GradeService
from app.ui.grades.widgets import configure_table_style, format_score
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

_COURSE_COLUMNS = [
    ("code",    "Mã HP",        90,  "w"),
    ("name",    "Tên học phần", 260, "w"),
    ("credits", "Tín chỉ",      70,  "center"),
    ("total",   "Sĩ số",        60,  "center"),
    ("graded",  "Đã có điểm",  110,  "center"),
    ("action",  "Thao tác",    130,  "center"),
]

_DETAIL_COLUMNS = [
    ("student_code", "Mã sinh viên", 105, "w"),
    ("student_name", "Họ và tên",    220, "w"),
    ("class_name",   "Lớp",          100, "w"),
    ("grade_id",     "Mã điểm",      100, "center"),
    ("final",        "Điểm",          70, "center"),
    ("status",       "Trạng thái",   110, "center"),
    ("action",       "Thao tác",      90, "center"),
]

_ALL_STATUS = "Tất cả trạng thái"
_STATUS_OPTIONS = [_ALL_STATUS, "Đã có điểm", "Chưa có điểm"]


class LecturerCoursesView(tk.Frame):
    """Danh sách học phần được phân công và màn hình chi tiết bảng điểm."""

    def __init__(
        self,
        parent: tk.Misc,
        grade_service: GradeService,
        session: Session,
        on_open_grades: Callable[[int | None], None] | None = None,
    ) -> None:
        super().__init__(parent, bg=BACKGROUND)
        self._service = grade_service
        self._session = session
        self._on_open_grades = on_open_grades

        self._courses: list[CourseOption] = []
        self._sheets: dict[int, CourseGradeSheet] = {}
        self._detail_sheet: CourseGradeSheet | None = None
        self._detail_rows: list[CourseGradeRow] = []
        self._detail_by_iid: dict[str, CourseGradeRow] = {}

        self._build()
        self._load_courses()

    # ------------------------------------------------------------------ shell

    def _build(self) -> None:
        outer = tk.Frame(self, bg=BACKGROUND)
        outer.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(outer, bg=BACKGROUND, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=self._canvas.yview)
        self._sf = tk.Frame(self._canvas, bg=BACKGROUND)
        self._sf.bind(
            "<Configure>",
            lambda _e: self._canvas.configure(scrollregion=self._canvas.bbox("all")),
        )
        window = self._canvas.create_window((0, 0), window=self._sf, anchor="nw")
        self._canvas.configure(yscrollcommand=scrollbar.set)
        self._canvas.bind(
            "<Configure>",
            lambda e: self._canvas.itemconfig(window, width=e.width),
        )
        self._canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._canvas.bind(
            "<Enter>",
            lambda _e: self._canvas.bind_all(
                "<MouseWheel>",
                lambda ev: self._canvas.yview_scroll(-1 * (ev.delta // 120), "units"),
            ),
        )
        self._canvas.bind("<Leave>", lambda _e: self._canvas.unbind_all("<MouseWheel>"))

        self._list_page = tk.Frame(self._sf, bg=BACKGROUND)
        self._list_page.pack(fill="both", expand=True)
        self._build_list_page(self._list_page)

        self._detail_page = tk.Frame(self._sf, bg=BACKGROUND)
        self._build_detail_page(self._detail_page)

    # ------------------------------------------------------------------ list

    def _build_list_page(self, parent: tk.Frame) -> None:
        page = tk.Frame(parent, bg=BACKGROUND)
        page.pack(fill="both", expand=True, padx=32, pady=24)

        breadcrumb = tk.Frame(page, bg=BACKGROUND)
        breadcrumb.pack(fill="x", pady=(0, 8))
        tk.Label(
            breadcrumb,
            text="Giảng viên  /  Học phần được phân công",
            bg=BACKGROUND,
            fg=MUTED,
            font=font(8),
        ).pack(side="left")

        tk.Label(
            page,
            text="Học phần được phân công",
            bg=BACKGROUND,
            fg=TEXT,
            font=font(20, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            page,
            text="Chọn một học phần để xem thông tin chi tiết và bảng điểm sinh viên. "
            "Giảng viên chỉ được ghi/sửa điểm cho học phần mình phụ trách.",
            bg=BACKGROUND,
            fg=MUTED,
            font=font(9),
            anchor="w",
            justify="left",
            wraplength=860,
        ).pack(fill="x", pady=(4, 18))

        search_row = tk.Frame(page, bg=BACKGROUND)
        search_row.pack(fill="x", pady=(0, 16))

        search_wrap = tk.Frame(
            search_row, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1
        )
        search_wrap.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self._search_entry = tk.Entry(
            search_wrap,
            font=font(9),
            relief="flat",
            bd=0,
            bg=SURFACE,
            fg="#94A3B8",
            insertbackground=TEXT,
            highlightthickness=0,
        )
        self._search_entry.insert(0, "Tìm theo mã hoặc tên học phần...")
        self._search_entry.bind("<FocusIn>", self._clear_placeholder)
        self._search_entry.bind("<FocusOut>", self._restore_placeholder)
        self._search_entry.bind("<KeyRelease>", lambda _e: self._render_courses())
        self._search_entry.pack(fill="x", expand=True, padx=12, pady=9)

        self._status_var = tk.StringVar(value=_ALL_STATUS)
        status_wrap = tk.Frame(
            search_row, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1
        )
        status_wrap.pack(side="left", padx=(0, 10))
        status_combo = ttk.Combobox(
            status_wrap,
            textvariable=self._status_var,
            values=[_ALL_STATUS, "Đã có điểm", "Chưa đủ điểm"],
            state="readonly",
            width=18,
            font=font(9),
        )
        status_combo.pack(padx=8, pady=7)
        status_combo.bind("<<ComboboxSelected>>", lambda _e: self._render_courses())

        tk.Button(
            search_row,
            text="Xóa tìm kiếm",
            command=self._clear_filter,
            bg=SURFACE,
            fg=TEXT,
            activebackground=BACKGROUND,
            relief="flat",
            bd=0,
            highlightbackground=BORDER,
            highlightthickness=1,
            cursor="hand2",
            font=font(9),
            padx=14,
            pady=7,
        ).pack(side="left")

        table_card = tk.Frame(
            page, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1
        )
        table_card.pack(fill="x", pady=(0, 16))
        ti = tk.Frame(table_card, bg=SURFACE)
        ti.pack(fill="both", expand=True, padx=20, pady=16)

        tk.Label(
            ti,
            text="Danh sách học phần",
            bg=SURFACE,
            fg=TEXT,
            font=font(11, "bold"),
            anchor="w",
        ).pack(fill="x")

        self._summary_label = tk.Label(
            ti, text="", bg=SURFACE, fg=MUTED, font=font(8), anchor="w"
        )
        self._summary_label.pack(fill="x", pady=(4, 10))

        configure_table_style(ti)
        self._course_tree = ttk.Treeview(
            ti,
            columns=[c[0] for c in _COURSE_COLUMNS],
            show="headings",
            height=8,
            style="Grades.Treeview",
            selectmode="browse",
        )
        for key, label, width, anchor in _COURSE_COLUMNS:
            self._course_tree.heading(key, text=label, anchor=anchor)
            self._course_tree.column(
                key, width=width, minwidth=40, anchor=anchor, stretch=True
            )
        self._course_tree.tag_configure("passed", foreground="#15803D")
        self._course_tree.tag_configure("pending", foreground="#B45309")
        self._course_tree.bind("<Double-1>", lambda _e: self._open_selected_course())
        self._course_tree.bind("<Return>", lambda _e: self._open_selected_course())
        self._course_tree.pack(fill="x")

        self._footer_label = tk.Label(
            ti, text="", bg=SURFACE, fg=MUTED, font=font(8), anchor="w"
        )
        self._footer_label.pack(fill="x", pady=(10, 0))
        tk.Label(
            ti,
            text="Mẹo: nhấp đúp vào một học phần để mở chi tiết và bảng điểm.",
            bg=SURFACE,
            fg=MUTED,
            font=font(8),
            anchor="w",
        ).pack(fill="x", pady=(4, 0))

        self._list_feedback = tk.Label(
            page,
            text="",
            bg=BACKGROUND,
            fg=DANGER,
            font=font(9),
            anchor="w",
            wraplength=700,
        )
        self._list_feedback.pack(fill="x")

    # ------------------------------------------------------------------ detail

    def _build_detail_page(self, parent: tk.Frame) -> None:
        page = tk.Frame(parent, bg=BACKGROUND)
        page.pack(fill="both", expand=True, padx=32, pady=24)

        breadcrumb = tk.Frame(page, bg=BACKGROUND)
        breadcrumb.pack(fill="x", pady=(0, 8))
        self._detail_breadcrumb = tk.Label(
            breadcrumb,
            text="Giảng viên  /  Học phần được phân công",
            bg=BACKGROUND,
            fg=MUTED,
            font=font(8),
        )
        self._detail_breadcrumb.pack(side="left")

        title_row = tk.Frame(page, bg=BACKGROUND)
        title_row.pack(fill="x", pady=(0, 4))
        self._detail_title = tk.Label(
            title_row,
            text="Chi tiết học phần",
            bg=BACKGROUND,
            fg=TEXT,
            font=font(20, "bold"),
            anchor="w",
        )
        self._detail_title.pack(side="left")

        tk.Button(
            title_row,
            text="Về học phần của tôi",
            command=self._show_list,
            bg=SURFACE,
            fg=TEXT,
            activebackground=PRIMARY_SOFT,
            activeforeground=PRIMARY_DARK,
            relief="flat",
            bd=0,
            highlightbackground=BORDER,
            highlightthickness=1,
            cursor="hand2",
            font=font(9),
            padx=16,
            pady=8,
        ).pack(side="right")

        self._detail_subtitle = tk.Label(
            page,
            text="",
            bg=BACKGROUND,
            fg=PRIMARY,
            font=font(9),
            anchor="w",
        )
        self._detail_subtitle.pack(fill="x", pady=(0, 14))

        info_card = tk.Frame(
            page, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1
        )
        info_card.pack(fill="x", pady=(0, 14))
        info = tk.Frame(info_card, bg=SURFACE)
        info.pack(fill="both", expand=True, padx=20, pady=16)

        left = tk.Frame(info, bg=SURFACE)
        left.pack(side="left", fill="both", expand=True)
        self._detail_info_title = tk.Label(
            left,
            text="—",
            bg=SURFACE,
            fg=TEXT,
            font=font(13, "bold"),
            anchor="w",
        )
        self._detail_info_title.pack(fill="x")
        self._detail_info_desc = tk.Label(
            left,
            text="",
            bg=SURFACE,
            fg=MUTED,
            font=font(8),
            anchor="w",
            justify="left",
            wraplength=620,
        )
        self._detail_info_desc.pack(fill="x", pady=(4, 0))

        right = tk.Frame(info, bg=SURFACE)
        right.pack(side="right", anchor="n")
        self._detail_graded = tk.Label(
            right,
            text="—",
            bg=SURFACE,
            fg=PRIMARY_DARK,
            font=font(16, "bold"),
            anchor="e",
        )
        self._detail_graded.pack(anchor="e")
        self._detail_pending = tk.Label(
            right,
            text="",
            bg=SURFACE,
            fg=MUTED,
            font=font(8),
            anchor="e",
        )
        self._detail_pending.pack(anchor="e")

        filter_row = tk.Frame(page, bg=BACKGROUND)
        filter_row.pack(fill="x", pady=(0, 14))

        self._detail_course_var = tk.StringVar()
        course_wrap = tk.Frame(
            filter_row, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1
        )
        course_wrap.pack(side="left", padx=(0, 10))
        self._detail_course_combo = ttk.Combobox(
            course_wrap,
            textvariable=self._detail_course_var,
            state="readonly",
            width=24,
            font=font(9),
        )
        self._detail_course_combo.pack(padx=8, pady=7)
        self._detail_course_combo.bind(
            "<<ComboboxSelected>>", lambda _e: self._on_detail_course_change()
        )

        search_wrap = tk.Frame(
            filter_row, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1
        )
        search_wrap.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self._detail_search_entry = tk.Entry(
            search_wrap,
            font=font(9),
            relief="flat",
            bd=0,
            bg=SURFACE,
            fg="#94A3B8",
            insertbackground=TEXT,
            highlightthickness=0,
        )
        self._detail_search_entry.insert(0, "Tìm mã, họ tên hoặc lớp sinh viên...")
        self._detail_search_entry.bind("<FocusIn>", self._clear_detail_placeholder)
        self._detail_search_entry.bind("<FocusOut>", self._restore_detail_placeholder)
        self._detail_search_entry.bind(
            "<KeyRelease>", lambda _e: self._render_detail_rows()
        )
        self._detail_search_entry.pack(fill="x", expand=True, padx=12, pady=9)

        self._detail_status_var = tk.StringVar(value=_ALL_STATUS)
        status_wrap = tk.Frame(
            filter_row, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1
        )
        status_wrap.pack(side="left", padx=(0, 10))
        status_combo = ttk.Combobox(
            status_wrap,
            textvariable=self._detail_status_var,
            values=_STATUS_OPTIONS,
            state="readonly",
            width=16,
            font=font(9),
        )
        status_combo.pack(padx=8, pady=7)
        status_combo.bind(
            "<<ComboboxSelected>>", lambda _e: self._render_detail_rows()
        )

        tk.Button(
            filter_row,
            text="Xóa",
            command=self._clear_detail_filter,
            bg=SURFACE,
            fg=TEXT,
            activebackground=BACKGROUND,
            relief="flat",
            bd=0,
            highlightbackground=BORDER,
            highlightthickness=1,
            cursor="hand2",
            font=font(9),
            padx=12,
            pady=7,
        ).pack(side="left")

        table_card = tk.Frame(
            page, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1
        )
        table_card.pack(fill="x", pady=(0, 16))
        ti = tk.Frame(table_card, bg=SURFACE)
        ti.pack(fill="both", expand=True, padx=20, pady=16)

        header = tk.Frame(ti, bg=SURFACE)
        header.pack(fill="x", pady=(0, 10))
        tk.Label(
            header,
            text="Điểm cuối kỳ  ·  Thang 0–10",
            bg=SURFACE,
            fg=TEXT,
            font=font(11, "bold"),
            anchor="w",
        ).pack(side="left")
        tk.Button(
            header,
            text="+ Ghi điểm mới",
            command=self._open_grade_entry,
            bg=PRIMARY,
            fg="white",
            activebackground="#1E40AF",
            activeforeground="white",
            relief="flat",
            bd=0,
            highlightthickness=0,
            cursor="hand2",
            font=font(9, "bold"),
            padx=16,
            pady=8,
        ).pack(side="right")

        configure_table_style(ti)
        self._detail_tree = ttk.Treeview(
            ti,
            columns=[c[0] for c in _DETAIL_COLUMNS],
            show="headings",
            height=10,
            style="Grades.Treeview",
            selectmode="browse",
        )
        for key, label, width, anchor in _DETAIL_COLUMNS:
            self._detail_tree.heading(key, text=label, anchor=anchor)
            self._detail_tree.column(
                key, width=width, minwidth=40, anchor=anchor, stretch=True
            )
        self._detail_tree.tag_configure("passed", foreground="#15803D")
        self._detail_tree.tag_configure("pending", foreground="#B45309")
        self._detail_tree.bind("<Double-1>", lambda _e: self._open_grade_entry())
        self._detail_tree.pack(fill="x")

        self._detail_count = tk.Label(
            ti, text="", bg=SURFACE, fg=MUTED, font=font(8), anchor="w"
        )
        self._detail_count.pack(fill="x", pady=(10, 0))

        note = tk.Frame(
            page, bg="#EFF6FF", highlightbackground="#BFDBFE", highlightthickness=1
        )
        note.pack(fill="x", pady=(0, 12))
        tk.Label(
            note,
            text="Một sinh viên · Một học phần · Một điểm cuối kỳ. "
            "Chỉ giảng viên đang được phân công mới có quyền ghi hoặc cập nhật điểm.",
            bg="#EFF6FF",
            fg="#1D4ED8",
            font=font(8),
            anchor="w",
            justify="left",
            wraplength=820,
        ).pack(fill="x", padx=16, pady=10)

        self._detail_feedback = tk.Label(
            page,
            text="",
            bg=BACKGROUND,
            fg=DANGER,
            font=font(9),
            anchor="w",
            wraplength=760,
        )
        self._detail_feedback.pack(fill="x")

    # ------------------------------------------------------------------ list data

    def _load_courses(self) -> None:
        try:
            self._courses = self._service.lecturer_courses(self._session)
        except (ServiceError, DataAccessError) as exc:
            self._list_feedback.configure(text=str(exc))
            self._render_courses()
            return

        self._sheets.clear()
        for course in self._courses:
            try:
                self._sheets[course.course_id] = self._service.course_grade_sheet(
                    self._session, course.course_id
                )
            except (ServiceError, DataAccessError):
                continue

        self._render_courses()

    def _render_courses(self) -> None:
        for item in self._course_tree.get_children():
            self._course_tree.delete(item)

        keyword = self._search_entry.get().strip().lower()
        if keyword == "tìm theo mã hoặc tên học phần...":
            keyword = ""
        status_filter = self._status_var.get()

        shown: list[tuple[CourseOption, int, int]] = []
        for course in self._courses:
            if keyword and keyword not in (
                course.course_code + course.course_name
            ).lower():
                continue
            sheet = self._sheets.get(course.course_id)
            total = len(sheet.rows) if sheet else 0
            graded = (
                sum(1 for row in sheet.rows if row.final_score is not None)
                if sheet
                else 0
            )
            if status_filter == "Đã có điểm" and graded == 0:
                continue
            if status_filter == "Chưa đủ điểm" and total > 0 and graded == total:
                continue
            shown.append((course, total, graded))

        total_credits = sum(course.credits for course, _, _ in shown)
        lecturer_name = (
            shown[0][0].lecturer_name if shown else self._session.full_name
        )
        self._summary_label.configure(
            text=f"{len(shown)} học phần  ·  {total_credits} tín chỉ  ·  "
            f"Giảng viên phụ trách: {lecturer_name or self._session.full_name}"
        )

        for course, total, graded in shown:
            tag = ("passed",) if total > 0 and graded == total else ("pending",)
            self._course_tree.insert(
                "",
                "end",
                iid=str(course.course_id),
                values=(
                    course.course_code,
                    course.course_name,
                    course.credits,
                    total,
                    f"{graded} / {total}",
                    "Xem chi tiết",
                ),
                tags=tag,
            )

        self._footer_label.configure(
            text=f"Hiển thị tất cả {len(shown)} học phần được phân công"
            if shown
            else "Không có học phần phù hợp bộ lọc."
        )

    # ------------------------------------------------------------------ detail data

    def _show_detail(self, course_id: int) -> None:
        if not self._courses:
            return
        self._list_page.pack_forget()
        if not self._detail_page.winfo_manager():
            self._detail_page.pack(fill="both", expand=True)

        labels = [f"{c.course_code}  ·  {c.course_name}" for c in self._courses]
        self._detail_course_combo.configure(values=labels, state="readonly")
        for index, course in enumerate(self._courses):
            if course.course_id == course_id:
                self._detail_course_combo.current(index)
                break

        self._detail_search_entry.delete(0, "end")
        self._detail_search_entry.insert(0, "Tìm mã, họ tên hoặc lớp sinh viên...")
        self._detail_search_entry.configure(fg="#94A3B8")
        self._detail_status_var.set(_ALL_STATUS)
        self._detail_feedback.configure(text="")
        self._load_detail(course_id)
        self._canvas.yview_moveto(0)

    def _show_list(self) -> None:
        self._detail_page.pack_forget()
        if not self._list_page.winfo_manager():
            self._list_page.pack(fill="both", expand=True)
        self._canvas.yview_moveto(0)

    def _open_selected_course(self) -> None:
        selection = self._course_tree.selection()
        if selection:
            self._show_detail(int(selection[0]))

    def _on_detail_course_change(self) -> None:
        index = self._detail_course_combo.current()
        if 0 <= index < len(self._courses):
            self._detail_feedback.configure(text="")
            self._load_detail(self._courses[index].course_id)

    def _load_detail(self, course_id: int) -> None:
        try:
            sheet = self._service.course_grade_sheet(self._session, course_id)
        except (ServiceError, DataAccessError) as exc:
            self._detail_feedback.configure(text=str(exc))
            return

        self._detail_sheet = sheet
        self._detail_rows = list(sheet.rows)
        course = sheet.course

        self._detail_breadcrumb.configure(
            text=f"Giảng viên  /  Học phần được phân công  /  {course.course_code}"
        )
        self._detail_title.configure(
            text=f"{course.course_code}  ·  {course.course_name}"
        )
        self._detail_subtitle.configure(
            text=f"Phụ trách: {course.lecturer_name or self._session.full_name}"
            f"  ·  {self._session.username}"
            f"  ·  Quyền nhập điểm đang hiệu lực"
        )
        self._detail_info_title.configure(
            text=f"{course.course_name}  ·  {course.credits} tín chỉ"
        )
        self._detail_info_desc.configure(
            text=f"{course.course_code}  ·  {course.semester} {course.academic_year}"
            f"  ·  Giảng viên: {course.lecturer_name or '—'}"
        )

        graded = sum(1 for row in sheet.rows if row.final_score is not None)
        total = len(sheet.rows)
        pending = total - graded
        self._detail_graded.configure(text=f"{graded} / {total} đã có điểm")
        self._detail_pending.configure(
            text=f"{pending} lượt sinh viên chưa có điểm cuối kỳ"
            if pending
            else "Tất cả sinh viên đã có điểm"
        )
        self._detail_course_var.set(
            f"{course.course_code}  ·  {course.course_name}"
        )
        self._render_detail_rows()

    def _render_detail_rows(self) -> None:
        for item in self._detail_tree.get_children():
            self._detail_tree.delete(item)
        self._detail_by_iid.clear()

        keyword = self._detail_search_entry.get().strip().lower()
        if keyword == "tìm mã, họ tên hoặc lớp sinh viên...":
            keyword = ""
        status_filter = self._detail_status_var.get()

        shown: list[CourseGradeRow] = []
        for row in self._detail_rows:
            haystack = (
                row.student_code + row.student_name + row.class_name
            ).lower()
            if keyword and keyword not in haystack:
                continue
            if status_filter == "Đã có điểm" and row.final_score is None:
                continue
            if status_filter == "Chưa có điểm" and row.final_score is not None:
                continue
            shown.append(row)

        for row in shown:
            has_score = row.final_score is not None
            iid = f"d-{row.student_id}"
            self._detail_by_iid[iid] = row
            grade_id = f"D{row.grade_id:06d}" if row.grade_id else "—"
            self._detail_tree.insert(
                "",
                "end",
                iid=iid,
                values=(
                    row.student_code,
                    row.student_name,
                    row.class_name or "—",
                    grade_id,
                    format_score(row.final_score),
                    "Đã có điểm" if has_score else "Chưa có điểm",
                    "Cập nhật" if has_score else "Nhập điểm",
                ),
                tags=("passed",) if has_score else ("pending",),
            )

        self._detail_count.configure(
            text=f"Hiển thị {len(shown)} / {len(self._detail_rows)} sinh viên"
        )

    # ------------------------------------------------------------------ actions

    def _open_grade_entry(self) -> None:
        if self._detail_sheet is None:
            return
        if self._on_open_grades is None:
            self._detail_feedback.configure(
                text="Dùng menu bên trái → \"Nhập & cập nhật điểm\" để nhập điểm.",
                fg=MUTED,
            )
            return
        self._on_open_grades(self._detail_sheet.course.course_id)

    def _clear_filter(self) -> None:
        self._search_entry.delete(0, "end")
        self._search_entry.insert(0, "Tìm theo mã hoặc tên học phần...")
        self._search_entry.configure(fg="#94A3B8")
        self._status_var.set(_ALL_STATUS)
        self._render_courses()

    def _clear_placeholder(self, _event=None) -> None:
        if self._search_entry.get() == "Tìm theo mã hoặc tên học phần...":
            self._search_entry.delete(0, "end")
            self._search_entry.configure(fg=TEXT)

    def _restore_placeholder(self, _event=None) -> None:
        if not self._search_entry.get():
            self._search_entry.insert(0, "Tìm theo mã hoặc tên học phần...")
            self._search_entry.configure(fg="#94A3B8")

    def _clear_detail_filter(self) -> None:
        self._detail_search_entry.delete(0, "end")
        self._detail_search_entry.insert(0, "Tìm mã, họ tên hoặc lớp sinh viên...")
        self._detail_search_entry.configure(fg="#94A3B8")
        self._detail_status_var.set(_ALL_STATUS)
        self._render_detail_rows()

    def _clear_detail_placeholder(self, _event=None) -> None:
        if (
            self._detail_search_entry.get()
            == "Tìm mã, họ tên hoặc lớp sinh viên..."
        ):
            self._detail_search_entry.delete(0, "end")
            self._detail_search_entry.configure(fg=TEXT)

    def _restore_detail_placeholder(self, _event=None) -> None:
        if not self._detail_search_entry.get():
            self._detail_search_entry.insert(
                0, "Tìm mã, họ tên hoặc lớp sinh viên..."
            )
            self._detail_search_entry.configure(fg="#94A3B8")
