"""Màn hình Kết quả học tập của sinh viên (UI 1.5)."""

from __future__ import annotations

import tkinter as tk

from app.dao.errors import DataAccessError
from app.security.session import Session
from app.service.exceptions import ServiceError
from app.service.grade_service import GradeService
from app.ui.grades.widgets import (
    create_table,
    format_score,
    page_header,
    row_tag,
    stat_card,
    status_label,
)
from app.ui.theme import BACKGROUND, DANGER, MUTED, SUCCESS, TEXT, font

_COLUMNS = [
    ("course_code", "Mã HP", 90, "w"),
    ("course_name", "Học phần", 230, "w"),
    ("credits", "TC", 50, "center"),
    ("semester", "Học kỳ", 65, "center"),
    ("academic_year", "Năm học", 90, "center"),
    ("process", "Quá trình", 80, "center"),
    ("final", "Cuối kỳ", 80, "center"),
    ("average", "Trung bình", 80, "center"),
    ("status", "Trạng thái", 110, "center"),
]


class StudentResultsView(tk.Frame):
    """Bảng điểm của chính sinh viên đang đăng nhập."""

    def __init__(self, parent: tk.Misc, grade_service: GradeService, session: Session) -> None:
        super().__init__(parent, bg=BACKGROUND)
        self._service = grade_service
        self._session = session
        self._build()
        self._load()

    def _build(self) -> None:
        page = tk.Frame(self, bg=BACKGROUND)
        page.pack(fill="both", expand=True, padx=32, pady=28)

        page_header(
            page,
            "Kết quả học tập",
            "Điểm trung bình tích lũy được tính theo tín chỉ: "
            "tổng (điểm trung bình học phần × số tín chỉ) chia cho tổng tín chỉ đã có điểm.",
        )

        self.student_label = tk.Label(
            page,
            text="Đang tải...",
            bg=BACKGROUND,
            fg=MUTED,
            font=font(9),
            anchor="w",
        )
        self.student_label.pack(fill="x", pady=(10, 0))

        summary = tk.Frame(page, bg=BACKGROUND)
        summary.pack(fill="x", pady=(18, 16))
        gpa_card, self.gpa_value = stat_card(summary, "GPA tích lũy (hệ 10)")
        gpa_card.pack(side="left", fill="x", expand=True, padx=(0, 10))
        credit_card, self.credit_value = stat_card(summary, "Tín chỉ đạt / có điểm")
        credit_card.pack(side="left", fill="x", expand=True, padx=(0, 10))
        course_card, self.course_value = stat_card(summary, "Học phần đã có điểm")
        course_card.pack(side="left", fill="x", expand=True)

        tk.Label(
            page,
            text="Bảng điểm chi tiết",
            bg=BACKGROUND,
            fg=TEXT,
            font=font(11, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 8))

        table, self.tree = create_table(page, _COLUMNS, height=11)
        table.pack(fill="both", expand=True)

        self.feedback = tk.Label(
            page,
            text="",
            bg=BACKGROUND,
            fg=MUTED,
            font=font(9),
            anchor="w",
            justify="left",
            wraplength=860,
        )
        self.feedback.pack(fill="x", pady=(8, 0))

    def _load(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            result = self._service.student_results(self._session)
        except (ServiceError, DataAccessError) as exc:
            self.student_label.configure(text="Không tải được kết quả học tập.")
            self.feedback.configure(text=str(exc), fg=DANGER)
            return

        self.student_label.configure(
            text=(
                f"Sinh viên: {result.student.full_name} • {result.student.student_code} "
                f"• Lớp {result.student.class_name}"
            )
        )
        self.gpa_value.configure(text=format_score(result.gpa))
        self.credit_value.configure(
            text=f"{result.passed_credits}/{result.total_credits}"
        )
        self.course_value.configure(text=str(len(result.grades)))

        for grade in result.grades:
            self.tree.insert(
                "",
                "end",
                values=(
                    grade.course_code,
                    grade.course_name,
                    grade.credits,
                    grade.semester,
                    grade.academic_year,
                    format_score(grade.process_score),
                    format_score(grade.final_score),
                    format_score(grade.average_score),
                    status_label(grade.status),
                ),
                tags=row_tag(grade.status),
            )

        if result.grades:
            self.feedback.configure(
                text=(
                    f"{len(result.grades)} học phần • GPA chỉ tính các học phần đã đủ "
                    "điểm quá trình và điểm cuối kỳ."
                ),
                fg=MUTED,
            )
        else:
            self.feedback.configure(text="Chưa có dữ liệu điểm.", fg=SUCCESS)
