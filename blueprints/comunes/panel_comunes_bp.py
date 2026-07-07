# =============================================================================
# 1️⃣ PANEL COMUNES · panel_comunes_bp
# =============================================================================
# Convención (Super Admin · columna 1):
#   panel_<panel_id>_bp
#
# En este caso:
#   panel_id  = comunes
#   blueprint = panel_comunes_bp
#
# RESPONSABILIDAD:
#   - Solo sirve como “panel raíz” para el Super Admin.
#   - No contiene lógica de negocio pesada.
#   - Opcionalmente puede mostrar un placeholder o redirigir al Super Admin.
# =============================================================================

from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required
from services.helpers import rol_required

panel_comunes_bp = Blueprint(
    "panel_comunes_bp",
    __name__,
    url_prefix="/comunes",
    template_folder="templates/comunes",
)


@panel_comunes_bp.route("/", methods=["GET"])
@login_required
@rol_required("gestor", "super_admin")
def panel_comunes():
    """
    PANEL · COMUNES

    - Punto de entrada del panel "Comunes".
    - El Super Admin lo descubre como:
          panel_comunes_bp
    - Esta vista puede:
        · Mostrar un HTML simple (panel_comunes.html), o
        · Redirigir directamente al Super Admin.
    """

    # Opción B: redirigir al Super Admin (descomenta si prefieres esto)
    # return redirect(url_for("super_admin_bp.super_admin"))
