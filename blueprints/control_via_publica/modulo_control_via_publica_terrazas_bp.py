# blueprints/modulos/modulo_control_via_publica_terrazas_bp.py
# =============================================================================
# ☕ MÓDULO control_via_publica_TERRAZAS · Agrupador de botones
# =============================================================================
# FUNCIÓN: Agrupador de botones relacionados con terrazas
# Discovery: detecta "modulo_control_via_publica_terrazas_bp"
#   · panel:  control_via_publica
#   · módulo: control_via_publica_terrazas
# =============================================================================

from flask import Blueprint, render_template
from services.helpers import rol_required

modulo_control_via_publica_terrazas_bp = Blueprint(
    "modulo_control_via_publica_terrazas_bp",
    __name__,
    url_prefix="/control-via-publica/terrazas",
    template_folder="templates/modulos/terrazas",
)

@modulo_control_via_publica_terrazas_bp.route("/", methods=["GET"])
@rol_required("gestor_via_publica")
def modulo_control_via_publica_terrazas():
    """Página principal del módulo control_via_publica_TERRAZAS (agrupador de botones)."""
    return render_template("terrazas/index.html")