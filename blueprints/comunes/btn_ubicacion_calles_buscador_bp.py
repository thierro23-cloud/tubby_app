# ================================================
# BLUEPRINT BUSCADOR DE CALLES
# ================================================
# Archivo: blueprints/comunes/btn_ubicacion_calles_buscador_bp.py
#
# DESCRIPCIÓN:
#   Blueprint de Flask responsable de:
#     - Mostrar el formulario/HTML del buscador de calles.
#     - Exponer APIs para:
#         · Listar municipios de una provincia.
#         · Buscar calles por municipio + texto (solo por nombre),
#           devolviendo también el tipo de vía (tbl_tipos_de_vias.tipos_de_vias)
#           para mostrar combinaciones como:
#             "CALLE Castilla", "PLAZA Castilla", "AVENIDA Castilla", etc.
#
# RUTAS (url_prefix="/comunes/calles"):
#   • GET  /buscador       → Página HTML del buscador.
#   • GET  /api/municipios → API: municipios por provincia.
#   • GET  /api/calles     → API: buscador de calles por municipio + texto.
#
# RELACIÓN:
#   • Se integra con el blueprint de edición:
#       btn_ubicacion_calles_editar_bp (url_prefix="/comunes/calles/editar")
#   • El HTML usa url_for para:
#       - api_municipios_por_provincia
#       - api_buscador_calles
#       - btn_ubicacion_calles_editar_form (para el botón "Editar").
# ================================================

from flask import Blueprint, render_template, request, jsonify
from db import ejecutar_query
from services.helpers import login_required, rol_required

btn_ubicacion_calles_buscador_bp = Blueprint(
    "btn_ubicacion_calles_buscador_bp",
    __name__,
    url_prefix="/comunes/calles",
)


# ================================================
# PÁGINA PRINCIPAL DEL BUSCADOR
# ================================================
@btn_ubicacion_calles_buscador_bp.route("/buscador", methods=["GET"])
@login_required
@rol_required("su")
def btn_ubicacion_calles_buscador():
    """
    Página principal del buscador de calles.

    Endpoint:
        GET /comunes/calles/buscador

    Requisitos:
        • Usuario autenticado (@login_required).
        • Rol de superusuario (@rol_required("su")).

    Flujo:
        1. Carga el listado de provincias (para el <select> inicial).
        2. Renderiza la plantilla 'comunes/calles/buscador_calles.html'
           con la lista de provincias.
    """
    sql_provincias = """
    SELECT
        idtbl_provincias AS id,
        provincias       AS nombre
    FROM tbl_provincias
    ORDER BY nombre
    """
    provincias = ejecutar_query(sql_provincias, nombre_bd="bd_tbl_comunes")

    return render_template(
        "comunes/calles/buscador_calles.html",
        provincias=provincias or [],
    )


# ================================================
# API: MUNICIPIOS POR PROVINCIA
# ================================================
@btn_ubicacion_calles_buscador_bp.route("/api/municipios", methods=["GET"])
@login_required
@rol_required("su")
def api_municipios_por_provincia():
    """
    Devuelve los municipios de una provincia en formato JSON.

    Endpoint:
        GET /comunes/calles/api/municipios

    Parámetros GET:
        • id_provincia (int, obligatorio): ID de la provincia.

    Respuesta JSON:
        • Exitoso:
            {
              "ok": true,
              "data": [
                  {"id": 1, "nombre": "Valladolid"},
                  ...
              ]
            }
        • Error de validación:
            {"ok": false, "msg": "..."}.
    """
    id_provincia = request.args.get("id_provincia", "").strip()
    if not id_provincia.isdigit():
        return jsonify({"ok": False, "msg": "Provincia no válida"})

    id_provincia = int(id_provincia)

    sql_municipios = """
    SELECT
        idtbl_municipios AS id,
        municipios       AS nombre
    FROM tbl_municipios
    WHERE idtbl_provincias = %s
    ORDER BY nombre
    """
    municipios = ejecutar_query(
        sql_municipios,
        params=(id_provincia,),
        nombre_bd="bd_tbl_comunes",
    )

    return jsonify({"ok": True, "data": municipios or []})


# ================================================
# API: BUSCADOR DE CALLES
# ================================================
@btn_ubicacion_calles_buscador_bp.route("/api/calles", methods=["GET"])
@login_required
@rol_required("su")
def api_buscador_calles():
    """
    Busca calles por municipio y texto (solo por el nombre de la calle),
    devolviendo todas las coincidencias que contengan esos caracteres,
    independientemente del tipo de vía (CALLE, PLAZA, AVENIDA, CTRA, etc.).

    El tipo de vía se obtiene desde tbl_tipos_de_vias.tipos_de_vias.

    Endpoint:
        GET /comunes/calles/api/calles

    Parámetros GET:
        • id_municipio (int, obligatorio): ID del municipio.
        • q (string, obligatorio): Texto a buscar (mín. 2 caracteres).

    Comportamiento:
        • Filtro:
            - c.idtbl_municipios = id_municipio
            - c.calles LIKE '%q%'
        • No se filtra por tipo de vía, solo se devuelve:
            - 'tipo_via' = tv.tipos_de_vias

    Ejemplo de resultados para q = 'Castilla':
        [
          {"id": 1, "nombre": "Castilla", "tipo_via": "CALLE"},
          {"id": 2, "nombre": "Castilla", "tipo_via": "PLAZA"},
          {"id": 3, "nombre": "Castilla", "tipo_via": "AVENIDA"}
        ]
    """
    id_municipio = request.args.get("id_municipio", "").strip()
    q = request.args.get("q", "").strip()

    if not id_municipio.isdigit():
        return jsonify({"ok": False, "msg": "Municipio no válido"})

    if len(q) < 2:
        return jsonify({"ok": False, "msg": "Introduce al menos 2 caracteres"})

    id_municipio = int(id_municipio)

    sql_calles = """
    SELECT
        c.idtbl_calles       AS id,
        c.calles             AS nombre,
        tv.tipos_de_vias     AS tipo_via
    FROM tbl_calles c
    LEFT JOIN tbl_tipos_de_vias tv
           ON c.idtbl_tipos_de_vias = tv.idtbl_tipos_de_vias
    WHERE c.idtbl_municipios = %s
      AND c.calles LIKE %s
    ORDER BY c.calles, tv.tipos_de_vias
    """
    data = ejecutar_query(
        sql_calles,
        params=(id_municipio, f"%{q}%"),
        nombre_bd="bd_tbl_comunes",
    )

    return jsonify({"ok": True, "data": data or []})
