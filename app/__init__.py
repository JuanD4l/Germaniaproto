from flask import Flask
from app.config import CONFIG_MAP
from app.database import close_db
from app.utils.responses import error_response


def create_app(config_name="development"):
    """
    Application Factory para el Sistema de Gestión Escolar Germania.
    Inicializa configuración, base de datos, manejadores de error y blueprints.
    """
    app = Flask(__name__)
    config_class = CONFIG_MAP.get(config_name, CONFIG_MAP["default"])
    app.config.from_object(config_class)

    # Registrar teardown para liberar conexiones a BD
    app.teardown_appcontext(close_db)

    # Registrar Blueprints API & Web
    from app.blueprints.auth import auth_bp
    from app.blueprints.academico import academico_bp
    from app.blueprints.asistencia import asistencia_bp
    from app.blueprints.web import web_bp
    from app.blueprints.estudiante import estudiante_bp
    from app.blueprints.reportes import reportes_bp
    from app.blueprints.calificaciones import calificaciones_bp
    from app.blueprints.configuracion import configuracion_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(academico_bp)
    app.register_blueprint(asistencia_bp)
    app.register_blueprint(web_bp)
    app.register_blueprint(estudiante_bp)
    app.register_blueprint(reportes_bp)
    app.register_blueprint(calificaciones_bp)
    app.register_blueprint(configuracion_bp)

    # Handlers globales de error HTTP para peticiones JSON
    @app.errorhandler(400)
    def handle_bad_request(e):
        return error_response("Petición incorrecta o parámetros inválidos", status_code=400)

    @app.errorhandler(401)
    def handle_unauthorized(e):
        return error_response("No autorizado. Credenciales o token requeridos", status_code=401)

    @app.errorhandler(403)
    def handle_forbidden(e):
        return error_response("Acceso prohibido. Permisos insuficientes", status_code=403)

    @app.errorhandler(404)
    def handle_not_found(e):
        return error_response("El recurso solicitado no fue encontrado", status_code=404)

    @app.errorhandler(409)
    def handle_conflict(e):
        return error_response("Conflicto en la solicitud: el recurso ya existe", status_code=409)

    @app.errorhandler(422)
    def handle_unprocessable_entity(e):
        return error_response("Entidad no procesable: violación de reglas de negocio", status_code=422)

    @app.errorhandler(500)
    def handle_internal_error(e):
        return error_response("Error interno del servidor", status_code=500)

    @app.route("/api/v1/health", methods=["GET"])
    def health_check():
        return {
            "success": True,
            "status": "online",
            "service": "Germania SIE & SAT API",
            "version": "2.0.0"
        }, 200

    return app
