from flask import jsonify


def success_response(data=None, message="Operación exitosa", status_code=200):
    """Genera una respuesta JSON estandarizada de éxito."""
    payload = {
        "success": True,
        "message": message,
        "data": data if data is not None else {}
    }
    return jsonify(payload), status_code


def error_response(error_message, status_code=400, details=None):
    """Genera una respuesta JSON estandarizada de error."""
    payload = {
        "success": False,
        "error": error_message
    }
    if details:
        payload["details"] = details
    return jsonify(payload), status_code

