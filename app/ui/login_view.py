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
    PRIMARY_SOFT,
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
        self._show_pw = False

        self.title("UniCore • Hệ thống quản lý sinh viên")
        self.geometry("1020x660")
        self.minsize(960, 600)
        self.configure(bg=BACKGROUND)

        self._build()
        self.bind("<Return>", lambda event: self._attempt_login())
        self.after(120, self.username_entry.focus_set)

    # ------------------------------------------------------------------ build

    def _build(self) -> None:
        self.grid_columnconfigure(0, minsize=460, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ── Left brand panel ──────────────────────────────────────────────
        self.brand = tk.Canvas(self, width=460, bg=PRIMARY_DARK, highlightthickness=0)
        self.brand.grid(row=0, column=0, sticky="nsew")
        self.brand.bind("<Configure>", self._paint_brand)

        # ── Right login panel ─────────────────────────────────────────────
        right = tk.Frame(self, bg=BACKGROUND)
        right.grid(row=0, column=1, sticky="nsew")

        card = tk.Frame(right, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        card.place(relx=0.5, rely=0.5, anchor="center", width=480, height=580)
        inner = tk.Frame(card, bg=SURFACE)
        inner.pack(fill="both", expand=True, padx=44, pady=36)

        # Lock badge
        badge = tk.Frame(inner, bg=SURFACE)
        badge.pack(anchor="w", pady=(0, 14))
        tk.Label(badge, text="🔒", bg=SURFACE, font=font(10)).pack(side="left")
        tk.Label(
            badge,
            text="Cổng truy cập nội bộ",
            bg=SURFACE,
            fg=MUTED,
            font=font(9),
        ).pack(side="left", padx=(4, 0))

        # Headline
        tk.Label(
            inner,
            text="Chào mừng trở lại",
            bg=SURFACE,
            fg=TEXT,
            font=font(22, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            inner,
            text="Đăng nhập để tiếp tục đến không gian UniCore của bạn.",
            bg=SURFACE,
            fg=MUTED,
            font=font(9),
            anchor="w",
            justify="left",
        ).pack(fill="x", pady=(4, 20))

        # Fields
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()

        self.username_entry = self._field(inner, "Tên đăng nhập", self.username_var, placeholder="Nhập tên đăng nhập")
        self._build_password_field(inner)

        # Error feedback
        feedback_holder = tk.Frame(inner, bg=SURFACE, height=36)
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
            wraplength=380,
        )
        self.feedback.pack(fill="both", expand=True)

        # Login button
        self.login_button = primary_button(inner, "Đăng nhập  →", self._attempt_login)
        self.login_button.pack(fill="x", pady=(4, 14))

        # Role note
        tk.Label(
            inner,
            text="Không gian Quản trị viên, Giảng viên hoặc Sinh viên được xác định theo tài khoản.",
            bg=SURFACE,
            fg=MUTED,
            font=font(8),
            wraplength=380,
            justify="left",
        ).pack(fill="x", pady=(0, 16))

        # Divider
        tk.Frame(inner, bg=BORDER, height=1).pack(fill="x", pady=(0, 14))

        # Support section
        tk.Label(
            inner,
            text="Bạn cần hỗ trợ đăng nhập?",
            bg=SURFACE,
            fg=TEXT,
            font=font(9, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            inner,
            text="Liên hệ quản trị viên để được cấp tài khoản hoặc đặt lại mật khẩu.",
            bg=SURFACE,
            fg=MUTED,
            font=font(8),
            wraplength=380,
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(2, 4))
        email_lbl = tk.Label(
            inner,
            text="hotro@unicore.edu.vn",
            bg=SURFACE,
            fg=PRIMARY,
            font=font(9, "bold"),
            anchor="w",
            cursor="hand2",
        )
        email_lbl.pack(fill="x")

        # Bottom note
        tk.Label(
            inner,
            text="Chỉ sử dụng tài khoản được nhà trường cung cấp.",
            bg=SURFACE,
            fg="#94A3B8",
            font=font(8),
            anchor="w",
        ).pack(fill="x", pady=(10, 0))

    # ------------------------------------------------------------------ helpers

    def _field(
        self,
        parent: tk.Misc,
        label_text: str,
        variable: tk.StringVar,
        *,
        show: str | None = None,
        placeholder: str = "",
    ) -> tk.Entry:
        tk.Label(
            parent,
            text=label_text,
            bg=SURFACE,
            fg=TEXT,
            font=font(9, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 5))
        wrapper, entry = text_field(parent, show=show)
        entry.configure(textvariable=variable)
        if placeholder:
            self._attach_placeholder(entry, variable, placeholder)
        wrapper.pack(fill="x", pady=(0, 14))
        return entry

    def _build_password_field(self, parent: tk.Misc) -> None:
        tk.Label(
            parent,
            text="Mật khẩu",
            bg=SURFACE,
            fg=TEXT,
            font=font(9, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 5))

        wrapper = tk.Frame(
            parent,
            bg=SURFACE,
            highlightbackground=BORDER,
            highlightcolor=PRIMARY,
            highlightthickness=1,
        )
        wrapper.pack(fill="x", pady=(0, 14))

        self.password_entry = tk.Entry(
            wrapper,
            textvariable=self.password_var,
            font=font(11),
            relief="flat",
            bd=0,
            bg=SURFACE,
            fg=TEXT,
            insertbackground=TEXT,
            highlightthickness=0,
            show="•",
        )
        self.password_entry.pack(side="left", fill="x", expand=True, padx=12, pady=9)

        # Eye toggle button
        self._eye_btn = tk.Button(
            wrapper,
            text="🙈",
            command=self._toggle_password,
            bg=SURFACE,
            fg=MUTED,
            activebackground=SURFACE,
            relief="flat",
            bd=0,
            highlightthickness=0,
            cursor="hand2",
            font=font(11),
            padx=8,
            pady=0,
        )
        self._eye_btn.pack(side="right", padx=(0, 4))

    @staticmethod
    def _attach_placeholder(entry: tk.Entry, var: tk.StringVar, text: str) -> None:
        """Light placeholder simulation using fg color."""
        PLACEHOLDER_COLOR = "#CBD5E1"
        NORMAL_COLOR = TEXT

        def on_focus_in(_event=None) -> None:
            if var.get() == text:
                var.set("")
                entry.configure(fg=NORMAL_COLOR)

        def on_focus_out(_event=None) -> None:
            if var.get() == "":
                var.set(text)
                entry.configure(fg=PLACEHOLDER_COLOR)

        var.set(text)
        entry.configure(fg=PLACEHOLDER_COLOR)
        entry.bind("<FocusIn>", on_focus_in)
        entry.bind("<FocusOut>", on_focus_out)

    # ------------------------------------------------------------------ brand panel

    def _paint_brand(self, event: tk.Event | None = None) -> None:
        canvas = self.brand
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width <= 2 or height <= 2:
            return

        canvas.delete("all")

        # Gradient background
        for y in range(height):
            ratio = y / max(height - 1, 1)
            color = "#%02x%02x%02x" % tuple(
                round(start + (end - start) * ratio)
                for start, end in zip(_BRAND_START, _BRAND_END)
            )
            canvas.create_line(0, y, width, y, fill=color)

        # Decorative circles
        canvas.create_oval(
            -140, height - 300, 300, height + 160,
            fill=self._blend(_BRAND_END, "#FFFFFF", 0.08), outline="",
        )
        canvas.create_oval(
            width - 160, -140, width + 180, 200,
            fill=self._blend(_BRAND_START, "#FFFFFF", 0.07), outline="",
        )

        # Logo row
        canvas.create_text(38, 42, anchor="nw", text="🎓", font=font(14), fill="white")
        canvas.create_text(68, 44, anchor="nw", text="UniCore", fill="white", font=font(16, "bold"))

        # Tagline
        canvas.create_text(
            38, 120, anchor="nw",
            text="MỘT KHÔNG GIAN HỌC VỤ THỐNG NHẤT",
            fill="#93C5FD", font=font(8, "bold"),
        )
        canvas.create_text(
            38, 148, anchor="nw",
            text="Kết nối dữ liệu.", fill="white", font=font(22, "bold"),
        )
        canvas.create_text(
            38, 184, anchor="nw",
            text="Đồng hành học tập.", fill="white", font=font(22, "bold"),
        )
        canvas.create_text(
            38, 234, anchor="nw",
            text="Quản lý hồ sơ, học phần và kết quả học tập trong\nmột hệ thống rõ ràng, liên mạch.",
            fill="#BFDBFE", font=font(9), width=360,
        )

        # Feature card
        card_x1, card_y1, card_x2, card_y2 = 38, 300, width - 38, 500
        self._rounded_rect(canvas, card_x1, card_y1, card_x2, card_y2, radius=12,
                           fill=self._blend(_BRAND_END, "#FFFFFF", 0.12), outline="")

        canvas.create_text(
            card_x1 + 20, card_y1 + 18, anchor="nw",
            text="Hành trình học tập", fill="white", font=font(10, "bold"),
        )
        canvas.create_text(
            card_x2 - 20, card_y1 + 20, anchor="ne",
            text="📖", font=font(11), fill="white",
        )

        features = [
            ("👤", "Hồ sơ sinh viên", "Thông tin cá nhân được kết nối"),
            ("📊", "Học phần & ghi danh", "Theo dõi từng bước học tập"),
            ("📈", "Kết quả học tập", "Tra cứu rõ ràng, chính xác"),
        ]
        for i, (icon, title, desc) in enumerate(features):
            fy = card_y1 + 60 + i * 54
            # Icon background circle
            canvas.create_oval(
                card_x1 + 16, fy - 2, card_x1 + 46, fy + 28,
                fill=self._blend(_BRAND_END, "#FFFFFF", 0.18), outline="",
            )
            canvas.create_text(card_x1 + 31, fy + 13, text=icon, font=font(10), fill="white")
            canvas.create_text(
                card_x1 + 60, fy + 2, anchor="nw",
                text=title, fill="white", font=font(10, "bold"),
            )
            canvas.create_text(
                card_x1 + 60, fy + 20, anchor="nw",
                text=desc, fill="#BFDBFE", font=font(8),
            )

        # Footer
        canvas.create_text(
            38, height - 28, anchor="sw",
            text="UniCore  •  Hệ thống quản lý sinh viên",
            fill="#93C5FD", font=font(8),
        )

    @staticmethod
    def _rounded_rect(
        canvas: tk.Canvas,
        x1: int, y1: int, x2: int, y2: int,
        radius: int = 10,
        **kwargs,
    ) -> None:
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
        ]
        canvas.create_polygon(points, smooth=True, **kwargs)

    @staticmethod
    def _blend(first: tuple[int, int, int], second: str, ratio: float) -> str:
        first_hex = "#%02x%02x%02x" % first
        first_rgb = tuple(int(first_hex[i: i + 2], 16) for i in (1, 3, 5))
        second_rgb = tuple(int(second[i: i + 2], 16) for i in (1, 3, 5))
        return "#%02x%02x%02x" % tuple(
            round(start + (end - start) * ratio)
            for start, end in zip(first_rgb, second_rgb)
        )

    # ------------------------------------------------------------------ interaction

    def _toggle_password(self) -> None:
        self._show_pw = not self._show_pw
        if self._show_pw:
            self.password_entry.configure(show="")
            self._eye_btn.configure(text="👁")
        else:
            self.password_entry.configure(show="•")
            self._eye_btn.configure(text="🙈")

    def _attempt_login(self) -> None:
        if self._busy:
            return
        raw_username = self.username_var.get().strip()
        # Loại bỏ placeholder nếu người dùng chưa nhập
        username = "" if raw_username == "Nhập tên đăng nhập" else raw_username
        password = self.password_var.get()

        self._set_busy(True)
        self.feedback.configure(text="")

        def worker() -> None:
            try:
                session = self.auth_service.login(username, password)
            except Exception as exc:
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
            text="Đang đăng nhập..." if busy else "Đăng nhập  →",
            bg=DISABLED if busy else PRIMARY,
            activebackground=DISABLED if busy else "#1E40AF",
        )
