# -*- coding: utf-8 -*-
# =============================================================================
# 0 BOTÓN INDEPENDIENTE · RIO_TORIO · LISTAR, VER PLAZAS Y EDITAR USUARIOS
# =============================================================================
# OBJETIVO
#   1) Liste todos los usuarios del parquin Río Torío.
#   2) Permita ver las plazas asociadas a un usuario.
#   3) Permita editar un usuario concreto desde el listado.
# =============================================================================

from __future__ import annotations

from flask import Blueprint, render_template, request, redirect, url_for, flash
from services.helpers import login_required, rol_required
from db import ejecutar_query, ejecutar_non_query


# =============================================================================
# 1 BLUEPRINT DEL BOTÓN
# =============================================================================

btn_rio_torio_listar_usuarios_bp = Blueprint(
    "btn_rio_torio_listar_usuarios_bp",
    __name__,
    url_prefix="/parquin/rio_torio/usuarios",
)


# =============================================================================
# 2 HELPERS SQL · LISTAR, ACTUALIZAR USUARIOS Y OBTENER PLAZAS
# =============================================================================

def _rt_listar_usuarios_parquin():
    """
    Devuelve todos los usuarios del parquin Río Torío.
    """
    sql = """
        SELECT
            u.idtbl_usuarios,
            u.idtbl_proveedores,
            u.numero_cuenta,
            u.activo_baja,
            u.fecha_inicio,
            u.fecha_baja,
            u.rol,
            p.Nombre_Razon_Social AS nombre_proveedor
        FROM tbl_usuarios AS u
        INNER JOIN bd_tbl_comunes.tbl_proveedores AS p
            ON u.idtbl_proveedores = p.Idtbl_proveedores
        WHERE u.activo_baja = 1
        ORDER BY p.Nombre_Razon_Social
    """
    return ejecutar_query(sql, nombre_bd="parquin_camiones")


def _rt_actualizar_usuario(id_usuario: int, datos: dict) -> None:
    """
    Actualiza un usuario existente identificado por idtbl_usuarios.
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


def _rt_obtener_plazas_por_usuario(id_usuario: int):
    """
    Devuelve las plazas (fila y número de plaza) asociadas a un usuario.
    """
    sql = """
        SELECT
            idtbl_plazas,
            fila,
            codigo_plazas
        FROM tbl_plazas
        WHERE idtbl_usuarios = %(id_usuario)s
        ORDER BY fila, codigo_plazas
    """
    return ejecutar_query(
        sql,
        params={"id_usuario": id_usuario},
        nombre_bd="parquin_camiones",
    )


# =============================================================================
# 3 VISTA PRINCIPAL · LISTADO DE USUARIOS RIO_TORIO
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
    """
    usuarios = _rt_listar_usuarios_parquin()

    return render_template(
        "parquin/rio_torio/rio_torio_listar_usuarios.html",
        usuarios=usuarios,
    )


# =============================================================================
# 4 VISTA · VER PLAZAS DE UN USUARIO
# =============================================================================

@btn_rio_torio_listar_usuarios_bp.route(
    "/usuarios/<int:id_usuario>/plazas",
    methods=["GET"],
)
@login_required
@rol_required("gestor", "super_admin")
def btn_rio_torio_ver_plazas(id_usuario: int):
    """
    Muestra las plazas asociadas a un usuario/proveedor del parquin Río Torío.
    """
    plazas = _rt_obtener_plazas_por_usuario(id_usuario)

    return render_template(
        "parquin/rio_torio/rio_torio_plazas_usuario.html",
        id_usuario=id_usuario,
        plazas=plazas,
    )


# =============================================================================
# 5 VISTA · EDITAR USUARIO RIO_TORIO
# =============================================================================

@btn_rio_torio_listar_usuarios_bp.route(
    "/usuarios/<int:id_usuario>/editar",
    methods=["GET", "POST"],
)
@login_required
@rol_required("gestor", "super_admin")
def btn_rio_torio_editar_usuario(id_usuario: int):
    """
    Formulario de edición de un usuario de parquin Río Torío.
    """

    # -------------------------------------------------------------------------
    # 5.1 POST · GUARDAR CAMBIOS
    # -------------------------------------------------------------------------
    if request.method == "POST":
        datos = {
            "idtbl_proveedores": request.form.get("idtbl_proveedores"),
            "numero_cuenta": request.form.get("numero_cuenta"),
            "activo_baja": int(request.form.get("activo_baja", 1)),
            "fecha_inicio": request.form.get("fecha_inicio"),
            "fecha_baja": request.form.get("fecha_baja") or None,
            "rol": request.form.get("rol"),
        }

        _rt_actualizar_usuario(id_usuario, datos)

        flash("Usuario actualizado correctamente.", "success")
        return redirect(
            url_for(
                "btn_rio_torio_listar_usuarios_bp.btn_rio_torio_listar_usuarios"
            )
        )

    # -------------------------------------------------------------------------
    # 5.2 GET · CARGAR DATOS DEL USUARIO
    # -------------------------------------------------------------------------
    sql = """
        SELECT
            u.idtbl_usuarios,
            u.idtbl_proveedores,
            u.numero_cuenta,
            u.activo_baja,
            u.fecha_inicio,
            u.fecha_baja,
            u.rol,
            p.Nombre_Razon_Social AS nombre_proveedor
        FROM tbl_usuarios AS u
        INNER JOIN bd_tbl_comunes.tbl_proveedores AS p
            ON u.idtbl_proveedores = p.Idtbl_proveedores
        WHERE u.idtbl_usuarios = %(id)s
    """

    usuario = ejecutar_query(
        sql,
        params={"id": id_usuario},
        nombre_bd="parquin_camiones",
    )[0]

    return render_template(
        "parquin/rio_torio/rio_torio_usuarios_editar.html",
        usuario=usuario,
    )