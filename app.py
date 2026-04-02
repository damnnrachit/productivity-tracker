from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from models import Task, User, db


def create_app() -> Flask:
    app_root = Path(__file__).resolve().parent
    app = Flask(__name__, template_folder=str(app_root / "templates"))
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    data_dir = app_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "app.db"

    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path.as_posix()}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "login_page"
    login_manager.login_message = "Please log in to continue."
    login_manager.session_protection = "strong"

    with app.app_context():
        db.create_all()

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        return db.session.get(User, int(user_id))

    def parse_due_date(value: str) -> date | None:
        clean = value.strip()
        if not clean:
            return None
        try:
            return date.fromisoformat(clean)
        except ValueError:
            return None

    def get_user_tasks() -> list[Task]:
        return (
            Task.query.filter_by(user_id=current_user.id)
            .order_by(Task.created_at.asc(), Task.id.asc())
            .all()
        )

    def get_task_by_index(index: int) -> Task:
        tasks = get_user_tasks()
        if not (0 <= index < len(tasks)):
            abort(404)
        return tasks[index]

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
        if User.query.filter(db.func.lower(User.username) == username.lower()).first() is not None:
            return render_template(
                "signup.html",
                error="Username already exists.",
                username=username,
            )

        user = User(username=username, password_hash=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        login_user(user, remember=False)
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
        user = User.query.filter(db.func.lower(User.username) == username.lower()).first()
        if user is None or not check_password_hash(user.password_hash, password):
            return render_template(
                "login.html",
                error="Invalid username or password.",
                username=username,
            )

        login_user(user, remember=False)
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
        tasks = get_user_tasks()
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
        title = request.form.get("title", "").strip()
        due_date_raw = request.form.get("due_date", "").strip()
        due_date = parse_due_date(due_date_raw)

        if not title:
            return render_template(
                "add.html",
                error="Title cannot be empty.",
                title=title,
                due_date=due_date_raw,
            )

        if due_date_raw and due_date is None:
            return render_template(
                "add.html",
                error="Due date must be a valid date.",
                title=title,
                due_date=due_date_raw,
            )

        db.session.add(Task(title=title, due_date=due_date, user_id=current_user.id))
        db.session.commit()
        return redirect(url_for("home"))

    @app.get("/review")
    @login_required
    def review_page():
        tasks = get_user_tasks()
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
        task = get_task_by_index(index)
        task.is_completed = True
        db.session.commit()
        return redirect(url_for("review_page"))

    @app.post("/review/<int:index>/delete")
    @login_required
    def delete_task(index: int):
        task = get_task_by_index(index)
        db.session.delete(task)
        db.session.commit()
        return redirect(url_for("review_page"))

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    host = os.environ.get("HOST", "0.0.0.0")
    debug = os.environ.get("FLASK_DEBUG", "0").strip().lower() in {"1", "true", "yes", "on"}
    app.run(host=host, port=port, debug=debug)