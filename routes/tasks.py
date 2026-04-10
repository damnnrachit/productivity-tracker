from __future__ import annotations

from datetime import date, datetime

from flask import Blueprint, abort, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from models import Task, db

tasks_bp = Blueprint("tasks", __name__)

PRIORITY_LEVELS = ("Low", "Medium", "High")


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


@tasks_bp.get("/")
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


@tasks_bp.get("/add")
@login_required
def add_task_page():
    return render_template(
        "add.html",
        error=None,
        title="",
        due_date="",
        category="General",
        priority="Medium",
        priorities=PRIORITY_LEVELS,
    )


@tasks_bp.post("/add")
@login_required
def add_task():
    title = request.form.get("title", "").strip()
    due_date_raw = request.form.get("due_date", "").strip()
    category = request.form.get("category", "").strip() or "General"
    priority = request.form.get("priority", "Medium").strip() or "Medium"
    due_date = parse_due_date(due_date_raw)

    if not title:
        return render_template(
            "add.html",
            error="Title cannot be empty.",
            title=title,
            due_date=due_date_raw,
            category=category,
            priority=priority,
            priorities=PRIORITY_LEVELS,
        )

    if priority not in PRIORITY_LEVELS:
        return render_template(
            "add.html",
            error="Priority must be Low, Medium, or High.",
            title=title,
            due_date=due_date_raw,
            category=category,
            priority=priority,
            priorities=PRIORITY_LEVELS,
        )

    if due_date_raw and due_date is None:
        return render_template(
            "add.html",
            error="Due date must be a valid date.",
            title=title,
            due_date=due_date_raw,
            category=category,
            priority=priority,
            priorities=PRIORITY_LEVELS,
        )

    db.session.add(
        Task(
            title=title,
            due_date=due_date,
            category=category,
            priority=priority,
            user_id=current_user.id,
        )
    )
    db.session.commit()
    return redirect(url_for("tasks.home"))


@tasks_bp.get("/review")
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


@tasks_bp.get("/review/<int:index>/edit")
@login_required
def edit_task_page(index: int):
    task = get_task_by_index(index)
    return render_template(
        "edit_task.html",
        error=None,
        index=index,
        title=task.title,
        due_date=task.due_date.isoformat() if task.due_date else "",
        category=task.category,
        priority=task.priority,
        priorities=PRIORITY_LEVELS,
    )


@tasks_bp.post("/review/<int:index>/edit")
@login_required
def edit_task(index: int):
    task = get_task_by_index(index)
    title = request.form.get("title", "").strip()
    due_date_raw = request.form.get("due_date", "").strip()
    category = request.form.get("category", "").strip() or "General"
    priority = request.form.get("priority", "Medium").strip() or "Medium"
    due_date = parse_due_date(due_date_raw)

    if not title:
        return render_template(
            "edit_task.html",
            error="Title cannot be empty.",
            index=index,
            title=title,
            due_date=due_date_raw,
            category=category,
            priority=priority,
            priorities=PRIORITY_LEVELS,
        )
    if priority not in PRIORITY_LEVELS:
        return render_template(
            "edit_task.html",
            error="Priority must be Low, Medium, or High.",
            index=index,
            title=title,
            due_date=due_date_raw,
            category=category,
            priority=priority,
            priorities=PRIORITY_LEVELS,
        )
    if due_date_raw and due_date is None:
        return render_template(
            "edit_task.html",
            error="Due date must be a valid date.",
            index=index,
            title=title,
            due_date=due_date_raw,
            category=category,
            priority=priority,
            priorities=PRIORITY_LEVELS,
        )

    task.title = title
    task.category = category
    task.priority = priority
    task.due_date = due_date
    db.session.commit()
    return redirect(url_for("tasks.review_page"))


@tasks_bp.post("/review/<int:index>/complete")
@login_required
def complete_task(index: int):
    task = get_task_by_index(index)
    if not task.is_completed:
        task.is_completed = True
        task.completed_at = datetime.utcnow()
        db.session.commit()
    return redirect(url_for("tasks.review_page"))


@tasks_bp.post("/review/<int:index>/delete")
@login_required
def delete_task(index: int):
    task = get_task_by_index(index)
    db.session.delete(task)
    db.session.commit()
    return redirect(url_for("tasks.review_page"))
