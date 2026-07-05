# =============================================================================
# 🔘 0️⃣ INICIO · BOTÓN INDEPENDIENTE · USUARIOS PLAZAS RIO_TORIO
# =============================================================================
# 🎯 OBJETIVO
# -----------------------------------------------------------------------------
# Crear un botón independiente:
#
#   btn_rio_torio_usuarios_plazas
#
# que:
#   - Tiene su propio BLUEPRINT:
#         btn_rio_torio_usuarios_plazas_bp
#   - Se cuelga de:
#         /control_via_publica/rio_torio/usuarios
#   - Es descubierto por el SUPER ADMIN (vista empieza por 'btn_').
#   - Es ejecutable: al pulsarlo, abre la plantilla:
#         parquin/rio_torio/rio_torio_usuarios_plazas.html
#
# ARQUITECTURA:
#   PANEL   → panel_control_via_publica_bp
#   MÓDULO  → modulo_control_via_publica_rio_torio_bp
#   BOTÓN   → btn_rio_torio_usuarios_plazas (este archivo)
# =============================================================================
# 🛑 FIN INTRODUCCIÓN
# =============================================================================


# =============================================================================
# 📦 1️⃣ IMPORTACIONES Y BLUEPRINT DEL BOTÓN USUARIOS PLAZAS
# =============================================================================

from __future__ import annotations

from flask import Blueprint, render_template, request
from services.helpers import login_required, rol_required
from db import ejecutar_query


# =============================================================================
# 1.1️⃣ DEFINICIÓN DEL BLUEPRINT
# =============================================================================
# NOMBRE DEL BLUEPRINT:
#   - "btn_rio_torio_usuarios_plazas_bp"
#
# URL_PREFIX:
#   - "/control_via_publica/rio_torio/usuarios"
#
# RUTA COMPLETA DEL BOTÓN:
#   - /control_via_publica/rio_torio/usuarios/btn_rio_torio_usuarios_plazas
#
# ENDPOINT:
#   - "btn_rio_torio_usuarios_plazas_bp.btn_rio_torio_usuarios_plazas"
# =============================================================================

btn_rio_torio_usuarios_plazas_bp = Blueprint(
    "btn_rio_torio_usuarios_plazas_bp",
    __name__,
    url_prefix="/control_via_publica/rio_torio/usuarios",
)


# =============================================================================
# 🧠 2️⃣ HELPERS SQL · OBTENER USUARIOS Y PLAZAS
# =============================================================================
# DESCRIPCIÓN GENERAL
# -----------------------------------------------------------------------------
#   - _rt_obtener_usuarios_parquin:
#       · Devuelve la lista de usuarios de parquin_camiones.tbl_usuarios
#         con datos básicos de proveedor.
#
#   - _rt_obtener_plazas_de_usuario:
#       · Devuelve las plazas asociadas a un usuario concreto.
#
# NOTA:
#   - Se utiliza "parquin_camiones" como base de datos lógica
#     para usuarios y plazas de Río Torío.
# =============================================================================

def _rt_obtener_usuarios_parquin():
    """
    2.1️⃣ Devuelve la lista de usuarios de parquin_camiones.tbl_usuarios
         con información agregada de proveedor/cuenta.

    Campos devueltos:
      - idtbl_usuarios
      - idtbl_proveedores
      - numero_cuenta
      - nombre_proveedor (alias de Nombre_Razon_Social en tbl_proveedores)
    """
    sql = """
        SELECT
            u.idtbl_usuarios,
            u.idtbl_proveedores,
            u.numero_cuenta,
            p.Nombre_Razon_Social AS nombre_proveedor
        FROM tbl_usuarios AS u
        INNER JOIN bd_tbl_comunes.tbl_proveedores AS p
            ON u.idtbl_proveedores = p.Idtbl_proveedores
        ORDER BY u.idtbl_usuarios DESC
    """
    # Se usa tu patrón habitual: parámetros posicionales + nombre_bd
    return ejecutar_query(sql, (), "parquin_camiones")


def _rt_obtener_plazas_de_usuario(idtbl_usuarios: int):
    """
    2.2️⃣ Devuelve las plazas asociadas a un usuario concreto de parquin.

    Parámetros:
      - idtbl_usuarios: identificador del usuario de tbl_usuarios.

    Campos esperados en el SELECT (ajusta según tu tabla real):
      - idtbl_plazas
      - codigo_plazas
      - fila
    """
    sql = """
        SELECT
            p.idtbl_plazas,
            p.codigo_plazas,
            p.fila
        FROM tbl_plazas AS p
        WHERE p.idtbl_usuarios = %s
        ORDER BY p.codigo_plazas
    """
    return ejecutar_query(sql, (idtbl_usuarios,), "parquin_camiones")


# =============================================================================
# 📄 3️⃣ VISTA DEL BOTÓN · USUARIOS PLAZAS
# =============================================================================
# CONVENCIÓN
# -----------------------------------------------------------------------------
#   - Nombre de la función/vista:
#       btn_rio_torio_usuarios_plazas
#
#   - Ruta relativa al url_prefix:
#       /btn_rio_torio_usuarios_plazas
#
#   - Ruta completa:
#       /control_via_publica/rio_torio/usuarios/btn_rio_torio_usuarios_plazas
#
# PROTECCIONES
# -----------------------------------------------------------------------------
#   - @login_required:
#       · Requiere usuario autenticado.
#
#   - @rol_required("gestor"):
#       · Solo usuarios con rol "gestor" (y superiores, si tu decorator lo
#         contempla) pueden acceder.
#
# COMPORTAMIENTO
# -----------------------------------------------------------------------------
#   - GET sin parámetros:
#       · usuarios_parquin: lista para el <select>.
#       · usuario_seleccionado: None.
#       · plazas_usuario: [].
#
#   - GET con ?idtbl_usuarios=<ID>:
#       · usuarios_parquin: lista para el <select>.
#       · usuario_seleccionado: ese ID (string original de la query).
#       · plazas_usuario: lista de plazas asociadas al usuario.
#
# PLANTILLA RENDERIZADA
# -----------------------------------------------------------------------------
#   - templates/parquin/rio_torio/rio_torio_usuarios_plazas.html
#   - Render:
#       return render_template(
#           "parquin/rio_torio/rio_torio_usuarios_plazas.html",
#           usuarios_parquin=usuarios_parquin,
#           usuario_seleccionado=usuario_seleccionado,
#           plazas_usuario=plazas_usuario,
#       )
# =============================================================================

@btn_rio_torio_usuarios_plazas_bp.route(
    "/btn_rio_torio_usuarios_plazas",
    methods=["GET"],
)
@login_required
@rol_required("gestor")
def btn_rio_torio_usuarios_plazas():
    """
    3.1️⃣ BOTÓN · Usuarios → Plazas (RIO_TORIO)

    - Recupera la lista de usuarios de parquin (para el combo).
    - Si viene idtbl_usuarios en la query string, carga sus plazas.
    - Renderiza la plantilla:
        parquin/rio_torio/rio_torio_usuarios_plazas.html
    """

    # 3.1.1 Lista de usuarios disponibles para el <select>
    usuarios_parquin = _rt_obtener_usuarios_parquin()

    # 3.1.2 Leer parámetro de filtro (usuario seleccionado)
    usuario_seleccionado = request.args.get("idtbl_usuarios", "").strip()

    plazas_usuario = []
    if usuario_seleccionado:
        try:
            usuario_id_int = int(usuario_seleccionado)
        except ValueError:
            usuario_id_int = None

        if usuario_id_int:
            plazas_usuario = _rt_obtener_plazas_de_usuario(usuario_id_int)

    # 3.1.3 Renderizar plantilla con toda la información necesaria
    return render_template(
        "parquin/rio_torio/rio_torio_usuarios_plazas.html",
        usuarios_parquin=usuarios_parquin,
        usuario_seleccionado=usuario_seleccionado,
        plazas_usuario=plazas_usuario,
    )


# =============================================================================
# 🔗 4️⃣ INTEGRACIÓN Y REGISTRO DEL BLUEPRINT (DOCUMENTACIÓN)
# =============================================================================
# Este bloque es SOLO DOCUMENTACIÓN de integración (no se ejecuta aquí).
#
# 4.1️⃣ REGISTRO MANUAL EN create_app
# -----------------------------------------------------------------------------
#   from blueprints.parquin.btn_rio_torio_usuarios_plazas_bp import (
#       btn_rio_torio_usuarios_plazas_bp,
#   )
#   app.register_blueprint(btn_rio_torio_usuarios_plazas_bp)
#
# 4.2️⃣ RELACIÓN CON EL LISTADO PRINCIPAL
# -----------------------------------------------------------------------------
#   - Listado de usuarios:
#       · Plantilla:
#           templates/parquin/rio_torio/rio_torio_listar_usuarios.html
#       · Endpoint:
#           btn_rio_torio_listar_usuarios_bp.btn_rio_torio_listar_usuarios
#
#   - Desde ese listado, cuando implementes “Ver plazas”, podrás usar:
#
#       <a href="{{ url_for(
#                   'btn_rio_torio_usuarios_plazas_bp.btn_rio_torio_usuarios_plazas',
#                   idtbl_usuarios=u.idtbl_usuarios
#                ) }}">
#           Ver plazas
#       </a>
#
#   - Este botón (usuarios_plazas) mostrará la plantilla:
#       parquin/rio_torio/rio_torio_usuarios_plazas.html
#
# =============================================================================
# 🛑 FIN · BOTÓN INDEPENDIENTE USUARIOS PLAZAS RIO_TORIO
# =============================================================================