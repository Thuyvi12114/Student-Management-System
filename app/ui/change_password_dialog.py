"""Hộp thoại đổi mật khẩu cho tài khoản đang đăng nhập."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox

from app.dao.errors import DataAccessError
from app.service.auth_service import AuthService
from app.service.exceptions import ServiceError
from app.ui.theme import (
    BACKGROUND,
    DANGER,
    DISABLED,
    MUTED,
    PRIMARY,
    SURFACE,
    TEXT,
    font,
    primary_button,
    secondary_button,
    text_field,
)


class ChangePasswordDialog(tk.Toplevel):
    """Cửa sổ modal đổi mật khẩu."""

    def __init__(self, parent: tk.Misc, auth_service: AuthService) -> None:
        super().__init__(parent)
        self.auth_service = auth_service
        self._busy = False

        self.title("Đổi mật khẩu")
        self.configure(bg=SURFACE)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self._build()
        self.update_idletasks()

        width, height = 500, 560
        x = parent.winfo_rootx() + max((parent.winfo_width() - width) // 2, 0)
        y = parent.winfo_rooty() + max((parent.winfo_height() - height) // 2, 0)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.after(120, self.current_entry.focus_set)

    def _build(self) -> None:
        actions = tk.Frame(self, bg=SURFACE)
        actions.pack(side="bottom", fill="x", padx=28, pady=(0, 22))

        self.save_button = primary_button(actions, "Cập nhật mật khẩu", self._submit)
        self.save_button.pack(side="right")
        self.cancel_button = secondary_button(actions, "Hủy", self.destroy)
        self.cancel_button.pack(side="right", padx=(0, 10))

        body = tk.Frame(self, bg=SURFACE)
        body.pack(fill="both", expand=True, padx=28, pady=(24, 12))

        tk.Label(
            body,
            text="BẢO MẬT TÀI KHOẢN",
            bg=SURFACE,
            fg=PRIMARY,
            font=font(7, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            body,
            text="Đổi mật khẩu",
            bg=SURFACE,
            fg=TEXT,
            font=font(17, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(4, 4))
        tk.Label(
            body,
            text=(
                "Mật khẩu mới cần tối thiểu 8 ký tự, gồm chữ hoa, chữ thường và chữ số; "
                "không trùng mật khẩu hiện tại."
            ),
            bg=SURFACE,
            fg=MUTED,
            font=font(9),
            anchor="w",
            justify="left",
            wraplength=420,
        ).pack(fill="x", pady=(0, 18))

        self.current_entry = self._field(body, "Mật khẩu hiện tại")
        self.new_entry = self._field(body, "Mật khẩu mới")
        self.confirm_entry = self._field(body, "Xác nhận mật khẩu mới")

        self.show_password = tk.BooleanVar(value=False)
        tk.Checkbutton(
            body,
            text="Hiện mật khẩu",
            variable=self.show_password,
            command=self._toggle_password,
            bg=SURFACE,
            fg=MUTED,
            activebackground=SURFACE,
            activeforeground=MUTED,
            selectcolor=SURFACE,
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=font(9),
            anchor="w",
            cursor="hand2",
        ).pack(fill="x")

        feedback_holder = tk.Frame(body, bg=SURFACE, height=38)
        feedback_holder.pack(fill="x")
        feedback_holder.pack_propagate(False)
        self.feedback = tk.Label(
            feedback_holder,
            text="",
            bg=SURFACE,
            fg=DANGER,
            font=font(9),
            anchor="nw",
            justify="left",
            wraplength=420,
        )
        self.feedback.pack(fill="both", expand=True)

    def _field(self, parent: tk.Misc, label_text: str) -> tk.Entry:
        tk.Label(
            parent,
            text=label_text,
            bg=SURFACE,
            fg=TEXT,
            font=font(9, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 6))
        wrapper, entry = text_field(parent, show="•")
        wrapper.pack(fill="x", pady=(0, 12))
        return entry

    def _toggle_password(self) -> None:
        show = "" if self.show_password.get() else "•"
        for entry in (self.current_entry, self.new_entry, self.confirm_entry):
            entry.configure(show=show)

    def _submit(self) -> None:
        if self._busy:
            return
        current_password = self.current_entry.get()
        new_password = self.new_entry.get()
        confirm_password = self.confirm_entry.get()

        self._set_busy(True)
        self.feedback.configure(text="")

        def worker() -> None:
            try:
                self.auth_service.change_password(current_password, new_password, confirm_password)
            except Exception as exc:
                self._post(lambda error=exc: self._finish_error(error))
            else:
                self._post(self._finish_success)

        threading.Thread(target=worker, daemon=True).start()

    def _post(self, callback) -> None:
        try:
            self.after(0, callback)
        except tk.TclError:
            pass

    def _finish_success(self) -> None:
        self._set_busy(False)
        messagebox.showinfo(
            "Thành công",
            "Mật khẩu đã được cập nhật thành công.",
            parent=self,
        )
        self.destroy()

    def _finish_error(self, error: BaseException) -> None:
        self._set_busy(False)
        if isinstance(error, (ServiceError, DataAccessError)):
            message = str(error)
        else:
            message = f"Không thể đổi mật khẩu: {error}"
        self.feedback.configure(text=message)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        state = "disabled" if busy else "normal"
        for entry in (self.current_entry, self.new_entry, self.confirm_entry):
            entry.configure(state=state)
        self.cancel_button.configure(state=state)
        self.save_button.configure(
            state=state,
            text="Đang cập nhật..." if busy else "Cập nhật mật khẩu",
            bg=DISABLED if busy else PRIMARY,
            activebackground=DISABLED if busy else "#1E40AF",
        )
