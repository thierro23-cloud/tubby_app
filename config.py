# =============================================================================
# ⚙️ CONFIGURACIÓN GLOBAL DE LA APLICACIÓN FLASK (HARDENED)
# =============================================================================
#
# 🔐 MEJORAS DE SEGURIDAD APLICADAS:
#   1) Se eliminan secretos hardcodeados del código fuente.
#   2) Todas las credenciales se leen desde variables de entorno.
#   3) Se refuerzan cookies/sesión para entorno producción.
#   4) Se corrige estructura de aliases de BD (sin claves duplicadas).
#   5) Se añade validación básica de variables críticas.
# autor Tinito
# ✅ COMPATIBLE:
#   - Local (tu portátil)
#   - Remoto (servidor)
#   Solo cambias .env / variables de entorno, no el código.
# =============================================================================

from __future__ import annotations
import os


# =============================================================================
# 0) HELPERS DE ENTORNO
# =============================================================================
def _env(name: str, default: str | None = None) -> str | None:
    """
    Lee variable de entorno y hace strip.

    Args:
        name: Nombre de la variable.
        default: Valor por defecto si no existe.

    Returns:
        str | None
    """
    value = os.getenv(name, default)
    if isinstance(value, str):
        return value.strip()
    return value


def _env_int(name: str, default: int) -> int:
    """
    Lee entero desde entorno con fallback seguro.
    """
    raw = _env(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    """
    Lee booleano desde entorno.
    Valores true: 1, true, yes, y, on
    """
    raw = _env(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "y", "on"}


# =============================================================================
# 1) CONFIG PRINCIPAL DE FLASK
# =============================================================================
class Config:
    # -------------------------------------------------------------------------
    # 1.1 SECRET KEY
    # -------------------------------------------------------------------------
    # En producción debe venir SIEMPRE del entorno.
    SECRET_KEY = _env("SECRET_KEY", "dev-only-change-me-in-production")

    # -------------------------------------------------------------------------
    # 1.2 MODO ENTORNO
    # -------------------------------------------------------------------------
    FLASK_ENV = _env("FLASK_ENV", "development")
    DEBUG = _env_bool("FLASK_DEBUG", FLASK_ENV == "development")

    # -------------------------------------------------------------------------
    # 1.3 HARDENING DE SESIÓN/COOKIES
    # -------------------------------------------------------------------------
    # Recomendado:
    # - Local HTTP: COOKIE_SECURE=False
    # - Producción HTTPS: COOKIE_SECURE=True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = _env("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", FLASK_ENV == "production")

    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = _env("REMEMBER_COOKIE_SAMESITE", "Lax")
    REMEMBER_COOKIE_SECURE = _env_bool("REMEMBER_COOKIE_SECURE", FLASK_ENV == "production")

    # Si quieres forzar login siempre al cerrar navegador:
    SESSION_PERMANENT = _env_bool("SESSION_PERMANENT", False)

    # -------------------------------------------------------------------------
    # 1.4 AJUSTES GENERALES
    # -------------------------------------------------------------------------
    TEMPLATES_AUTO_RELOAD = True

    # -------------------------------------------------------------------------
    # 1.5 CONFIGURACIÓN LLM
    # -------------------------------------------------------------------------
    LLM_BACKEND = _env("LLM_BACKEND", "ollama")
    LLM_MODEL = _env("LLM_MODEL", "gemma3:4b")
    LLM_TIMEOUT = _env_int("LLM_TIMEOUT", 90)

    # -------------------------------------------------------------------------
    # 1.6 PARÁMETROS BASE DE MYSQL (reutilizables por todas las BDs)
    # -------------------------------------------------------------------------
    _DB_HOST = _env("DB_HOST", "127.0.0.1")
    _DB_USER = _env("DB_USER", "root")
    _DB_PASSWORD = _env("DB_PASSWORD", "")
    _DB_PORT = _env_int("DB_PORT", 3306)

    # -------------------------------------------------------------------------
    # 1.7 DICCIONARIO DE BASES DE DATOS (DATABASES)
    # -------------------------------------------------------------------------
    # Puedes sobrescribir por entorno cada BD con:
    #   DB_<ALIAS>_NAME
    # Ejemplo:
    #   DB_PARQUIN_CAMIONES_NAME=parquin_camiones
    #   DB_BD_TBL_COMUNES_NAME=bd_tbl_comunes
    DATABASES = {
        "bd_tbl_comunes": {
            "HOST": _DB_HOST,
            "USER": _DB_USER,
            "PASSWORD": _DB_PASSWORD,
            "DB": _env("DB_BD_TBL_COMUNES_NAME", "bd_tbl_comunes"),
            "PORT": _DB_PORT,
        },
        "control_via_publica": {
            "HOST": _DB_HOST,
            "USER": _DB_USER,
            "PASSWORD": _DB_PASSWORD,
            "DB": _env("DB_CONTROL_VIA_PUBLICA_NAME", "control_via_publica"),
            "PORT": _DB_PORT,
        },
        # Alias antiguo "obras" -> misma BD física
        "obras": {
            "HOST": _DB_HOST,
            "USER": _DB_USER,
            "PASSWORD": _DB_PASSWORD,
            "DB": _env("DB_CONTROL_VIA_PUBLICA_NAME", "control_via_publica"),
            "PORT": _DB_PORT,
        },
        "gis_municipal": {
            "HOST": _DB_HOST,
            "USER": _DB_USER,
            "PASSWORD": _DB_PASSWORD,
            "DB": _env("DB_GIS_MUNICIPAL_NAME", "gis_municipal"),
            "PORT": _DB_PORT,
        },
        "inventario": {
            "HOST": _DB_HOST,
            "USER": _DB_USER,
            "PASSWORD": _DB_PASSWORD,
            "DB": _env("DB_INVENTARIO_NAME", "inventario"),
            "PORT": _DB_PORT,
        },
        "mobiliario_urbano": {
            "HOST": _DB_HOST,
            "USER": _DB_USER,
            "PASSWORD": _DB_PASSWORD,
            "DB": _env("DB_MOBILIARIO_URBANO_NAME", "mobiliario_urbano"),
            "PORT": _DB_PORT,
        },
        "parquin_camiones": {
            "HOST": _DB_HOST,
            "USER": _DB_USER,
            "PASSWORD": _DB_PASSWORD,
            "DB": _env("DB_PARQUIN_CAMIONES_NAME", "parquin_camiones"),
            "PORT": _DB_PORT,
        },
        "patrulla_verde": {
            "HOST": _DB_HOST,
            "USER": _DB_USER,
            "PASSWORD": _DB_PASSWORD,
            "DB": _env("DB_PATRULLA_VERDE_NAME", "patrulla_verde"),
            "PORT": _DB_PORT,
        },
        "personal_vestuario": {
            "HOST": _DB_HOST,
            "USER": _DB_USER,
            "PASSWORD": _DB_PASSWORD,
            "DB": _env("DB_PERSONAL_VESTUARIO_NAME", "personal_vestuario"),
            "PORT": _DB_PORT,
        },
        "plan_de_emergencias": {
            "HOST": _DB_HOST,
            "USER": _DB_USER,
            "PASSWORD": _DB_PASSWORD,
            "DB": _env("DB_PLAN_DE_EMERGENCIAS_NAME", "plan_de_emergencias"),
            "PORT": _DB_PORT,
        },
    }

    # -------------------------------------------------------------------------
    # 1.8 VALIDACIONES BÁSICAS DE SEGURIDAD (opcional, pero recomendable)
    # -------------------------------------------------------------------------
    @classmethod
    def validar_seguridad(cls) -> list[str]:
        """
        Devuelve lista de advertencias de seguridad detectadas.
        """
        warnings: list[str] = []

        if cls.FLASK_ENV == "production":
            if not cls.SECRET_KEY or "dev-only" in cls.SECRET_KEY:
                warnings.append("SECRET_KEY insegura en producción.")
            if not cls.SESSION_COOKIE_SECURE:
                warnings.append("SESSION_COOKIE_SECURE debería ser True en producción.")
            if not cls.REMEMBER_COOKIE_SECURE:
                warnings.append("REMEMBER_COOKIE_SECURE debería ser True en producción.")
            if cls.DEBUG:
                warnings.append("DEBUG no debería estar activo en producción.")

        return warnings


# =============================================================================
# 2) CONFIG WATCHER ENDPOINTS
# =============================================================================
class WatcherConfig:
    """
    Configuración específica del sistema de vigilancia de endpoints.
    """

    LOG_FILE = _env("WATCHER_LOG_FILE", "endpoints_watcher.log")
    LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
    LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    LOG_LEVEL = _env("WATCHER_LOG_LEVEL", "INFO")

    DEBOUNCE_SECONDS = _env_int("WATCHER_DEBOUNCE_SECONDS", 2)
    WATCH_RECURSIVE = _env_bool("WATCHER_RECURSIVE", True)

    ENDPOINTS_DATABASE = _env("WATCHER_ENDPOINTS_DATABASE", "bd_tbl_comunes")
    ENDPOINTS_TABLE = _env("WATCHER_ENDPOINTS_TABLE", "tbl_endpoints")
    ENDPOINTS_TABLE = "tbl_endpoints"
