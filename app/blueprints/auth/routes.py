from flask import request, g
from app.blueprints.auth import auth_bp
from app.database import query_db, execute_db
from app.utils.security import hash_password, verify_password, generate_jwt_token
from app.utils.decorators import jwt_requerido
from app.utils.responses import success_response, error_response


@auth_bp.route("/roles", methods=["GET"])
def listar_roles():
    """Catálogo de roles del sistema."""
    roles = query_db("SELECT id_rol, codigo, nombre, descripcion FROM rol ORDER BY id_rol ASC")
    return success_response(roles, "Roles obtenidos exitosamente")


@auth_bp.route("/registro", methods=["POST"])
def registrar_usuario():
    """
    Registro formal de usuarios en la base de datos relacional.
    Previene duplicados en documento (409 Conflict) y email.
    """
    data = request.get_json(silent=True)
    if not data:
        return error_response("El cuerpo de la petición debe ser JSON válido", status_code=400)

    campos_requeridos = ["id_rol", "tipo_documento", "documento", "nombre", "apellido", "contrasena"]
    for campo in campos_requeridos:
        if not data.get(campo):
            return error_response(f"El campo '{campo}' es obligatorio", status_code=400)

    id_rol = data["id_rol"]
    tipo_documento = str(data["tipo_documento"]).strip().upper()
    documento = str(data["documento"]).strip()
    nombre = str(data["nombre"]).strip()
    apellido = str(data["apellido"]).strip()
    contrasena = str(data["contrasena"]).strip()
    email = data.get("email")
    email = str(email).strip().lower() if email else None
    telefono = data.get("telefono")
    telefono = str(telefono).strip() if telefono else None

    # Validar que el rol exista
    rol = query_db("SELECT id_rol, codigo FROM rol WHERE id_rol = %s", (id_rol,), one=True)
    if not rol:
        return error_response("El id_rol especificado no existe", status_code=400)

    # Validar unicidad de documento (Prevención de duplicados - 409 Conflict)
    existente_doc = query_db(
        "SELECT id_usuario FROM usuario WHERE tipo_documento = %s AND documento = %s",
        (tipo_documento, documento),
        one=True
    )
    if existente_doc:
        return error_response(
            "Conflicto: Ya existe un usuario registrado con ese tipo y número de documento",
            status_code=409
        )

    # Validar unicidad de email si fue suministrado
    if email:
        existente_email = query_db("SELECT id_usuario FROM usuario WHERE email = %s", (email,), one=True)
        if existente_email:
            return error_response("Conflicto: El correo electrónico ya se encuentra registrado", status_code=409)

    hashed_pw = hash_password(contrasena)

    resultado = execute_db(
        """
        INSERT INTO usuario (id_rol, tipo_documento, documento, nombre, apellido, email, contrasena, telefono)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (id_rol, tipo_documento, documento, nombre, apellido, email, hashed_pw, telefono)
    )

    return success_response(
        {
            "id_usuario": resultado["lastrowid"],
            "tipo_documento": tipo_documento,
            "documento": documento,
            "nombre": nombre,
            "apellido": apellido,
            "email": email,
            "id_rol": id_rol,
            "rol_codigo": rol["codigo"]
        },
        message="Usuario registrado exitosamente",
        status_code=201
    )


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Inicio de sesión seguro.
    Permite autenticación por (tipo_documento + documento) o por email.
    Emite token JWT con payload de identidad y rol.
    """
    data = request.get_json(silent=True)
    if not data:
        return error_response("El cuerpo de la petición debe ser JSON válido", status_code=400)

    contrasena = data.get("contrasena")
    if not contrasena:
        return error_response("La contraseña es obligatoria", status_code=400)

    identificador = data.get("identificador")
    tipo_documento = data.get("tipo_documento")

    usuario = None
    if tipo_documento and identificador:
        tipo_documento = str(tipo_documento).strip().upper()
        documento = str(identificador).strip()
        sql = """
            SELECT u.id_usuario, u.id_rol, u.tipo_documento, u.documento, u.nombre,
                   u.apellido, u.email, u.contrasena, u.estado, r.codigo AS rol_codigo, r.nombre AS rol_nombre
            FROM usuario u
            JOIN rol r ON r.id_rol = u.id_rol
            WHERE u.tipo_documento = %s AND u.documento = %s
        """
        usuario = query_db(sql, (tipo_documento, documento), one=True)
    elif identificador:
        identificador = str(identificador).strip()
        sql = """
            SELECT u.id_usuario, u.id_rol, u.tipo_documento, u.documento, u.nombre,
                   u.apellido, u.email, u.contrasena, u.estado, r.codigo AS rol_codigo, r.nombre AS rol_nombre
            FROM usuario u
            JOIN rol r ON r.id_rol = u.id_rol
            WHERE u.email = %s OR u.documento = %s
        """
        usuario = query_db(sql, (identificador, identificador), one=True)
    else:
        return error_response("Debe proveer documento con tipo_documento o correo electrónico", status_code=400)

    if not usuario:
        return error_response("Credenciales inválidas", status_code=401)

    if usuario["estado"] != "activo":
        return error_response("Usuario inactivo o suspendido. Contacte a Rectoría", status_code=403)

    if not verify_password(contrasena, usuario["contrasena"]):
        return error_response("Credenciales inválidas", status_code=401)

    token = generate_jwt_token({
        "id_usuario": usuario["id_usuario"],
        "id_rol": usuario["id_rol"],
        "rol_codigo": usuario["rol_codigo"],
        "documento": usuario["documento"],
        "tipo_documento": usuario["tipo_documento"],
        "email": usuario["email"],
        "nombre_completo": f"{usuario['nombre']} {usuario['apellido']}"
    })

    return success_response({
        "token": token,
        "usuario": {
            "id_usuario": usuario["id_usuario"],
            "nombre": usuario["nombre"],
            "apellido": usuario["apellido"],
            "tipo_documento": usuario["tipo_documento"],
            "documento": usuario["documento"],
            "email": usuario["email"],
            "rol_codigo": usuario["rol_codigo"],
            "rol_nombre": usuario["rol_nombre"]
        }
    }, message="Inicio de sesión exitoso")


@auth_bp.route("/me", methods=["GET"])
@jwt_requerido
def obtener_perfil():
    """Retorna los datos de identidad y claims del usuario autenticado."""
    id_usuario = g.current_user["id_usuario"]
    sql = """
        SELECT u.id_usuario, u.id_rol, u.tipo_documento, u.documento, u.nombre,
               u.apellido, u.email, u.telefono, u.fecha_creacion, u.estado,
               r.codigo AS rol_codigo, r.nombre AS rol_nombre
        FROM usuario u
        JOIN rol r ON r.id_rol = u.id_rol
        WHERE u.id_usuario = %s
    """
    usuario = query_db(sql, (id_usuario,), one=True)
    if not usuario:
        return error_response("Usuario no encontrado en base de datos", status_code=404)

    return success_response(usuario, "Perfil de usuario obtenido")
