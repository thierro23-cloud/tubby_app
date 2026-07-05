# blueprints/modulos/modulo_control_via_publica_vados_bp.py
# =============================================================================
# 🚗 MÓDULO control_via_publica_VADOS · Agrupador de botones
# =============================================================================
# FUNCIÓN: Agrupador de botones relacionados con vados
# Discovery: detecta "modulo_control_via_publica_vados_bp"
#   · panel:  control_via_publica
#   · módulo: control_via_publica_vados
# =============================================================================

from flask import Blueprint, render_template
from services.helpers import rol_required

modulo_control_via_publica_vados_bp = Blueprint(
    "modulo_control_via_publica_vados_bp",
    __name__,
    url_prefix="/control-via-publica/vados",
    template_folder="templates/modulos/vados",
)

@modulo_control_via_publica_vados_bp.route("/", methods=["GET"])
@rol_required("gestor_via_publica")
def modulo_control_via_publica_vados():
    """Página principal del módulo control_via_publica_VADOS (agrupador de botones)."""
    return render_template("vados/index.html")