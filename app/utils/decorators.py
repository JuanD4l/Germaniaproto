from functools import wraps
from flask import request, g
import jwt
from app.utils.security import decode_jwt_token
from app.utils.responses import error_response


def jwt_requerido(f):
    """
    Middleware / decorador que intercepta la petición, verifica el Bearer Token JWT
    y fija la identidad en g.current_user.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization", None)
        if not auth_header:
            return error_response("Cabecera Authorization faltante", status_code=401)

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return error_response("Formato de token inválido. Use 'Bearer <token>'", status_code=401)

        token = parts[1]
        try:
            payload = decode_jwt_token(token)
            g.current_user = payload
        except jwt.ExpiredSignatureError:
            return error_response("El token ha expirado. Inicie sesión nuevamente", status_code=401)
        except (jwt.InvalidTokenError, Exception):
            return error_response("Token inválido o corrupto", status_code=401)

        return f(*args, **kwargs)
    return decorated_function


def requiere_rol(*roles_permitidos):
    """
    Control de acceso basado en roles (RBAC).
    Valida que el usuario autenticado posea al menos uno de los roles autorizados.
    Retorna 403 Forbidden si el rol no tiene privilegios.
    """
    def decorator(f):
        @wraps(f)
        @jwt_requerido
        def decorated_function(*args, **kwargs):
            user_role = g.current_user.get("rol_codigo")
            if user_role not in roles_permitidos:
                return error_response(
                    f"Acceso denegado: el rol '{user_role}' no cuenta con permisos para este recurso",
                    status_code=403
                )
            return f(*args, **kwargs)
        return decorated_function
    return decorator

