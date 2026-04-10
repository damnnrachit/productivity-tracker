from __future__ import annotations

import os
from pathlib import Path

from flask import Flask
from flask_login import LoginManager

from models import User, db
from routes import analytics_bp, auth_bp, spotify_bp, study_bp, tasks_bp


def run_sqlite_migrations() -> None:
    # Lightweight schema patching so old local DB files keep working.
    cols = {
        row[1]
        for row in db.session.execute(db.text("PRAGMA table_info(task)")).fetchall()
    }
    if "category" not in cols:
        db.session.execute(
            db.text("ALTER TABLE task ADD COLUMN category VARCHAR(80) NOT NULL DEFAULT 'General'")
        )
    if "priority" not in cols:
        db.session.execute(
            db.text("ALTER TABLE task ADD COLUMN priority VARCHAR(20) NOT NULL DEFAULT 'Medium'")
        )
    if "completed_at" not in cols:
        db.session.execute(db.text("ALTER TABLE task ADD COLUMN completed_at DATETIME"))
    db.session.commit()


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
    login_manager.login_view = "auth.login_page"
    login_manager.login_message = "Please log in to continue."
    login_manager.session_protection = "strong"

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        return db.session.get(User, int(user_id))

    app.register_blueprint(auth_bp)
    app.register_blueprint(tasks_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(study_bp)
    app.register_blueprint(spotify_bp)

    with app.app_context():
        db.create_all()
        run_sqlite_migrations()

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    host = os.environ.get("HOST", "0.0.0.0")
    debug = os.environ.get("FLASK_DEBUG", "0").strip().lower() in {"1", "true", "yes", "on"}
    app.run(host=host, port=port, debug=debug)