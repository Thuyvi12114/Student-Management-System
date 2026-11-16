"""Màn hình Học phần được phân công dành cho giảng viên — UI UniCore."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.dao.errors import DataAccessError
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
    TEXT,
    font,
)

_COURSE_COLUMNS = [
    ("code",    "Mã HP",        80,  "w"),
    ("name",    "Tên học phần", 260, "w"),
    ("credits", "Tín chỉ",      60,  "center"),
    ("total",   "Sĩ số",        60,  "center"),
    ("graded",  "Đã có điểm",  110,  "center"),
    ("action",  "Thao tác",    120,  "center"),
]


class LecturerCoursesView(tk.Frame):
    """Giảng viên xem danh sách học phần được phân công."""

    def __init__(self, parent: tk.Misc, grade_service: GradeService, session: Session) -> None:
        super().__init__(parent, bg=BACKGROUND)
        self._service  = grade_service
        self._session  = session
        self._courses  = []
        self._sheets: dict[int, CourseGradeSheet] = {}
        self._search_active = False
        self._build()
        self._load_courses()

    # ------------------------------------------------------------------ build

    def _build(self) -> None:
        # Main 2-column layout: left content + right info panel
        outer = tk.Frame(self, bg=BACKGROUND)
        outer.pack(fill="both", expand=True)

        # Scrollable left area
        left_canvas = tk.Canvas(outer, bg=BACKGROUND, highlightthickness=0)
        left_sb = ttk.Scrollbar(outer, orient="vertical", command=left_canvas.yview)
        self._sf = tk.Frame(left_canvas, bg=BACKGROUND)
        self._sf.bind("<Configure>",
                      lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all")))
        _win = left_canvas.create_window((0, 0), window=self._sf, anchor="nw")
        left_canvas.configure(yscrollcommand=left_sb.set)
        left_canvas.bind("<Configure>",
                         lambda e: left_canvas.itemconfig(_win, width=e.width))

        # Right info panel (fixed width)
        self._right_panel = tk.Frame(outer, bg=BACKGROUND, width=240)
        self._right_panel.pack(side="right", fill="y", padx=(0, 0))
        self._right_panel.pack_propagate(False)
        self._build_right_panel(self._right_panel)

        tk.Frame(outer, bg=BORDER, width=1).pack(side="right", fill="y")

        left_canvas.pack(side="left", fill="both", expand=True)
        left_sb.pack(side="right", fill="y")

        left_canvas.bind("<Enter>",
                         lambda e: left_canvas.bind_all(
                             "<MouseWheel>",
                             lambda ev: left_canvas.yview_scroll(-1*(ev.delta//120), "units")))
        left_canvas.bind("<Leave>", lambda e: left_canvas.unbind_all("<MouseWheel>"))

        page = tk.Frame(self._sf, bg=BACKGROUND)
        page.pack(fill="both", expand=True, padx=32, pady=24)

        # ── Breadcrumb ────────────────────────────────────────────────────
        bc = tk.Frame(page, bg=BACKGROUND)
        bc.pack(fill="x", pady=(0, 8))
        tk.Label(bc, text="Giảng viên  /  Học phần được phân công",
                 bg=BACKGROUND, fg=MUTED, font=font(8)).pack(side="left")

        # ── Title row ─────────────────────────────────────────────────────
        title_row = tk.Frame(page, bg=BACKGROUND)
        title_row.pack(fill="x", pady=(0, 4))
        tk.Label(title_row, text="Học phần được phân công",
                 bg=BACKGROUND, fg=TEXT, font=font(20, "bold"), anchor="w").pack(side="left")

        # "Tra cứu sinh viên" button (top right)
        search_btn = tk.Button(
            title_row, text="Tra cứu sinh viên",
            command=self._toggle_student_search,
            bg=SURFACE, fg=TEXT,
            activebackground=PRIMARY_SOFT, activeforeground=PRIMARY_DARK,
            relief="flat", bd=0,
            highlightbackground=BORDER, highlightthickness=1,
            cursor="hand2", font=font(9),
            padx=16, pady=8,
        )
        search_btn.pack(side="right")

        tk.Label(page,
                 text="Chỉ hiển thị các học phần hiện do bạn phụ trách. "
                      "Không có quyền thêm, sửa hoặc xóa học phần.",
                 bg=BACKGROUND, fg=MUTED, font=font(9), anchor="w", justify="left").pack(
            fill="x", pady=(0, 18))

        # ── Search bar ────────────────────────────────────────────────────
        search_row = tk.Frame(page, bg=BACKGROUND)
        search_row.pack(fill="x", pady=(0, 16))

        search_wrap = tk.Frame(search_row, bg=SURFACE,
                               highlightbackground=BORDER, highlightthickness=1)
        search_wrap.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self._search_entry = tk.Entry(
            search_wrap, font=font(9),
            relief="flat", bd=0,
            bg=SURFACE, fg="#94A3B8", insertbackground=TEXT, highlightthickness=0,
        )
        self._search_entry.insert(0, "Tìm theo mã hoặc tên học phần...")
        self._search_entry.bind("<FocusIn>",  self._clear_placeholder)
        self._search_entry.bind("<FocusOut>", self._restore_placeholder)
        self._search_entry.bind("<KeyRelease>", lambda _e: self._render_courses())
        self._search_entry.pack(fill="x", expand=True, padx=12, pady=9)

        # Status filter
        self._status_var = tk.StringVar(value="Tất cả trạng thái")
        status_wrap = tk.Frame(search_row, bg=SURFACE,
                               highlightbackground=BORDER, highlightthickness=1)
        status_wrap.pack(side="left", padx=(0, 10))
        status_combo = ttk.Combobox(
            status_wrap, textvariable=self._status_var,
            values=["Tất cả trạng thái", "Đã có điểm", "Chưa đủ điểm"],
            state="readonly", width=18, font=font(9),
        )
        status_combo.pack(padx=8, pady=7)
        status_combo.bind("<<ComboboxSelected>>", lambda _e: self._render_courses())

        clear_btn = tk.Button(
            search_row, text="Xóa tìm kiếm",
            command=self._clear_filter,
            bg=SURFACE, fg=TEXT,
            activebackground=BACKGROUND,
            relief="flat", bd=0,
            highlightbackground=BORDER, highlightthickness=1,
            cursor="hand2", font=font(9),
            padx=14, pady=7,
        )
        clear_btn.pack(side="left")

        # ── Course table card ─────────────────────────────────────────────
        table_card = tk.Frame(page, bg=SURFACE,
                              highlightbackground=BORDER, highlightthickness=1)
        table_card.pack(fill="x", pady=(0, 16))
        ti = tk.Frame(table_card, bg=SURFACE)
        ti.pack(fill="both", expand=True, padx=20, pady=16)

        # Card header
        ch = tk.Frame(ti, bg=SURFACE)
        ch.pack(fill="x", pady=(0, 4))
        tk.Label(ch, text="Danh sách học phần",
                 bg=SURFACE, fg=TEXT, font=font(11, "bold"), anchor="w").pack(side="left")

        self._summary_label = tk.Label(ti, text="",
                                       bg=SURFACE, fg=MUTED, font=font(8), anchor="w")
        self._summary_label.pack(fill="x", pady=(0, 10))

        # Treeview
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
            self._course_tree.column(key, width=width, minwidth=40,
                                     anchor=anchor, stretch=True)
        self._course_tree.tag_configure("passed",  foreground="#15803D")
        self._course_tree.tag_configure("pending", foreground="#B45309")
        self._course_tree.bind("<<TreeviewSelect>>", self._on_course_select)
        self._course_tree.pack(fill="x")

        self._footer_label = tk.Label(ti, text="",
                                      bg=SURFACE, fg=MUTED, font=font(8), anchor="w")
        self._footer_label.pack(fill="x", pady=(10, 0))

        self.feedback = tk.Label(page, text="",
                                 bg=BACKGROUND, fg=DANGER, font=font(9),
                                 anchor="w", wraplength=700)
        self.feedback.pack(fill="x")

    def _build_right_panel(self, parent: tk.Frame) -> None:
        rp = tk.Frame(parent, bg=BACKGROUND)
        rp.pack(fill="both", expand=True, padx=20, pady=24)

        perm_card = tk.Frame(rp, bg=SURFACE,
                             highlightbackground=BORDER, highlightthickness=1)
        perm_card.pack(fill="x")
        pi = tk.Frame(perm_card, bg=SURFACE)
        pi.pack(fill="both", expand=True, padx=16, pady=16)

        tk.Label(pi, text="Quyền của giảng viên",
                 bg=SURFACE, fg=TEXT, font=font(10, "bold"), anchor="w").pack(fill="x", pady=(0, 10))

        # Được phép
        tk.Label(pi, text="Được phép",
                 bg=SURFACE, fg="#15803D", font=font(8, "bold"), anchor="w").pack(fill="x")
        tk.Label(pi,
                 text="Xem học phần được phân công. Tra cứu mã, tên "
                      "và lớp sinh viên. Nhập hoặc cập nhật điểm cuối "
                      "kỳ từ 0 đến 10.",
                 bg=SURFACE, fg=MUTED, font=font(8),
                 wraplength=190, justify="left", anchor="nw").pack(fill="x", pady=(4, 12))

        # Không được phép
        tk.Label(pi, text="Không được phép",
                 bg=SURFACE, fg=DANGER, font=font(8, "bold"), anchor="w").pack(fill="x")
        tk.Label(pi,
                 text="Sửa thông tin cá nhân sinh viên, quản lý học "
                      "phần hoặc nhập điểm ngoài phạm vi được phân công.",
                 bg=SURFACE, fg=MUTED, font=font(8),
                 wraplength=190, justify="left", anchor="nw").pack(fill="x", pady=(4, 12))

        # Info note
        note = tk.Frame(pi, bg="#EFF6FF",
                        highlightbackground="#BFDBFE", highlightthickness=1)
        note.pack(fill="x")
        tk.Label(note,
                 text="Khi học phần được chuyển cho người khác, "
                      "quyền nhập và cập nhật điểm của bạn sẽ chấm dứt.",
                 bg="#EFF6FF", fg="#1D4ED8", font=font(8),
                 wraplength=190, justify="left").pack(padx=10, pady=10)

    # ------------------------------------------------------------------ data

    def _load_courses(self) -> None:
        try:
            self._courses = self._service.lecturer_courses(self._session)
        except (ServiceError, DataAccessError) as exc:
            self.feedback.configure(text=str(exc))
            return

        # Pre-load all sheets to get student counts
        for course in self._courses:
            try:
                sheet = self._service.course_grade_sheet(self._session, course.course_id)
                self._sheets[course.course_id] = sheet
            except (ServiceError, DataAccessError):
                pass

        self._render_courses()

    def _render_courses(self) -> None:
        for item in self._course_tree.get_children():
            self._course_tree.delete(item)

        keyword = self._search_entry.get().strip().lower()
        placeholder = "tìm theo mã hoặc tên học phần..."
        if keyword == placeholder:
            keyword = ""

        status_filter = self._status_var.get()

        shown = []
        for course in self._courses:
            if keyword and keyword not in (course.course_code + course.course_name).lower():
                continue
            sheet = self._sheets.get(course.course_id)
            total = len(sheet.rows) if sheet else 0
            graded = sum(1 for r in sheet.rows if r.final_score is not None) if sheet else 0

            if status_filter == "Đã có điểm" and graded == 0:
                continue
            if status_filter == "Chưa đủ điểm" and graded == total and total > 0:
                continue

            shown.append((course, total, graded))

        total_credits = sum(c.credits for c, _, _ in shown)
        lecturer_name = shown[0][0].lecturer_name if shown else self._session.full_name
        self._summary_label.configure(
            text=f"{len(shown)} học phần  ·  {total_credits} tín chỉ  ·  "
                 f"Giảng viên phụ trách: {lecturer_name or self._session.full_name}"
        )

        for course, total, graded in shown:
            tag = ("passed",) if graded == total and total > 0 else ("pending",)
            self._course_tree.insert(
                "", "end",
                iid=str(course.course_id),
                values=(
                    course.course_code,
                    course.course_name,
                    course.credits,
                    total,
                    f"{graded} / {total}",
                    "Xem / Nhập điểm",
                ),
                tags=tag,
            )

        total_shown = len(shown)
        self._footer_label.configure(
            text=f"Hiển thị tất cả {total_shown} học phần được phân công"
            if shown else "Không có học phần phù hợp bộ lọc."
        )

    # ------------------------------------------------------------------ interaction

    def _on_course_select(self, _event=None) -> None:
        sel = self._course_tree.selection()
        if not sel:
            return
        course_id = int(sel[0])
        course = next((c for c in self._courses if c.course_id == course_id), None)
        if course:
            self.feedback.configure(
                text=f"Đã chọn: {course.course_code} – {course.course_name}  "
                     f"({course.semester} {course.academic_year})",
                fg=MUTED,
            )

    def _toggle_student_search(self) -> None:
        self.feedback.configure(
            text="Chức năng tra cứu sinh viên: nhập điểm qua mục "
                 "\"Nhập & cập nhật điểm\" trong menu bên trái.",
            fg=MUTED,
        )

    def _clear_filter(self) -> None:
        self._search_entry.delete(0, "end")
        self._search_entry.insert(0, "Tìm theo mã hoặc tên học phần...")
        self._search_entry.configure(fg="#94A3B8")
        self._status_var.set("Tất cả trạng thái")
        self._render_courses()

    def _clear_placeholder(self, _event=None) -> None:
        if self._search_entry.get() == "Tìm theo mã hoặc tên học phần...":
            self._search_entry.delete(0, "end")
            self._search_entry.configure(fg=TEXT)

    def _restore_placeholder(self, _event=None) -> None:
        if not self._search_entry.get():
            self._search_entry.insert(0, "Tìm theo mã hoặc tên học phần...")
            self._search_entry.configure(fg="#94A3B8")
