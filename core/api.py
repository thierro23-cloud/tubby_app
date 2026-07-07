# =============================================================================
# 🌐 CORE.API_RESPONSES · ESTÁNDAR PROFESIONAL DE RESPUESTAS HTTP
# =============================================================================
#
# 🎯 PROPÓSITO:
# Unificar TODAS las respuestas de la API bajo un formato estándar.
#
# ✔ Consistencia en frontend y backend
# ✔ Facilita debugging
# ✔ Compatible con APIs REST profesionales
#
# 📦 ESTRUCTURA BASE:
#
# SUCCESS:
# {
#   "status": "success",
#   "message": "...",
#   "data": {...},
#   "meta": {...}
# }
#
# ERROR:
# {
#   "status": "error",
#   "message": "...",
#   "error_code": "...",
#   "data": {...}
# }
#
# =============================================================================


# =============================================================================
# 1️⃣ IMPORTS
# =============================================================================

from flask import jsonify, request
import uuid
import datetime

# =============================================================================
# 2️⃣ GENERADOR DE METADATOS
# =============================================================================
#
# 🎯 OBJETIVO:
# Añadir información útil en TODAS las respuestas.
#
# ✔ request_id → trazabilidad (debug)
# ✔ timestamp → auditoría
# ✔ path → endpoint ejecutado
#
# =============================================================================


def _build_meta(extra_meta=None):
    """
    🧠 Genera metadatos estándar para cada respuesta.
    """

    meta = {
        "request_id": str(uuid.uuid4()),
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "path": request.path,
    }

    if extra_meta:
        meta.update(extra_meta)

    return meta


# =============================================================================
# 3️⃣ RESPUESTA EXITOSA
# =============================================================================


def success(data=None, message="OK", code=200, meta=None):
    """
    🟢 Respuesta estándar de éxito.

    :param data: contenido principal
    :param message: mensaje descriptivo
    :param code: HTTP status code
    :param meta: metadatos adicionales (paginación, etc.)
    """

    response = {
        "status": "success",
        "message": message,
        "data": data,
        "meta": _build_meta(meta),
    }

    return jsonify(response), code


# =============================================================================
# 4️⃣ RESPUESTA DE ERROR
# =============================================================================


def error(message="Error", code=400, data=None, error_code=None):
    """
    🔴 Respuesta estándar de error.

    :param message: descripción del error
    :param code: HTTP status code
    :param data: detalles adicionales
    :param error_code: código interno (ej: USER_NOT_FOUND)
    """

    response = {
        "status": "error",
        "message": message,
        "error_code": error_code,
        "data": data,
        "meta": _build_meta(),
    }

    return jsonify(response), code


# =============================================================================
# 5️⃣ RESPUESTAS ESPECIALIZADAS (PRO)
# =============================================================================
#
# 🎯 OBJETIVO:
# Evitar repetir código en casos comunes
#
# =============================================================================


def created(data=None, message="Recurso creado"):
    return success(data, message, 201)


def no_content():
    return "", 204


def bad_request(message="Petición inválida", data=None):
    return error(message, 400, data, "BAD_REQUEST")


def unauthorized(message="No autorizado"):
    return error(message, 401, None, "UNAUTHORIZED")


def forbidden(message="Acceso denegado"):
    return error(message, 403, None, "FORBIDDEN")


def not_found(message="Recurso no encontrado"):
    return error(message, 404, None, "NOT_FOUND")


def server_error(message="Error interno del servidor"):
    return error(message, 500, None, "SERVER_ERROR")


# =============================================================================
# 6️⃣ RESPUESTA CON PAGINACIÓN (MUY PRO)
# =============================================================================
#
# 🎯 OBJETIVO:
# Estandarizar respuestas de listados grandes
#
# =============================================================================


def paginated(data, page, per_page, total):
    """
    📊 Respuesta paginada estándar
    """

    meta = {
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (total // per_page) + (1 if total % per_page else 0),
        }
    }

    return success(data=data, meta=meta)


# =============================================================================
# 7️⃣ HOOK PARA LOGGING (OPCIONAL)
# =============================================================================
#
# 🎯 IDEAL PARA:
# - Auditoría
# - Logs centralizados
# - Monitorización
#
# =============================================================================


def log_response(response_body):
    """
    📊 Punto central para logging de respuestas.
    (puedes integrarlo con tu auditoría)
    """

    # 👉 aquí podrías enviar a:
    # - base de datos
    # - archivo log
    # - sistema externo (ELK, Datadog, etc.)
    pass


# =============================================================================
# 🧠 RESUMEN DEL SISTEMA
# =============================================================================
#
# ✔ Respuestas homogéneas
# ✔ Trazabilidad (request_id)
# ✔ Preparado para debugging
# ✔ Escalable a APIs grandes
# ✔ Compatible con frontend moderno
#
# 🚀 NIVEL:
# 👉 Producción real / API profesional
#
# =============================================================================
