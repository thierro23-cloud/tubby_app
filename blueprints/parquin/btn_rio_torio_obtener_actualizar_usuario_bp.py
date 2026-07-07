# -*- coding: utf-8 -*-
# =============================================================================
# 0 INICIO · BOTÓN INDEPENDIENTE · LISTAR USUARIOS RIO_TORIO
# =============================================================================
# OBJETIVO
# -----------------------------------------------------------------------------
# Crear un botón individual que encapsule el flujo:
#
#   - Listar todos los usuarios del parquin Río Torío.
#   - Cada usuario corresponde a un proveedor con el parquin seleccionado.
#   - Mostrar un listado con sus datos básicos y enlaces a acciones
#     (p. ej. editar, ver plazas, etc.).
#
# BOTÓN (VISTA PRINCIPAL):
#   - Nombre de la vista:
#       btn_rio_torio_listar_usuarios
#   - Ruta relativa al blueprint:
#       /
#
# BLUEPRINT:
#   - Nombre:
#       btn_rio_torio_listar_usuarios_bp
#   - url_prefix:
#       /parquin/rio_torio/usuarios
#
# INTEGRACIÓN SUPER ADMIN:
#   - La vista principal empieza por "btn_", así que se descubre como botón
#     ejecutable en el módulo de Río Torío.
#
# PLANTILLA:
#   - Renderiza:
#       parquin/rio_torio/rio_torio_usuarios_listado.html
# =============================================================================

from __future__ import annotations

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
    send_file,
)

from services.helpers import login_required, rol_required
from db import ejecutar_query, ejecutar_non_query

# =============================================================================
# 1 BLUEPRINT DEL BOTÓN
# =============================================================================
# NOMBRE DEL BLUEPRINT:
#   - "btn_rio_torio_listar_usuarios_bp"
#
# URL_PREFIX:
#   - "/parquin/rio_torio/usuarios"
#
# RUTA COMPLETA DEL BOTÓN:
#   - /parquin/rio_torio/usuarios/
#       btn_rio_torio_listar_usuarios
#
# Endpoint (para url_for):
#   - "btn_rio_torio_listar_usuarios_bp.btn_rio_torio_listar_usuarios"
# =============================================================================

btn_rio_torio_listar_usuarios_bp = Blueprint(
    "btn_rio_torio_listar_usuarios_bp",
    __name__,
    url_prefix="/parquin/rio_torio/usuarios",
)


# =============================================================================
# 2 HELPERS SQL · LISTAR Y ACTUALIZAR USUARIOS
# =============================================================================


def _rt_listar_usuarios_parquin():
    """
    Devuelve todos los usuarios de parquin Río Torío.

    Suposición:
      - Los usuarios están en parquin_camiones.tbl_usuarios.
      - Cada usuario está vinculado a un proveedor en bd_tbl_comunes.tbl_proveedores.
      - "Usuarios del parquin" son aquellos que tienen el parquin seleccionado
        (ajusta el WHERE a tu lógica real).
    """
    sql = """
       SELECT
    tbl_proveedores.Idtbl_proveedores,
    tbl_proveedores.NIF,
    tbl_proveedores.Nombre_Razon_Social,
    tbl_proveedores.numero_cuenta,
    tbl_proveedores.parquin,
    tbl_proveedores.peticcion_parquin,
    tbl_proveedores.Telefono,
    tbl_proveedores.Persona_contacto_comercial
FROM tbl_proveedores
WHERE tbl_proveedores.parquin = 1
ORDER BY tbl_proveedores.Nombre_Razon_Social;
    """
    return ejecutar_query(sql, nombre_bd="parquin_camiones")


def _rt_actualizar_usuario(id_usuario: int, datos: dict) -> None:
    """
    Actualiza un usuario existente identificado por idtbl_usuarios.

    Campos:
      - idtbl_proveedores
      - numero_cuenta
      - activo_baja
      - fecha_inicio
      - fecha_baja
      - rol
    """
    sql = """
        UPDATE tbl_usuarios SET
            idtbl_proveedores = %(idtbl_proveedores)s,
            numero_cuenta     = %(numero_cuenta)s,
            activo_baja       = %(activo_baja)s,
            fecha_inicio      = %(fecha_inicio)s,
            fecha_baja        = %(fecha_baja)s,
            rol               = %(rol)s
        WHERE idtbl_usuarios = %(id)s
    """
    datos["id"] = id_usuario
    ejecutar_non_query(sql, datos, "parquin_camiones")


# =============================================================================
# 3 VISTA PRINCIPAL · LISTADO DE USUARIOS RIO_TORIO
# =============================================================================
# Convención:
#   - Nombre de la función/vista:
#       btn_rio_torio_listar_usuarios
#
#   - Ruta relativa al url_prefix:
#       "/"  (listado principal)
#
#   - Ruta completa:
#       /parquin/rio_torio/usuarios/btn_rio_torio_listar_usuarios
#
# SUPER ADMIN:
#   - Descubrirá este botón porque:
#       · el endpoint empieza por "btn_".
# =============================================================================


@btn_rio_torio_listar_usuarios_bp.route(
    "/btn_rio_torio_listar_usuarios",
    methods=["GET"],
)
@login_required
@rol_required("gestor", "super_admin")
def btn_rio_torio_listar_usuarios():
    """
    BOTÓN · Listado de usuarios del parquin Río Torío.

    - GET:
        · Recupera todos los usuarios/proveedores del parquin.
        · Renderiza la plantilla de listado con acciones por usuario.
    """
    usuarios = _rt_listar_usuarios_parquin()

    return render_template(
        "parquin/rio_torio/rio_torio_usuarios_listado.html",
        usuarios=usuarios,
    )
