from flask import Blueprint

academico_bp = Blueprint("academico", __name__, url_prefix="/api/v1")

from app.blueprints.academico import routes  # noqa: E402, F401

