from flask import Blueprint

reportes_bp = Blueprint("reportes", __name__, url_prefix="/api/v1/reportes")

from app.blueprints.reportes import routes  # noqa: E402, F401

