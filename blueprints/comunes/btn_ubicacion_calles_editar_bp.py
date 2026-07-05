# ================================================
# BLUEPRINT EDICIÓN DE CALLES (SIN DESTINADO)
# ================================================
# Archivo: blueprints/communes/btn_ubicacion_calles_editar_bp.py
#
# Gestiona el CRUD de calles (tbl_calles) y sus relaciones:
#   - tbl_municipios
#   - tbl_tipos_de_vias
#   - tbl_barrios
# ================================================

from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from db import ejecutar_query
from services.helpers import login_required, rol_required

btn_ubicacion_calles_editar_bp = Blueprint(
    "btn_ubicacion_calles_editar_bp",
    __name__,
    url_prefix="/comunes/calles/editar",
)

# ================================================
# FUNCIONES AUXILIARES
# ================================================

def obtener_calle_por_id(idtbl_calles):
    """
    Devuelve los datos completos de una calle dada su ID.

    IMPORTANTE:
        ejecutar_query devuelve una lista de filas.
        Esta función devuelve SOLO la primera fila (dict),
        para que en Jinja se use calle.campo y no lista.campo.
    """
    sql = """
    SELECT
        idtbl_calles,
        idtbl_municipios,
        idtbl_tipos_de_vias,
        calles,
        Codigopostal,
        Barrio,
        idtbl_barrios
    FROM tbl_calles
    WHERE idtbl_calles = %s
    """
    rows = ejecutar_query(
        sql,
        params=(idtbl_calles,),
        nombre_bd="bd_tbl_comunes",
    )

    # DEBUG: imprimir qué devuelve ejecutar_query
    print("DEBUG obtener_calle_por_id rows =", rows)

    if rows:
        # rows[0] es la primera fila (dict o similar)
        return rows[0]
    return None


def obtener_lista_municipios():
    """
    Devuelve la lista de municipios para el <select>.
    """
    sql = """
    SELECT
        idtbl_municipios AS id,
        municipios       AS nombre
    FROM tbl_municipios
    ORDER BY nombre
    """
    return ejecutar_query(sql, nombre_bd="bd_tbl_comunes") or []


def obtener_lista_tipos_de_vias():
    """
    Devuelve la lista de tipos de vías (tbl_tipos_de_vias).
    """
    sql = """
    SELECT
        idtbl_tipos_de_vias AS id,
        tipos_de_vias       AS nombre
    FROM tbl_tipos_de_vias
    ORDER BY nombre
    """
    return ejecutar_query(sql, nombre_bd="bd_tbl_comunes") or []


def obtener_lista_barrios():
    """
    Devuelve la lista de barrios (tbl_barrios).
    """
    sql = """
    SELECT
        idtbl_barrios AS id,
        barrios       AS nombre
    FROM tbl_barrios
    ORDER BY nombre
    """
    return ejecutar_query(sql, nombre_bd="bd_tbl_comunes") or []

# ================================================
# RUTAS
# ================================================

@btn_ubicacion_calles_editar_bp.route("/<int:idtbl_calles>", methods=["GET"])
@login_required
@rol_required("su")
def btn_ubicacion_calles_editar_form(idtbl_calles):
    """
    Muestra el formulario para editar una calle existente.

    Flujo:
        1. Obtiene la calle por ID (dict con los campos de tbl_calles).
        2. Si no existe, redirige al buscador de calles.
        3. Carga las listas de:
           - municipios
           - tipos de vías
           - barrios
        4. Renderiza la plantilla 'comunes/calles/editar_calle.html'.
    """
    calle = obtener_calle_por_id(idtbl_calles)

    # DEBUG opcional: ver qué llega a la plantilla
    print("DEBUG btn_ubicacion_calles_editar_form calle =", calle, "type =", type(calle))

    if not calle:
        return redirect(
            url_for("btn_ubicacion_calles_buscador_bp.btn_ubicacion_calles_buscador")
        )

    municipios_list = obtener_lista_municipios()
    tipos_de_vias_list = obtener_lista_tipos_de_vias()
    barrios_list = obtener_lista_barrios()

    return render_template(
        "comunes/calles/editar_calle.html",
        calle=calle,
        municipios_list=municipios_list,
        tipos_de_vias_list=tipos_de_vias_list,
        barrios_list=barrios_list,
    )


@btn_ubicacion_calles_editar_bp.route("/<int:idtbl_calles>", methods=["POST"])
@login_required
@rol_required("su")
def btn_ubicacion_calles_editar_update(idtbl_calles):
    """
    Actualiza los datos de una calle existente.

    Endpoint:
        POST /comunes/calles/editar/<idtbl_calles>

    Notas:
        - 'Barrio' puede ir vacío en el formulario; se guarda como NULL.
    """
    calles = request.form.get("calles", "").strip()
    Codigopostal = request.form.get("Codigopostal", "").strip()
    Barrio = request.form.get("Barrio", "").strip()

    # Permitir barrio nulo: si viene vacío, lo convertimos a None (NULL en MySQL)
    if not Barrio:
        Barrio = None

    idtbl_municipios = int(request.form.get("idtbl_municipios", "0") or 0)
    idtbl_tipos_de_vias = int(request.form.get("idtbl_tipos_de_vias", "0") or 0)
    idtbl_barrios = int(request.form.get("idtbl_barrios", "0") or 0)

    if not calles or not idtbl_municipios:
        return jsonify(
            {"ok": False, "msg": "Nombre de calle y municipio son obligatorios"}
        )

    sql = """
    UPDATE tbl_calles
    SET
        idtbl_municipios    = %s,
        idtbl_tipos_de_vias = %s,
        calles              = %s,
        Codigopostal        = %s,
        Barrio              = %s,
        idtbl_barrios       = %s
    WHERE idtbl_calles = %s
    """
    try:
        ejecutar_query(
            sql,
            params=(
                idtbl_municipios,
                idtbl_tipos_de_vias,
                calles,
                Codigopostal,
                Barrio,          # puede ser None → NULL
                idtbl_barrios,
                idtbl_calles,
            ),
            nombre_bd="bd_tbl_comunes",
        )
        return jsonify({"ok": True, "msg": "Calle actualizada correctamente"})
    except Exception as e:
        return jsonify({"ok": False, "msg": f"Error al actualizar: {str(e)}"})


@btn_ubicacion_calles_editar_bp.route("/crear", methods=["POST"])
@login_required
@rol_required("su")
def btn_ubicacion_calles_crear():
    """
    Crea una nueva calle en tbl_calles.

    Endpoint:
        POST /comunes/calles/editar/crear

    Notas:
        - 'Barrio' puede ir vacío en el formulario; se guarda como NULL.
    """
    calles = request.form.get("calles", "").strip()
    Codigopostal = request.form.get("Codigopostal", "").strip()
    Barrio = request.form.get("Barrio", "").strip()

    # Permitir barrio nulo: si viene vacío, lo convertimos a None (NULL en MySQL)
    if not Barrio:
        Barrio = None

    idtbl_municipios = int(request.form.get("idtbl_municipios", "0") or 0)
    idtbl_tipos_de_vias = int(request.form.get("idtbl_tipos_de_vias", "0") or 0)
    idtbl_barrios = int(request.form.get("idtbl_barrios", "0") or 0)

    if not calles or not idtbl_municipios:
        return jsonify(
            {"ok": False, "msg": "Nombre de calle y municipio son obligatorios"}
        )

    sql = """
    INSERT INTO tbl_calles (
        idtbl_municipios,
        idtbl_tipos_de_vias,
        calles,
        Codigopostal,
        Barrio,
        idtbl_barrios
    )
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    try:
        ejecutar_query(
            sql,
            params=(
                idtbl_municipios,
                idtbl_tipos_de_vias,
                calles,
                Codigopostal,
                Barrio,      # puede ser None → NULL
                idtbl_barrios,
            ),
            nombre_bd="bd_tbl_comunes",
        )
        return jsonify({"ok": True, "msg": "Calle creada correctamente"})
    except Exception as e:
        return jsonify({"ok": False, "msg": f"Error al crear: {str(e)}"})


@btn_ubicacion_calles_editar_bp.route("/eliminar/<int:idtbl_calles>", methods=["POST"])
@login_required
@rol_required("su")
def btn_ubicacion_calles_eliminar(idtbl_calles):
    """
    Elimina una calle por su ID.

    Endpoint:
        POST /comunes/calles/editar/eliminar/<idtbl_calles>
    """
    sql = """
    DELETE FROM tbl_calles
    WHERE idtbl_calles = %s
    """
    try:
        ejecutar_query(
            sql,
            params=(idtbl_calles,),
            nombre_bd="bd_tbl_comunes",
        )
        return jsonify({"ok": True, "msg": "Calle eliminada correctamente"})
    except Exception as e:
        return jsonify({"ok": False, "msg": f"Error al eliminar: {str(e)}"})