from flask import Blueprint

calificaciones_bp = Blueprint("calificaciones", __name__, url_prefix="/calificaciones")

from app.blueprints.calificaciones import routes  # noqa

