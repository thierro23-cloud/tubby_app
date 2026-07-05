# blueprints/modulos/modulo_control_via_publica_ocupacion_via_bp.py
# =============================================================================
# 🚧 MÓDULO control_via_publica_OCUPACION_VIA · Agrupador de botones
# =============================================================================
# FUNCIÓN: Agrupador de botones relacionados con ocupación de vía pública
# Discovery: detecta "modulo_control_via_publica_ocupacion_via_bp"
#   · panel:  control_via_publica
#   · módulo: control_via_publica_ocupacion_via
# =============================================================================

from flask import Blueprint, render_template
from services.helpers import rol_required

modulo_control_via_publica_ocupacion_via_bp = Blueprint(
    "modulo_control_via_publica_ocupacion_via_bp",
    __name__,
    url_prefix="/control-via-publica/ocupacion-via",
    template_folder="templates/modulos/ocupacion_via",
)

@modulo_control_via_publica_ocupacion_via_bp.route("/", methods=["GET"])
@rol_required("gestor_via_publica")
def modulo_control_via_publica_ocupacion_via():
    """Página principal del módulo control_via_publica_OCUPACION_VIA (agrupador de botones)."""
    return render_template("ocupacion_via/index.html")