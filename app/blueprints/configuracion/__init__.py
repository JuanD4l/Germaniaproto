from flask import Blueprint

configuracion_bp = Blueprint("configuracion", __name__, url_prefix="/configuracion")

from app.blueprints.configuracion import routes  # noqa

