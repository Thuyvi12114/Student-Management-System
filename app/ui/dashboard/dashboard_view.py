"""Dashboard tổng quan theo vai trò (UI 1.2, 1.6, 1.7; Module 4 - Sơn).

Admin: KPI sinh viên/giảng viên/học phần/lớp. Giảng viên: học phần, sinh viên, tiến độ nhập điểm.
Sinh viên: số học phần có điểm, tín chỉ đã đạt, điểm trung bình.
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable

from app.models import Role
from app.security.rbac import AppModule
from app.security.session import Session
from app.service.grade_service import GradeService
from app.service.student_search_service import StudentSearchService
from app.ui.management.widgets import create_stat_card, run_in_background
from app.ui.theme import BACKGROUND, BORDER, MUTED, PRIMARY_DARK, SURFACE, TEXT, font

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


class DashboardView(tk.Frame):
    def __init__(
        self,
        parent: tk.Misc,
        search_service: StudentSearchService,
        grade_service: GradeService,
        session: Session,
        modules: list[AppModule],
        on_open: Callable[[AppModule], None],
    ) -> None:
        super().__init__(parent, bg=BACKGROUND)
        self._search_service = search_service
        self._grade_service = grade_service
        self._session = session
        self._modules = modules
        self._on_open = on_open
        self._build()

    def _build(self) -> None:
        parent = self
        wrapper = tk.Frame(parent, bg=BACKGROUND)
        wrapper.pack(fill="both", expand=True, padx=32, pady=28)

        tk.Label(
            wrapper,
            text=f"Xin chào, {self._session.full_name}",
            bg=BACKGROUND,
            fg=TEXT,
            font=font(20, "bold"),
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            wrapper,
            text=f"{self._session.role.label}  —  {self._session.role.description}",
            bg=BACKGROUND,
            fg=MUTED,
            font=font(9),
            anchor="w",
            justify="left",
            wraplength=820,
        ).pack(fill="x", pady=(6, 0))

        stats = tk.Frame(wrapper, bg=BACKGROUND)
        stats.pack(fill="x", pady=(20, 0))
        if self._session.role is Role.ADMIN:
            metrics = (
                ("Sinh viên", lambda result: result.total_students),
                ("Giảng viên", lambda result: result.total_lecturers),
                ("Môn học", lambda result: result.total_courses),
                ("Lớp", lambda result: result.total_classes),
            )
            operation = lambda: self._search_service.dashboard(self._session)
        elif self._session.role is Role.LECTURER:
            metrics = (
                ("Học phần được phân công", lambda result: result.assigned_courses),
                ("Sinh viên trong hệ thống", lambda result: result.total_students),
                (
                    "Tiến độ nhập điểm",
                    lambda result: f"{result.graded_entries}/{result.expected_entries}",
                ),
            )
            operation = lambda: self._search_service.dashboard(self._session)
        else:
            metrics = (
                ("Học phần đã có điểm", lambda result: len(result.grades)),
                ("Tín chỉ đã đạt", lambda result: result.passed_credits),
                (
                    "Điểm trung bình (thang 10)",
                    lambda result: f"{result.gpa:.2f}" if result.gpa is not None else "—",
                ),
            )
            operation = lambda: self._grade_service.student_results(self._session)

        for column in range(len(metrics)):
            stats.grid_columnconfigure(column, weight=1, uniform="dashboard-stat")
        stat_values = []
        for column, (label, _value) in enumerate(metrics):
            card, value = create_stat_card(stats, label)
            card.grid(
                row=0,
                column=column,
                sticky="nsew",
                padx=(0 if column == 0 else 6, 0 if column == len(metrics) - 1 else 6),
            )
            stat_values.append(value)
        self._dashboard_feedback = tk.Label(
            wrapper, text="", bg=BACKGROUND, fg=MUTED, font=font(8), anchor="w"
        )
        self._dashboard_feedback.pack(fill="x", pady=(4, 0))

        def loaded(result) -> None:
            if not self.winfo_exists():
                return
            for value_label, (_label, get_value) in zip(stat_values, metrics):
                value_label.configure(text=str(get_value(result)))

        def failed(error: BaseException) -> None:
            if not self.winfo_exists():
                return
            self._dashboard_feedback.configure(
                text=f"Không tải được thống kê từ cơ sở dữ liệu: {error}",
                fg="#B91C1C",
            )

        run_in_background(self, operation, loaded, failed)

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
            w.bind("<Button-1>", lambda e, m=module: self._on_open(m))
        return card
