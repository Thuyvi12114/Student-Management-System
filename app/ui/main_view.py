"""Khung làm việc chính với thanh điều hướng phân quyền (RBAC)."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from app.security.rbac import AppModule, RbacPolicy
from app.security.session import Session
from app.service.auth_service import AuthService
from app.service.grade_service import GradeService
from app.ui.change_password_dialog import ChangePasswordDialog
from app.ui.grades import (
    AdminGradesView,
    GradeEntryView,
    LecturerCoursesView,
    StudentResultsView,
)
from app.ui.theme import (
    BACKGROUND,
    BORDER,
    MUTED,
    PRIMARY_DARK,
    PRIMARY_SOFT,
    SURFACE,
    TEXT,
    font,
    role_chip,
    secondary_button,
    subtle_button,
)


class MainView(tk.Tk):
    """Cửa sổ sau đăng nhập; lưu ``logout_requested`` khi người dùng đăng xuất."""

    def __init__(
        self,
        auth_service: AuthService,
        grade_service: GradeService,
        session: Session,
    ) -> None:
        super().__init__()
        self.auth_service = auth_service
        self.grade_service = grade_service
        self.session = session
        self.logout_requested = False
        self._modules = RbacPolicy.navigation_for(session.role)
        self._nav_buttons: dict[AppModule, tk.Button] = {}

        self.title(f"Hệ thống quản lý sinh viên • {session.role.label}")
        self.geometry("1180x720")
        self.minsize(1024, 640)
        self.configure(bg=BACKGROUND)
        self.protocol("WM_DELETE_WINDOW", self._confirm_exit)

        self._build()
        if self._modules:
            self._select_module(self._modules[0])

    def _build(self) -> None:
        self._build_header()
        self._build_status_bar()

        body = tk.Frame(self, bg=BACKGROUND)
        body.pack(fill="both", expand=True)

        self._build_sidebar(body)
        tk.Frame(body, bg=BORDER, width=1).pack(side="left", fill="y")

        self.content = tk.Frame(body, bg=BACKGROUND)
        self.content.pack(side="left", fill="both", expand=True)

    def _build_header(self) -> None:
        header = tk.Frame(self, bg=SURFACE, height=78)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        brand = tk.Frame(header, bg=SURFACE)
        brand.pack(side="left", padx=24, pady=14)

        tk.Label(
            brand,
            text="SMS • Hệ thống quản lý sinh viên",
            bg=SURFACE,
            fg=PRIMARY_DARK,
            font=font(13, "bold"),
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            brand,
            text="Kiến trúc 3 lớp • Python • Phân quyền theo vai trò",
            bg=SURFACE,
            fg=MUTED,
            font=font(8),
            anchor="w",
        ).pack(anchor="w")

        actions = tk.Frame(header, bg=SURFACE)
        actions.pack(side="right", padx=24, pady=12)

        subtle_button(actions, "Đăng xuất", self._logout).pack(side="right", padx=(10, 0))
        secondary_button(actions, "Đổi mật khẩu", self._open_change_password).pack(
            side="right", padx=(10, 0)
        )

        identity = tk.Frame(actions, bg=SURFACE)
        identity.pack(side="right", padx=(0, 6))
        tk.Label(
            identity,
            text=self.session.full_name,
            bg=SURFACE,
            fg=TEXT,
            font=font(9, "bold"),
            anchor="e",
        ).pack(anchor="e")
        role_chip(identity, self.session.role).pack(anchor="e", pady=(3, 0))

        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")

    def _build_status_bar(self) -> None:
        border = tk.Frame(self, bg=BORDER, height=1)
        border.pack(fill="x", side="bottom")

        bar = tk.Frame(self, bg=SURFACE, height=36)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        self.status_var = tk.StringVar(value="Sẵn sàng")
        tk.Label(
            bar,
            textvariable=self.status_var,
            bg=SURFACE,
            fg=MUTED,
            font=font(8),
        ).pack(side="left", padx=24)
        tk.Label(
            bar,
            text=f"Phiên 8 giờ • Mã tài khoản #{self.session.account_id}",
            bg=SURFACE,
            fg=MUTED,
            font=font(8),
        ).pack(side="right", padx=24)

    def _build_sidebar(self, parent: tk.Frame) -> None:
        sidebar = tk.Frame(parent, bg=SURFACE, width=280)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tk.Label(
            sidebar,
            text="CHỨC NĂNG THEO VAI TRÒ",
            bg=SURFACE,
            fg=MUTED,
            font=font(7, "bold"),
            anchor="w",
        ).pack(fill="x", padx=22, pady=(20, 8))

        for module in self._modules:
            button = tk.Button(
                sidebar,
                text=module.label,
                anchor="w",
                bg=SURFACE,
                fg=TEXT,
                activebackground=PRIMARY_SOFT,
                activeforeground=PRIMARY_DARK,
                relief="flat",
                bd=0,
                highlightthickness=0,
                padx=22,
                pady=10,
                font=font(9),
                cursor="hand2",
                command=lambda selected=module: self._select_module(selected),
            )
            button.pack(fill="x", padx=10, pady=1)
            self._nav_buttons[module] = button

        footer = tk.Frame(sidebar, bg=SURFACE)
        footer.pack(side="bottom", fill="x", padx=22, pady=16)
        tk.Label(
            footer,
            text=f"Tài khoản: {self.session.username}",
            bg=SURFACE,
            fg=MUTED,
            font=font(8),
            anchor="w",
        ).pack(fill="x")

    def _select_module(self, module: AppModule) -> None:
        """Chốt chặn RBAC ở tầng giao diện trước khi hiển thị module."""
        if not RbacPolicy.can_access(self.session.role, module):
            messagebox.showwarning(
                "Không có quyền truy cập",
                f'Vai trò {self.session.role.label} không có quyền truy cập '
                f'chức năng "{module.label}".',
                parent=self,
            )
            return

        for item, button in self._nav_buttons.items():
            if item is module:
                button.configure(bg=PRIMARY_SOFT, fg=PRIMARY_DARK, font=font(9, "bold"))
            else:
                button.configure(bg=SURFACE, fg=TEXT, font=font(9))

        for child in self.content.winfo_children():
            child.destroy()

        if module is AppModule.DASHBOARD:
            self._build_dashboard(self.content)
        elif module is AppModule.MY_GRADES:
            StudentResultsView(self.content, self.grade_service, self.session).pack(
                fill="both", expand=True
            )
        elif module is AppModule.ADMIN_GRADE_LOOKUP:
            AdminGradesView(self.content, self.grade_service, self.session).pack(
                fill="both", expand=True
            )
        elif module is AppModule.LECTURER_COURSE_GRADES:
            LecturerCoursesView(self.content, self.grade_service, self.session).pack(
                fill="both", expand=True
            )
        elif module is AppModule.GRADE_MANAGEMENT:
            GradeEntryView(self.content, self.grade_service, self.session).pack(
                fill="both", expand=True
            )
        else:
            self._build_placeholder(self.content, module)
        self.status_var.set(f"Đang mở: {module.label}")

    def _build_dashboard(self, parent: tk.Frame) -> None:
        wrapper = tk.Frame(parent, bg=BACKGROUND)
        wrapper.pack(fill="both", expand=True, padx=32, pady=28)

        tk.Label(
            wrapper,
            text=f"Xin chào, {self.session.full_name}",
            bg=BACKGROUND,
            fg=TEXT,
            font=font(20, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            wrapper,
            text=f"{self.session.role.label} — {self.session.role.description}",
            bg=BACKGROUND,
            fg=MUTED,
            font=font(9),
            anchor="w",
            justify="left",
            wraplength=820,
        ).pack(fill="x", pady=(6, 0))
        tk.Label(
            wrapper,
            text="Chức năng bạn có thể truy cập",
            bg=BACKGROUND,
            fg=TEXT,
            font=font(11, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(24, 10))

        cards = tk.Frame(wrapper, bg=BACKGROUND)
        cards.pack(fill="both", expand=True)
        cards.grid_columnconfigure(0, weight=1, uniform="card")
        cards.grid_columnconfigure(1, weight=1, uniform="card")

        accessible = [module for module in self._modules if module is not AppModule.DASHBOARD]
        for index, module in enumerate(accessible):
            card = self._build_access_card(cards, module)
            card.grid(row=index // 2, column=index % 2, sticky="nsew", padx=7, pady=7)
        for row in range((len(accessible) + 1) // 2):
            cards.grid_rowconfigure(row, weight=1)

    def _build_access_card(self, parent: tk.Frame, module: AppModule) -> tk.Frame:
        card = tk.Frame(
            parent,
            bg=SURFACE,
            highlightbackground=BORDER,
            highlightthickness=1,
            cursor="hand2",
        )
        inner = tk.Frame(card, bg=SURFACE)
        inner.pack(fill="both", expand=True, padx=18, pady=14)

        title = tk.Label(
            inner,
            text=module.label,
            bg=SURFACE,
            fg=PRIMARY_DARK,
            font=font(10, "bold"),
            anchor="w",
        )
        title.pack(fill="x")
        description = tk.Label(
            inner,
            text=module.description,
            bg=SURFACE,
            fg=MUTED,
            font=font(8),
            anchor="nw",
            justify="left",
            wraplength=280,
        )
        description.pack(fill="both", expand=True, pady=(6, 0))

        for widget in (card, inner, title, description):
            widget.bind(
                "<Button-1>",
                lambda event, selected=module: self._select_module(selected),
            )
        return card

    def _build_placeholder(self, parent: tk.Frame, module: AppModule) -> None:
        wrapper = tk.Frame(parent, bg=BACKGROUND)
        wrapper.pack(fill="both", expand=True, padx=32, pady=28)

        card = tk.Frame(wrapper, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", anchor="n")
        inner = tk.Frame(card, bg=SURFACE)
        inner.pack(fill="x", padx=30, pady=26)

        tk.Label(
            inner,
            text=module.label,
            bg=SURFACE,
            fg=TEXT,
            font=font(18, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            inner,
            text=f"Vai trò được phép: {module.allowed_roles_label}",
            bg=SURFACE,
            fg=MUTED,
            font=font(8),
            anchor="w",
        ).pack(fill="x", pady=(6, 16))
        tk.Label(
            inner,
            text=module.description,
            bg=SURFACE,
            fg=TEXT,
            font=font(9),
            anchor="w",
            justify="left",
            wraplength=640,
        ).pack(fill="x")

        note = tk.Frame(inner, bg=BACKGROUND)
        note.pack(fill="x", pady=(22, 0))
        tk.Label(
            note,
            text=(
                "Khung điều hướng và phân quyền đã được thiết lập. "
                "Phần nghiệp vụ chi tiết của module này do thành viên phụ trách module đảm nhiệm."
            ),
            bg=BACKGROUND,
            fg=MUTED,
            font=font(8),
            anchor="w",
            justify="left",
            wraplength=610,
        ).pack(fill="x", padx=18, pady=14)

    def _open_change_password(self) -> None:
        ChangePasswordDialog(self, self.auth_service)

    def _logout(self) -> None:
        if not messagebox.askyesno(
            "Xác nhận đăng xuất",
            "Bạn có chắc muốn đăng xuất khỏi hệ thống?",
            parent=self,
        ):
            return
        self.auth_service.logout()
        self.logout_requested = True
        self.destroy()

    def _confirm_exit(self) -> None:
        if not messagebox.askyesno(
            "Xác nhận thoát",
            "Thoát ứng dụng? Phiên đăng nhập hiện tại sẽ bị hủy.",
            parent=self,
        ):
            return
        self.auth_service.logout()
        self.destroy()
