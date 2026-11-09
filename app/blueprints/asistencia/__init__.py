from flask import Blueprint

asistencia_bp = Blueprint("asistencia", __name__, url_prefix="/api/v1")

from app.blueprints.asistencia import routes  # noqa: E402, F401

