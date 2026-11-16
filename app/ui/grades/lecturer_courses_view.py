"""Màn hình Học phần & điểm dành cho giảng viên (chỉ xem)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.dao.errors import DataAccessError
from app.security.session import Session
from app.service.exceptions import ServiceError
from app.service.grade_service import CourseGradeSheet, GradeService
from app.ui.grades.widgets import (
    create_table,
    format_score,
    page_header,
    row_tag,
    status_label,
)
from app.ui.theme import BACKGROUND, BORDER, DANGER, MUTED, SURFACE, font

_COLUMNS = [
    ("student_code", "Mã SV", 95, "w"),
    ("student_name", "Họ tên", 240, "w"),
    ("process", "Quá trình", 85, "center"),
    ("final", "Cuối kỳ", 85, "center"),
    ("average", "Trung bình", 85, "center"),
    ("status", "Trạng thái", 120, "center"),
]


class LecturerCoursesView(tk.Frame):
    """Giảng viên xem chi tiết học phần được phân công và bảng điểm."""

    def __init__(self, parent: tk.Misc, grade_service: GradeService, session: Session) -> None:
        super().__init__(parent, bg=BACKGROUND)
        self._service = grade_service
        self._session = session
        self._courses = []
        self._course = None
        self._build()
        self._load_courses()

    def _build(self) -> None:
        page = tk.Frame(self, bg=BACKGROUND)
        page.pack(fill="both", expand=True, padx=32, pady=28)

        page_header(
            page,
            "Học phần & điểm",
            "Chỉ các học phần bạn được phân công giảng dạy mới xuất hiện ở đây. "
            "Bảng điểm dưới đây ở chế độ chỉ xem; việc nhập điểm dùng mục "
            "\"Nhập & cập nhật điểm\".",
        )

        selector_card = tk.Frame(
            page,
            bg=SURFACE,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        selector_card.pack(fill="x", pady=(18, 12))
        inner = tk.Frame(selector_card, bg=SURFACE)
        inner.pack(fill="x", padx=18, pady=14)

        tk.Label(
            inner,
            text="Học phần phụ trách",
            bg=SURFACE,
            fg=MUTED,
            font=font(8, "bold"),
            anchor="w",
        ).pack(fill="x")
        self.course_combo = ttk.Combobox(inner, state="readonly", width=64)
        self.course_combo.pack(fill="x", pady=(4, 8))
        self.course_combo.bind("<<ComboboxSelected>>", lambda event: self._on_course_change())

        self.course_info = tk.Label(
            inner,
            text="",
            bg=SURFACE,
            fg=MUTED,
            font=font(9),
            anchor="w",
            justify="left",
            wraplength=800,
        )
        self.course_info.pack(fill="x")

        table, self.tree = create_table(page, _COLUMNS, height=13)
        table.pack(fill="both", expand=True)

        self.feedback = tk.Label(
            page,
            text="",
            bg=BACKGROUND,
            fg=DANGER,
            font=font(9),
            anchor="w",
            justify="left",
            wraplength=860,
        )
        self.feedback.pack(fill="x", pady=(8, 0))

    def _load_courses(self) -> None:
        try:
            self._courses = self._service.lecturer_courses(self._session)
        except (ServiceError, DataAccessError) as exc:
            self.feedback.configure(text=str(exc))
            return

        if not self._courses:
            self.course_combo.configure(values=[], state="disabled")
            self.course_info.configure(text="Bạn chưa được phân công học phần nào.")
            return

        self.course_combo.configure(
            values=[course.label for course in self._courses],
            state="readonly",
        )
        self.course_combo.current(0)
        self._on_course_change()

    def _on_course_change(self) -> None:
        index = self.course_combo.current()
        if index < 0 or index >= len(self._courses):
            return
        self._load_sheet(self._courses[index].course_id)

    def _load_sheet(self, course_id: int) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            sheet: CourseGradeSheet = self._service.course_grade_sheet(
                self._session, course_id
            )
        except (ServiceError, DataAccessError) as exc:
            self.feedback.configure(text=str(exc))
            return

        self._course = sheet.course
        self.feedback.configure(text="")
        self.course_info.configure(
            text=(
                f"{sheet.course.course_code} • {sheet.course.credits} tín chỉ "
                f"• {sheet.course.semester} {sheet.course.academic_year} "
                f"• Giảng viên: {sheet.course.lecturer_name or '—'} "
                f"• {len(sheet.rows)} sinh viên"
            )
        )

        for row in sheet.rows:
            self.tree.insert(
                "",
                "end",
                values=(
                    row.student_code,
                    row.student_name,
                    format_score(row.process_score),
                    format_score(row.final_score),
                    format_score(row.average_score),
                    status_label(row.status),
                ),
                tags=row_tag(row.status),
            )
