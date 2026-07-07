# blueprints/gestores/panel_gestores_bp.py
# =============================================================================
# 👥 PANEL GESTORES · REDIRECCIÓN SENCILLA
# =============================================================================
# Este panel no tiene plantilla propia.
# Solo define una ruta "bonita" /panel-gestores/panel
# que redirige al botón principal:
#   btn_administrar_gestores_bp.btn_administrar_gestores
# =============================================================================

from flask import Blueprint, redirect, url_for
from services.helpers import rol_required

panel_gestores_bp = Blueprint(
    "panel_gestores_bp",
    __name__,
    url_prefix="/panel-gestores",
)


@panel_gestores_bp.route("/panel", methods=["GET"])
@rol_required("super_admin")
def panel_gestores():
    """
    Redirige al botón principal de administración de tableros de gestores.

    Solo accesible para SUPER ADMIN.
    """
    return redirect(url_for("btn_administrar_gestores_bp.btn_administrar_gestores"))
