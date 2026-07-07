from __future__ import annotations

# =============================================================================
# 0️⃣ BOTÓN INDEPENDIENTE · RIO_TORIO · EDITAR USUARIO
# =============================================================================
# 🎯 OBJETIVO
# -----------------------------------------------------------------------------
# Definir un BOTÓN independiente para editar un usuario del parquin Río Torío.
#
# RUTA DEL BOTÓN:
#   - /parquin/rio_torio/usuarios_editar/rio_torio_usuarios_editar/<idtbl_usuarios>
#
# BLUEPRINT:
#   - Nombre interno:
#         btn_rio_torio_usuarios_editar_bp
#   - url_prefix:
#         /parquin/rio_torio/usuarios_editar
#
# ENDPOINT PRINCIPAL:
#   - Nombre para url_for:
#         "btn_rio_torio_usuarios_editar_bp.rio_torio_usuarios_editar"
#
# PLANTILLAS RELACIONADAS:
#   1) Formulario de edición:
#        - templates/parquin/rio_torio/rio_torio_usuarios_editar.html
#        - Se usa en esta vista (editar).
#
#   2) Listado principal de usuarios:
#        - templates/parquin/rio_torio/rio_torio_listar_usuarios.html
#        - Vista:
#            btn_rio_torio_listar_usuarios_bp.btn_rio_torio_listar_usuarios
#        - Desde el listado se puede llegar a este botón de edición.
#
# FLUJO GENERAL:
#   - GET:
#       · Busca el usuario por ID en parquin_camiones.tbl_usuarios.
#       · Si no existe, muestra aviso y redirige al listado de usuarios.
#       · Si existe, renderiza el formulario de edición con los datos actuales.
#
#   - POST:
#       · Lee los datos enviados desde el formulario.
#       · Actualiza el registro en parquin_camiones.tbl_usuarios.
#       · Muestra mensaje de éxito.
#       · Redirige al listado principal de usuarios Río Torío:
#             rio_torio_listar_usuarios.html
# =============================================================================

from flask import Blueprint, render_template, request, redirect, url_for, flash
from services.helpers import login_required, rol_required
from db import ejecutar_query, ejecutar_non_query

# =============================================================================
# 1️⃣ BLUEPRINT · RIO_TORIO · EDITAR USUARIO
# =============================================================================
# DESCRIPCIÓN
# -----------------------------------------------------------------------------
#   - Define el blueprint específico para la operación de edición.
#   - Todas las rutas de este archivo cuelgan de:
#         /parquin/rio_torio/usuarios_editar
#
# NOMBRE INTERNO:
#   - "btn_rio_torio_usuarios_editar_bp"
# =============================================================================

btn_rio_torio_usuarios_editar_bp = Blueprint(
    "btn_rio_torio_usuarios_editar_bp",
    __name__,
    url_prefix="/parquin/rio_torio/usuarios_editar",
)


# =============================================================================
# 2️⃣ HELPERS SQL · LEER Y ACTUALIZAR UN USUARIO
# =============================================================================
# DESCRIPCIÓN
# -----------------------------------------------------------------------------
#   - _rt_obtener_usuario_por_id:
#       · Recupera un usuario concreto a partir de su ID.
#
#   - _rt_actualizar_usuario:
#       · Actualiza los campos principales del usuario.
#
# NOTAS:
#   - Tabla:
#       parquin_camiones.tbl_usuarios
# =============================================================================


def _rt_obtener_usuario_por_id(idtbl_usuarios: int):
    """
    Devuelve un usuario por su ID (idtbl_usuarios) o None si no existe.

    Tabla:
      - parquin_camiones.tbl_usuarios
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
        WHERE idtbl_usuarios = %(id)s
    """
    filas = ejecutar_query(sql, {"id": idtbl_usuarios}, "parquin_camiones")
    return filas[0] if filas else None


def _rt_actualizar_usuario(idtbl_usuarios: int, datos: dict) -> None:
    """
    Actualiza un usuario existente en parquin_camiones.tbl_usuarios.

    Campos que se actualizan:
      - idtbl_proveedores
      - numero_cuenta
      - activo_baja
      - fecha_inicio
      - fecha_baja
      - rol

    Parámetros:
      - idtbl_usuarios: ID del usuario (clave primaria).
      - datos: diccionario con los campos a actualizar.
    """
    sql = """
        UPDATE tbl_usuarios
           SET
               idtbl_proveedores = %(idtbl_proveedores)s,
               numero_cuenta     = %(numero_cuenta)s,
               activo_baja       = %(activo_baja)s,
               fecha_inicio      = %(fecha_inicio)s,
               fecha_baja        = %(fecha_baja)s,
               rol               = %(rol)s
         WHERE idtbl_usuarios = %(idtbl_usuarios)s
    """
    datos["idtbl_usuarios"] = idtbl_usuarios
    ejecutar_non_query(sql, datos, "parquin_camiones")


# =============================================================================
# 3️⃣ VISTA · BOTÓN EDITAR USUARIO RIO_TORIO
# =============================================================================
# RUTA
# -----------------------------------------------------------------------------
#   - Relativa al blueprint:
#         /rio_torio_usuarios_editar/<int:idtbl_usuarios>
#
#   - Ruta completa:
#         /parquin/rio_torio/usuarios_editar/rio_torio_usuarios_editar/<idtbl_usuarios>
#
# ENDPOINT
# -----------------------------------------------------------------------------
#   - Nombre para url_for:
#         btn_rio_torio_usuarios_editar_bp.rio_torio_usuarios_editar
#
# PROTECCIONES
# -----------------------------------------------------------------------------
#   - @login_required
#   - @rol_required("gestor", "super_admin")
#
# RELACIÓN CON LISTADO (rio_torio_listar_usuarios.html)
# -----------------------------------------------------------------------------
#   - Desde el listado (rio_torio_listar_usuarios.html) el enlace "Editar"
#     puede apuntar a este botón con:
#
#       url_for(
#           'btn_rio_torio_usuarios_editar_bp.rio_torio_usuarios_editar',
#           idtbl_usuarios=u.idtbl_usuarios
#       )
#
#   - Tras guardar, esta vista redirige al listado:
#       btn_rio_torio_listar_usuarios_bp.btn_rio_torio_listar_usuarios
#       que usa la plantilla:
#           parquin/rio_torio/rio_torio_listar_usuarios.html
# =============================================================================


@btn_rio_torio_usuarios_editar_bp.route(
    "/rio_torio_usuarios_editar/<int:idtbl_usuarios>",
    methods=["GET", "POST"],
)
@login_required
@rol_required("gestor", "super_admin")
def rio_torio_usuarios_editar(idtbl_usuarios: int):
    """
    BOTÓN · Edición de un usuario del parquin Río Torío.

    Parámetros:
      - idtbl_usuarios: ID del usuario a editar (clave primaria de tbl_usuarios).

    Flujo:
      - GET:
          · Recupera el usuario a partir de su ID.
          · Si no existe, muestra aviso y redirige al listado.
          · Si existe, muestra la plantilla de edición con los datos actuales.
      - POST:
          · Lee los datos del formulario.
          · Actualiza el registro en parquin_camiones.tbl_usuarios.
          · Redirige al listado de usuarios de Río Torío
            (rio_torio_listar_usuarios.html).
    """

    # 3.1 Obtener el usuario a editar (GET inicial)
    usuario = _rt_obtener_usuario_por_id(idtbl_usuarios)

    if not usuario:
        flash("Usuario no encontrado.", "warning")
        # Redirigir al listado principal de usuarios Río Torío
        return redirect(
            url_for("btn_rio_torio_listar_usuarios_bp.btn_rio_torio_listar_usuarios")
        )

    # 3.2 Procesar envío del formulario (POST)
    if request.method == "POST":
        datos = {
            "idtbl_proveedores": request.form.get("idtbl_proveedores") or None,
            "numero_cuenta": request.form.get("numero_cuenta") or "",
            # activo_baja llega como "1" o "0" (string) desde el formulario
            "activo_baja": request.form.get("activo_baja") or 1,
            "fecha_inicio": request.form.get("fecha_inicio") or None,
            "fecha_baja": request.form.get("fecha_baja") or None,
            "rol": request.form.get("rol") or "",
        }

        _rt_actualizar_usuario(idtbl_usuarios, datos)
        flash("Usuario actualizado correctamente.", "success")

        # Volver al listado de usuarios de Río Torío
        return redirect(
            url_for("btn_rio_torio_listar_usuarios_bp.btn_rio_torio_listar_usuarios")
        )

    # 3.3 GET → Mostrar formulario con datos actuales
    return render_template(
        "parquin/rio_torio/rio_torio_usuarios_editar.html",
        usuario=usuario,
    )
