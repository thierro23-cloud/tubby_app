# blueprints/panel_vigilantes/panel_vigilantes_bp.py
from flask import Blueprint, render_template

panel_vigilantes_bp = Blueprint(
    "panel_vigilantes_bp",     # nombre del blueprint
    __name__,
    url_prefix="/panel_vigilantes",
)

@panel_vigilantes_bp.route("/panel")
def panel_vigilantes():
    tarjetas = obtener_tarjetas("vigilantes")
    return render_template(
        "vigilantes/panel_vigilantes.html",
        tarjetas=tarjetas,
    )
