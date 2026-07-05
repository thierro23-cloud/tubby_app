# =============================================================================
# 📊 CORE.AUDIT · SISTEMA DE AUDITORÍA SIMPLIFICADO
# =============================================================================
#
# 🎯 PROPÓSITO:
# Registrar acciones importantes del sistema en la base de datos de forma directa.
# Ideal para desarrollo o entornos donde no es crítico que falle la auditoría.
#
# 🔹 Características:
# - Registro de login, logout, errores y accesos denegados
# - Guarda usuario, rol, IP, endpoint y fecha
# - Compatible con Flask (requests web)
#
# 🧰 Tabla objetivo: audit_log
# Columns: idtbl_audit_log, idtbl_gestores, idtbl_roles, accion, modulo,
#          descripcion, ip, endpoint, path, user_agent, request_id, fecha
#
# =============================================================================

# =============================================================================
# 1️⃣ IMPORTS
# =============================================================================
from flask import request, session
from datetime import datetime
from core.db import ejecutar_query
import uuid

# =============================================================================
# 2️⃣ FUNCIÓN PRINCIPAL: registrar_evento()
# =============================================================================
#
# Registra un evento en la tabla audit_log de forma directa.
# No incluye manejo avanzado de errores, es simple y eficiente.
#

def registrar_evento(accion, modulo=None, descripcion=None):
    """
    📌 Registra un evento en la auditoría

    :param accion: acción realizada (ej: 'login', 'acceso_denegado')
    :param modulo: módulo afectado (ej: 'auth', 'contenedores')
    :param descripcion: detalle opcional
    """

    idtbl_gestores = session.get("user_id")  # ID del usuario logueado
    idtbl_roles = session.get("rol_id")      # ID del rol
    ip = request.remote_addr                  # IP de origen
    endpoint = request.endpoint               # Endpoint llamado
    path = request.path                       # Path de la request
    user_agent = request.headers.get("User-Agent")  # Navegador / cliente
    request_id = str(uuid.uuid4())            # ID único para trazabilidad

    # Inserción directa en base de datos
    ejecutar_query("""
        INSERT INTO audit_log
        (
            idtbl_gestores,
            idtbl_roles,
            accion,
            modulo,
            descripcion,
            ip,
            endpoint,
            path,
            user_agent,
            request_id,
            fecha
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        idtbl_gestores,
        idtbl_roles,
        accion,
        modulo,
        descripcion,
        ip,
        endpoint,
        path,
        user_agent,
        request_id,
        datetime.utcnow()
    ))

# =============================================================================
# 3️⃣ FUNCIONES DE ATAJO PARA EVENTOS COMUNES
# =============================================================================

def audit_login(idtbl_gestores):
    """ Registra un login """
    registrar_evento("login", "auth", f"user_id={idtbl_gestores}")


def audit_logout(idtbl_gestores):
    """ Registra un logout """
    registrar_evento("logout", "auth", f"user_id={idtbl_gestores}")


def audit_error(descripcion):
    """ Registra un error del sistema """
    registrar_evento("error", "sistema", descripcion)


def audit_acceso_denegado(modulo):
    """ Registra un intento de acceso denegado """
    registrar_evento("acceso_denegado", modulo)

# =============================================================================
# 4️⃣ RESUMEN DEL SISTEMA
# =============================================================================
#
# - Sistema simple de auditoría para Flask
# - Registra usuario, rol, IP, endpoint, path y request_id
# - Fácil de mantener y leer
# - Ideal para entornos donde la seguridad absoluta no es crítica
#
# =============================================================================