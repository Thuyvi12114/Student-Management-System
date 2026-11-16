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
    PRIMARY,
    PRIMARY_DARK,
    PRIMARY_SOFT,
    SURFACE,
    TEXT,
    font,
    role_chip,
    secondary_button,
    subtle_button,
)

# Sidebar nav icon map
_NAV_ICONS: dict[AppModule, str] = {
    AppModule.DASHBOARD: "⊞",
    AppModule.ACCOUNT_MANAGEMENT: "🔒",
    AppModule.STUDENT_MANAGEMENT: "🎓",
    AppModule.LECTURER_MANAGEMENT: "👨‍🏫",
    AppModule.COURSE_MANAGEMENT: "📚",
    AppModule.ADMIN_GRADE_LOOKUP: "📊",
    AppModule.GRADE_MANAGEMENT: "✏️",
    AppModule.LECTURER_COURSE_GRADES: "📋",
    AppModule.MY_GRADES: "📈",
    AppModule.PROFILE: "👤",
}

_ROLE_SECTION: dict = {
    "ADMIN": "QUẢN TRỊ HỆ THỐNG",
    "LECTURER": "KHÔNG GIAN GIẢNG VIÊN",
    "STUDENT": "KHÔNG GIAN SINH VIÊN",
}


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

        self.title(f"UniCore  •  Hệ thống quản lý sinh viên")
        self.geometry("1200x740")
        self.minsize(1024, 640)
        self.configure(bg=BACKGROUND)
        self.protocol("WM_DELETE_WINDOW", self._confirm_exit)

        self._build()
        if self._modules:
            self._select_module(self._modules[0])

    # ------------------------------------------------------------------ layout

    def _build(self) -> None:
        body = tk.Frame(self, bg=BACKGROUND)
        body.pack(fill="both", expand=True)

        self._build_sidebar(body)

        right = tk.Frame(body, bg=BACKGROUND)
        right.pack(side="left", fill="both", expand=True)

        self._build_topbar(right)
        tk.Frame(right, bg=BORDER, height=1).pack(fill="x")

        self.content = tk.Frame(right, bg=BACKGROUND)
        self.content.pack(fill="both", expand=True)

        self._build_footer(right)

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def _build_sidebar(self, parent: tk.Frame) -> None:
        sidebar = tk.Frame(parent, bg=PRIMARY_DARK, width=200)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # Logo
        logo_frame = tk.Frame(sidebar, bg=PRIMARY_DARK)
        logo_frame.pack(fill="x", padx=20, pady=(22, 20))
        logo_icon = tk.Label(logo_frame, text="🎓", bg=PRIMARY_DARK, font=font(14), fg="white")
        logo_icon.pack(side="left")
        tk.Label(
            logo_frame,
            text="UniCore",
            bg=PRIMARY_DARK,
            fg="white",
            font=font(14, "bold"),
        ).pack(side="left", padx=(6, 0))

        tk.Frame(sidebar, bg="#2D4F9E", height=1).pack(fill="x", padx=16, pady=(0, 12))

        # Section label
        section_text = _ROLE_SECTION.get(self.session.role.value, "KHÔNG GIAN HỌC VỤ")
        tk.Label(
            sidebar,
            text=section_text,
            bg=PRIMARY_DARK,
            fg="#93C5FD",
            font=font(7, "bold"),
            anchor="w",
        ).pack(fill="x", padx=20, pady=(0, 8))

        # Nav buttons
        for module in self._modules:
            icon = _NAV_ICONS.get(module, "•")
            btn = tk.Button(
                sidebar,
                text=f"  {icon}  {module.label}",
                anchor="w",
                bg=PRIMARY_DARK,
                fg="#CBD5E1",
                activebackground="#2563EB",
                activeforeground="white",
                relief="flat",
                bd=0,
                highlightthickness=0,
                padx=10,
                pady=9,
                font=font(9),
                cursor="hand2",
                command=lambda m=module: self._select_module(m),
            )
            btn.pack(fill="x", padx=10, pady=1)
            self._nav_buttons[module] = btn

        # User info at bottom
        bottom = tk.Frame(sidebar, bg=PRIMARY_DARK)
        bottom.pack(side="bottom", fill="x", padx=16, pady=18)
        tk.Frame(bottom, bg="#2D4F9E", height=1).pack(fill="x", pady=(0, 12))

        user_row = tk.Frame(bottom, bg=PRIMARY_DARK)
        user_row.pack(fill="x")

        # Avatar circle (canvas)
        avatar = tk.Canvas(user_row, width=34, height=34, bg=PRIMARY_DARK,
                           highlightthickness=0)
        avatar.pack(side="left")
        avatar.create_oval(2, 2, 32, 32, fill="#2563EB", outline="")
        initials = "".join(w[0].upper() for w in self.session.full_name.split()[:2])
        avatar.create_text(17, 17, text=initials, fill="white", font=font(9, "bold"))

        name_frame = tk.Frame(user_row, bg=PRIMARY_DARK)
        name_frame.pack(side="left", padx=(10, 0), fill="x", expand=True)
        tk.Label(
            name_frame,
            text=self.session.full_name,
            bg=PRIMARY_DARK,
            fg="white",
            font=font(9, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            name_frame,
            text=self.session.username,
            bg=PRIMARY_DARK,
            fg="#93C5FD",
            font=font(7),
            anchor="w",
        ).pack(fill="x")

        # Action links
        action_frame = tk.Frame(bottom, bg=PRIMARY_DARK)
        action_frame.pack(fill="x", pady=(10, 0))

        def _sidebar_link(text: str, icon: str, cmd) -> tk.Button:
            return tk.Button(
                action_frame,
                text=f"  {icon}  {text}",
                anchor="w",
                bg=PRIMARY_DARK,
                fg="#CBD5E1",
                activebackground="#1E3A8A",
                activeforeground="white",
                relief="flat",
                bd=0,
                highlightthickness=0,
                padx=4,
                pady=5,
                font=font(8),
                cursor="hand2",
                command=cmd,
            )

        _sidebar_link("Bảo mật tài khoản", "🔑", self._open_change_password).pack(fill="x")
        _sidebar_link("Đăng xuất", "→", self._logout).pack(fill="x")

        # Info note for admin
        if self.session.role.value == "ADMIN":
            note_frame = tk.Frame(sidebar, bg="#1E3A8A")
            note_frame.pack(fill="x", padx=16, pady=(0, 12))
            tk.Label(
                note_frame,
                text="Dữ liệu học vụ tập trung. Quản\nlý nhất quán, tra cứu rõ ràng.",
                bg="#1E3A8A",
                fg="#93C5FD",
                font=font(7),
                justify="left",
                wraplength=160,
                anchor="w",
            ).pack(padx=4, pady=8, anchor="w")
    # ── Top bar ───────────────────────────────────────────────────────────────

    def _build_topbar(self, parent: tk.Frame) -> None:
        bar = tk.Frame(parent, bg=SURFACE, height=52)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        tk.Label(
            bar,
            text="Hệ thống quản lý sinh viên",
            bg=SURFACE,
            fg=MUTED,
            font=font(9),
        ).pack(side="left", padx=28)

        right = tk.Frame(bar, bg=SURFACE)
        right.pack(side="right", padx=28)

        role_chip(right, self.session.role).pack(side="left")
        tk.Label(
            right,
            text="  Năm học 2024-2025",
            bg=SURFACE,
            fg=MUTED,
            font=font(9),
        ).pack(side="left", padx=(10, 0))

    # ── Footer ────────────────────────────────────────────────────────────────

    def _build_footer(self, parent: tk.Frame) -> None:
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x")
        bar = tk.Frame(parent, bg=SURFACE, height=36)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        tk.Label(
            bar,
            text="UniCore  •  Hệ thống quản lý sinh viên",
            bg=SURFACE,
            fg=MUTED,
            font=font(8),
        ).pack(side="left", padx=24)
        tk.Label(
            bar,
            text="Không gian quản trị  •  Dữ liệu minh hoạ",
            bg=SURFACE,
            fg=MUTED,
            font=font(8),
        ).pack(side="right", padx=24)

    # ------------------------------------------------------------------ routing

    def _select_module(self, module: AppModule) -> None:
        if not RbacPolicy.can_access(self.session.role, module):
            messagebox.showwarning(
                "Không có quyền truy cập",
                f'Vai trò {self.session.role.label} không có quyền truy cập '
                f'chức năng "{module.label}".',
                parent=self,
            )
            return

        for item, btn in self._nav_buttons.items():
            if item is module:
                btn.configure(bg="#1D4ED8", fg="white", font=font(9, "bold"))
            else:
                btn.configure(bg=PRIMARY_DARK, fg="#CBD5E1", font=font(9))

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

    # ------------------------------------------------------------------ pages

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
            text=f"{self.session.role.label}  —  {self.session.role.description}",
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

        accessible = [m for m in self._modules if m is not AppModule.DASHBOARD]
        for idx, module in enumerate(accessible):
            card = self._build_access_card(cards, module)
            card.grid(row=idx // 2, column=idx % 2, sticky="nsew", padx=7, pady=7)
        for row in range((len(accessible) + 1) // 2):
            cards.grid_rowconfigure(row, weight=1)

    def _build_access_card(self, parent: tk.Frame, module: AppModule) -> tk.Frame:
        card = tk.Frame(
            parent, bg=SURFACE,
            highlightbackground=BORDER, highlightthickness=1,
            cursor="hand2",
        )
        inner = tk.Frame(card, bg=SURFACE)
        inner.pack(fill="both", expand=True, padx=18, pady=14)

        icon = _NAV_ICONS.get(module, "•")
        title = tk.Label(
            inner, text=f"{icon}  {module.label}",
            bg=SURFACE, fg=PRIMARY_DARK,
            font=font(10, "bold"), anchor="w",
        )
        title.pack(fill="x")
        desc = tk.Label(
            inner, text=module.description,
            bg=SURFACE, fg=MUTED,
            font=font(8), anchor="nw", justify="left", wraplength=280,
        )
        desc.pack(fill="both", expand=True, pady=(6, 0))

        for w in (card, inner, title, desc):
            w.bind("<Button-1>", lambda e, m=module: self._select_module(m))
        return card

    def _build_placeholder(self, parent: tk.Frame, module: AppModule) -> None:
        wrapper = tk.Frame(parent, bg=BACKGROUND)
        wrapper.pack(fill="both", expand=True, padx=32, pady=28)

        card = tk.Frame(wrapper, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x", anchor="n")
        inner = tk.Frame(card, bg=SURFACE)
        inner.pack(fill="x", padx=30, pady=26)

        tk.Label(inner, text=module.label, bg=SURFACE, fg=TEXT,
                 font=font(18, "bold"), anchor="w").pack(fill="x")
        tk.Label(inner, text=f"Vai trò được phép: {module.allowed_roles_label}",
                 bg=SURFACE, fg=MUTED, font=font(8), anchor="w").pack(fill="x", pady=(6, 16))
        tk.Label(inner, text=module.description, bg=SURFACE, fg=TEXT,
                 font=font(9), anchor="w", justify="left", wraplength=640).pack(fill="x")

    # ------------------------------------------------------------------ actions

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
