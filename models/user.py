from __future__ import annotations

from datetime import datetime

from flask_login import UserMixin

from .extensions import db


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    tasks = db.relationship("Task", backref="user", lazy=True, cascade="all, delete-orphan")
    study_sessions = db.relationship(
        "StudySession", backref="user", lazy=True, cascade="all, delete-orphan"
    )
