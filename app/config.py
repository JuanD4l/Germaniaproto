import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Configuración inmutable del Sistema Germania."""
    SECRET_KEY = os.getenv("SECRET_KEY", "germania_secret_key_sena_2026_super_segura_jwt_rbac")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "germania-jwt-secret-2026")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        minutes=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", "480"))
    )

    # Detección de PostgreSQL (Render)
    DATABASE_URL = os.getenv("DATABASE_URL")
    if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    if DATABASE_URL:
        DB_TYPE = "postgres"
    else:
        DB_TYPE = os.getenv("DB_TYPE", "sqlite")

    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "colegio_rural")

    SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", os.path.join(BASE_DIR, "..", "germania_local.db"))
    TEST_DB_PATH = os.path.join(BASE_DIR, "..", "test_germania_suite.db")

    TESTING = False
    DEBUG = False


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    DB_TYPE = "sqlite"
    TEST_DB_PATH = os.path.join(BASE_DIR, "..", "test_germania_suite.db")


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
