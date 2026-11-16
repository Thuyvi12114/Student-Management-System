"""Màn hình Nhập & cập nhật điểm dành cho giảng viên."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.dao.errors import DataAccessError
from app.models import CourseGradeRow
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
from app.ui.theme import (
    BACKGROUND,
    BORDER,
    DANGER,
    MUTED,
    SUCCESS,
    SURFACE,
    font,
    primary_button,
    text_field,
)

_COLUMNS = [
    ("student_code", "Mã SV", 95, "w"),
    ("student_name", "Họ tên", 220, "w"),
    ("process", "Quá trình", 80, "center"),
    ("final", "Cuối kỳ", 80, "center"),
    ("average", "Trung bình", 80, "center"),
    ("status", "Trạng thái", 110, "center"),
]


class GradeEntryView(tk.Frame):
    """Giảng viên nhập điểm mới hoặc cập nhật điểm cho sinh viên."""

    def __init__(self, parent: tk.Misc, grade_service: GradeService, session: Session) -> None:
        super().__init__(parent, bg=BACKGROUND)
        self._service = grade_service
        self._session = session
        self._courses = []
        self._course = None
        self._rows_by_iid: dict[str, CourseGradeRow] = {}
        self._selected_row: CourseGradeRow | None = None
        self._build()
        self._load_courses()

    def _build(self) -> None:
        page = tk.Frame(self, bg=BACKGROUND)
        page.pack(fill="both", expand=True, padx=32, pady=28)

        page_header(
            page,
            "Nhập & cập nhật điểm",
            "Chọn học phần được phân công, chọn sinh viên trong bảng rồi nhập điểm. "
            "Điểm hợp lệ từ 0 đến 10, tối đa 2 chữ số thập phân; "
            "mỗi sinh viên chỉ có một bản ghi điểm cho mỗi học phần.",
        )

        selector_card = tk.Frame(
            page,
            bg=SURFACE,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        selector_card.pack(fill="x", pady=(16, 10))
        selector_inner = tk.Frame(selector_card, bg=SURFACE)
        selector_inner.pack(fill="x", padx=18, pady=12)
        tk.Label(
            selector_inner,
            text="Học phần phụ trách",
            bg=SURFACE,
            fg=MUTED,
            font=font(8, "bold"),
            anchor="w",
        ).pack(fill="x")
        self.course_combo = ttk.Combobox(selector_inner, state="readonly", width=64)
        self.course_combo.pack(fill="x", pady=(4, 0))
        self.course_combo.bind("<<ComboboxSelected>>", lambda event: self._on_course_change())

        table, self.tree = create_table(page, _COLUMNS, height=8)
        table.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda event: self._on_select())

        editor = tk.Frame(
            page,
            bg=SURFACE,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        editor.pack(fill="x", pady=(12, 0))
        editor_inner = tk.Frame(editor, bg=SURFACE)
        editor_inner.pack(fill="x", padx=18, pady=14)

        top_row = tk.Frame(editor_inner, bg=SURFACE)
        top_row.pack(fill="x")
        self.selected_label = tk.Label(
            top_row,
            text="Chọn sinh viên trong bảng để nhập điểm",
            bg=SURFACE,
            fg="#0F172A",
            font=font(10, "bold"),
            anchor="w",
        )
        self.selected_label.pack(side="left")
        self.mode_label = tk.Label(
            top_row,
            text="",
            bg=SURFACE,
            fg=MUTED,
            font=font(8, "bold"),
            anchor="e",
        )
        self.mode_label.pack(side="right")

        fields_row = tk.Frame(editor_inner, bg=SURFACE)
        fields_row.pack(fill="x", pady=(10, 0))

        process_group = tk.Frame(fields_row, bg=SURFACE)
        process_group.pack(side="left", padx=(0, 18))
        tk.Label(
            process_group,
            text="Điểm quá trình (40%)",
            bg=SURFACE,
            fg=MUTED,
            font=font(8, "bold"),
            anchor="w",
        ).pack(fill="x")
        process_wrapper, self.process_entry = text_field(process_group)
        self.process_entry.configure(width=12)
        process_wrapper.pack(fill="x", pady=(4, 0))

        final_group = tk.Frame(fields_row, bg=SURFACE)
        final_group.pack(side="left", padx=(0, 18))
        tk.Label(
            final_group,
            text="Điểm cuối kỳ (60%)",
            bg=SURFACE,
            fg=MUTED,
            font=font(8, "bold"),
            anchor="w",
        ).pack(fill="x")
        final_wrapper, self.final_entry = text_field(final_group)
        self.final_entry.configure(width=12)
        final_wrapper.pack(fill="x", pady=(4, 0))

        save_button = primary_button(fields_row, "Lưu điểm", self._save)
        save_button.pack(side="right", pady=(18, 0))

        self.feedback = tk.Label(
            editor_inner,
            text="Điểm được lưu sẽ tự tính trung bình 40% quá trình + 60% cuối kỳ "
            "và trạng thái Đạt/Không đạt (ngưỡng 5.0).",
            bg=SURFACE,
            fg=MUTED,
            font=font(8),
            anchor="w",
            justify="left",
            wraplength=780,
        )
        self.feedback.pack(fill="x", pady=(10, 0))

    def _load_courses(self) -> None:
        try:
            self._courses = self._service.lecturer_courses(self._session)
        except (ServiceError, DataAccessError) as exc:
            self.feedback.configure(text=str(exc), fg=DANGER)
            return

        if not self._courses:
            self.course_combo.configure(values=[], state="disabled")
            self.feedback.configure(
                text="Bạn chưa được phân công học phần nào nên chưa thể nhập điểm.",
                fg=DANGER,
            )
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

    def _load_sheet(self, course_id: int, select_student_id: int | None = None) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._rows_by_iid.clear()
        self._selected_row = None
        self._clear_form()

        try:
            sheet: CourseGradeSheet = self._service.course_grade_sheet(
                self._session, course_id
            )
        except (ServiceError, DataAccessError) as exc:
            self.feedback.configure(text=str(exc), fg=DANGER)
            return

        self._course = sheet.course
        for row in sheet.rows:
            iid = f"student-{row.student_id}"
            self._rows_by_iid[iid] = row
            self.tree.insert(
                "",
                "end",
                iid=iid,
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

        self.feedback.configure(
            text=(
                f"{sheet.course.course_code} • {len(sheet.rows)} sinh viên • "
                "Chọn một dòng để nhập hoặc cập nhật điểm."
            ),
            fg=MUTED,
        )

        if select_student_id is not None:
            iid = f"student-{select_student_id}"
            if iid in self._rows_by_iid:
                self.tree.selection_set(iid)
                self.tree.focus(iid)

    def _on_select(self) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        row = self._rows_by_iid.get(selection[0])
        if row is None:
            return

        self._selected_row = row
        self.selected_label.configure(text=f"{row.student_code} - {row.student_name}")
        self.mode_label.configure(
            text="Cập nhật điểm" if row.grade_id is not None else "Thêm điểm mới"
        )
        self.process_entry.delete(0, "end")
        self.final_entry.delete(0, "end")
        if row.process_score is not None:
            self.process_entry.insert(0, f"{row.process_score:.2f}")
        if row.final_score is not None:
            self.final_entry.insert(0, f"{row.final_score:.2f}")
        self.feedback.configure(
            text="Điểm được lưu sẽ tự tính trung bình 40% quá trình + 60% cuối kỳ "
            "và trạng thái Đạt/Không đạt (ngưỡng 5.0).",
            fg=MUTED,
        )

    def _save(self) -> None:
        if self._course is None:
            self.feedback.configure(text="Vui lòng chọn học phần.", fg=DANGER)
            return
        if self._selected_row is None:
            self.feedback.configure(
                text="Vui lòng chọn sinh viên trong bảng trước khi lưu điểm.",
                fg=DANGER,
            )
            return

        try:
            self._service.save_grade(
                self._session,
                self._course.course_id,
                self._selected_row.student_id,
                self.process_entry.get(),
                self.final_entry.get(),
                self._selected_row.grade_id,
            )
        except (ServiceError, DataAccessError) as exc:
            self.feedback.configure(text=str(exc), fg=DANGER)
            return

        student_id = self._selected_row.student_id
        self._load_sheet(self._course.course_id, select_student_id=student_id)
        self.feedback.configure(text="Đã lưu điểm thành công.", fg=SUCCESS)

    def _clear_form(self) -> None:
        self.selected_label.configure(text="Chọn sinh viên trong bảng để nhập điểm")
        self.mode_label.configure(text="")
        self.process_entry.delete(0, "end")
        self.final_entry.delete(0, "end")
