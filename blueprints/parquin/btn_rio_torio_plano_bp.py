from __future__ import annotations

from flask import (
    Blueprint,
    render_template,
    request,
    flash,
    redirect,
    url_for,
    session,
)

from services.helpers import rol_required
from db import get_connection

# =============================================================================
# 1️⃣ BLUEPRINT DEL BOTÓN · PLANO RIO_TORIO
# =============================================================================
# ARCHIVO:
#   - btn_rio_torio_plano_bp.py
#
# NOMBRE DEL BLUEPRINT:
#   - btn_rio_torio_plano_bp
#
# URL_PREFIX:
#   - /parquin/rio_torio
#
# RUTA COMPLETA:
#   - /parquin/rio_torio/plano
#
# CONVENCIÓN SUPER ADMIN:
#   - Blueprint de botón: debe empezar por "btn_rio_torio_"
#   - Vista de botón:    debe empezar por "btn_"
# =============================================================================

btn_rio_torio_plano_bp = Blueprint(
    "btn_rio_torio_plano_bp",
    __name__,
    url_prefix="/parquin/rio_torio",
)

# =============================================================================
# 2️⃣ VISTA DEL BOTÓN · PLANO RIO_TORIO
# =============================================================================
# CONVENCIÓN:
#   - Nombre de la vista: btn_rio_torio_plano
#   - Endpoint generado:   btn_rio_torio_plano_bp.btn_rio_torio_plano
#   - Ruta:               /parquin/rio_torio/plano
# =============================================================================

@btn_rio_torio_plano_bp.route("/plano", methods=["GET"])
@rol_required("gestor", "super_admin")
def btn_rio_torio_plano():
    """
    BOTÓN · Plano del parquin Rio Torío.

    Muestra una fila del parquin con el estado de sus plazas
    y permite navegar entre filas mediante selector y navegación.

    CONTEXTO QUE ENVÍA AL TEMPLATE:
      - fila              -> fila seleccionada.
      - filas_disponibles -> lista de filas existentes.
      - plazas            -> plazas de la fila actual.
      - total             -> total de plazas en la fila.
      - libres            -> plazas libres en la fila.
      - ocupadas          -> plazas ocupadas en la fila.
    """

    # Seguridad extra basada en sesión, coherente con el resto del proyecto.
    if not session.get("user_id"):
        flash("Debes iniciar sesión", "danger")
        return redirect(url_for("auth_bp.login"))

    # Fila a visualizar. Se recibe como querystring ?fila=.
    fila = request.args.get("fila", 1, type=int)

    conn = get_connection("parquin_camiones")
    cursor = conn.cursor(dictionary=True)

    try:
        # Obtener todas las filas disponibles para selector y navegación.
        cursor.execute(
            """
            SELECT DISTINCT fila
            FROM tbl_plazas
            WHERE fila IS NOT NULL
            ORDER BY fila
            """
        )
        filas_rows = cursor.fetchall()
        filas_disponibles = [row["fila"] for row in filas_rows] or [fila]

        # Si la fila pedida no existe, forzamos la primera disponible.
        if fila not in filas_disponibles:
            fila = filas_disponibles[0]

        # Obtener plazas de la fila seleccionada.
        cursor.execute(
            """
            SELECT
                pl.idtbl_plazas AS idtbl_plazas,
                pl.codigo_plazas AS codigo_plazas,
                pl.fila AS fila,
                pl.idtbl_usuarios AS idtbl_usuarios,
                CASE
                    WHEN pl.idtbl_usuarios IS NULL THEN 'libre'
                    ELSE 'ocupada'
                END AS estado,
                COALESCE(p.Nombre_Razon_Social, '') AS texto_asignacion
            FROM tbl_plazas pl
            LEFT JOIN tbl_usuarios u
                   ON pl.idtbl_usuarios = u.idtbl_usuarios
            LEFT JOIN bd_tbl_comunes.tbl_proveedores p
                   ON u.idtbl_proveedores = p.Idtbl_proveedores
            WHERE pl.fila = %s
            ORDER BY pl.codigo_plazas
            """,
            (fila,),
        )
        plazas = cursor.fetchall()

        # Estadísticas de la fila.
        total = len(plazas)
        libres = sum(1 for p in plazas if p["estado"] == "libre")
        ocupadas = sum(1 for p in plazas if p["estado"] == "ocupada")

    finally:
        cursor.close()
        conn.close()

    return render_template(
        "parquin/rio_torio/rio_torio_plano.html",
        fila=fila,
        filas_disponibles=filas_disponibles,
        plazas=plazas,
        total=total,
        libres=libres,
        ocupadas=ocupadas,
    )