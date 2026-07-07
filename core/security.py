# =============================================================================
# 🔐 CORE.SECURITY · SISTEMA DE PERMISOS ACL (ACCESS CONTROL LIST)
# =============================================================================
#
# 🎯 PROPÓSITO:
# Controlar el acceso a funcionalidades de la aplicación mediante permisos.
#
# ✔ Basado en roles (RBAC)
# ✔ Compatible con endpoints web y API
# ✔ Integrado con sistema de auditoría
#
# 🔥 ESTE MÓDULO:
# - Define permisos por rol
# - Protege rutas con decoradores
# - Registra accesos no autorizados
#
# =============================================================================


# =============================================================================
# 1️⃣ IMPORTS · DEPENDENCIAS DEL SISTEMA
# =============================================================================

from functools import wraps
from flask import session, redirect, url_for, flash, request
from core.audit import registrar_evento

# =============================================================================
# 2️⃣ MATRIZ DE PERMISOS (ACL EN MEMORIA)
# =============================================================================
#
# 🎯 OBJETIVO:
# Definir qué puede hacer cada rol.
#
# 📌 ESTRUCTURA:
# { rol: [lista_permisos] }
#
# 💡 NOTAS:
# - "*" = acceso total (super admin)
# - Fácil de migrar a base de datos en el futuro
#
# =============================================================================

PERMISOS = {
    # ---------------------------------------------------------
    # 👑 SUPER ADMIN → ACCESO TOTAL
    # ---------------------------------------------------------
    "super_admin": ["*"],
    # ---------------------------------------------------------
    # 🧑‍💼 GESTORES → GESTIÓN DE CONTENEDORES
    # ---------------------------------------------------------
    "gestores": [
        "ver_panel",
        "crear_contenedor",
        "editar_contenedor",
    ],
    # ---------------------------------------------------------
    # 🚓 POLICÍAS → VALIDACIÓN
    # ---------------------------------------------------------
    "policias": [
        "ver_panel",
        "validar_contenedor",
    ],
    # ---------------------------------------------------------
    # 👤 USUARIOS → SOLO VISUALIZACIÓN
    # ---------------------------------------------------------
    "usuarios": ["ver_panel"],
}


# =============================================================================
# 3️⃣ DECORADOR PRINCIPAL DE PERMISOS
# =============================================================================
#
# 🎯 OBJETIVO:
# Proteger rutas Flask mediante permisos.
#
# 📌 USO:
#
# @requiere_permiso("crear_contenedor")
# def crear():
#     ...
#
# =============================================================================


def requiere_permiso(permiso):
    """
    🔒 Decorador para proteger endpoints por permisos.

    :param permiso: string del permiso requerido
    """

    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):

            # ---------------------------------------------------------
            # 🧩 3.1 OBTENER DATOS DE SESIÓN
            # ---------------------------------------------------------
            rol = session.get("rol")
            user_id = session.get("user_id")  # opcional (para auditoría)

            # ---------------------------------------------------------
            # 🚫 3.2 USUARIO NO AUTENTICADO
            # ---------------------------------------------------------
            if not rol:
                flash("Debes iniciar sesión.", "warning")
                return redirect(url_for("auth_bp.login"))

            # ---------------------------------------------------------
            # 🧠 3.3 OBTENER PERMISOS DEL ROL
            # ---------------------------------------------------------
            permisos = PERMISOS.get(rol, [])

            # ---------------------------------------------------------
            # 🟢 3.4 ACCESO PERMITIDO
            # ---------------------------------------------------------
            if "*" in permisos or permiso in permisos:
                return func(*args, **kwargs)

            # ---------------------------------------------------------
            # 🔴 3.5 ACCESO DENEGADO
            # ---------------------------------------------------------

            # 📊 AUDITORÍA DE SEGURIDAD
            registrar_evento(
                tipo_evento="acceso_denegado",
                descripcion=f"Intento de acceso a '{permiso}'",
                idtbl_gestores=user_id,
            )

            # ---------------------------------------------------------
            # 🌐 3.6 RESPUESTA SEGÚN TIPO DE REQUEST
            # ---------------------------------------------------------

            # 👉 API (JSON)
            if request.path.startswith("/api"):
                return {
                    "status": "error",
                    "message": "Forbidden",
                    "permiso_requerido": permiso,
                }, 403

            # 👉 WEB (HTML)
            flash("No tienes permisos para acceder.", "danger")
            return redirect(url_for("super_admin_bp.dashboard"))

        return wrapper

    return decorator


# =============================================================================
# 4️⃣ FUNCIONES AUXILIARES (OPCIONAL PERO PRO)
# =============================================================================
#
# 🎯 Estas funciones ayudan a reutilizar lógica en otras partes del sistema
#
# =============================================================================


def usuario_tiene_permiso(permiso):
    """
    🔍 Comprueba si el usuario actual tiene un permiso (sin decorar rutas)

    :param permiso: string permiso
    :return: True / False
    """
    rol = session.get("rol")
    if not rol:
        return False

    permisos = PERMISOS.get(rol, [])
    return "*" in permisos or permiso in permisos


def es_super_admin():
    """
    👑 Verifica si el usuario actual es super admin
    """
    return session.get("rol") == "super_admin"


# =============================================================================
# 🧠 RESUMEN DEL SISTEMA ACL
# =============================================================================
#
# ✔ Control de acceso por roles (RBAC)
# ✔ Decoradores reutilizables
# ✔ Auditoría integrada
# ✔ Soporte API + Web
#
# 🚀 ESCALABILIDAD:
# 👉 Siguiente paso: mover PERMISOS a base de datos
# 👉 Integrar con tbl_roles_permisos (tu otro módulo)
#
# =============================================================================
