# =============================================================================
# 🧱 COMUNES · PROVEEDORES · USUARIOS (BOTÓN)
# =============================================================================
# OBJETIVO GENERAL
# -----------------------------------------------------------------------------
# Gestionar, desde un módulo COMÚN, el usuario asociado a cada proveedor:
#
#   - Lee proveedores de:      bd_tbl_comunes.tbl_proveedores
#   - Lee/crea/actualiza de:   parquin_camiones.tbl_usuarios
#
# Cada PROVEEDOR tendrá un pequeño formulario incrustado en la tabla para
# crear/editar su usuario (numero_cuenta, activo_baja, fechas...).
#
# PLANTILLA ASOCIADA
# -----------------------------------------------------------------------------
#   templates/comunes/proveedores/proveedores_usuarios_gestionar.html
#
#   La vista hace:
#       return render_template(
#           "comunes/proveedores/proveedores_usuarios_gestionar.html",
#           filas=filas,
#           titulo="Usuarios por proveedor",
#       )
#
# RUTA HTTP Y ENDPOINT
# -----------------------------------------------------------------------------
#   - url_prefix del blueprint:
#         /comunes/proveedores_usuarios_gestionar
#
#   - Ruta de la vista:
#         /btn_proveedores_usuarios_gestionar
#
#   - URL final:
#         /comunes/proveedores_usuarios/btn_proveedores_usuarios_gestionar
#
#   - Endpoint (para url_for):
#         "btn_proveedores_usuarios_gestionar_bp.btn_proveedores_usuarios_gestionar"
#
# SISTEMA DE LOGIN Y ROLES UTILIZADO
# -----------------------------------------------------------------------------
# ⚠️ IMPORTANTE: En este módulo NO se usa Flask-Login.
#
#   - NO debemos importar ni usar:
#         from flask_login import login_required
#         current_user, login_user, etc.
#
#   - SÍ usamos nuestro sistema propio definido en services/helpers.py:
#         - login_required  → comprueba session["user_id"]
#         - rol_required    → comprueba session["rol"] con regla de oro:
#                                rol == "super_admin" → acceso total
#
# De esta forma TODO el control de acceso pasa por:
#   - session["user_id"] y session["rol"]
#   - funciones is_logged(), get_role(), rol_required(), etc.
# =============================================================================

from __future__ import annotations

from flask import Blueprint, render_template, request, redirect, url_for, flash

# ⚠️ NO USAR Flask-Login AQUÍ:
# from flask_login import login_required  ❌  (NO)
# En su lugar usamos nuestros decoradores propios:
from services.helpers import login_required, rol_required

from db import ejecutar_query, ejecutar_non_query

# =============================================================================
# 0️⃣ BLUEPRINT · REGISTRO EN LA APP
# =============================================================================
# Este blueprint "agrupa" las rutas relacionadas con
# COMUNES / PROVEEDORES / USUARIOS.
#
#   - Nombre interno: btn_proveedores_usuarios_gestionar_bp
#   - Prefijo de URL: /comunes/proveedores_usuarios
#
# Cualquier ruta que declaremos aquí colgará de ese prefijo.
# =============================================================================

btn_proveedores_usuarios_gestionar_bp = Blueprint(
    "btn_proveedores_usuarios_gestionar_bp",
    __name__,
    url_prefix="/comunes/proveedores_usuarios",
)


# =============================================================================
# 1️⃣ HELPERS SQL · PROVEEDORES + USUARIOS (NOMBRES REALES)
# =============================================================================
# PROVEEDORES:
#   - BD:    bd_tbl_comunes
#   - Tabla: tbl_proveedores
#   - Campos relevantes aquí:
#       Idtbl_proveedores, Nombre_Razon_Social, NIF,
#       Telefono, telefono_movil, correo_electronico_comercial,
#       parquin, ... (y otros que no usamos en esta pantalla)
#
# USUARIOS:
#   - BD:    parquin_camiones
#   - Tabla: tbl_usuarios
#   - Se asume que tiene:
#       idtbl_usuarios, idtbl_proveedores, numero_cuenta,
#       activo_baja, fecha_inicio, fecha_baja
# =============================================================================


def _obtener_proveedores_con_usuarios():
    """
    Devuelve proveedores + usuario (si existe), cruzando:

      - bd_tbl_comunes.tbl_proveedores  (alias p)
      - parquin_camiones.tbl_usuarios   (alias u)

    Campos devueltos (coinciden con la plantilla):
      - idtbl_proveedores        (Idtbl_proveedores)
      - proveedor_nombre         (Nombre_Razon_Social)
      - proveedor_nif            (NIF)
      - proveedor_telefono       (Telefono)
      - proveedor_email          (correo_electronico_comercial)
      - proveedor_activo_baja    (recibir_informe_pendientes u otro estado)
      - proveedor_parquin        (parquin, flag de proveedor con parquin)
      - idtbl_usuarios
      - numero_cuenta
      - usuario_activo_baja
      - fecha_inicio
      - fecha_baja
    """
    sql = """
        SELECT
            -- 🧑‍💼 DATOS DEL PROVEEDOR (bd_tbl_comunes.tbl_proveedores)
            p.Idtbl_proveedores                       AS idtbl_proveedores,
            p.Nombre_Razon_Social                     AS proveedor_nombre,
            p.NIF                                     AS proveedor_nif,
            p.Telefono                                AS proveedor_telefono,
            p.correo_electronico_comercial            AS proveedor_email,
            p.recibir_informe_pendientes              AS proveedor_activo_baja,
            p.parquin                                 AS proveedor_parquin,

            -- 👤 DATOS DEL USUARIO (parquin_camiones.tbl_usuarios)
            u.idtbl_usuarios,
            u.numero_cuenta,
            u.activo_baja                             AS usuario_activo_baja,
            u.fecha_inicio,
            u.fecha_baja

        FROM bd_tbl_comunes.tbl_proveedores AS p
        LEFT JOIN parquin_camiones.tbl_usuarios AS u
               ON u.idtbl_proveedores = p.Idtbl_proveedores

        -- Solo proveedores con checkbox de parquin activo
        WHERE p.parquin = 1

        ORDER BY p.Nombre_Razon_Social
    """
    # Conectamos contra bd_tbl_comunes; el SQL ya indica la BD de cada tabla.
    return ejecutar_query(sql, (), "bd_tbl_comunes")


def _guardar_usuario_proveedor(datos: dict) -> None:
    """
    Inserta o actualiza un usuario vinculado a un proveedor en:

      parquin_camiones.tbl_usuarios

    REGLA:
      - Si viene idtbl_usuarios → UPDATE.
      - Si NO viene            → INSERT.

    Espera en "datos":
      - idtbl_proveedores: int  (Idtbl_proveedores del proveedor en comunes)
      - idtbl_usuarios   : int | None
      - numero_cuenta    : str
      - activo_baja      : str
      - fecha_inicio     : str | None (YYYY-MM-DD)
      - fecha_baja       : str | None (YYYY-MM-DD)
    """
    id_usuario = datos.get("idtbl_usuarios")

    if id_usuario:
        # 🔁 UPDATE existente
        sql = """
            UPDATE parquin_camiones.tbl_usuarios
               SET
                   idtbl_proveedores = %(idtbl_proveedores)s,
                   numero_cuenta     = %(numero_cuenta)s,
                   activo_baja       = %(activo_baja)s,
                   fecha_inicio      = %(fecha_inicio)s,
                   fecha_baja        = %(fecha_baja)s
             WHERE idtbl_usuarios = %(idtbl_usuarios)s
        """
    else:
        # 🆕 INSERT nuevo
        sql = """
            INSERT INTO parquin_camiones.tbl_usuarios (
                idtbl_proveedores,
                numero_cuenta,
                activo_baja,
                fecha_inicio,
                fecha_baja
            )
            VALUES (
                %(idtbl_proveedores)s,
                %(numero_cuenta)s,
                %(activo_baja)s,
                %(fecha_inicio)s,
                %(fecha_baja)s
            )
        """

    ejecutar_non_query(sql, datos, "parquin_camiones")


# =============================================================================
# 2️⃣ VISTA · BOTÓN GESTIONAR USUARIOS POR PROVEEDOR
# =============================================================================
# URL FINAL:
#   /comunes/proveedores_usuarios/btn_proveedores_usuarios_gestionar
#
# ENDPOINT (para url_for):
#   "btn_proveedores_usuarios_gestionar_bp.btn_proveedores_usuarios_gestionar"
#
# PROTECCIÓN DE ACCESO:
#   - @login_required (nuestro, de services.helpers):
#       · Exige que exista session["user_id"].
#
#   - @rol_required("gestor", "super_admin"):
#       · Permite si:
#           · rol_actual == "gestor"
#           · o bien rol_actual == "super_admin" (regla de oro).
#
# ⚠️ IMPORTANTE:
#   - No interviene Flask-Login.
#   - No se chequea current_user, solo session["user_id"] y session["rol"].
# =============================================================================


@btn_proveedores_usuarios_gestionar_bp.route(
    "/btn_proveedores_usuarios_gestionar",
    methods=["GET", "POST"],
)
@login_required
@rol_required("gestor", "super_admin")
def btn_proveedores_usuarios_gestionar():
    """
    BOTÓN · Gestionar usuarios por proveedor (módulo comunes).

    - GET  → lista proveedores + usuario (si existe) y pinta la tabla
             con un formulario por proveedor.

    - POST → guarda usuario del proveedor (INSERT/UPDATE) usando los datos
             del formulario de la fila enviada.
    """

    # -------------------------------------------------------------------------
    # 2.1 CASO POST → GUARDAR CAMBIOS DE UN PROVEEDOR
    # -------------------------------------------------------------------------
    if request.method == "POST":
        # En cada formulario de la tabla tenemos:
        #   <input type="hidden" name="idtbl_proveedores" ...>
        id_proveedor = request.form.get("idtbl_proveedores")

        if not id_proveedor:
            flash("Falta el id del proveedor.", "warning")
            return redirect(
                url_for(
                    "btn_proveedores_usuarios_gestionar_bp."
                    "btn_proveedores_usuarios_gestionar"
                )
            )

        # Construimos el diccionario de datos con valores seguros por defecto.
        datos = {
            "idtbl_proveedores": int(id_proveedor),
            "idtbl_usuarios": request.form.get("idtbl_usuarios") or None,
            "numero_cuenta": request.form.get("numero_cuenta") or "",
            "activo_baja": request.form.get("activo_baja") or "activo",
            "fecha_inicio": request.form.get("fecha_inicio") or None,
            "fecha_baja": request.form.get("fecha_baja") or None,
        }

        # Guardar en BD (INSERT o UPDATE según haya idtbl_usuarios)
        _guardar_usuario_proveedor(datos)
        flash("Usuario del proveedor actualizado.", "success")

        # Patrón PRG (Post/Redirect/Get): recargar la página tras guardar
        return redirect(
            url_for(
                "btn_proveedores_usuarios_gestionar_bp."
                "btn_proveedores_usuarios_gestionar"
            )
        )

    # -------------------------------------------------------------------------
    # 2.2 CASO GET → MOSTRAR TABLA DE PROVEEDORES + USUARIOS
    # -------------------------------------------------------------------------
    filas = _obtener_proveedores_con_usuarios()

    # "filas" se pasa a la plantilla, que dibuja una fila y un formulario
    # por proveedor.
    return render_template(
        "comunes/proveedores/proveedores_usuarios_gestionar.html",
        filas=filas,
        titulo="Usuarios por proveedor",
    )
