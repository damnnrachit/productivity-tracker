from .analytics import analytics_bp
from .auth import auth_bp
from .spotify import spotify_bp
from .study import study_bp
from .tasks import tasks_bp

__all__ = ["auth_bp", "tasks_bp", "analytics_bp", "study_bp", "spotify_bp"]
