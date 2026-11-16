"""Màn hình Tra cứu điểm dành cho Admin (chỉ đọc)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.dao.errors import DataAccessError
from app.security.session import Session
from app.service.exceptions import ServiceError
from app.service.grade_service import GradeService
from app.ui.grades.widgets import (
    create_table,
    format_score,
    page_header,
    row_tag,
    status_label,
)
from app.ui.theme import BACKGROUND, BORDER, DANGER, MUTED, SURFACE, font, primary_button

_COLUMNS = [
    ("student_code", "Mã SV", 90, "w"),
    ("student_name", "Họ tên", 170, "w"),
    ("course_code", "Mã HP", 90, "w"),
    ("course_name", "Học phần", 190, "w"),
    ("credits", "TC", 50, "center"),
    ("process", "Quá trình", 75, "center"),
    ("final", "Cuối kỳ", 75, "center"),
    ("average", "Trung bình", 75, "center"),
    ("status", "Trạng thái", 100, "center"),
]

_ALL_STUDENTS = "Tất cả sinh viên"
_ALL_COURSES = "Tất cả học phần"


class AdminGradesView(tk.Frame):
    """Admin xem toàn bộ điểm, lọc theo sinh viên và học phần."""

    def __init__(self, parent: tk.Misc, grade_service: GradeService, session: Session) -> None:
        super().__init__(parent, bg=BACKGROUND)
        self._service = grade_service
        self._session = session
        self._students = []
        self._courses = []
        self._build()
        self._load_options()

    def _build(self) -> None:
        page = tk.Frame(self, bg=BACKGROUND)
        page.pack(fill="both", expand=True, padx=32, pady=28)

        page_header(
            page,
            "Tra cứu điểm",
            "Xem bảng điểm toàn hệ thống. Admin chỉ được tra cứu, không sửa điểm; "
            "việc nhập và cập nhật điểm do giảng viên phụ trách học phần thực hiện.",
        )

        filter_card = tk.Frame(
            page,
            bg=SURFACE,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        filter_card.pack(fill="x", pady=(18, 12))
        inner = tk.Frame(filter_card, bg=SURFACE)
        inner.pack(fill="x", padx=18, pady=14)

        tk.Label(
            inner,
            text="Sinh viên",
            bg=SURFACE,
            fg=MUTED,
            font=font(8, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")
        self.student_combo = ttk.Combobox(inner, state="readonly", width=34)
        self.student_combo.grid(row=1, column=0, sticky="w", padx=(0, 16), pady=(4, 0))
        self.student_combo.bind("<<ComboboxSelected>>", lambda event: self._search())

        tk.Label(
            inner,
            text="Học phần",
            bg=SURFACE,
            fg=MUTED,
            font=font(8, "bold"),
            anchor="w",
        ).grid(row=0, column=1, sticky="w")
        self.course_combo = ttk.Combobox(inner, state="readonly", width=42)
        self.course_combo.grid(row=1, column=1, sticky="w", padx=(0, 16), pady=(4, 0))
        self.course_combo.bind("<<ComboboxSelected>>", lambda event: self._search())

        search_button = primary_button(inner, "Tra cứu", self._search)
        search_button.grid(row=1, column=2, sticky="w", pady=(4, 0))

        result_row = tk.Frame(page, bg=BACKGROUND)
        result_row.pack(fill="x", pady=(0, 8))
        tk.Label(
            result_row,
            text="Kết quả",
            bg=BACKGROUND,
            fg="#0F172A",
            font=font(11, "bold"),
            anchor="w",
        ).pack(side="left")
        self.count_label = tk.Label(
            result_row,
            text="",
            bg=BACKGROUND,
            fg=MUTED,
            font=font(8),
            anchor="e",
        )
        self.count_label.pack(side="right")

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

    def _load_options(self) -> None:
        try:
            self._students, self._courses = self._service.list_filter_options(self._session)
        except (ServiceError, DataAccessError) as exc:
            self.feedback.configure(text=str(exc))
            return

        self.student_combo.configure(
            values=[_ALL_STUDENTS]
            + [f"{student.student_code} - {student.full_name}" for student in self._students]
        )
        self.course_combo.configure(
            values=[_ALL_COURSES]
            + [f"{course.course_code} - {course.course_name}" for course in self._courses]
        )
        self.student_combo.current(0)
        self.course_combo.current(0)
        self._search()

    def _selected_student_id(self) -> int | None:
        index = self.student_combo.current()
        return self._students[index - 1].student_id if index > 0 else None

    def _selected_course_id(self) -> int | None:
        index = self.course_combo.current()
        return self._courses[index - 1].course_id if index > 0 else None

    def _search(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            rows = self._service.admin_search(
                self._session,
                self._selected_student_id(),
                self._selected_course_id(),
            )
        except (ServiceError, DataAccessError) as exc:
            self.count_label.configure(text="")
            self.feedback.configure(text=str(exc))
            return

        self.feedback.configure(text="")
        for grade in rows:
            self.tree.insert(
                "",
                "end",
                values=(
                    grade.student_code,
                    grade.student_name,
                    grade.course_code,
                    grade.course_name,
                    grade.credits,
                    format_score(grade.process_score),
                    format_score(grade.final_score),
                    format_score(grade.average_score),
                    status_label(grade.status),
                ),
                tags=row_tag(grade.status),
            )

        self.count_label.configure(text=f"{len(rows)} dòng")
        if not rows:
            self.feedback.configure(text="Không có dữ liệu phù hợp bộ lọc.", fg=MUTED)
