from datetime import datetime, timezone
import jwt
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app


def hash_password(password: str) -> str:
    """Genera hash seguro de contraseña usando algoritmo PBKDF2:SHA256 con salt."""
    return generate_password_hash(password, method="scrypt")


def verify_password(password: str, hashed_password: str) -> bool:
    """Verifica una contraseña contra su hash criptográfico."""
    if not password or not hashed_password:
        return False
    return check_password_hash(hashed_password, password)


def generate_jwt_token(payload_data: dict) -> str:
    """Genera un token JWT firmado con expiración segura."""
    secret = current_app.config["JWT_SECRET_KEY"]
    expires_delta = current_app.config["JWT_ACCESS_TOKEN_EXPIRES"]
    now = datetime.now(timezone.utc)

    claims = {
        **payload_data,
        "iat": now,
        "exp": now + expires_delta
    }
    return jwt.encode(claims, secret, algorithm="HS256")


def decode_jwt_token(token: str) -> dict:
    """Decodifica y valida un token JWT; lanza excepciones en caso de expiración o firma inválida."""
    secret = current_app.config["JWT_SECRET_KEY"]
    return jwt.decode(token, secret, algorithms=["HS256"])

