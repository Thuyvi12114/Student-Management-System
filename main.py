"""Điểm khởi động ứng dụng quản lý sinh viên."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

from app.context import AppContext
from app.ui.login_view import LoginView
from app.ui.main_view import MainView


def main() -> None:
    try:
        context = AppContext.create()
    except Exception as exc:  # Cấu hình thiếu hoặc driver chưa cài
        _show_startup_error(str(exc))
        return

    while True:
        login = LoginView(context.auth_service)
        login.mainloop()
        if login.session is None:
            break

        workspace = MainView(
            context.auth_service,
            context.grade_service,
            context.student_service,
            context.student_search_service,
            context.lecturer_service,
            context.account_service,
            context.course_service,
            context.profile_service,
            login.session,
        )
        workspace.mainloop()
        if not workspace.logout_requested:
            break


def _show_startup_error(message: str) -> None:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Lỗi cấu hình", message)
    root.destroy()


if __name__ == "__main__":
    main()
