"""Khung làm việc chính với thanh điều hướng phân quyền (RBAC)."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from app.security.rbac import AppModule, RbacPolicy
from app.security.session import Session
from app.models import Role
from app.service.auth_service import AuthService
from app.service.account_service import AccountService
from app.service.course_service import CourseService
from app.service.grade_service import GradeService
from app.service.lecturer_service import LecturerService
from app.service.profile_service import ProfileService
from app.service.student_search_service import StudentSearchService
from app.service.student_service import StudentService
from app.ui.change_password_dialog import ChangePasswordDialog
from app.ui.accounts import AccountManagementView
from app.ui.courses import CourseManagementView
from app.ui.grades import (
    AdminGradesView,
    GradeEntryView,
    LecturerCoursesView,
    StudentResultsView,
)
from app.ui.dashboard import DashboardView
from app.ui.profile import ProfileView
from app.ui.search import LecturerStudentSearchView
from app.ui.students import StudentManagementView
from app.ui.lecturers import LecturerManagementView
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
    AppModule.LECTURER_STUDENT_SEARCH: "🔎",
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
        student_service: StudentService,
        student_search_service: StudentSearchService,
        lecturer_service: LecturerService,
        account_service: AccountService,
        course_service: CourseService,
        profile_service: ProfileService,
        session: Session,
    ) -> None:
        super().__init__()
        self.auth_service = auth_service
        self.grade_service = grade_service
        self.student_service = student_service
        self.student_search_service = student_search_service
        self.lecturer_service = lecturer_service
        self.account_service = account_service
        self.course_service = course_service
        self.profile_service = profile_service
        self.session = session
        self.logout_requested = False
        self._modules = RbacPolicy.navigation_for(session.role)
        self._nav_buttons: dict[AppModule, tk.Button] = {}
        self._navigation_generation = 0

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
        section_text = _ROLE_SECTION.get(self.session.role.name, "KHÔNG GIAN HỌC VỤ")
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
        if self.session.role is Role.ADMIN:
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
            text="  Nhóm 05  •  Công nghệ phần mềm",
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
            text="UniCore  •  Dữ liệu hệ thống",
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

        self._navigation_generation += 1
        for item, btn in self._nav_buttons.items():
            if item is module:
                btn.configure(bg="#1D4ED8", fg="white", font=font(9, "bold"))
            else:
                btn.configure(bg=PRIMARY_DARK, fg="#CBD5E1", font=font(9))

        for child in self.content.winfo_children():
            child.destroy()

        if module is AppModule.DASHBOARD:
            DashboardView(
                self.content,
                self.student_search_service,
                self.grade_service,
                self.session,
                self._modules,
                self._select_module,
            ).pack(fill="both", expand=True)
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
        elif module is AppModule.LECTURER_STUDENT_SEARCH:
            LecturerStudentSearchView(
                self.content, self.student_search_service, self.session
            ).pack(fill="both", expand=True)
        elif module is AppModule.STUDENT_MANAGEMENT:
            StudentManagementView(
                self.content, self.student_service, self.student_search_service, self.session
            ).pack(fill="both", expand=True)
        elif module is AppModule.LECTURER_MANAGEMENT:
            LecturerManagementView(
                self.content, self.lecturer_service, self.session
            ).pack(fill="both", expand=True)
        elif module is AppModule.PROFILE:
            ProfileView(
                self.content, self.profile_service, self.auth_service, self.session
            ).pack(fill="both", expand=True)
        elif module is AppModule.ACCOUNT_MANAGEMENT:
            AccountManagementView(
                self.content, self.account_service, self.session
            ).pack(fill="both", expand=True)
        elif module is AppModule.COURSE_MANAGEMENT:
            CourseManagementView(
                self.content, self.course_service, self.lecturer_service, self.session
            ).pack(fill="both", expand=True)
        else:
            self._build_placeholder(self.content, module)

    # ------------------------------------------------------------------ pages

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
