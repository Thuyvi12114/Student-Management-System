"""UI 1.3 / 1.14 - Hồ sơ cá nhân (UC-03) và cập nhật thông tin liên hệ của sinh viên (UC-08).

Sinh viên: xem hồ sơ, chỉ sửa email / số điện thoại / địa chỉ.
Giảng viên: hồ sơ chỉ đọc.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from app.dao.errors import DataAccessError
from app.models import Lecturer, Role, StudentRecord
from app.security.session import Session
from app.service.auth_service import AuthService
from app.service.exceptions import ServiceError
from app.service.profile_service import ProfileService
from app.ui.change_password_dialog import ChangePasswordDialog
from app.ui.management.widgets import run_in_background
from app.ui.theme import (
    BACKGROUND, BORDER, DANGER, MUTED, SUCCESS, SURFACE, TEXT,
    font, primary_button, secondary_button,
)


def _message(error: BaseException) -> str:
    if isinstance(error, (ServiceError, DataAccessError)):
        return str(error)
    return f"Không thể hoàn tất thao tác: {error}"


class ProfileView(tk.Frame):
    def __init__(self, parent: tk.Misc, service: ProfileService, auth_service: AuthService, session: Session) -> None:
        super().__init__(parent, bg=BACKGROUND)
        self._service = service
        self._auth = auth_service
        self._session = session
        self._profile: StudentRecord | Lecturer | None = None
        self._editing = False
        self._busy = False
        self._contact_vars: dict[str, tk.StringVar] = {}

        self._page = tk.Frame(self, bg=BACKGROUND)
        self._page.pack(fill="both", expand=True, padx=32, pady=24)
        tk.Label(self._page, text="Hồ sơ cá nhân", bg=BACKGROUND, fg=TEXT, font=font(20, "bold"), anchor="w").pack(fill="x")
        subtitle = (
            "Bạn chỉ có thể sửa email, số điện thoại và địa chỉ. Các thông tin khác do quản trị viên quản lý."
            if session.role is Role.STUDENT
            else "Thông tin giảng viên chỉ được xem; liên hệ quản trị viên nếu cần chỉnh sửa."
        )
        tk.Label(self._page, text=subtitle, bg=BACKGROUND, fg=MUTED, font=font(9), anchor="w").pack(fill="x", pady=(5, 14))
        self._card = tk.Frame(self._page, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        self._card.pack(fill="x")
        self._feedback = tk.Label(self._page, text="", bg=BACKGROUND, fg=DANGER, font=font(9), anchor="w", wraplength=760, justify="left")
        self._feedback.pack(fill="x", pady=(10, 0))
        self._load()

    # ------------------------------------------------------------------ dữ liệu
    def _load(self) -> None:
        self._feedback.configure(text="", fg=DANGER)
        run_in_background(self, lambda: self._service.my_profile(self._session), self._loaded, self._failed)

    def _loaded(self, profile: StudentRecord | Lecturer) -> None:
        self._profile = profile
        self._editing = False
        self._render()

    def _failed(self, error: BaseException) -> None:
        self._busy = False
        self._feedback.configure(text=_message(error), fg=DANGER)

    # ------------------------------------------------------------------ hiển thị
    def _render(self) -> None:
        for child in self._card.winfo_children():
            child.destroy()
        profile = self._profile
        inner = tk.Frame(self._card, bg=SURFACE)
        inner.pack(fill="x", padx=24, pady=20)
        inner.grid_columnconfigure((0, 1), weight=1, uniform="profile")

        if isinstance(profile, StudentRecord):
            readonly = [
                ("Mã sinh viên", profile.student_id), ("Họ và tên", profile.full_name),
                ("Ngày sinh", profile.date_of_birth.strftime("%d/%m/%Y")), ("Giới tính", profile.gender),
                ("Lớp", profile.class_name), ("Tên đăng nhập", self._session.username),
            ]
            contact = [("email", "Email", profile.email), ("phone", "Số điện thoại", profile.phone),
                       ("address", "Địa chỉ", profile.address or "")]
        else:
            assert isinstance(profile, Lecturer)
            readonly = [
                ("Mã giảng viên", profile.lecturer_id), ("Họ và tên", profile.full_name),
                ("Khoa/bộ môn", profile.department), ("Tên đăng nhập", self._session.username),
                ("Email", profile.email), ("Số điện thoại", profile.phone),
            ]
            contact = []

        row = 0
        for index, (label, value) in enumerate(readonly):
            self._info_cell(inner, label, value).grid(row=index // 2, column=index % 2, sticky="ew", padx=6, pady=6)
            row = index // 2 + 1

        if contact:
            tk.Frame(inner, bg=BORDER, height=1).grid(row=row, column=0, columnspan=2, sticky="ew", pady=(10, 4))
            tk.Label(inner, text="Thông tin liên hệ", bg=SURFACE, fg=TEXT, font=font(10, "bold"), anchor="w").grid(
                row=row + 1, column=0, columnspan=2, sticky="w", padx=6)
            self._contact_vars = {}
            for index, (key, label, value) in enumerate(contact):
                cell = tk.Frame(inner, bg=SURFACE)
                cell.grid(row=row + 2 + index // 2, column=index % 2, sticky="ew", padx=6, pady=6)
                tk.Label(cell, text=label, bg=SURFACE, fg=MUTED, font=font(8), anchor="w").pack(fill="x")
                if self._editing:
                    var = tk.StringVar(value=value)
                    self._contact_vars[key] = var
                    ttk.Entry(cell, textvariable=var, font=font(9)).pack(fill="x", ipady=5, pady=(3, 0))
                else:
                    tk.Label(cell, text=value or "Chưa cập nhật", bg=SURFACE, fg=TEXT, font=font(10, "bold"), anchor="w").pack(fill="x", pady=(3, 0))
            row += 2 + (len(contact) + 1) // 2

        buttons = tk.Frame(inner, bg=SURFACE)
        buttons.grid(row=row + 1, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        secondary_button(buttons, "Đổi mật khẩu", lambda: ChangePasswordDialog(self.winfo_toplevel(), self._auth)).pack(side="left")
        if contact and not self._editing:
            self._edit_button = primary_button(buttons, "Chỉnh sửa thông tin liên hệ", self._start_edit)
            self._edit_button.pack(side="right")
        elif contact:
            self._save_button = primary_button(buttons, "Lưu", self._save)
            self._save_button.pack(side="right")
            secondary_button(buttons, "Hủy", self._cancel).pack(side="right", padx=(0, 8))

    @staticmethod
    def _info_cell(parent: tk.Misc, label: str, value: str) -> tk.Frame:
        cell = tk.Frame(parent, bg=SURFACE)
        tk.Label(cell, text=label, bg=SURFACE, fg=MUTED, font=font(8), anchor="w").pack(fill="x")
        tk.Label(cell, text=value, bg=SURFACE, fg=TEXT, font=font(10, "bold"), anchor="w").pack(fill="x", pady=(3, 0))
        return cell

    # ------------------------------------------------------------------ sửa liên hệ (UC-08)
    def _start_edit(self) -> None:
        self._editing = True
        self._feedback.configure(text="")
        self._render()

    def _cancel(self) -> None:  # AF2: hủy → bỏ thay đổi
        self._editing = False
        self._feedback.configure(text="")
        self._render()

    def _save(self) -> None:
        if self._busy:
            return
        values = {key: var.get() for key, var in self._contact_vars.items()}
        self._busy = True
        self._save_button.configure(state="disabled", text="Đang lưu...")
        run_in_background(
            self,
            lambda: self._service.update_contact(
                self._session, email=values["email"], phone=values["phone"], address=values["address"]
            ),
            self._saved,
            self._save_failed,
        )

    def _saved(self, profile: StudentRecord) -> None:
        self._busy = False
        self._profile = profile
        self._editing = False
        self._render()
        self._feedback.configure(text="Đã cập nhật thông tin liên hệ.", fg=SUCCESS)

    def _save_failed(self, error: BaseException) -> None:  # AF1: dữ liệu sai → giữ form để sửa
        self._busy = False
        self._save_button.configure(state="normal", text="Lưu")
        self._feedback.configure(text=_message(error), fg=DANGER)
