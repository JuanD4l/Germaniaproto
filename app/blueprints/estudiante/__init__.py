from flask import Blueprint

estudiante_bp = Blueprint("estudiante", __name__, url_prefix="/estudiante")

from app.blueprints.estudiante import routes  # noqa: E402, F401

