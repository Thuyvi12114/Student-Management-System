"""UI 1.4 / 1.10 - Xem và quản lý học phần (UC-12, UC-13)."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from app.models import CourseOption, CourseSearchResult, Lecturer, Role
from app.security.session import Session
from app.service.course_service import CourseService
from app.service.lecturer_service import LecturerService
from app.ui.management.widgets import configure_management_table, run_in_background
from app.ui.theme import (
    BACKGROUND,
    BORDER,
    DANGER,
    MUTED,
    SURFACE,
    TEXT,
    font,
    primary_button,
    secondary_button,
)

_PAGE_SIZE = 8


class CourseManagementView(tk.Frame):
    """Search courses with server-side paging; only admins can edit catalog data."""

    def __init__(
        self,
        parent: tk.Misc,
        course_service: CourseService,
        lecturer_service: LecturerService,
        session: Session,
    ) -> None:
        super().__init__(parent, bg=BACKGROUND)
        self._service = course_service
        self._lecturer_service = lecturer_service
        self._session = session
        self._is_admin = session.role is Role.ADMIN
        self._page = 1
        self._total_pages = 0
        self._search_after_id: str | None = None
        self._courses: dict[str, CourseOption] = {}
        self._build()
        self._load()

    def _build(self) -> None:
        page = tk.Frame(self, bg=BACKGROUND)
        page.pack(fill="both", expand=True, padx=32, pady=24)
        title_row = tk.Frame(page, bg=BACKGROUND)
        title_row.pack(fill="x")
        title_copy = tk.Frame(title_row, bg=BACKGROUND)
        title_copy.pack(side="left", fill="x", expand=True)
        tk.Label(
            title_copy, text="Quản lý học phần", bg=BACKGROUND, fg=TEXT,
            font=font(20, "bold"), anchor="w",
        ).pack(fill="x")
        tk.Label(
            title_copy,
            text="Tra cứu học phần, số tín chỉ và giảng viên phụ trách. Không thể xóa học phần đã có điểm.",
            bg=BACKGROUND, fg=MUTED, font=font(9), anchor="w",
        ).pack(fill="x", pady=(5, 0))
        if self._is_admin:
            primary_button(title_row, "+  Thêm học phần", self._open_create).pack(
                side="right", padx=(16, 0)
            )

        filters = tk.Frame(page, bg=BACKGROUND)
        filters.pack(fill="x", pady=(20, 14))
        search_wrap = tk.Frame(
            filters, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1
        )
        search_wrap.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self._keyword = tk.StringVar()
        entry = ttk.Entry(search_wrap, textvariable=self._keyword, font=font(9))
        entry.pack(fill="x", padx=10, pady=8)
        entry.bind("<KeyRelease>", self._schedule_search)

        secondary_button(filters, "Xóa bộ lọc", self._clear_filters).pack(side="left")

        card = tk.Frame(page, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="both", expand=True)
        inner = tk.Frame(card, bg=SURFACE)
        inner.pack(fill="both", expand=True, padx=18, pady=16)
        heading = tk.Frame(inner, bg=SURFACE)
        heading.pack(fill="x", pady=(0, 10))
        tk.Label(
            heading, text="Danh sách học phần", bg=SURFACE, fg=TEXT,
            font=font(11, "bold"), anchor="w",
        ).pack(side="left")
        self._summary = tk.Label(
            heading, text="Đang tải...", bg=SURFACE, fg=MUTED, font=font(8)
        )
        self._summary.pack(side="right")

        configure_management_table(inner)
        columns = (
            ("course_code", "Mã học phần", 120),
            ("course_name", "Tên học phần", 220),
            ("credits", "Tín chỉ", 70),
            ("lecturer", "Giảng viên phụ trách", 220),
            ("description", "Mô tả", 260),
        )
        self._tree = ttk.Treeview(
            inner, columns=[column[0] for column in columns], show="headings",
            height=_PAGE_SIZE, style="Management.Treeview", selectmode="browse",
        )
        for key, label, width in columns:
            self._tree.heading(key, text=label, anchor="w")
            self._tree.column(key, width=width, minwidth=60, anchor="w")
        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        self._tree.bind("<Double-1>", self._show_detail)
        self._tree.pack(fill="both", expand=True)
        self._empty = tk.Label(inner, text="", bg=SURFACE, fg=MUTED, font=font(9), pady=12)
        self._empty.pack(fill="x")

        footer = tk.Frame(inner, bg=SURFACE)
        footer.pack(fill="x", pady=(10, 0))
        self._range = tk.Label(footer, text="", bg=SURFACE, fg=MUTED, font=font(8))
        self._range.pack(side="left")
        actions = tk.Frame(footer, bg=SURFACE)
        actions.pack(side="right")
        self._detail_button = secondary_button(actions, "Chi tiết", self._show_detail)
        self._detail_button.pack(side="left", padx=(0, 6))
        if self._is_admin:
            self._edit_button = secondary_button(actions, "Chỉnh sửa", self._open_edit)
            self._edit_button.pack(side="left", padx=(0, 6))
            self._delete_button = secondary_button(actions, "Xóa", self._delete)
            self._delete_button.pack(side="left", padx=(0, 10))
        self._previous = secondary_button(actions, "Trước", self._previous_page)
        self._previous.pack(side="left", padx=(0, 6))
        self._page_label = tk.Label(
            actions, text="Trang 0 / 0", bg=SURFACE, fg=TEXT,
            font=font(8, "bold"), padx=6,
        )
        self._page_label.pack(side="left")
        self._next = secondary_button(actions, "Sau", self._next_page)
        self._next.pack(side="left", padx=(6, 0))
        self._feedback = tk.Label(
            page, text="", bg=BACKGROUND, fg=DANGER, font=font(9), anchor="w"
        )
        self._feedback.pack(fill="x", pady=(8, 0))
        self._set_action_state("disabled")

    def _schedule_search(self, _event: tk.Event | None = None) -> None:
        if self._search_after_id is not None:
            self.after_cancel(self._search_after_id)
        self._search_after_id = self.after(250, self._filter_changed)

    def _filter_changed(self, _event: tk.Event | None = None) -> None:
        self._page = 1
        self._load()

    def _clear_filters(self) -> None:
        self._keyword.set("")
        self._page = 1
        self._load()

    def _load(self) -> None:
        self._summary.configure(text="Đang tải...")
        keyword = self._keyword.get().strip() or None
        run_in_background(
            self,
            lambda: self._service.search(
                self._session, keyword, page=self._page,
                page_size=_PAGE_SIZE,
            ),
            self._loaded,
            self._failed,
        )

    def _loaded(self, result: CourseSearchResult) -> None:
        self._courses = {course.course_id: course for course in result.items}
        self._page = result.page
        self._total_pages = result.total_pages
        self._tree.delete(*self._tree.get_children())
        for course in result.items:
            self._tree.insert(
                "", "end", iid=str(course.course_id),
                values=(
                    course.course_code,
                    course.course_name,
                    course.credits,
                    course.lecturer_name,
                    (course.description or "—").replace("\n", " ")[:60],
                ),
            )
        start = (result.page - 1) * result.page_size + 1 if result.total_count else 0
        end = min(result.page * result.page_size, result.total_count)
        self._range.configure(text=f"Hiển thị {start}–{end} trong {result.total_count} học phần")
        self._summary.configure(text=f"{result.total_count} học phần")
        self._page_label.configure(text=f"Trang {result.page} / {result.total_pages}")
        self._previous.configure(state="normal" if result.page > 1 else "disabled")
        self._next.configure(state="normal" if result.page < result.total_pages else "disabled")
        self._empty.configure(text="Chưa có học phần phù hợp." if not result.items else "")
        self._feedback.configure(text="")
        self._set_action_state("disabled")

    def _failed(self, error: BaseException) -> None:
        self._courses = {}
        self._tree.delete(*self._tree.get_children())
        self._summary.configure(text="Không tải được dữ liệu")
        self._range.configure(text="")
        self._page_label.configure(text="Trang 0 / 0")
        self._empty.configure(text="")
        self._feedback.configure(text=f"Không tải được danh sách học phần: {error}")
        self._set_action_state("disabled")

    def _set_action_state(self, state: str) -> None:
        self._detail_button.configure(state=state)
        if self._is_admin:
            self._edit_button.configure(state=state)
            self._delete_button.configure(state=state)

    def _on_select(self, _event: tk.Event | None = None) -> None:
        self._set_action_state("normal" if self._tree.selection() else "disabled")

    def _selected_course(self) -> CourseOption | None:
        selection = self._tree.selection()
        return self._courses.get(selection[0]) if selection else None

    def _show_detail(self, _event: tk.Event | None = None) -> None:
        course = self._selected_course()
        if course is None:
            return
        details = (
            ("Mã học phần", course.course_code),
            ("Tên học phần", course.course_name),
            ("Số tín chỉ", str(course.credits)),
            ("Giảng viên phụ trách", f"{course.lecturer_name} ({course.lecturer_id})"),
            ("Mô tả", course.description or "Chưa có mô tả"),
        )
        dialog = tk.Toplevel(self)
        dialog.title("Chi tiết học phần")
        dialog.configure(bg=BACKGROUND)
        dialog.transient(self.winfo_toplevel())
        body = tk.Frame(dialog, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        body.pack(fill="both", expand=True, padx=20, pady=20)
        tk.Label(body, text="Chi tiết học phần", bg=SURFACE, fg=TEXT, font=font(14, "bold")).pack(
            anchor="w", padx=20, pady=(18, 12)
        )
        for label, value in details:
            tk.Label(
                body, text=f"{label}:  {value}", bg=SURFACE, fg=TEXT,
                font=font(9), anchor="w", justify="left", wraplength=420,
            ).pack(fill="x", padx=20, pady=5)
        secondary_button(body, "Đóng", dialog.destroy).pack(anchor="e", padx=20, pady=16)
        dialog.grab_set()

    def _open_create(self) -> None:
        self._open_form(None)

    def _open_edit(self) -> None:
        course = self._selected_course()
        if course is not None:
            self._open_form(course)

    def _open_form(self, course: CourseOption | None) -> None:
        dialog = tk.Toplevel(self)
        dialog.title("Thêm học phần" if course is None else "Chỉnh sửa học phần")
        dialog.configure(bg=BACKGROUND)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        body = tk.Frame(dialog, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        body.pack(fill="both", expand=True, padx=20, pady=20)
        tk.Label(
            body, text="Thông tin học phần", bg=SURFACE, fg=TEXT,
            font=font(14, "bold"), anchor="w",
        ).pack(fill="x", padx=20, pady=(18, 12))

        fields: dict[str, tk.StringVar] = {}
        for key, label, initial in (
            ("course_id", "Mã học phần", course.course_id if course else ""),
            ("course_name", "Tên học phần", course.course_name if course else ""),
            ("credits", "Số tín chỉ (1-10)", str(course.credits) if course else ""),
            ("description", "Mô tả (không bắt buộc)", (course.description or "") if course else ""),
        ):
            tk.Label(body, text=label, bg=SURFACE, fg=TEXT, font=font(8), anchor="w").pack(
                fill="x", padx=20, pady=(7, 0)
            )
            value = tk.StringVar(value=initial)
            entry = ttk.Entry(body, textvariable=value, font=font(9), width=52)
            entry.pack(fill="x", padx=20, pady=(3, 0))
            if key == "course_id" and course is not None:
                entry.configure(state="readonly")  # mã học phần bất biến
            fields[key] = value

        lecturer_var = tk.StringVar(value="Đang tải giảng viên...")
        tk.Label(body, text="Giảng viên phụ trách", bg=SURFACE, fg=TEXT, font=font(8), anchor="w").pack(
            fill="x", padx=20, pady=(7, 0)
        )
        lecturer_combo = ttk.Combobox(
            body, textvariable=lecturer_var, state="disabled", font=font(9)
        )
        lecturer_combo.pack(fill="x", padx=20, pady=(3, 0))
        feedback = tk.Label(body, text="", bg=SURFACE, fg=DANGER, font=font(8), anchor="w")
        feedback.pack(fill="x", padx=20, pady=(8, 0))
        save_button = primary_button(body, "Lưu học phần", lambda: None)
        save_button.pack(anchor="e", padx=20, pady=16)
        lecturers: list[Lecturer] = []

        def loaded_options(options: list[Lecturer]) -> None:
            lecturers.extend(options)
            labels = [f"{item.lecturer_id} - {item.full_name}" for item in lecturers]
            lecturer_combo.configure(values=labels, state="readonly")
            if course:
                match = next(
                    (i for i, item in enumerate(lecturers) if item.lecturer_id == course.lecturer_id),
                    None,
                )
                if match is not None:
                    lecturer_combo.current(match)
            elif labels:
                lecturer_combo.current(0)
            if not labels:
                feedback.configure(text="Không tìm thấy giảng viên để phân công.")

        def options_failed(error: BaseException) -> None:
            lecturer_combo.configure(state="disabled")
            feedback.configure(text=f"Không tải được danh sách giảng viên: {error}")

        def save() -> None:
            if not lecturers or lecturer_combo.current() < 0:
                feedback.configure(text="Vui lòng chọn giảng viên phụ trách.")
                return
            lecturer_id = lecturers[lecturer_combo.current()].lecturer_id
            values = dict(
                course_name=fields["course_name"].get(),
                credits=fields["credits"].get(),
                lecturer_id=lecturer_id,
                description=fields["description"].get(),
            )
            if course is None:
                values["course_id"] = fields["course_id"].get()
            save_button.configure(state="disabled")
            feedback.configure(text="Đang lưu...", fg=MUTED)

            def operation() -> CourseOption:
                if course is None:
                    return self._service.create(self._session, **values)
                return self._service.update(self._session, course.course_id, **values)

            def saved(_result: CourseOption) -> None:
                if dialog.winfo_exists():
                    dialog.destroy()
                self._page = 1
                self._load()

            def save_failed(error: BaseException) -> None:
                if dialog.winfo_exists():
                    save_button.configure(state="normal")
                    feedback.configure(text=str(error), fg=DANGER)

            run_in_background(dialog, operation, saved, save_failed)

        save_button.configure(command=save)
        run_in_background(
            dialog,
            self._all_lecturers,
            loaded_options,
            options_failed,
        )

    def _all_lecturers(self) -> list[Lecturer]:
        first = self._lecturer_service.search(self._session, page=1, page_size=200)
        lecturers = list(first.items)
        for page in range(2, first.total_pages + 1):
            lecturers.extend(
                self._lecturer_service.search(
                    self._session, page=page, page_size=200
                ).items
            )
        return lecturers

    def _delete(self) -> None:
        course = self._selected_course()
        if course is None:
            return
        if not messagebox.askyesno(
            "Xác nhận xóa",
            f"Xóa học phần {course.course_id} - {course.course_name}? "
            "Học phần đã có điểm sẽ không thể xóa.",
            parent=self,
        ):
            return
        self._set_action_state("disabled")

        def delete() -> None:
            self._service.delete(self._session, course.course_id)

        def deleted(_result: None) -> None:
            self._load()

        def failed(error: BaseException) -> None:
            self._feedback.configure(text=f"Không xóa được học phần: {error}")
            self._set_action_state("normal")

        run_in_background(self, delete, deleted, failed)

    def _previous_page(self) -> None:
        if self._page > 1:
            self._page -= 1
            self._load()

    def _next_page(self) -> None:
        if self._page < self._total_pages:
            self._page += 1
            self._load()
