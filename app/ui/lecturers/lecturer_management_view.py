"""Database-backed lecturer management page for administrators."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from app.dao.errors import DataAccessError
from app.models import Lecturer, LecturerSearchResult
from app.security.session import Session
from app.service.exceptions import ServiceError
from app.service.lecturer_service import LecturerService
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
_ALL_DEPARTMENTS = "Tất cả khoa/bộ môn"


class LecturerManagementView(tk.Frame):
    """Search, filter, page and maintain lecturer records from MySQL."""

    def __init__(
        self,
        parent: tk.Misc,
        lecturer_service: LecturerService,
        session: Session,
    ) -> None:
        super().__init__(parent, bg=BACKGROUND)
        self._service = lecturer_service
        self._session = session
        self._page = 1
        self._page_count = 0
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
            text="Quản lý giảng viên",
            bg=BACKGROUND,
            fg=TEXT,
            font=font(20, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            title_copy,
            text="Tìm kiếm, xem và quản lý hồ sơ giảng viên trong cơ sở dữ liệu.",
            bg=BACKGROUND,
            fg=MUTED,
            font=font(9),
            anchor="w",
        ).pack(fill="x", pady=(5, 0))
        self._add_button = primary_button(
            title_row, "+  Thêm giảng viên", self._open_create
        )
        self._add_button.pack(side="right", padx=(16, 0))

        stats_row = tk.Frame(page, bg=BACKGROUND)
        stats_row.pack(fill="x", pady=(20, 16))
        stats_row.grid_columnconfigure(0, weight=1, uniform="lecturer-stats")
        stats_row.grid_columnconfigure(1, weight=1, uniform="lecturer-stats")
        self._total_card, self._total_value = create_stat_card(
            stats_row, "Tổng số giảng viên"
        )
        self._department_card, self._department_value = create_stat_card(
            stats_row, "Số khoa/bộ môn"
        )
        self._total_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self._department_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

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

        self._department_var = tk.StringVar(value=_ALL_DEPARTMENTS)
        self._department_combo = ttk.Combobox(
            filter_row,
            textvariable=self._department_var,
            values=[_ALL_DEPARTMENTS],
            state="readonly",
            width=24,
            font=font(9),
        )
        self._department_combo.pack(side="left", padx=(0, 10), ipady=5)
        self._department_combo.bind("<<ComboboxSelected>>", self._filter_changed)
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
            text="Danh sách giảng viên",
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
        columns = (
            "lecturer_code",
            "full_name",
            "department",
            "email",
            "phone",
            "actions",
        )
        self._tree = ttk.Treeview(
            inner,
            columns=columns,
            show="headings",
            height=_PAGE_SIZE,
            style="Management.Treeview",
            selectmode="browse",
        )
        specs = (
            ("lecturer_code", "Mã giảng viên", 115, "w"),
            ("full_name", "Họ và tên", 170, "w"),
            ("department", "Khoa/bộ môn", 175, "w"),
            ("email", "Email", 225, "w"),
            ("phone", "Số điện thoại", 120, "w"),
            ("actions", "Thao tác", 145, "center"),
        )
        for key, label, width, anchor in specs:
            self._tree.heading(key, text=label, anchor=anchor)
            self._tree.column(
                key, width=width, minwidth=70, anchor=anchor, stretch=key == "email"
            )
        self._tree.tag_configure("odd", background="#F8FAFC")
        self._tree.bind("<Double-1>", self._on_double_click)
        self._tree.bind("<Button-1>", self._on_action_click, add="+")
        self._tree.pack(fill="both", expand=True)
        self._empty_state = tk.Label(
            inner, text="", bg=SURFACE, fg=MUTED, font=font(9), pady=14
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
        if getattr(self, "_search_after_id", None) is not None:
            self.after_cancel(self._search_after_id)
        self._search_after_id = self.after(250, self._filter_changed)

    def _filter_changed(self, _event: tk.Event | None = None) -> None:
        self._page = 1
        self._load()

    def _clear_filters(self) -> None:
        self._keyword.set("")
        self._department_var.set(_ALL_DEPARTMENTS)
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
        department = self._department_var.get()
        selected_department = (
            None if department == _ALL_DEPARTMENTS else department
        )
        keyword = self._keyword.get()
        page = self._page

        def fetch():
            result = self._service.search(
                self._session,
                keyword,
                page=page,
                page_size=_PAGE_SIZE,
                department=selected_department,
            )
            total = self._service.count_all(self._session) if refresh_options else None
            departments = (
                self._service.departments(self._session) if refresh_options else None
            )
            return result, total, departments

        run_in_background(self, fetch, self._load_succeeded, self._load_failed)

    def _load_succeeded(
        self,
        data: tuple[LecturerSearchResult, int | None, list[str] | None],
    ) -> None:
        result, total, departments = data
        self._loading = False
        self._set_controls_enabled(True)
        self._page = result.page
        self._page_count = result.total_pages
        self._render_rows(result)
        if total is not None:
            self._total_value.configure(text=str(total))
        if departments is not None:
            self._department_value.configure(text=str(len(departments)))
            values = [_ALL_DEPARTMENTS, *departments]
            self._department_combo.configure(values=values)
            if self._department_var.get() not in values:
                self._department_var.set(_ALL_DEPARTMENTS)

    def _load_failed(self, error: BaseException) -> None:
        self._loading = False
        self._set_controls_enabled(True)
        self._tree.delete(*self._tree.get_children())
        self._total_value.configure(text="—")
        self._department_value.configure(text="—")
        self._summary.configure(text="Không tải được dữ liệu")
        self._empty_state.configure(text="Không thể tải danh sách giảng viên.")
        self._range_label.configure(text="")
        self._page_label.configure(text="Trang —")
        self._page_count = 0
        self._previous_button.configure(state="disabled")
        self._next_button.configure(state="disabled")
        self._feedback.configure(text=self._error_message(error))

    def _render_rows(self, result: LecturerSearchResult) -> None:
        self._tree.delete(*self._tree.get_children())
        if not result.items:
            self._empty_state.configure(text="Chưa có giảng viên phù hợp.")
        else:
            self._empty_state.configure(text="")
            for index, lecturer in enumerate(result.items):
                self._tree.insert(
                    "",
                    "end",
                    iid=str(lecturer.lecturer_id),
                    values=(
                        lecturer.lecturer_code,
                        lecturer.full_name,
                        lecturer.department,
                        lecturer.email,
                        lecturer.phone,
                        "Xem  |  Sửa  |  Xóa",
                    ),
                    tags=("odd",) if index % 2 else (),
                )
        total = result.total_count
        start = (result.page - 1) * result.page_size + 1 if total else 0
        end = min(result.page * result.page_size, total)
        self._summary.configure(text=f"{total} giảng viên")
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
        self._department_combo.configure(state="readonly" if enabled else "disabled")
        if not enabled:
            self._previous_button.configure(state="disabled")
            self._next_button.configure(state="disabled")

    def _on_action_click(self, event: tk.Event) -> str | None:
        if self._tree.identify_column(event.x) != "#7":
            return None
        item = self._tree.identify_row(event.y)
        if not item:
            return None
        bounds = self._tree.bbox(item, "#7")
        if not bounds:
            return None
        relative_x = event.x - bounds[0]
        action_index = min(2, max(0, relative_x * 3 // max(bounds[2], 1)))
        self._tree.selection_set(item)
        self._tree.focus(item)
        self.after_idle(lambda: self._run_row_action(str(item), int(action_index)))
        return "break"

    def _on_double_click(self, event: tk.Event) -> None:
        if self._tree.identify_column(event.x) != "#7":
            item = self._tree.identify_row(event.y)
            if item:
                self._show_detail(str(item))

    def _run_row_action(self, lecturer_id: str, action_index: int) -> None:
        if action_index == 0:
            self._show_detail(lecturer_id)
        elif action_index == 1:
            self._open_edit(lecturer_id)
        else:
            self._delete_lecturer(lecturer_id)

    def _show_detail(self, lecturer_id: str) -> None:
        run_in_background(
            self,
            lambda: self._service.get_by_id(self._session, lecturer_id),
            lambda record: LecturerDetailDialog(self, record),
            lambda error: self._feedback.configure(text=self._error_message(error)),
        )

    def _open_create(self) -> None:
        if not self._loading:
            LecturerFormDialog(
                self,
                self._service,
                self._session,
                on_saved=lambda _record: self._refresh_after_save(),
            )

    def _open_edit(self, lecturer_id: str) -> None:
        run_in_background(
            self,
            lambda: self._service.get_by_id(self._session, lecturer_id),
            lambda record: LecturerFormDialog(
                self,
                self._service,
                self._session,
                record=record,
                on_saved=lambda _updated: self._refresh_after_save(),
            ),
            lambda error: self._feedback.configure(text=self._error_message(error)),
        )

    def _delete_lecturer(self, lecturer_id: str) -> None:
        values = self._tree.item(str(lecturer_id), "values")
        name = values[1] if values else lecturer_id
        if not messagebox.askyesno(
            "Xác nhận xóa giảng viên",
            f"Xóa hồ sơ {name} và tài khoản liên kết?\n"
            "Không thể xóa giảng viên đang phụ trách học phần.",
            parent=self,
        ):
            return
        if self._loading:
            return
        self._loading = True
        self._set_controls_enabled(False)
        run_in_background(
            self,
            lambda: self._service.delete(self._session, lecturer_id),
            self._delete_succeeded,
            self._delete_failed,
        )

    def _delete_succeeded(self, _result: None) -> None:
        self._loading = False
        self._set_controls_enabled(True)
        self._feedback.configure(text="Đã xóa hồ sơ giảng viên và tài khoản liên kết.")
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

    def _refresh_after_save(self) -> None:
        self._page = 1
        self._load(refresh_options=True)

    @staticmethod
    def _error_message(error: BaseException) -> str:
        if isinstance(error, (ServiceError, DataAccessError)):
            return str(error)
        return f"Không thể hoàn tất thao tác: {error}"


class LecturerFormDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        service: LecturerService,
        session: Session,
        *,
        on_saved,
        record: Lecturer | None = None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._session = session
        self._record = record
        self._on_saved = on_saved
        self._busy = False
        self._fields: dict[str, ttk.Entry | ttk.Combobox] = {}
        self.title("Chỉnh sửa giảng viên" if record else "Thêm giảng viên")
        self.configure(bg=BACKGROUND)
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        self._build()
        self.geometry("660x500")

    def _build(self) -> None:
        body = tk.Frame(self, bg=BACKGROUND)
        body.pack(fill="both", expand=True, padx=24, pady=20)
        tk.Label(
            body,
            text="Chỉnh sửa hồ sơ giảng viên" if self._record else "Thêm giảng viên",
            bg=BACKGROUND,
            fg=TEXT,
            font=font(17, "bold"),
        ).pack(anchor="w")
        tk.Label(
            body,
            text="Tạo giảng viên sẽ tạo luôn tài khoản Giảng viên (tên đăng nhập = mã giảng viên) trong cùng một giao dịch.",
            bg=BACKGROUND,
            fg=MUTED,
            font=font(8),
        ).pack(anchor="w", pady=(4, 12))

        card = tk.Frame(body, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="both", expand=True)
        grid = tk.Frame(card, bg=SURFACE)
        grid.pack(fill="both", expand=True, padx=14, pady=12)
        grid.grid_columnconfigure(0, weight=1)
        grid.grid_columnconfigure(1, weight=1)

        self._field(grid, "Mã giảng viên * (cũng là tên đăng nhập)", "lecturer_id", 0, 0)
        if self._record is None:
            self._field(grid, "Mật khẩu ban đầu *", "password", 0, 1, show="•")
        self._field(grid, "Họ và tên *", "full_name", 1, 0)
        self._field(grid, "Khoa/bộ môn *", "department", 1, 1)
        self._field(grid, "Email *", "email", 2, 0)
        self._field(grid, "Số điện thoại *", "phone", 2, 1)
        if self._record:
            self._fields["lecturer_id"].insert(0, self._record.lecturer_id)
            self._fields["lecturer_id"].configure(state="readonly")  # mã giảng viên bất biến
            for key, value in (
                ("full_name", self._record.full_name),
                ("email", self._record.email),
                ("phone", self._record.phone),
                ("department", self._record.department),
            ):
                field = self._fields[key]
                if isinstance(field, ttk.Combobox):
                    field.set(value)
                else:
                    field.insert(0, value)

        self._feedback = tk.Label(
            body, text="", bg=BACKGROUND, fg=DANGER, font=font(8), anchor="w",
            wraplength=600, justify="left",
        )
        self._feedback.pack(fill="x", pady=(8, 4))
        buttons = tk.Frame(body, bg=BACKGROUND)
        buttons.pack(fill="x", pady=(8, 0))
        secondary_button(buttons, "Hủy", self.destroy).pack(side="right", padx=(8, 0))
        self._save_button = primary_button(
            buttons,
            "Lưu thay đổi" if self._record else "Tạo giảng viên và tài khoản",
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
    ) -> None:
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

    def _submit(self) -> None:
        if self._busy:
            return
        values = {
            "full_name": self._fields["full_name"].get(),
            "email": self._fields["email"].get(),
            "phone": self._fields["phone"].get(),
            "department": self._fields["department"].get(),
        }
        if self._record is None:
            values["lecturer_id"] = self._fields["lecturer_id"].get()
            values["password"] = self._fields["password"].get()
            operation = lambda: self._service.create(self._session, **values)
        else:
            operation = lambda: self._service.update(
                self._session, self._record.lecturer_id, **values
            )
        self._busy = True
        self._save_button.configure(state="disabled", text="Đang lưu...")
        run_in_background(
            self, operation, self._save_succeeded, self._save_failed
        )

    def _save_succeeded(self, record: Lecturer) -> None:
        self._on_saved(record)
        self.destroy()

    def _save_failed(self, error: BaseException) -> None:
        self._busy = False
        self._save_button.configure(
            state="normal",
            text="Lưu thay đổi" if self._record else "Tạo giảng viên và tài khoản",
        )
        self._feedback.configure(text=LecturerManagementView._error_message(error))


class LecturerDetailDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, record: Lecturer) -> None:
        super().__init__(parent)
        self.title("Hồ sơ giảng viên")
        self.configure(bg=BACKGROUND)
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        body = tk.Frame(self, bg=BACKGROUND)
        body.pack(fill="both", expand=True, padx=24, pady=20)
        tk.Label(
            body, text="Hồ sơ giảng viên", bg=BACKGROUND, fg=TEXT, font=font(17, "bold")
        ).pack(anchor="w")
        tk.Label(
            body,
            text=f"{record.lecturer_code}  ·  {record.full_name}",
            bg=BACKGROUND,
            fg=MUTED,
            font=font(9),
        ).pack(anchor="w", pady=(4, 14))
        card = tk.Frame(body, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="both", expand=True)
        fields = (
            ("Mã giảng viên", record.lecturer_id),
            ("Họ và tên", record.full_name),
            ("Khoa/bộ môn", record.department),
            ("Email", record.email),
            ("Số điện thoại", record.phone),
            ("Tên đăng nhập", record.lecturer_id),
        )
        for index, (label, value) in enumerate(fields):
            row = tk.Frame(card, bg=SURFACE)
            row.pack(fill="x", padx=16, pady=(12 if index == 0 else 4, 0))
            tk.Label(
                row, text=label, bg=SURFACE, fg=MUTED, font=font(8), anchor="w"
            ).pack(fill="x")
            tk.Label(
                row, text=value, bg=SURFACE, fg=TEXT, font=font(9, "bold"), anchor="w"
            ).pack(fill="x", pady=(2, 0))
        secondary_button(body, "Đóng", self.destroy).pack(anchor="e", pady=(14, 0))
        self.geometry("520x470")
