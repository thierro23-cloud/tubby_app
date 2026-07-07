# blueprints/control_obras/modulo_control_via_publica_obras_bp.py

from flask import Blueprint, render_template, request, jsonify
from services.helpers import rol_required
from datetime import datetime

from obras_core.backend_obras import crear_evento_para_obra
from db import ejecutar_query

modulo_control_via_publica_obras_bp = Blueprint(
    "modulo_control_via_publica_obras_bp",
    __name__,
    url_prefix="/control-via-publica/obras",
    template_folder="templates/modulos/obras",
)


@modulo_control_via_publica_obras_bp.route("/", methods=["GET"])
@rol_required("gestor_via_publicica")
def modulo_control_via_publica_obras():
    """Página principal del módulo control_via_publica_OBRAS (agrupador de botones)."""
    return render_template("obras/index.html")


@modulo_control_via_publica_obras_bp.route("/<int:id_obra>/agenda", methods=["POST"])
@rol_required("gestor_via_publicica")
def api_crear_evento_agenda_obra(id_obra: int):
    """
    Crea un evento de agenda para la obra indicada.

    Agrupa la lógica:
      - Lee la obra.
      - Valida que tenga calle y fechas.
      - Llama al backend de obras para crear el evento de agenda.
    """
    filas = ejecutar_query(
        """
        SELECT
            idtbl_obras,
            idtbl_calles,
            numero_expediente,
            ref_catastral,
            fecha_obras_inicio,
            fecha_obras_fin
        FROM tbl_obras
        WHERE idtbl_obras = %s
        """,
        (id_obra,),
        nombre_bd="control_via_publica",
    )

    if not filas:
        return jsonify({"error": "Obra no encontrada"}), 404

    obra = filas[0]

    if (
        not obra["idtbl_calles"]
        or not obra["fecha_obras_inicio"]
        or not obra["fecha_obras_fin"]
    ):
        return jsonify({"error": "La obra no tiene calle o fechas definidas"}), 400

    id_calle = obra["idtbl_calles"]
    fecha_inicio: datetime = obra["fecha_obras_inicio"]
    fecha_fin: datetime = obra["fecha_obras_fin"]

    titulo = f"Obra {obra['numero_expediente'] or ''}".strip()
    descripcion = f"Ref. catastral: {obra['ref_catastral'] or ''}".strip()

    id_agenda = crear_evento_para_obra(
        id_obra=id_obra,
        id_calle=id_calle,
        titulo=titulo,
        descripcion=descripcion or None,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
    )

    return jsonify({"estado": "ok", "id_agenda": id_agenda})
