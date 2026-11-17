"""UI 1.12 - Quản lý tài khoản (UC-07, Module 2): xem, lọc, khóa/mở khóa, đặt lại mật khẩu."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from app.models import AccountStatus, AccountSummary, Role
from app.security.session import Session
from app.dao.errors import DataAccessError
from app.service.account_service import AccountService
from app.service.exceptions import ServiceError
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
    SURFACE,
    TEXT,
    font,
    primary_button,
    secondary_button,
)

_ALL_ROLES = "Tất cả vai trò"
_ALL_STATUSES = "Tất cả trạng thái"


class AccountManagementView(tk.Frame):
    """Search accounts and change active status without exposing credentials."""

    def __init__(
        self,
        parent: tk.Misc,
        service: AccountService,
        session: Session,
    ) -> None:
        super().__init__(parent, bg=BACKGROUND)
        self._service = service
        self._session = session
        self._accounts: list[AccountSummary] = []
        self._selected: AccountSummary | None = None
        self._build()
        self._load()

    def _build(self) -> None:
        page = tk.Frame(self, bg=BACKGROUND)
        page.pack(fill="both", expand=True, padx=32, pady=24)

        tk.Label(
            page,
            text="Tài khoản và phân quyền",
            bg=BACKGROUND,
            fg=TEXT,
            font=font(20, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            page,
            text="Tài khoản được tạo/xóa cùng hồ sơ sinh viên, giảng viên. Tại đây chỉ khóa, mở khóa và đặt lại mật khẩu.",
            bg=BACKGROUND,
            fg=MUTED,
            font=font(9),
            anchor="w",
        ).pack(fill="x", pady=(5, 0))

        stats = tk.Frame(page, bg=BACKGROUND)
        stats.pack(fill="x", pady=(20, 16))
        for column in range(3):
            stats.grid_columnconfigure(column, weight=1, uniform="account-stats")
        stat_cards = [
            create_stat_card(stats, "Tổng tài khoản"),
            create_stat_card(stats, "Đang hoạt động"),
            create_stat_card(stats, "Đang khóa"),
        ]
        self._total_value, self._active_value, self._inactive_value = (
            value for _card, value in stat_cards
        )
        for column, (card, _value) in enumerate(stat_cards):
            card.grid(row=0, column=column, sticky="nsew", padx=6)

        filters = tk.Frame(page, bg=BACKGROUND)
        filters.pack(fill="x", pady=(0, 14))
        search_wrap = tk.Frame(
            filters, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1
        )
        search_wrap.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self._keyword = tk.StringVar()
        entry = ttk.Entry(search_wrap, textvariable=self._keyword, font=font(9))
        entry.pack(fill="x", padx=10, pady=8)
        entry.bind("<KeyRelease>", self._apply_filters)

        self._role = tk.StringVar(value=_ALL_ROLES)
        role_combo = ttk.Combobox(
            filters,
            textvariable=self._role,
            values=[_ALL_ROLES, Role.STUDENT.label, Role.LECTURER.label],
            state="readonly",
            width=18,
            font=font(9),
        )
        role_combo.pack(side="left", padx=(0, 8), ipady=5)
        role_combo.bind("<<ComboboxSelected>>", self._apply_filters)

        self._status = tk.StringVar(value=_ALL_STATUSES)
        status_combo = ttk.Combobox(
            filters,
            textvariable=self._status,
            values=[_ALL_STATUSES, "Đang hoạt động", "Đang khóa"],
            state="readonly",
            width=18,
            font=font(9),
        )
        status_combo.pack(side="left", padx=(0, 8), ipady=5)
        status_combo.bind("<<ComboboxSelected>>", self._apply_filters)
        secondary_button(filters, "Tải lại", self._load).pack(side="left")

        card = tk.Frame(page, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="both", expand=True)
        inner = tk.Frame(card, bg=SURFACE)
        inner.pack(fill="both", expand=True, padx=18, pady=16)
        heading = tk.Frame(inner, bg=SURFACE)
        heading.pack(fill="x", pady=(0, 10))
        tk.Label(
            heading, text="Danh sách tài khoản", bg=SURFACE, fg=TEXT,
            font=font(11, "bold"), anchor="w",
        ).pack(side="left")
        self._count = tk.Label(heading, text="Đang tải...", bg=SURFACE, fg=MUTED, font=font(8))
        self._count.pack(side="right")

        configure_management_table(inner)
        columns = ("account_id", "username", "full_name", "role", "status")
        self._tree = ttk.Treeview(
            inner, columns=columns, show="headings", height=12,
            style="Management.Treeview", selectmode="browse",
        )
        for key, label, width in (
            ("account_id", "Mã", 70),
            ("username", "Tên đăng nhập", 180),
            ("full_name", "Họ và tên", 260),
            ("role", "Vai trò", 180),
            ("status", "Trạng thái", 140),
        ):
            self._tree.heading(key, text=label, anchor="w")
            self._tree.column(key, width=width, minwidth=60, anchor="w")
        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        self._tree.pack(fill="both", expand=True)

        self._empty = tk.Label(inner, text="", bg=SURFACE, fg=MUTED, font=font(9), pady=12)
        self._empty.pack(fill="x")
        action_row = tk.Frame(inner, bg=SURFACE)
        action_row.pack(fill="x", pady=(10, 0))
        self._action = primary_button(action_row, "Khóa tài khoản", self._toggle_status)
        self._action.pack(side="right")
        self._reset = secondary_button(action_row, "Đặt lại mật khẩu", self._open_reset)
        self._reset.pack(side="right", padx=(0, 8))
        self._reset.configure(state="disabled")
        self._feedback = tk.Label(
            page, text="", bg=BACKGROUND, fg=DANGER, font=font(9), anchor="w"
        )
        self._feedback.pack(fill="x", pady=(8, 0))

    def _load(self) -> None:
        self._count.configure(text="Đang tải...")
        run_in_background(
            self,
            lambda: self._service.list_accounts(self._session),
            self._loaded,
            self._failed,
        )

    def _loaded(self, accounts: list[AccountSummary]) -> None:
        self._accounts = accounts
        active = sum(account.status is AccountStatus.ACTIVE for account in accounts)
        # Cards are kept as labels to avoid recomputing counts from filtered rows.
        self._total_value.configure(text=str(len(accounts)))
        self._active_value.configure(text=str(active))
        self._inactive_value.configure(text=str(len(accounts) - active))
        self._feedback.configure(text="")
        self._apply_filters()

    def _failed(self, error: BaseException) -> None:
        self._accounts = []
        self._tree.delete(*self._tree.get_children())
        self._total_value.configure(text="—")
        self._active_value.configure(text="—")
        self._inactive_value.configure(text="—")
        self._count.configure(text="Không tải được dữ liệu")
        self._feedback.configure(text=f"Không tải được tài khoản: {error}")

    def _apply_filters(self, _event: tk.Event | None = None) -> None:
        keyword = self._keyword.get().strip().casefold()
        role_label = self._role.get()
        status_label = self._status.get()
        filtered = [
            account
            for account in self._accounts
            if (
                not keyword
                or keyword in account.username.casefold()
                or keyword in account.full_name.casefold()
            )
            and (role_label == _ALL_ROLES or account.role.label == role_label)
            and (
                status_label == _ALL_STATUSES
                or _status_text(account.status) == status_label
            )
        ]
        self._tree.delete(*self._tree.get_children())
        self._selected = None
        for account in filtered:
            self._tree.insert(
                "", "end", iid=str(account.account_id),
                values=(
                    account.account_id,
                    account.username,
                    account.full_name,
                    account.role.label,
                    _status_text(account.status),
                ),
            )
        self._count.configure(text=f"{len(filtered)} tài khoản")
        self._empty.configure(
            text="Không tìm thấy tài khoản phù hợp." if not filtered else ""
        )
        self._action.configure(state="disabled")
        self._reset.configure(state="disabled")

    def _on_select(self, _event: tk.Event | None = None) -> None:
        selection = self._tree.selection()
        account_id = int(selection[0]) if selection else None
        self._selected = next(
            (account for account in self._accounts if account.account_id == account_id),
            None,
        )
        if self._selected is None:
            self._action.configure(state="disabled")
            self._reset.configure(state="disabled")
            return
        self._reset.configure(state="normal")
        self._feedback.configure(text="")
        label = (
            "Mở khóa tài khoản"
            if self._selected.status is AccountStatus.INACTIVE
            else "Khóa tài khoản"
        )
        self._action.configure(text=label, state="normal")

    def _toggle_status(self) -> None:
        account = self._selected
        if account is None:
            return
        target = (
            AccountStatus.ACTIVE
            if account.status is AccountStatus.INACTIVE
            else AccountStatus.INACTIVE
        )
        action = "mở khóa" if target is AccountStatus.ACTIVE else "khóa"
        if not messagebox.askyesno(
            "Xác nhận cập nhật",
            f"Bạn có chắc muốn {action} tài khoản {account.username}?\n"
            "Hồ sơ cá nhân của tài khoản này được giữ nguyên.",
            parent=self,
        ):
            return
        self._action.configure(state="disabled")

        def update() -> None:
            self._service.set_account_status(self._session, account.account_id, target)

        def updated(_result: None) -> None:
            self._selected = None
            self._load()

        def failed(error: BaseException) -> None:
            self._action.configure(state="normal")
            self._feedback.configure(text=_message(error))

        run_in_background(self, update, updated, failed)


    def _open_reset(self) -> None:
        account = self._selected
        if account is not None:
            ResetPasswordDialog(self, self._service, self._session, account, on_done=self._reset_done)

    def _reset_done(self, username: str) -> None:
        self._feedback.configure(text=f"Đã đặt lại mật khẩu cho tài khoản {username}.", fg="#15803D")


def _message(error: BaseException) -> str:
    if isinstance(error, (ServiceError, DataAccessError)):
        return str(error)
    return f"Không thể hoàn tất thao tác: {error}"


class ResetPasswordDialog(tk.Toplevel):
    """UC-07 luồng b: quản trị viên nhập mật khẩu mới cho tài khoản được chọn."""

    def __init__(self, parent: tk.Misc, service: AccountService, session: Session, account: AccountSummary, *, on_done) -> None:
        super().__init__(parent)
        self._service, self._session, self._account, self._on_done = service, session, account, on_done
        self._busy = False
        self.title("Đặt lại mật khẩu")
        self.configure(bg=BACKGROUND)
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        body = tk.Frame(self, bg=BACKGROUND)
        body.pack(fill="both", expand=True, padx=24, pady=20)
        tk.Label(body, text="Đặt lại mật khẩu", bg=BACKGROUND, fg=TEXT, font=font(17, "bold")).pack(anchor="w")
        tk.Label(body, text=f"{account.username}  ·  {account.full_name}", bg=BACKGROUND, fg=MUTED, font=font(9)).pack(anchor="w", pady=(4, 12))
        self._password = tk.StringVar()
        self._confirm = tk.StringVar()
        for label, var in (("Mật khẩu mới", self._password), ("Nhập lại mật khẩu mới", self._confirm)):
            tk.Label(body, text=label, bg=BACKGROUND, fg=TEXT, font=font(8, "bold"), anchor="w").pack(fill="x", pady=(6, 3))
            entry = ttk.Entry(body, textvariable=var, show="•", font=font(9), width=40)
            entry.pack(fill="x", ipady=5)
            if var is self._password:
                self._first = entry
        tk.Label(body, text="Tối thiểu 8 ký tự, có chữ hoa, chữ thường, chữ số, không chứa khoảng trắng.",
                 bg=BACKGROUND, fg=MUTED, font=font(8), wraplength=360, justify="left").pack(anchor="w", pady=(6, 0))
        self._feedback = tk.Label(body, text="", bg=BACKGROUND, fg=DANGER, font=font(8), anchor="w", wraplength=360, justify="left")
        self._feedback.pack(fill="x", pady=(8, 0))
        buttons = tk.Frame(body, bg=BACKGROUND)
        buttons.pack(fill="x", pady=(10, 0))
        secondary_button(buttons, "Hủy", self.destroy).pack(side="right", padx=(8, 0))
        self._save = primary_button(buttons, "Lưu mật khẩu mới", self._submit)
        self._save.pack(side="right")
        self.after(100, self._first.focus_set)

    def _submit(self) -> None:
        if self._busy:
            return
        if self._password.get() != self._confirm.get():
            self._feedback.configure(text="Hai mật khẩu nhập vào không khớp.")
            return
        password = self._password.get()
        self._busy = True
        self._save.configure(state="disabled", text="Đang lưu...")

        def done(_result: None) -> None:
            self._on_done(self._account.username)
            self.destroy()

        def failed(error: BaseException) -> None:
            self._busy = False
            self._save.configure(state="normal", text="Lưu mật khẩu mới")
            self._feedback.configure(text=_message(error))

        run_in_background(
            self,
            lambda: self._service.reset_password(self._session, self._account.account_id, password),
            done,
            failed,
        )


def _status_text(status: AccountStatus) -> str:
    return "Đang hoạt động" if status is AccountStatus.ACTIVE else "Đang khóa"
