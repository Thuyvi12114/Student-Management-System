"""Màn hình đăng nhập (UI 1.1).

Chỉ gọi xuống tầng service, không truy cập trực tiếp DAO hay cơ sở dữ liệu.
"""

from __future__ import annotations

import threading
import tkinter as tk

from app.dao.errors import DataAccessError
from app.security.session import Session
from app.service.auth_service import AuthService
from app.service.exceptions import ServiceError
from app.ui.theme import (
    BACKGROUND,
    BORDER,
    DANGER,
    DISABLED,
    MUTED,
    PRIMARY,
    PRIMARY_DARK,
    SURFACE,
    TEXT,
    font,
    primary_button,
    text_field,
)

_BRAND_START = (0x1E, 0x3A, 0x8A)
_BRAND_END = (0x25, 0x63, 0xEB)


class LoginView(tk.Tk):
    """Cửa sổ đăng nhập; đặt ``session`` khi xác thực thành công."""

    def __init__(self, auth_service: AuthService) -> None:
        super().__init__()
        self.auth_service = auth_service
        self.session: Session | None = None
        self._busy = False

        self.title("Đăng nhập • Hệ thống quản lý sinh viên")
        self.geometry("980x620")
        self.minsize(920, 580)
        self.configure(bg=BACKGROUND)

        self._build()
        self.bind("<Return>", lambda event: self._attempt_login())
        self.after(120, self.username_entry.focus_set)

    def _build(self) -> None:
        self.grid_columnconfigure(0, minsize=400, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.brand = tk.Canvas(self, width=400, bg=PRIMARY_DARK, highlightthickness=0)
        self.brand.grid(row=0, column=0, sticky="nsew")
        self.brand.bind("<Configure>", self._paint_brand)

        right = tk.Frame(self, bg=BACKGROUND)
        right.grid(row=0, column=1, sticky="nsew")

        card = tk.Frame(right, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        card.place(relx=0.5, rely=0.5, anchor="center", width=460, height=540)
        inner = tk.Frame(card, bg=SURFACE)
        inner.pack(fill="both", expand=True, padx=38, pady=30)

        tk.Label(
            inner,
            text="CHÀO MỪNG TRỞ LẠI",
            bg=SURFACE,
            fg=PRIMARY,
            font=font(8, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            inner,
            text="Đăng nhập tài khoản",
            bg=SURFACE,
            fg=TEXT,
            font=font(18, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(6, 4))
        tk.Label(
            inner,
            text="Truy cập hệ thống để quản lý đào tạo.\nVui lòng dùng tài khoản đã được cấp.",
            bg=SURFACE,
            fg=MUTED,
            font=font(9),
            anchor="w",
            justify="left",
        ).pack(fill="x", pady=(0, 20))

        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()

        self.username_entry = self._field(inner, "Tên đăng nhập", self.username_var)
        self.password_entry = self._field(inner, "Mật khẩu", self.password_var, show="•")

        self.show_password = tk.BooleanVar(value=False)
        tk.Checkbutton(
            inner,
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

        feedback_holder = tk.Frame(inner, bg=SURFACE, height=38)
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
            wraplength=360,
        )
        self.feedback.pack(fill="both", expand=True)

        self.login_button = primary_button(inner, "Đăng nhập", self._attempt_login)
        self.login_button.pack(fill="x", pady=(6, 12))

        tk.Label(
            inner,
            text="Tài khoản Admin mặc định: admin / Admin@123",
            bg=SURFACE,
            fg=MUTED,
            font=font(8),
        ).pack()

    def _field(
        self,
        parent: tk.Misc,
        label_text: str,
        variable: tk.StringVar,
        *,
        show: str | None = None,
    ) -> tk.Entry:
        tk.Label(
            parent,
            text=label_text,
            bg=SURFACE,
            fg=TEXT,
            font=font(9, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 6))
        wrapper, entry = text_field(parent, show=show)
        entry.configure(textvariable=variable)
        wrapper.pack(fill="x", pady=(0, 14))
        return entry

    def _paint_brand(self, event: tk.Event | None = None) -> None:
        canvas = self.brand
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width <= 2 or height <= 2:
            return

        canvas.delete("all")
        for y in range(height):
            ratio = y / max(height - 1, 1)
            color = "#%02x%02x%02x" % tuple(
                round(start + (end - start) * ratio) for start, end in zip(_BRAND_START, _BRAND_END)
            )
            canvas.create_line(0, y, width, y, fill=color)

        canvas.create_oval(
            -140,
            height - 280,
            300,
            height + 160,
            fill=self._blend(_BRAND_END, "#FFFFFF", 0.08),
            outline="",
        )
        canvas.create_oval(
            width - 160,
            -140,
            width + 180,
            200,
            fill=self._blend(_BRAND_START, "#FFFFFF", 0.07),
            outline="",
        )

        canvas.create_text(
            38,
            40,
            anchor="nw",
            text="STUDENT MANAGEMENT SYSTEM",
            fill="#BFDBFE",
            font=font(8, "bold"),
        )
        canvas.create_text(
            38,
            82,
            anchor="nw",
            text="Hệ thống quản lý",
            fill="white",
            font=font(24, "bold"),
        )
        canvas.create_text(
            38,
            124,
            anchor="nw",
            text="sinh viên",
            fill="white",
            font=font(24, "bold"),
        )
        canvas.create_text(
            38,
            180,
            anchor="nw",
            text="Kiến trúc 3 lớp  •  Python  •  MySQL",
            fill="#DBEAFE",
            font=font(10),
        )

        features = [
            "•  Đăng nhập an toàn với mật khẩu băm PBKDF2",
            "•  Phân quyền Admin, Giảng viên, Sinh viên",
            "•  Quản lý tài khoản, sinh viên, môn học, điểm số",
        ]
        for index, text in enumerate(features):
            canvas.create_text(
                38,
                248 + index * 44,
                anchor="nw",
                text=text,
                width=310,
                fill="#DBEAFE",
                font=font(10),
            )

        canvas.create_text(
            38,
            height - 34,
            anchor="sw",
            text="Phiên bản 1.0  •  Đồ án nhóm",
            fill="#BFDBFE",
            font=font(8),
        )

    @staticmethod
    def _blend(first: tuple[int, int, int], second: str, ratio: float) -> str:
        first_hex = "#%02x%02x%02x" % first
        first_rgb = tuple(int(first_hex[i : i + 2], 16) for i in (1, 3, 5))
        second_rgb = tuple(int(second[i : i + 2], 16) for i in (1, 3, 5))
        return "#%02x%02x%02x" % tuple(
            round(start + (end - start) * ratio)
            for start, end in zip(first_rgb, second_rgb)
        )

    def _toggle_password(self) -> None:
        self.password_entry.configure(show="" if self.show_password.get() else "•")

    def _attempt_login(self) -> None:
        if self._busy:
            return
        username = self.username_var.get().strip()
        password = self.password_var.get()

        self._set_busy(True)
        self.feedback.configure(text="")

        def worker() -> None:
            try:
                session = self.auth_service.login(username, password)
            except Exception as exc:  # Hiển thị mọi lỗi cấu hình/kết nối cho người dùng
                self._post(lambda error=exc: self._finish_error(error))
            else:
                self._post(lambda result=session: self._finish_success(result))

        threading.Thread(target=worker, daemon=True).start()

    def _post(self, callback) -> None:
        try:
            self.after(0, callback)
        except tk.TclError:
            pass

    def _finish_success(self, session: Session) -> None:
        self.session = session
        self.password_var.set("")
        self.destroy()

    def _finish_error(self, error: BaseException) -> None:
        self._set_busy(False)
        if isinstance(error, (ServiceError, DataAccessError)):
            message = str(error)
        else:
            message = f"Không thể đăng nhập: {error}"
        self.feedback.configure(text=message)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        state = "disabled" if busy else "normal"
        self.username_entry.configure(state=state)
        self.password_entry.configure(state=state)
        self.login_button.configure(
            state=state,
            text="Đang đăng nhập..." if busy else "Đăng nhập",
            bg=DISABLED if busy else PRIMARY,
            activebackground=DISABLED if busy else "#1E40AF",
        )
