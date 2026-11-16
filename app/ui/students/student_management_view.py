"""Database-backed student management page for administrators."""

from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from app.dao.errors import DataAccessError
from app.models import DashboardStats, StudentRecord, StudentSearchResult
from app.security.session import Session
from app.service.exceptions import ServiceError
from app.service.student_service import StudentService
from app.ui.management.widgets import (
    configure_management_table,
    create_stat_card,
    run_in_background,
)
from app.ui.theme import (
    BACKGROUND,
    BORDER,
    DANGER,
    MUTED,
    PRIMARY_DARK,
    SURFACE,
    TEXT,
    font,
    primary_button,
    secondary_button,
)

_PAGE_SIZE = 8
_ALL_CLASSES = "Tất cả lớp"


class StudentManagementView(tk.Frame):
    """Search, filter, page and maintain student records from MySQL."""

    def __init__(
        self,
        parent: tk.Misc,
        student_service: StudentService,
        session: Session,
    ) -> None:
        super().__init__(parent, bg=BACKGROUND)
        self._service = student_service
        self._session = session
        self._page = 1
        self._page_count = 0
        self._search_after_id: str | None = None
        self._loading = False
        self._build()
        self._load(refresh_options=True)

    def _build(self) -> None:
        page = tk.Frame(self, bg=BACKGROUND)
        page.pack(fill="both", expand=True, padx=32, pady=24)

        title_row = tk.Frame(page, bg=BACKGROUND)
        title_row.pack(fill="x")
        title_copy = tk.Frame(title_row, bg=BACKGROUND)
        title_copy.pack(side="left", fill="x", expand=True)
        tk.Label(
            title_copy,
            text="Quản lý sinh viên",
            bg=BACKGROUND,
            fg=TEXT,
            font=font(20, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            title_copy,
            text="Tìm kiếm, xem và quản lý hồ sơ sinh viên đang lưu trong cơ sở dữ liệu.",
            bg=BACKGROUND,
            fg=MUTED,
            font=font(9),
            anchor="w",
        ).pack(fill="x", pady=(5, 0))
        self._add_button = primary_button(
            title_row, "+  Thêm sinh viên", self._open_create
        )
        self._add_button.pack(side="right", padx=(16, 0))

        stats_row = tk.Frame(page, bg=BACKGROUND)
        stats_row.pack(fill="x", pady=(20, 16))
        stats_row.grid_columnconfigure((0, 1), weight=1, uniform="student-stats")
        self._total_card, self._total_value = create_stat_card(
            stats_row, "Tổng số sinh viên"
        )
        self._classes_card, self._classes_value = create_stat_card(
            stats_row, "Số lớp đang quản lý"
        )
        self._total_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self._classes_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        filter_row = tk.Frame(page, bg=BACKGROUND)
        filter_row.pack(fill="x", pady=(0, 14))
        search_wrap = tk.Frame(
            filter_row, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1
        )
        search_wrap.pack(side="left", fill="x", expand=True, padx=(0, 10))
        tk.Label(search_wrap, text="⌕", bg=SURFACE, fg=MUTED, font=font(13)).pack(
            side="left", padx=(10, 0)
        )
        self._keyword = tk.StringVar()
        self._search_entry = ttk.Entry(
            search_wrap, textvariable=self._keyword, font=font(9)
        )
        self._search_entry.pack(side="left", fill="x", expand=True, padx=8, pady=8)
        self._search_entry.bind("<KeyRelease>", self._schedule_search)

        self._class_var = tk.StringVar(value=_ALL_CLASSES)
        self._class_combo = ttk.Combobox(
            filter_row,
            textvariable=self._class_var,
            values=[_ALL_CLASSES],
            state="readonly",
            width=18,
            font=font(9),
        )
        self._class_combo.pack(side="left", padx=(0, 10), ipady=5)
        self._class_combo.bind("<<ComboboxSelected>>", self._filter_changed)
        self._clear_button = secondary_button(
            filter_row, "Xóa bộ lọc", self._clear_filters
        )
        self._clear_button.pack(side="left")

        card = tk.Frame(page, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="both", expand=True)
        inner = tk.Frame(card, bg=SURFACE)
        inner.pack(fill="both", expand=True, padx=18, pady=16)

        heading = tk.Frame(inner, bg=SURFACE)
        heading.pack(fill="x", pady=(0, 10))
        tk.Label(
            heading,
            text="Danh sách sinh viên",
            bg=SURFACE,
            fg=TEXT,
            font=font(11, "bold"),
            anchor="w",
        ).pack(side="left")
        self._summary = tk.Label(
            heading, text="Đang tải...", bg=SURFACE, fg=MUTED, font=font(8)
        )
        self._summary.pack(side="right")

        configure_management_table(inner)
        columns = ("student_code", "full_name", "class_name", "email", "phone", "actions")
        self._tree = ttk.Treeview(
            inner,
            columns=columns,
            show="headings",
            height=_PAGE_SIZE,
            style="Management.Treeview",
            selectmode="browse",
        )
        column_specs = (
            ("student_code", "Mã sinh viên", 115, "w"),
            ("full_name", "Họ và tên", 175, "w"),
            ("class_name", "Lớp", 95, "w"),
            ("email", "Email", 205, "w"),
            ("phone", "Số điện thoại", 115, "w"),
            ("actions", "Thao tác", 145, "center"),
        )
        for key, label, width, anchor in column_specs:
            self._tree.heading(key, text=label, anchor=anchor)
            self._tree.column(
                key, width=width, minwidth=70, anchor=anchor, stretch=key == "email"
            )
        self._tree.tag_configure("even", background=SURFACE)
        self._tree.tag_configure("odd", background="#F8FAFC")
        self._tree.bind("<Double-1>", self._on_double_click)
        self._tree.bind("<Button-1>", self._on_action_click, add="+")
        self._tree.pack(fill="both", expand=True)

        self._empty_state = tk.Label(
            inner,
            text="",
            bg=SURFACE,
            fg=MUTED,
            font=font(9),
            pady=14,
        )
        self._empty_state.pack(fill="x")

        footer = tk.Frame(inner, bg=SURFACE)
        footer.pack(fill="x", pady=(10, 0))
        self._range_label = tk.Label(
            footer, text="", bg=SURFACE, fg=MUTED, font=font(8), anchor="w"
        )
        self._range_label.pack(side="left")
        page_controls = tk.Frame(footer, bg=SURFACE)
        page_controls.pack(side="right")
        self._previous_button = secondary_button(
            page_controls, "Trước", self._previous_page
        )
        self._previous_button.pack(side="left", padx=(0, 6))
        self._page_label = tk.Label(
            page_controls,
            text="Trang 0 / 0",
            bg=SURFACE,
            fg=PRIMARY_DARK,
            font=font(8, "bold"),
            padx=8,
        )
        self._page_label.pack(side="left")
        self._next_button = secondary_button(page_controls, "Sau", self._next_page)
        self._next_button.pack(side="left", padx=(6, 0))

        self._feedback = tk.Label(
            page, text="", bg=BACKGROUND, fg=DANGER, font=font(9), anchor="w"
        )
        self._feedback.pack(fill="x", pady=(8, 0))

    def _schedule_search(self, _event: tk.Event | None = None) -> None:
        if self._search_after_id is not None:
            self.after_cancel(self._search_after_id)
        self._search_after_id = self.after(250, self._filter_changed)

    def _filter_changed(self, _event: tk.Event | None = None) -> None:
        self._page = 1
        self._load()

    def _clear_filters(self) -> None:
        self._keyword.set("")
        self._class_var.set(_ALL_CLASSES)
        self._page = 1
        self._load()

    def _previous_page(self) -> None:
        if self._page > 1 and not self._loading:
            self._page -= 1
            self._load()

    def _next_page(self) -> None:
        if self._page < self._page_count and not self._loading:
            self._page += 1
            self._load()

    def _load(self, *, refresh_options: bool = False) -> None:
        if self._loading:
            return
        self._loading = True
        self._set_controls_enabled(False)
        self._feedback.configure(text="")
        self._empty_state.configure(text="")

        selected_class = self._class_var.get()
        class_name = None if selected_class == _ALL_CLASSES else selected_class
        keyword = self._keyword.get()
        page = self._page

        def fetch():
            result = self._service.search_students(
                self._session,
                keyword,
                page=page,
                page_size=_PAGE_SIZE,
                class_name=class_name,
            )
            stats = self._service.dashboard(self._session) if refresh_options else None
            classes = self._service.class_names(self._session) if refresh_options else None
            return result, stats, classes

        run_in_background(
            self,
            fetch,
            self._load_succeeded,
            self._load_failed,
        )

    def _load_succeeded(
        self,
        data: tuple[
            StudentSearchResult, DashboardStats | None, list[str] | None
        ],
    ) -> None:
        result, stats, classes = data
        self._loading = False
        self._set_controls_enabled(True)
        self._page = result.page
        self._page_count = result.total_pages
        self._render_rows(result)
        if stats is not None:
            self._total_value.configure(text=str(stats.total_students))
            self._classes_value.configure(text=str(stats.total_classes))
        if classes is not None:
            values = [_ALL_CLASSES, *classes]
            self._class_combo.configure(values=values)
            if self._class_var.get() not in values:
                self._class_var.set(_ALL_CLASSES)

    def _load_failed(self, error: BaseException) -> None:
        self._loading = False
        self._set_controls_enabled(True)
        self._tree.delete(*self._tree.get_children())
        self._total_value.configure(text="—")
        self._classes_value.configure(text="—")
        self._feedback.configure(text=self._error_message(error))
        self._summary.configure(text="Không tải được dữ liệu")
        self._empty_state.configure(text="Không thể tải danh sách sinh viên.")
        self._range_label.configure(text="")
        self._page_label.configure(text="Trang —")
        self._page_count = 0
        self._previous_button.configure(state="disabled")
        self._next_button.configure(state="disabled")

    def _render_rows(self, result: StudentSearchResult) -> None:
        self._tree.delete(*self._tree.get_children())
        total = result.total_count
        if not result.items:
            self._empty_state.configure(
                text="Chưa có sinh viên phù hợp." if total == 0 else "Không có dữ liệu ở trang này."
            )
        else:
            self._empty_state.configure(text="")
            for index, student in enumerate(result.items):
                self._tree.insert(
                    "",
                    "end",
                    iid=str(student.student_id),
                    values=(
                        student.student_code,
                        student.full_name,
                        student.class_name,
                        student.email,
                        student.phone or "—",
                        "Xem  |  Sửa  |  Xóa",
                    ),
                    tags=("even" if index % 2 == 0 else "odd",),
                )
        start = (result.page - 1) * result.page_size + 1 if total else 0
        end = min(result.page * result.page_size, total)
        self._summary.configure(text=f"{total} sinh viên")
        self._range_label.configure(text=f"Hiển thị {start}–{end} trong {total} bản ghi")
        self._page_label.configure(
            text=f"Trang {result.page} / {result.total_pages or 1}"
        )
        self._previous_button.configure(
            state="normal" if result.page > 1 else "disabled"
        )
        self._next_button.configure(
            state="normal" if result.page < result.total_pages else "disabled"
        )

    def _set_controls_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self._add_button.configure(state=state)
        self._clear_button.configure(state=state)
        self._search_entry.configure(state=state)
        self._class_combo.configure(state="readonly" if enabled else "disabled")
        if not enabled:
            self._previous_button.configure(state="disabled")
            self._next_button.configure(state="disabled")

    def _on_action_click(self, event: tk.Event) -> str | None:
        if self._tree.identify_column(event.x) != "#6":
            return None
        item = self._tree.identify_row(event.y)
        if not item:
            return None
        bounds = self._tree.bbox(item, "#6")
        if not bounds:
            return None
        relative_x = event.x - bounds[0]
        action_index = min(2, max(0, relative_x * 3 // max(bounds[2], 1)))
        self._tree.selection_set(item)
        self._tree.focus(item)
        self.after_idle(lambda: self._run_row_action(int(item), int(action_index)))
        return "break"

    def _on_double_click(self, event: tk.Event) -> None:
        item = self._tree.identify_row(event.y)
        if item:
            self._show_detail(int(item))

    def _run_row_action(self, student_id: int, action_index: int) -> None:
        if action_index == 0:
            self._show_detail(student_id)
        elif action_index == 1:
            self._open_edit(student_id)
        else:
            self._delete_student(student_id)

    def _show_detail(self, student_id: int) -> None:
        run_in_background(
            self,
            lambda: self._service.student_detail(self._session, student_id),
            lambda record: StudentDetailDialog(self, record),
            lambda error: self._feedback.configure(text=self._error_message(error)),
        )

    def _open_create(self) -> None:
        if not self._loading:
            StudentFormDialog(
                self,
                self._service,
                self._session,
                on_saved=lambda _record: self._refresh_after_save(),
            )

    def _open_edit(self, student_id: int) -> None:
        run_in_background(
            self,
            lambda: self._service.student_detail(self._session, student_id),
            lambda record: StudentFormDialog(
                self,
                self._service,
                self._session,
                record=record,
                on_saved=lambda _updated: self._refresh_after_save(),
            ),
            lambda error: self._feedback.configure(text=self._error_message(error)),
        )

    def _refresh_after_save(self) -> None:
        self._page = 1
        self._load(refresh_options=True)

    def _delete_student(self, student_id: int) -> None:
        selected = self._tree.item(str(student_id), "values")
        name = selected[1] if selected else f"ID {student_id}"
        if not messagebox.askyesno(
            "Xác nhận xóa sinh viên",
            f"Xóa hồ sơ {name} và tài khoản liên kết?\n"
            "Thao tác chỉ thực hiện được khi sinh viên chưa có bản ghi điểm.",
            parent=self,
        ):
            return
        if self._loading:
            return

        self._loading = True
        self._set_controls_enabled(False)
        run_in_background(
            self,
            lambda: self._service.delete(self._session, student_id),
            self._delete_succeeded,
            self._delete_failed,
        )

    def _delete_succeeded(self, _result: None) -> None:
        self._loading = False
        self._set_controls_enabled(True)
        self._feedback.configure(text="Đã xóa hồ sơ sinh viên và tài khoản liên kết.")
        self._page = 1
        self._load(refresh_options=True)

    def _delete_failed(self, error: BaseException) -> None:
        self._loading = False
        self._set_controls_enabled(True)
        self._feedback.configure(text=self._error_message(error))
        self._previous_button.configure(
            state="normal" if self._page > 1 else "disabled"
        )
        self._next_button.configure(
            state="normal" if self._page < self._page_count else "disabled"
        )

    @staticmethod
    def _error_message(error: BaseException) -> str:
        if isinstance(error, (ServiceError, DataAccessError)):
            return str(error)
        return f"Không thể hoàn tất thao tác: {error}"


class StudentFormDialog(tk.Toplevel):
    """Create or edit a student profile using the existing service validation."""

    def __init__(
        self,
        parent: tk.Misc,
        service: StudentService,
        session: Session,
        *,
        on_saved,
        record: StudentRecord | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._session = session
        self._record = record
        self._on_saved = on_saved
        self._busy = False
        self._fields: dict[str, ttk.Entry | ttk.Combobox] = {}
        self.title("Chỉnh sửa sinh viên" if record else "Thêm sinh viên")
        self.configure(bg=BACKGROUND)
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        self._build()
        self.geometry("660x600")
        self.after(100, self._focus_first_field)

    def _build(self) -> None:
        body = tk.Frame(self, bg=BACKGROUND)
        body.pack(fill="both", expand=True, padx=24, pady=20)
        title = "Chỉnh sửa hồ sơ sinh viên" if self._record else "Thêm sinh viên"
        tk.Label(body, text=title, bg=BACKGROUND, fg=TEXT, font=font(17, "bold")).pack(
            anchor="w"
        )
        tk.Label(
            body,
            text="Thông tin được lưu trực tiếp vào MySQL. Mã sinh viên là tên đăng nhập và không thể sửa.",
            bg=BACKGROUND,
            fg=MUTED,
            font=font(8),
            wraplength=600,
            justify="left",
        ).pack(anchor="w", pady=(4, 14))

        form = tk.Frame(body, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        form.pack(fill="both", expand=True)
        grid = tk.Frame(form, bg=SURFACE)
        grid.pack(fill="both", expand=True, padx=16, pady=14)
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)

        code = self._field(grid, "Mã sinh viên *", "student_code", 0, 0)
        if self._record:
            code.insert(0, self._record.student_code)
            code.configure(state="readonly")
        else:
            self._field(grid, "Mật khẩu ban đầu *", "password", 0, 1, show="•")
        self._field(grid, "Họ và tên *", "full_name", 1, 0)
        self._field(grid, "Lớp *", "class_name", 1, 1)
        gender = self._field(grid, "Giới tính *", "gender", 2, 0, choices=(
            ("Male", "Female", "Other")
        ))
        self._field(grid, "Ngày sinh * (YYYY-MM-DD)", "date_of_birth", 2, 1)
        self._field(grid, "Email *", "email", 3, 0)
        self._field(grid, "Số điện thoại", "phone", 3, 1)
        self._field(grid, "Năm nhập học *", "enrollment_year", 4, 0)

        if self._record:
            for key, value in (
                ("full_name", self._record.full_name),
                ("class_name", self._record.class_name),
                ("gender", self._record.gender),
                ("date_of_birth", self._record.date_of_birth.isoformat()),
                ("email", self._record.email),
                ("phone", self._record.phone or ""),
                ("enrollment_year", str(self._record.enrollment_year)),
            ):
                field = self._fields[key]
                if isinstance(field, ttk.Combobox):
                    field.set(value)
                else:
                    field.insert(0, value)
        else:
            gender.set("")
            self._fields["date_of_birth"].insert(0, "")

        self._feedback = tk.Label(
            body, text="", bg=BACKGROUND, fg=DANGER, font=font(8), anchor="w",
            wraplength=600, justify="left",
        )
        self._feedback.pack(fill="x", pady=(8, 4))

        buttons = tk.Frame(body, bg=BACKGROUND)
        buttons.pack(fill="x", pady=(8, 0))
        secondary_button(buttons, "Hủy", self.destroy).pack(side="right", padx=(8, 0))
        self._save_button = primary_button(
            buttons, "Lưu thay đổi" if self._record else "Tạo sinh viên và tài khoản",
            self._submit,
        )
        self._save_button.pack(side="right")

    def _field(
        self,
        parent: tk.Misc,
        label: str,
        key: str,
        row: int,
        column: int,
        *,
        show: str | None = None,
        choices: tuple[str, ...] | None = None,
    ):
        cell = tk.Frame(parent, bg=SURFACE)
        cell.grid(row=row, column=column, sticky="ew", padx=6, pady=6)
        tk.Label(
            cell, text=label, bg=SURFACE, fg=TEXT, font=font(8, "bold"), anchor="w"
        ).pack(fill="x", pady=(0, 4))
        if choices:
            field = ttk.Combobox(
                cell, values=choices, state="readonly", font=font(9)
            )
        else:
            field = ttk.Entry(cell, font=font(9), show=show or "")
        field.pack(fill="x", ipady=5)
        self._fields[key] = field
        return field

    def _focus_first_field(self) -> None:
        field = self._fields.get("student_code") or self._fields.get("full_name")
        if field is not None and str(field.cget("state")) != "readonly":
            field.focus_set()

    def _submit(self) -> None:
        if self._busy:
            return
        try:
            raw_date = self._fields["date_of_birth"].get().strip()
            dob = datetime.strptime(raw_date, "%Y-%m-%d").date()
            enrollment_year = int(self._fields["enrollment_year"].get().strip())
        except ValueError:
            self._feedback.configure(
                text="Ngày sinh phải theo định dạng YYYY-MM-DD và năm nhập học phải là số nguyên."
            )
            return

        values = {
            "full_name": self._fields["full_name"].get(),
            "gender": self._fields["gender"].get(),
            "date_of_birth": dob,
            "email": self._fields["email"].get(),
            "phone": self._fields["phone"].get(),
            "class_name": self._fields["class_name"].get(),
            "enrollment_year": enrollment_year,
        }
        if self._record is None:
            values["student_code"] = self._fields["student_code"].get()
            values["password"] = self._fields["password"].get()
            operation = lambda: self._service.create(self._session, **values)
        else:
            operation = lambda: self._service.update(
                self._session, self._record.student_id, **values
            )

        self._busy = True
        self._save_button.configure(state="disabled", text="Đang lưu...")
        run_in_background(
            self,
            operation,
            self._save_succeeded,
            self._save_failed,
        )

    def _save_succeeded(self, record: StudentRecord) -> None:
        self._on_saved(record)
        self.destroy()

    def _save_failed(self, error: BaseException) -> None:
        self._busy = False
        self._save_button.configure(
            state="normal", text="Lưu thay đổi" if self._record else "Tạo sinh viên và tài khoản"
        )
        self._feedback.configure(text=StudentManagementView._error_message(error))


class StudentDetailDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, record: StudentRecord) -> None:
        super().__init__(parent)
        self.title("Hồ sơ sinh viên")
        self.configure(bg=BACKGROUND)
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        body = tk.Frame(self, bg=BACKGROUND)
        body.pack(fill="both", expand=True, padx=24, pady=20)
        tk.Label(
            body, text="Hồ sơ sinh viên", bg=BACKGROUND, fg=TEXT, font=font(17, "bold")
        ).pack(anchor="w")
        tk.Label(
            body,
            text=f"{record.student_code}  ·  {record.full_name}",
            bg=BACKGROUND,
            fg=MUTED,
            font=font(9),
        ).pack(anchor="w", pady=(4, 14))

        card = tk.Frame(body, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="both", expand=True)
        profile = (
            ("Mã sinh viên", record.student_code),
            ("Họ và tên", record.full_name),
            ("Lớp", record.class_name),
            ("Ngày sinh", record.date_of_birth.strftime("%d/%m/%Y")),
            ("Giới tính", record.gender),
            ("Email", record.email),
            ("Số điện thoại", record.phone or "Chưa cập nhật"),
            ("Năm nhập học", str(record.enrollment_year)),
            ("Tài khoản liên kết", str(record.account_id)),
        )
        for index, (label, value) in enumerate(profile):
            row = tk.Frame(card, bg=SURFACE)
            row.pack(fill="x", padx=16, pady=(12 if index == 0 else 4, 0))
            tk.Label(
                row, text=label, bg=SURFACE, fg=MUTED, font=font(8), anchor="w"
            ).pack(fill="x")
            tk.Label(
                row, text=value, bg=SURFACE, fg=TEXT, font=font(9, "bold"), anchor="w"
            ).pack(fill="x", pady=(2, 0))
        secondary_button(body, "Đóng", self.destroy).pack(anchor="e", pady=(14, 0))
        self.geometry("520x590")
