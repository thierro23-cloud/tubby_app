## blueprints/inventario/panel_inventario_bp.py
"""
Panel Inventario
"""

from flask import Blueprint, redirect, url_for
from flask_login import login_required
from services.helpers import rol_required

panel_inventario_bp = Blueprint(
    "panel_inventario_bp",
    __name__,
    url_prefix="/inventario",
    template_folder="templates/inventario",
)


@panel_inventario_bp.route("/", methods=["GET"])
@login_required
@rol_required("gestor", "super_admin")
def panel_inventario():
    """Panel Inventario - Redirige al listado"""
    return redirect(url_for("btn_edificios_listado_bp.btn_edificios_listado"))
