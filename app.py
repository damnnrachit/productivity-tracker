from __future__ import annotations

import os
import uuid

from flask import Flask, abort, redirect, render_template, request, session, url_for
from flask_login import LoginManager, UserMixin, current_user, login_user
from pathlib import Path

from task_manager import TaskManager


class SessionUser(UserMixin):
    def __init__(self, user_id: str) -> None:
        self.id = user_id


def create_app() -> Flask:
    app_root = Path(__file__).resolve().parent
    app = Flask(__name__, template_folder=str(app_root / "templates"))
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.session_protection = "strong"
    data_dir = app_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    @login_manager.user_loader
    def load_user(user_id: str) -> SessionUser:
        return SessionUser(user_id)

    @app.before_request
    def ensure_user() -> None:
        # Session-scoped identity so multiple users get unique JSON storage.
        if "user_id" not in session:
            session["user_id"] = uuid.uuid4().hex
        if not current_user.is_authenticated:
            login_user(SessionUser(session["user_id"]), remember=False)

    def get_manager() -> TaskManager:
        user_id = current_user.get_id() or session["user_id"]
        file_path = data_dir / f"tasks_{user_id}.json"
        return TaskManager(file_path=file_path)

    @app.get("/")
    def home():
        manager = get_manager()
        tasks = manager.tasks
        total = len(tasks)
        completed = sum(1 for t in tasks if t.is_completed)
        completion_pct = round((completed / total) * 100, 2) if total else 0.0
        return render_template(
            "index.html",
            tasks=tasks,
            total=total,
            completed=completed,
            completion_pct=completion_pct,
        )

    @app.get("/add")
    def add_task_page():
        return render_template("add.html", error=None, title="", due_date="")

    @app.post("/add")
    def add_task():
        manager = get_manager()
        title = request.form.get("title", "").strip()
        due_date = request.form.get("due_date", "").strip()

        if not title:
            return render_template(
                "add.html",
                error="Title cannot be empty.",
                title=title,
                due_date=due_date,
            )

        try:
            manager.add_task(title, due_date=due_date)
        except ValueError as exc:
            return render_template(
                "add.html",
                error=str(exc),
                title=title,
                due_date=due_date,
            )

        return redirect(url_for("home"))

    @app.get("/review")
    def review_page():
        manager = get_manager()
        tasks = manager.tasks
        total = len(tasks)
        completed = sum(1 for t in tasks if t.is_completed)
        completion_pct = round((completed / total) * 100, 2) if total else 0.0
        return render_template(
            "review.html",
            tasks=tasks,
            total=total,
            completed=completed,
            completion_pct=completion_pct,
        )

    @app.post("/review/<int:index>/complete")
    def complete_task(index: int):
        manager = get_manager()
        try:
            manager.mark_complete(index)
        except IndexError:
            abort(404)
        return redirect(url_for("review_page"))

    @app.post("/review/<int:index>/delete")
    def delete_task(index: int):
        manager = get_manager()
        try:
            manager.delete_task(index)
        except IndexError:
            abort(404)
        return redirect(url_for("review_page"))

    return app


app = create_app()

if __name__ == "__main__":
    import os

    port = int(os.environ.get("PORT", "5000"))
    host = os.environ.get("HOST", "0.0.0.0")
    debug = os.environ.get("FLASK_DEBUG", "0").strip().lower() in {"1", "true", "yes", "on"}
    app.run(host=host, port=port, debug=debug)

# Legacy Tkinter GUI is kept below as reference (commented out).
"""

import tkinter as tk
from tkinter import messagebox
from tkinter import font as tkfont

from models import TaskManager

try:
    import customtkinter as ctk

    HAS_CUSTOMTKINTER = True
except ImportError:
    ctk = None
    HAS_CUSTOMTKINTER = False


class TodoApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Daily Productivity Tracker")
        self.geometry("700x560")
        self.minsize(540, 420)
        self._center_window()

        self.manager = TaskManager("tasks.json")

        self.dark_bg = "#1E1E1E"
        self.panel_bg = "#2B2B2B"
        self.text_color = "#E8E8E8"
        self.muted_color = "#8B8B8B"
        self.accent_color = "#3B82F6"

        self.default_font = tkfont.nametofont("TkDefaultFont").copy()
        self.done_font = self.default_font.copy()
        self.done_font.configure(overstrike=1)

        if HAS_CUSTOMTKINTER:
            ctk.set_appearance_mode("dark")
            ctk.set_default_color_theme("dark-blue")

        self.configure(bg=self.dark_bg)
        self.task_vars: list[tk.BooleanVar] = []

        self._build_ui()
        self.refresh_task_list()
        self.bind("<Return>", lambda _event: self.add_task())

    def _center_window(self) -> None:
        self.update_idletasks()
        width = 700
        height = 560
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = (screen_w // 2) - (width // 2)
        y = (screen_h // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _build_ui(self) -> None:
        if HAS_CUSTOMTKINTER:
            self._build_ui_custom()
        else:
            self._build_ui_tk()

    def _build_ui_custom(self) -> None:
        self.main_frame = ctk.CTkFrame(self, corner_radius=10)
        self.main_frame.pack(fill="both", expand=True, padx=12, pady=12)

        input_frame = ctk.CTkFrame(self.main_frame)
        input_frame.pack(fill="x", padx=12, pady=(12, 8))

        self.task_entry = ctk.CTkEntry(input_frame, placeholder_text="Enter a task...")
        self.task_entry.pack(side="left", fill="x", expand=True, padx=(10, 8), pady=10)

        self.add_button = ctk.CTkButton(
            input_frame,
            text="Add Task",
            command=self.add_task,
            width=120,
        )
        self.add_button.pack(side="right", padx=(0, 10), pady=10)

        self.scrollable = ctk.CTkScrollableFrame(self.main_frame)
        self.scrollable.pack(fill="both", expand=True, padx=12, pady=8)

        controls_frame = ctk.CTkFrame(self.main_frame)
        controls_frame.pack(fill="x", padx=12, pady=(0, 8))

        self.clear_button = ctk.CTkButton(
            controls_frame,
            text="Clear Completed",
            command=self.clear_completed,
            fg_color="#DC2626",
            hover_color="#B91C1C",
            width=150,
        )
        self.clear_button.pack(side="right", padx=10, pady=10)

        self.status_label = ctk.CTkLabel(self.main_frame, text="")
        self.status_label.pack(fill="x", padx=14, pady=(0, 10))

    def _build_ui_tk(self) -> None:
        self.main_frame = tk.Frame(self, bg=self.dark_bg)
        self.main_frame.pack(fill="both", expand=True, padx=12, pady=12)

        input_frame = tk.Frame(self.main_frame, bg=self.panel_bg)
        input_frame.pack(fill="x", padx=0, pady=(0, 10))

        self.task_entry = tk.Entry(
            input_frame,
            bg="#3A3A3A",
            fg=self.text_color,
            insertbackground=self.text_color,
            relief="flat",
            font=("Segoe UI", 11),
        )
        self.task_entry.pack(side="left", fill="x", expand=True, padx=(10, 8), pady=10, ipady=6)

        self.add_button = tk.Button(
            input_frame,
            text="Add Task",
            bg=self.accent_color,
            fg="white",
            activebackground="#2563EB",
            activeforeground="white",
            relief="flat",
            command=self.add_task,
            padx=14,
            pady=6,
        )
        self.add_button.pack(side="right", padx=(0, 10), pady=10)

        middle_wrap = tk.Frame(self.main_frame, bg=self.panel_bg)
        middle_wrap.pack(fill="both", expand=True, pady=(0, 10))

        self.canvas = tk.Canvas(
            middle_wrap,
            bg=self.panel_bg,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(middle_wrap, orient="vertical", command=self.canvas.yview)
        scrollbar.pack(side="right", fill="y")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.tasks_container = tk.Frame(self.canvas, bg=self.panel_bg)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.tasks_container, anchor="nw")

        self.tasks_container.bind(
            "<Configure>",
            lambda _event: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        controls_frame = tk.Frame(self.main_frame, bg=self.dark_bg)
        controls_frame.pack(fill="x")

        self.clear_button = tk.Button(
            controls_frame,
            text="Clear Completed",
            command=self.clear_completed,
            bg="#DC2626",
            fg="white",
            relief="flat",
            activebackground="#B91C1C",
            activeforeground="white",
            padx=10,
            pady=6,
        )
        self.clear_button.pack(side="right")

        self.status_label = tk.Label(
            self.main_frame,
            text="",
            bg=self.dark_bg,
            fg=self.muted_color,
            anchor="w",
            font=("Segoe UI", 10),
        )
        self.status_label.pack(fill="x", pady=(10, 2))

    def _on_canvas_configure(self, event: tk.Event) -> None:
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def _clear_task_widgets(self) -> None:
        if HAS_CUSTOMTKINTER:
            for child in self.scrollable.winfo_children():
                child.destroy()
        else:
            for child in self.tasks_container.winfo_children():
                child.destroy()
        self.task_vars.clear()

    def refresh_task_list(self) -> None:
        self._clear_task_widgets()
        for idx, task in enumerate(self.manager.tasks):
            var = tk.BooleanVar(value=task.is_completed)
            self.task_vars.append(var)
            self._render_task_row(idx, task.title, var, task.is_completed)
        self._update_status_bar()

    def _render_task_row(self, index: int, title: str, var: tk.BooleanVar, done: bool) -> None:
        text_color = self.muted_color if done else self.text_color

        if HAS_CUSTOMTKINTER:
            row = ctk.CTkFrame(self.scrollable, fg_color="#303030")
            row.pack(fill="x", padx=6, pady=5)

            chk = ctk.CTkCheckBox(
                row,
                text=title,
                variable=var,
                command=lambda i=index: self.toggle_task(i),
                text_color=text_color,
            )
            chk.pack(side="left", fill="x", expand=True, padx=(12, 8), pady=8)

            del_btn = ctk.CTkButton(
                row,
                text="X",
                width=30,
                command=lambda i=index: self.delete_task(i),
                fg_color="#4B5563",
                hover_color="#374151",
            )
            del_btn.pack(side="right", padx=(0, 10), pady=8)
        else:
            row = tk.Frame(self.tasks_container, bg=self.panel_bg)
            row.pack(fill="x", padx=8, pady=4)

            chk = tk.Checkbutton(
                row,
                text=title,
                variable=var,
                command=lambda i=index: self.toggle_task(i),
                bg=self.panel_bg,
                fg=text_color,
                activebackground=self.panel_bg,
                activeforeground=text_color,
                selectcolor="#404040",
                anchor="w",
                relief="flat",
                bd=0,
                highlightthickness=0,
            )
            chk.configure(font=self.done_font if done else self.default_font)
            chk.pack(side="left", fill="x", expand=True, padx=(6, 8), pady=6)

            del_btn = tk.Button(
                row,
                text="X",
                command=lambda i=index: self.delete_task(i),
                bg="#4B5563",
                fg="white",
                relief="flat",
                activebackground="#374151",
                activeforeground="white",
                padx=8,
                pady=2,
            )
            del_btn.pack(side="right", padx=(0, 6), pady=4)

    def _update_status_bar(self) -> None:
        total = len(self.manager.tasks)
        completed = sum(task.is_completed for task in self.manager.tasks)
        self.status_label.configure(text=f"Total Tasks: {total} | Completed: {completed}")

    def add_task(self) -> None:
        title = self.task_entry.get().strip()
        if not title:
            return
        try:
            self.manager.add_task(title)
            self.task_entry.delete(0, "end")
            self.refresh_task_list()
        except OSError as exc:
            messagebox.showerror("Save Error", f"Could not save task.\n{exc}")

    def toggle_task(self, index: int) -> None:
        try:
            self.manager.toggle_task(index)
            self.refresh_task_list()
        except OSError as exc:
            messagebox.showerror("Save Error", f"Could not update task.\n{exc}")

    def delete_task(self, index: int) -> None:
        try:
            self.manager.delete_task(index)
            self.refresh_task_list()
        except OSError as exc:
            messagebox.showerror("Save Error", f"Could not delete task.\n{exc}")

    def clear_completed(self) -> None:
        try:
            self.manager.clear_completed()
            self.refresh_task_list()
        except OSError as exc:
            messagebox.showerror("Save Error", f"Could not clear completed tasks.\n{exc}")


if __name__ == "__main__":
    app = TodoApp()
    app.mainloop()
"""
import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)