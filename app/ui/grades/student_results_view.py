"""Màn hình Kết quả học tập của sinh viên (UI 1.5)."""

from __future__ import annotations

import tkinter as tk
from decimal import Decimal

from app.dao.errors import DataAccessError
from app.security.session import Session
from app.service.exceptions import ServiceError
from app.service.grade_service import GradeService
from app.ui.grades.widgets import (
    configure_table_style,
    format_score,
    row_tag,
    status_chip_label,
)
from app.ui.theme import (
    BACKGROUND,
    BORDER,
    DANGER,
    MUTED,
    PRIMARY,
    PRIMARY_DARK,
    PRIMARY_SOFT,
    SURFACE,
    TEXT,
    font,
)
from tkinter import ttk

_COLUMNS = [
    ("course_code", "Mã học phần",  110, "w"),
    ("course_name", "Tên học phần", 240, "w"),
    ("credits",     "Tín chỉ",       60, "center"),
    ("final",       "Điểm cuối kỳ", 110, "center"),
    ("status",      "Trạng thái",   120, "center"),
]


class StudentResultsView(tk.Frame):
    """Bảng điểm của chính sinh viên đang đăng nhập."""

    def __init__(self, parent: tk.Misc, grade_service: GradeService, session: Session) -> None:
        super().__init__(parent, bg=BACKGROUND)
        self._service = grade_service
        self._session = session
        self._build()
        self._load()

    # ------------------------------------------------------------------ build

    def _build(self) -> None:
        # Scrollable outer
        outer = tk.Frame(self, bg=BACKGROUND)
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(outer, bg=BACKGROUND, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        self._scroll_frame = tk.Frame(canvas, bg=BACKGROUND)

        self._scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        _win = canvas.create_window((0, 0), window=self._scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(_win, width=e.width))

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        canvas.bind("<Enter>",
                    lambda e: canvas.bind_all(
                        "<MouseWheel>",
                        lambda ev: canvas.yview_scroll(-1*(ev.delta//120), "units")))
        canvas.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        page = self._scroll_frame
        wrapper = tk.Frame(page, bg=BACKGROUND)
        wrapper.pack(fill="both", expand=True, padx=32, pady=24)

        # ── Breadcrumb ────────────────────────────────────────────────────
        breadcrumb = tk.Frame(wrapper, bg=BACKGROUND)
        breadcrumb.pack(fill="x", pady=(0, 10))
        tk.Label(breadcrumb, text="Sinh viên  /  Kết quả học tập",
                 bg=BACKGROUND, fg=MUTED, font=font(8)).pack(side="left")

        # ── Title ─────────────────────────────────────────────────────────
        tk.Label(wrapper, text="Kết quả học tập",
                 bg=BACKGROUND, fg=TEXT, font=font(20, "bold"), anchor="w").pack(fill="x")

        self.student_label = tk.Label(wrapper, text="Đang tải...",
                                      bg=BACKGROUND, fg=MUTED, font=font(9), anchor="w")
        self.student_label.pack(fill="x", pady=(4, 18))

        # ── Stat cards row ────────────────────────────────────────────────
        cards_row = tk.Frame(wrapper, bg=BACKGROUND)
        cards_row.pack(fill="x", pady=(0, 20))
        cards_row.grid_columnconfigure(0, weight=1, uniform="sc")
        cards_row.grid_columnconfigure(1, weight=1, uniform="sc")
        cards_row.grid_columnconfigure(2, weight=1, uniform="sc")

        self._card_course, self._val_course, self._sub_course = self._stat_card(
            cards_row, "Học phần đã có điểm", "📄"
        )
        self._card_course.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self._card_credit, self._val_credit, self._sub_credit = self._stat_card(
            cards_row, "Tín chỉ đã có điểm", "📖"
        )
        self._card_credit.grid(row=0, column=1, sticky="nsew", padx=(0, 10))

        self._card_gpa, self._val_gpa, self._sub_gpa = self._stat_card(
            cards_row, "Trung bình theo tín chỉ", "📊"
        )
        self._card_gpa.grid(row=0, column=2, sticky="nsew")

        # ── Grade table card ──────────────────────────────────────────────
        table_card = tk.Frame(wrapper, bg=SURFACE,
                              highlightbackground=BORDER, highlightthickness=1)
        table_card.pack(fill="x", pady=(0, 16))

        table_inner = tk.Frame(table_card, bg=SURFACE)
        table_inner.pack(fill="both", expand=True, padx=20, pady=16)

        # Table header row
        th_row = tk.Frame(table_inner, bg=SURFACE)
        th_row.pack(fill="x", pady=(0, 8))
        tk.Label(th_row, text="Bảng điểm của tôi",
                 bg=SURFACE, fg=TEXT, font=font(11, "bold"), anchor="w").pack(side="left")
        self._count_label = tk.Label(th_row, text="",
                                     bg=SURFACE, fg=MUTED, font=font(9))
        self._count_label.pack(side="right")

        tk.Label(table_inner,
                 text="Điểm cuối kỳ theo thang 0–10  •  Chỉ xem",
                 bg=SURFACE, fg=MUTED, font=font(8), anchor="w").pack(fill="x", pady=(0, 10))

        # Table
        configure_table_style(table_inner)
        self.tree = ttk.Treeview(
            table_inner,
            columns=[c[0] for c in _COLUMNS],
            show="headings",
            height=8,
            style="Grades.Treeview",
            selectmode="browse",
        )
        for key, label, width, anchor in _COLUMNS:
            self.tree.heading(key, text=label, anchor=anchor)
            self.tree.column(key, width=width, minwidth=50, anchor=anchor, stretch=True)

        self.tree.tag_configure("passed", foreground="#15803D")
        self.tree.tag_configure("failed", foreground="#B91C1C")
        self.tree.tag_configure("pending", foreground="#B45309")

        self.tree.pack(fill="x")

        # Total credits row
        tk.Frame(table_inner, bg=BORDER, height=1).pack(fill="x", pady=(8, 0))
        total_row = tk.Frame(table_inner, bg=SURFACE)
        total_row.pack(fill="x", pady=(8, 0))
        tk.Label(total_row, text="Tổng số tín chỉ đã ghi danh",
                 bg=SURFACE, fg=TEXT, font=font(9, "bold"), anchor="w").pack(side="left")
        self._total_credits_label = tk.Label(total_row, text="—",
                                             bg=SURFACE, fg=TEXT, font=font(9, "bold"))
        self._total_credits_label.pack(side="right")

        # ── GPA formula card ──────────────────────────────────────────────
        formula_card = tk.Frame(wrapper, bg=SURFACE,
                                highlightbackground=BORDER, highlightthickness=1)
        formula_card.pack(fill="x", pady=(0, 16))

        fi = tk.Frame(formula_card, bg=SURFACE)
        fi.pack(fill="both", expand=True, padx=20, pady=16)

        tk.Label(fi, text="Cách tính trung bình",
                 bg=SURFACE, fg=TEXT, font=font(11, "bold"), anchor="w").pack(fill="x")
        tk.Label(fi, text="Chỉ sử dụng các điểm cuối kỳ đã được ghi nhận.",
                 bg=SURFACE, fg=MUTED, font=font(8), anchor="w").pack(fill="x", pady=(2, 10))

        self._formula_label = tk.Label(fi, text="",
                                       bg=SURFACE, fg=TEXT, font=font(9, "bold"), anchor="w")
        self._formula_label.pack(fill="x")
        self._formula_detail = tk.Label(fi, text="",
                                        bg=SURFACE, fg=MUTED, font=font(8), anchor="w")
        self._formula_detail.pack(fill="x", pady=(2, 0))

        self._excluded_label = tk.Label(fi, text="",
                                        bg=SURFACE, fg="#B45309", font=font(8, "bold"), anchor="e")
        self._excluded_label.pack(fill="x")

        # ── Bottom note ───────────────────────────────────────────────────
        note = tk.Frame(wrapper, bg="#EFF6FF",
                        highlightbackground="#BFDBFE", highlightthickness=1)
        note.pack(fill="x", pady=(0, 24))
        ni = tk.Frame(note, bg="#EFF6FF")
        ni.pack(fill="x", padx=16, pady=12)
        tk.Label(ni, text="ℹ️", bg="#EFF6FF", font=font(10)).pack(side="left", anchor="n")
        tk.Label(
            ni,
            text="  Nếu cần kiểm tra lại điểm, vui lòng liên hệ giảng viên phụ trách. "
                 "Sinh viên không thể thay đổi kết quả học tập.",
            bg="#EFF6FF", fg="#1D4ED8", font=font(8),
            wraplength=800, justify="left",
        ).pack(side="left")

        self.feedback = tk.Label(wrapper, text="", bg=BACKGROUND,
                                 fg=DANGER, font=font(9), anchor="w", wraplength=860)
        self.feedback.pack(fill="x")

    @staticmethod
    def _stat_card(
        parent: tk.Misc, label: str, icon: str
    ) -> tuple[tk.Frame, tk.Label, tk.Label]:
        card = tk.Frame(parent, bg=SURFACE, highlightbackground=BORDER, highlightthickness=1)
        inner = tk.Frame(card, bg=SURFACE)
        inner.pack(fill="both", expand=True, padx=18, pady=16)

        top_row = tk.Frame(inner, bg=SURFACE)
        top_row.pack(fill="x")
        tk.Label(top_row, text=label, bg=SURFACE, fg=MUTED,
                 font=font(8), anchor="w").pack(side="left")
        tk.Label(top_row, text=icon, bg=SURFACE, fg=PRIMARY,
                 font=font(10)).pack(side="right")

        value_lbl = tk.Label(inner, text="—", bg=SURFACE, fg=PRIMARY_DARK,
                             font=font(20, "bold"), anchor="w")
        value_lbl.pack(fill="x", pady=(6, 2))

        sub_lbl = tk.Label(inner, text="", bg=SURFACE, fg=MUTED,
                           font=font(7), anchor="w")
        sub_lbl.pack(fill="x")

        return card, value_lbl, sub_lbl

    # ------------------------------------------------------------------ load

    def _load(self) -> None:
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            result = self._service.student_results(self._session)
        except (ServiceError, DataAccessError) as exc:
            self.student_label.configure(text="Không tải được kết quả học tập.")
            self.feedback.configure(text=str(exc))
            return

        # Student info line
        s = result.student
        self.student_label.configure(
            text=f"{s.full_name}  ·  {s.student_code}  ·  {s.class_name}"
        )

        graded = [g for g in result.grades if g.final_score is not None]
        pending = [g for g in result.grades if g.final_score is None]
        total_courses = len(result.grades)
        graded_courses = len(graded)

        # Stat cards
        self._val_course.configure(text=f"{graded_courses} / {total_courses}")
        self._sub_course.configure(
            text=f"{total_courses - graded_courses} học phần chưa có điểm"
        )

        self._val_credit.configure(text=f"{result.total_credits} / {result.passed_credits + result.total_credits - result.passed_credits}")
        # Recalculate for display: total_credits = credits of graded courses
        tc = sum(g.credits for g in graded)
        self._val_credit.configure(text=f"{tc} / {tc + sum(g.credits for g in pending)}")
        self._sub_credit.configure(
            text=f"Không bao gồm {sum(g.credits for g in pending)} tín chỉ chưa có điểm"
            if pending else "Tất cả học phần đã có điểm"
        )

        self._val_gpa.configure(
            text=format_score(result.gpa) + " / 10"
        )
        self._sub_gpa.configure(text="Tính trên các học phần đã có điểm")

        # Table rows
        for grade in result.grades:
            status_text = _status_display(grade.status)
            self.tree.insert(
                "", "end",
                values=(
                    grade.course_code,
                    grade.course_name,
                    grade.credits,
                    format_score(grade.final_score),
                    status_text,
                ),
                tags=row_tag(grade.status),
            )

        # Total credits
        all_credits = sum(g.credits for g in result.grades)
        self._total_credits_label.configure(text=f"{all_credits} tín chỉ")
        self._count_label.configure(text=f"{total_courses} học phần")

        # GPA formula
        if graded:
            parts = " + ".join(
                f"{format_score(g.final_score)} × {g.credits}" for g in graded
            )
            formula_sym = "Σ(điểm cuối kỳ × số tín chỉ) / Σ(tín chỉ của học phần đã có điểm)"
            tc_graded = sum(g.credits for g in graded)
            weighted = sum(g.final_score * g.credits for g in graded)
            gpa_calc = weighted / tc_graded if tc_graded else Decimal(0)

            self._formula_label.configure(text=formula_sym)
            self._formula_detail.configure(
                text=f"({parts}) / {tc_graded} = {float(gpa_calc):.2f}"
            )
            if pending:
                excluded = ", ".join(g.course_code for g in pending)
                self._excluded_label.configure(text=f"Không tính {excluded}")
        else:
            self._formula_label.configure(text="Chưa có học phần nào đủ điểm để tính trung bình.")


def _status_display(status: str | None) -> str:
    if not status:
        return "Chưa có điểm"
    mapping = {
        "PASSED": "Đã có điểm",
        "FAILED": "Không đạt",
        "PENDING": "Chưa có điểm",
    }
    return mapping.get(status.upper(), status)
