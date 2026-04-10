from __future__ import annotations

from datetime import datetime, timedelta

from flask import Blueprint, render_template
from flask_login import current_user, login_required

from models import StudySession, Task, db

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.get("/analytics")
@login_required
def analytics_dashboard():
    today = datetime.utcnow().date()
    last_7_days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    labels = [d.strftime("%a") for d in last_7_days]

    completed_by_day: list[int] = []
    productivity_by_day: list[float] = []
    study_hours_by_day: list[float] = []

    for day in last_7_days:
        day_start = datetime.combine(day, datetime.min.time())
        day_end = day_start + timedelta(days=1)

        completed_count = (
            Task.query.filter(
                Task.user_id == current_user.id,
                Task.completed_at.isnot(None),
                Task.completed_at >= day_start,
                Task.completed_at < day_end,
            ).count()
        )
        total_created = (
            Task.query.filter(
                Task.user_id == current_user.id,
                Task.created_at >= day_start,
                Task.created_at < day_end,
            ).count()
        )
        productivity_pct = (completed_count / total_created * 100.0) if total_created else 0.0
        study_seconds = (
            db.session.query(db.func.coalesce(db.func.sum(StudySession.duration_seconds), 0))
            .filter(
                StudySession.user_id == current_user.id,
                StudySession.end_time.isnot(None),
                StudySession.end_time >= day_start,
                StudySession.end_time < day_end,
            )
            .scalar()
            or 0
        )

        completed_by_day.append(int(completed_count))
        productivity_by_day.append(round(productivity_pct, 2))
        study_hours_by_day.append(round(study_seconds / 3600, 2))

    return render_template(
        "analytics.html",
        labels=labels,
        completed_by_day=completed_by_day,
        productivity_by_day=productivity_by_day,
        study_hours_by_day=study_hours_by_day,
    )
