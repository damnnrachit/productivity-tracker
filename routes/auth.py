from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from models import User, db

auth_bp = Blueprint("auth", __name__)


@auth_bp.get("/signup")
def signup_page():
    if current_user.is_authenticated:
        return redirect(url_for("tasks.home"))
    return render_template("signup.html", error=None, username="")


@auth_bp.post("/signup")
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("tasks.home"))

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

    user_exists = User.query.filter(db.func.lower(User.username) == username.lower()).first()
    if user_exists is not None:
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
    return redirect(url_for("tasks.home"))


@auth_bp.get("/login")
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for("tasks.home"))
    return render_template("login.html", error=None, username="")


@auth_bp.post("/login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("tasks.home"))

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
    return redirect(url_for("tasks.home"))


@auth_bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully.", "info")
    return redirect(url_for("auth.login_page"))
