# blueprints/modulos/modulo_control_via_publica_contenedores_bp.py
# =============================================================================
# 🗑️ MÓDULO control_via_publica_CONTENEDORES · AGRUPADOR DE BOTONES
# =============================================================================

from flask import Blueprint, render_template
from services.helpers import rol_required

modulo_control_via_publica_contenedores_bp = Blueprint(
    "modulo_control_via_publica_contenedores_bp",
    __name__,
    url_prefix="/control-via-publica/contenedores",
    template_folder="templates/modulos/contenedores",
)


@modulo_control_via_publica_contenedores_bp.route("/", methods=["GET"])
@rol_required("gestor_via_publica")
def modulo_control_via_publica_contenedores():
    """
    Página principal del módulo CONTROL VÍA PÚBLICA · CONTENEDORES.

    Misión: solo agrupar/mostrar los botones (btn_control_via_publica_contenedores_*),
    sin lógica de CRUD.
    """
    return render_template("contenedores/index.html")
