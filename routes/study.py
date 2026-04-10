from __future__ import annotations

from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from models import StudySession, db

study_bp = Blueprint("study", __name__)


@study_bp.get("/study")
@login_required
def study_page():
    active_session = (
        StudySession.query.filter_by(user_id=current_user.id, end_time=None)
        .order_by(StudySession.start_time.desc())
        .first()
    )
    recent_sessions = (
        StudySession.query.filter_by(user_id=current_user.id)
        .order_by(StudySession.created_at.desc())
        .limit(10)
        .all()
    )
    total_seconds = (
        db.session.query(db.func.coalesce(db.func.sum(StudySession.duration_seconds), 0))
        .filter(StudySession.user_id == current_user.id, StudySession.end_time.isnot(None))
        .scalar()
        or 0
    )
    return render_template(
        "study.html",
        active_session=active_session,
        recent_sessions=recent_sessions,
        total_hours=round(total_seconds / 3600, 2),
    )


@study_bp.post("/study/start")
@login_required
def start_study():
    active_session = (
        StudySession.query.filter_by(user_id=current_user.id, end_time=None)
        .order_by(StudySession.start_time.desc())
        .first()
    )
    if active_session is not None:
        flash("A study session is already running.", "info")
        return redirect(url_for("study.study_page"))

    db.session.add(StudySession(user_id=current_user.id, start_time=datetime.utcnow()))
    db.session.commit()
    flash("Study timer started.", "success")
    return redirect(url_for("study.study_page"))


@study_bp.post("/study/stop")
@login_required
def stop_study():
    active_session = (
        StudySession.query.filter_by(user_id=current_user.id, end_time=None)
        .order_by(StudySession.start_time.desc())
        .first()
    )
    if active_session is None:
        flash("No active study session found.", "info")
        return redirect(url_for("study.study_page"))

    end_time = datetime.utcnow()
    duration = int((end_time - active_session.start_time).total_seconds())
    active_session.end_time = end_time
    active_session.duration_seconds = max(duration, 0)
    db.session.commit()
    flash("Study timer stopped.", "success")
    return redirect(url_for("study.study_page"))
