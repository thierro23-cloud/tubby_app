# -*- coding: utf-8 -*-
from __future__ import annotations

# =============================================================================
# 0️⃣ BOTÓN INDEPENDIENTE · RIO_TORIO · USUARIOS TBL VS PROVEEDORES
# =============================================================================
# 🎯 OBJETIVO
# -----------------------------------------------------------------------------
# Definir un BOTÓN independiente que permita analizar:
#
#   - Usuarios de la tabla:
#         parquin_camiones.tbl_usuarios
#   - Proveedores con parquin activado en:
#         bd_tbl_comunes.tbl_proveedores
#
# mostrando ambos en tablas paralelas para comparar:
#   · Nombre_Razon_Social
#   · NIF
#   · IDs y claves relevantes.
#
# BOTÓN:
#   - Ruta completa:
#       /parquin/rio_torio/usuarios_tbl/btn_rio_torio_usuarios_tbl
#
# BLUEPRINT:
#   - Nombre interno:
#         btn_rio_torio_usuarios_tbl_bp
#   - url_prefix:
#         /parquin/rio_torio/usuarios_tbl
#
# ENDPOINT:
#   - Para url_for:
#         "btn_rio_torio_usuarios_tbl_bp.btn_rio_torio_usuarios_tbl"
#
# PLANTILLA:
#   - Renderiza:
#         templates/parquin/rio_torio/rio_torio_usuarios_tbl.html
# =============================================================================

from flask import Blueprint, render_template
from services.helpers import login_required, rol_required
from db import ejecutar_query

# =============================================================================
# 1️⃣ BLUEPRINT · USUARIOS TBL
# =============================================================================

btn_rio_torio_usuarios_tbl_bp = Blueprint(
    "btn_rio_torio_usuarios_tbl_bp",
    __name__,
    url_prefix="/parquin/rio_torio/usuarios_tbl",
)

# =============================================================================
# 2️⃣ HELPERS SQL · USUARIOS Y PROVEEDORES
# =============================================================================

def _rt_obtener_usuarios_tbl():
    """
    2.1️⃣ Devuelve usuarios de parquin_camiones.tbl_usuarios.

    Campos devueltos:
      - idtbl_usuarios
      - idtbl_proveedores
      - numero_cuenta
      - activo_baja
      - fecha_inicio
      - fecha_baja
      - rol
    """
    sql = """
        SELECT
            idtbl_usuarios,
            idtbl_proveedores,
            numero_cuenta,
            activo_baja,
            fecha_inicio,
            fecha_baja,
            rol
        FROM tbl_usuarios
        ORDER BY idtbl_usuarios
    """
    return ejecutar_query(sql, nombre_bd="parquin_camiones")


def _rt_obtener_proveedores_parquin_activo():
    """
    2.2️⃣ Devuelve proveedores con parquin activado desde bd_tbl_comunes.tbl_proveedores.

    Campos relevantes devueltos:
      - Idtbl_proveedores
      - Nombre_Razon_Social
      - NIF
      - parquin          (flag: 1 = tiene parquin, 0 = no)

    NOTA:
      - Se filtra por el campo 'parquin = 1', que es el flag real según
        la definición de la tabla.
    """
    sql = """
        SELECT
            Idtbl_proveedores,
            Nombre_Razon_Social,
            NIF,
            parquin
        FROM tbl_proveedores
        WHERE parquin = 1
        ORDER BY Nombre_Razon_Social
    """
    return ejecutar_query(sql, nombre_bd="bd_tbl_comunes")
#=============================================================================
# 3️⃣ VISTA · BOTÓN USUARIOS TBL RIO_TORIO
# =============================================================================
# RUTA
# -----------------------------------------------------------------------------
#   - Relativa al blueprint:
#         /btn_rio_torio_usuarios_tbl
#
#   - Ruta completa:
#         /parquin/rio_torio/usuarios_tbl/btn_rio_torio_usuarios_tbl
#
# ENDPOINT
# -----------------------------------------------------------------------------
#   - Nombre para url_for:
#         btn_rio_torio_usuarios_tbl_bp.btn_rio_torio_usuarios_tbl
#
# PROTECCIONES
# -----------------------------------------------------------------------------
#   - @login_required
#   - @rol_required("gestor", "super_admin")
#
# COMPORTAMIENTO
# -----------------------------------------------------------------------------
#   - Recupera:
#       · usuarios_tbl: usuarios de parquin_camiones.tbl_usuarios.
#       · proveedores_parquin: proveedores con parquin activado.
#   - Renderiza:
#       · templates/parquin/rio_torio/rio_torio_usuarios_tbl.html
#     con ambas colecciones paralelas para análisis comparativo.
# =============================================================================

@btn_rio_torio_usuarios_tbl_bp.route(
    "/btn_rio_torio_usuarios_tbl",
    methods=["GET"],
)
@login_required
@rol_required("gestor", "super_admin")
def btn_rio_torio_usuarios_tbl():
    """
    3.1️⃣ BOTÓN · Usuarios TBL vs Proveedores (RIO_TORIO)

    - Recupera los usuarios de tbl_usuarios.
    - Recupera los proveedores con parquin activado.
    - Renderiza la plantilla con ambas tablas paralelas.
    """

    usuarios_tbl = _rt_obtener_usuarios_tbl()
    proveedores_parquin = _rt_obtener_proveedores_parquin_activo()

    return render_template(
        "parquin/rio_torio/rio_torio_usuarios_tbl.html",
        usuarios_tbl=usuarios_tbl,
        proveedores_parquin=proveedores_parquin,
    )