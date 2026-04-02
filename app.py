from __future__ import annotations

import json
import os
import uuid

from flask import Flask, abort, flash, redirect, render_template, request, url_for
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash
from pathlib import Path

from task_manager import TaskManager


class AppUser(UserMixin):
    def __init__(self, user_id: str, username: str) -> None:
        self.id = user_id
        self.username = username


def create_app() -> Flask:
    app_root = Path(__file__).resolve().parent
    app = Flask(__name__, template_folder=str(app_root / "templates"))
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "login_page"
    login_manager.login_message = "Please log in to continue."
    login_manager.session_protection = "strong"
    data_dir = app_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    users_file = data_dir / "users.json"

    def load_users() -> list[dict[str, str]]:
        if not users_file.exists():
            return []
        try:
            data = json.loads(users_file.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                return []
            users: list[dict[str, str]] = []
            for item in data:
                if not isinstance(item, dict):
                    continue
                user_id = str(item.get("id", "")).strip()
                username = str(item.get("username", "")).strip()
                password_hash = str(item.get("password_hash", "")).strip()
                if user_id and username and password_hash:
                    users.append(
                        {"id": user_id, "username": username, "password_hash": password_hash}
                    )
            return users
        except (json.JSONDecodeError, OSError):
            return []

    def save_users(users: list[dict[str, str]]) -> None:
        users_file.parent.mkdir(parents=True, exist_ok=True)
        users_file.write_text(json.dumps(users, indent=2), encoding="utf-8")

    def find_user_by_id(user_id: str) -> dict[str, str] | None:
        for user in load_users():
            if user["id"] == user_id:
                return user
        return None

    def find_user_by_username(username: str) -> dict[str, str] | None:
        target = username.strip().lower()
        for user in load_users():
            if user["username"].lower() == target:
                return user
        return None

    @login_manager.user_loader
    def load_user(user_id: str) -> AppUser | None:
        user = find_user_by_id(user_id)
        if user is None:
            return None
        return AppUser(user_id=user["id"], username=user["username"])

    def get_manager() -> TaskManager:
        user_id = current_user.get_id()
        if not user_id:
            abort(401)
        file_path = data_dir / f"tasks_{user_id}.json"
        return TaskManager(file_path=file_path)

    @app.get("/signup")
    def signup_page():
        if current_user.is_authenticated:
            return redirect(url_for("home"))
        return render_template("signup.html", error=None, username="")

    @app.post("/signup")
    def signup():
        if current_user.is_authenticated:
            return redirect(url_for("home"))

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username:
            return render_template("signup.html", error="Username is required.", username=username)
        if len(username) < 3:
            return render_template(
                "signup.html",
                error="Username must be at least 3 characters.",
                username=username,
            )
        if len(password) < 6:
            return render_template(
                "signup.html",
                error="Password must be at least 6 characters.",
                username=username,
            )
        if password != confirm_password:
            return render_template(
                "signup.html",
                error="Passwords do not match.",
                username=username,
            )
        if find_user_by_username(username) is not None:
            return render_template(
                "signup.html",
                error="Username already exists.",
                username=username,
            )

        users = load_users()
        user_id = uuid.uuid4().hex
        users.append(
            {
                "id": user_id,
                "username": username,
                "password_hash": generate_password_hash(password),
            }
        )
        save_users(users)
        login_user(AppUser(user_id=user_id, username=username), remember=False)
        flash("Signup successful. Welcome!", "success")
        return redirect(url_for("home"))

    @app.get("/login")
    def login_page():
        if current_user.is_authenticated:
            return redirect(url_for("home"))
        return render_template("login.html", error=None, username="")

    @app.post("/login")
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("home"))

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = find_user_by_username(username)
        if user is None or not check_password_hash(user["password_hash"], password):
            return render_template(
                "login.html",
                error="Invalid username or password.",
                username=username,
            )

        login_user(AppUser(user_id=user["id"], username=user["username"]), remember=False)
        flash("Logged in successfully.", "success")
        return redirect(url_for("home"))

    @app.post("/logout")
    @login_required
    def logout():
        logout_user()
        flash("Logged out successfully.", "info")
        return redirect(url_for("login_page"))

    @app.get("/")
    @login_required
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
    @login_required
    def add_task_page():
        return render_template("add.html", error=None, title="", due_date="")

    @app.post("/add")
    @login_required
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
    @login_required
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
    @login_required
    def complete_task(index: int):
        manager = get_manager()
        try:
            manager.mark_complete(index)
        except IndexError:
            abort(404)
        return redirect(url_for("review_page"))

    @app.post("/review/<int:index>/delete")
    @login_required
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