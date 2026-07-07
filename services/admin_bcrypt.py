# =============================================================================
# 🔐 ADMIN BCRYPT SERVICE · VERSIÓN PRO TOTAL
# =============================================================================

import bcrypt
import os
import logging

logger = logging.getLogger("tubby_app")

# =============================================================================
# 1️⃣ CARGA SEGURA DEL HASH
# =============================================================================

HASH_ADMIN = "$2b$12$3aA4jE6s8N.CMVwXqDx6gOmp4IzWVDpXEvvEm/20te6LATfmWvKui"


def _es_hash_bcrypt_valido(hash_str: str) -> bool:
    """
    Valida si el hash tiene formato bcrypt.
    """
    return hash_str.startswith("$2b$") or hash_str.startswith("$2a$")


if not HASH_ADMIN:
    logger.critical("❌ ADMIN_HASH no definida")

    # 🔹 MODO DESARROLLO CONTROLADO
    if os.getenv("FLASK_ENV") == "development":
        logger.warning("⚠ Usando hash temporal (modo desarrollo)")

        HASH_ADMIN = bcrypt.hashpw(b"admin", bcrypt.gensalt()).decode()

    else:
        raise ValueError(
            "❌ ERROR CRÍTICO: ADMIN_HASH no definida en entorno de producción"
        )

# Validar formato
if not _es_hash_bcrypt_valido(HASH_ADMIN):
    raise ValueError("❌ ADMIN_HASH no es un hash bcrypt válido")

# =============================================================================
# 2️⃣ FUNCIÓN DE VERIFICACIÓN
# =============================================================================


def verificar_password(password_plano: str) -> bool:
    """
    Verifica contraseña contra hash bcrypt.

    ✔ Protegido contra errores
    ✔ Logging incluido
    ✔ Seguro ante inputs inválidos
    """

    if not password_plano:
        logger.warning("⚠ Password vacío")
        return False

    try:
        resultado = bcrypt.checkpw(
            password_plano.encode("utf-8"), HASH_ADMIN.encode("utf-8")
        )

        if not resultado:
            logger.info("🔐 Login fallido")

        return resultado

    except Exception as e:
        logger.error(f"❌ Error verificando password: {e}")
        return False
