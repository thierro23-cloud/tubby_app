# =============================================================================
# 🔐 CORE.PERMISOS · SISTEMA CENTRAL DE SEGURIDAD (NIVEL PROFESIONAL)
# =============================================================================
#
# 🎯 PROPÓSITO DEL MÓDULO:
# Este archivo controla TODA la lógica de permisos del sistema.
#
# RESPONSABILIDADES:
# ✔ Verificar si un endpoint está activo
# ✔ Verificar si un rol tiene acceso a un endpoint
# ✔ Registrar automáticamente endpoints nuevos
#
# 🔥 ESTE MÓDULO ES USADO POR:
# 👉 seguridad_global() (before_request en app.py)
#
# ⚠️ REGLA DE ORO:
# 👉 NO duplicar lógica de permisos en otros archivos
# 👉 TODO pasa por aquí
#
# =============================================================================


# =============================================================================
# 1️⃣ IMPORTS · CONEXIÓN A BASE DE DATOS
# =============================================================================
#
# 🎯 OBJETIVO:
# Importar la función que gestiona la conexión a la BD.
#
# 🔧 get_connection():
# - Abre conexión MySQL
# - Se usa en TODAS las funciones
#
# =============================================================================

from core.db import get_connection


# =============================================================================
# 2️⃣ VALIDACIÓN DE ENDPOINT ACTIVO
# =============================================================================
#
# 🎯 OBJETIVO:
# Determinar si un endpoint puede ejecutarse o está bloqueado.
#
# 🔄 FLUJO:
# 1. Busca el endpoint en BD
# 2. Si NO existe → lo registra automáticamente
# 3. Devuelve si está activo (True/False)
#
# 💡 VENTAJA:
# 👉 Sistema auto-regenerativo (no necesitas registrar endpoints manualmente)
#
# =============================================================================

def endpoint_activo(endpoint):
    """
    🔐 Verifica si un endpoint está activo en el sistema.

    :param endpoint: nombre del endpoint (ej: 'auth_bp.login')
    :return: True (activo) / False (desactivado)
    """

    # ---------------------------------------------------------
    # 🧩 2.1 ABRIR CONEXIÓN A BD
    # ---------------------------------------------------------
    conn = get_connection()
    cursor = conn.cursor()

    # ---------------------------------------------------------
    # 🧩 2.2 CONSULTAR ESTADO DEL ENDPOINT
    # ---------------------------------------------------------
    cursor.execute("""
        SELECT activo
        FROM tbl_endpoints
        WHERE endpoint = %s
        LIMIT 1
    """, (endpoint,))

    row = cursor.fetchone()

    # ---------------------------------------------------------
    # 🧩 2.3 CERRAR CONEXIÓN (SIEMPRE)
    # ---------------------------------------------------------
    cursor.close()
    conn.close()

    # ---------------------------------------------------------
    # 🧩 2.4 SI NO EXISTE → REGISTRO AUTOMÁTICO
    # ---------------------------------------------------------
    if not row:
        # 👉 Auto-crea el endpoint en BD
        registrar_endpoint(endpoint)

        # 👉 Por defecto se considera activo
        return True

    # ---------------------------------------------------------
    # 🧩 2.5 DEVOLVER ESTADO (0 o 1 → bool)
    # ---------------------------------------------------------
    return bool(row[0])


# =============================================================================
# 3️⃣ VALIDACIÓN DE PERMISOS POR ROL
# =============================================================================
#
# 🎯 OBJETIVO:
# Verificar si un rol tiene acceso a un endpoint específico.
#
# 🔄 FLUJO:
# 1. Cruza tabla roles_permisos + endpoints
# 2. Comprueba si existe relación
#
# 📌 EJEMPLO:
# rol_id = 2 (gestor)
# endpoint = 'clientes_bp.listar'
#
# 👉 Si existe en BD → acceso permitido
# 👉 Si NO → acceso denegado
#
# =============================================================================

def tiene_permiso(endpoint, rol_id):
    """
    🔐 Verifica si un rol puede acceder a un endpoint.

    :param endpoint: nombre del endpoint
    :param rol_id: ID del rol del usuario
    :return: True (permitido) / False (denegado)
    """

    # ---------------------------------------------------------
    # 🧩 3.1 VALIDACIÓN BÁSICA DE SEGURIDAD
    # ---------------------------------------------------------
    if not rol_id:
        return False  # usuario sin rol → bloqueado

    # ---------------------------------------------------------
    # 🧩 3.2 ABRIR CONEXIÓN
    # ---------------------------------------------------------
    conn = get_connection()
    cursor = conn.cursor()

    # ---------------------------------------------------------
    # 🧩 3.3 CONSULTA DE PERMISOS
    # ---------------------------------------------------------
    cursor.execute("""
        SELECT 1
        FROM tbl_roles_permisos rp
        JOIN tbl_endpoints e ON rp.idtbl_endpoints = e.idtbl_endpoints
        WHERE rp.idtbl_roles = %s
        AND e.endpoint = %s
        LIMIT 1
    """, (rol_id, endpoint))

    permitido = cursor.fetchone() is not None

    # ---------------------------------------------------------
    # 🧩 3.4 CERRAR CONEXIÓN
    # ---------------------------------------------------------
    cursor.close()
    conn.close()

    # ---------------------------------------------------------
    # 🧩 3.5 RESULTADO FINAL
    # ---------------------------------------------------------
    return permitido


# =============================================================================
# 4️⃣ REGISTRO AUTOMÁTICO DE ENDPOINTS
# =============================================================================
#
# 🎯 OBJETIVO:
# Insertar automáticamente nuevos endpoints en la BD.
#
# 💡 CUÁNDO SE USA:
# 👉 Cuando un endpoint no existe en tbl_endpoints
#
# 🔥 IMPORTANTE:
# - Usa INSERT IGNORE → evita duplicados
# - No rompe la app si ya existe
#
# =============================================================================

def registrar_endpoint(endpoint):
    """
    🧩 Registra un endpoint en la BD si no existe.

    :param endpoint: nombre del endpoint
    """

    # ---------------------------------------------------------
    # 🧩 4.1 ABRIR CONEXIÓN
    # ---------------------------------------------------------
    conn = get_connection()
    cursor = conn.cursor()

    # ---------------------------------------------------------
    # 🧩 4.2 INSERTAR ENDPOINT
    # ---------------------------------------------------------
    cursor.execute("""
        INSERT IGNORE INTO tbl_endpoints (endpoint, activo)
        VALUES (%s, 1)
    """, (endpoint,))

    # ---------------------------------------------------------
    # 🧩 4.3 CONFIRMAR CAMBIOS
    # ---------------------------------------------------------
    conn.commit()

    # ---------------------------------------------------------
    # 🧩 4.4 CERRAR CONEXIÓN
    # ---------------------------------------------------------
    cursor.close()
    conn.close()


# =============================================================================
# 🧠 RESUMEN DEL MÓDULO
# =============================================================================
#
# ✔ endpoint_activo() → controla si el endpoint está habilitado
# ✔ tiene_permiso() → controla acceso por rol
# ✔ registrar_endpoint() → auto-registra endpoints nuevos
#
# 🔥 RESULTADO:
# Sistema de seguridad:
# ✔ dinámico
# ✔ escalable
# ✔ basado en BD
# ✔ listo para producción
#
# =============================================================================