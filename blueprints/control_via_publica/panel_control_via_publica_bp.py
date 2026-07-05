# blueprints/control_obras/panel_control_via_publica_bp.py
# =============================================================================
# 🌐 PANEL CONTROL VÍA PÚBLICA · SOLO AGRUPA MÓDULOS
# =============================================================================

from flask import Blueprint, jsonify, current_app
from services.helpers import rol_required

panel_control_via_publica_bp = Blueprint(
    "panel_control_via_publica_bp",
    __name__,
    url_prefix="/panel-control-via-publica",
)

def _descubrir_modulos_control_via_publica():
    """
    Devuelve la lista de módulos de CONTROL VÍA PÚBLICA
    a partir de los blueprints:

        modulo_control_via_publica_<modulo_id>_bp
    """
    panel_id = "control_via_publica"
    modulos = []

    for bp_name, bp in current_app.blueprints.items():
        if not bp_name.startswith("modulo_control_via_publica_"):
            continue
        if not bp_name.endswith("_bp"):
            continue

        # modulo_control_via_publica_contenedores_bp
        partes = bp_name.split("_")
        # ["modulo", "control", "via", "publica", "contenedores", "bp"]
        modulo_id = "_".join(partes[4:-1]) or partes[4]  # contenedores, obras, ocupacion_via, ...

        modulos.append(
            {
                "modulo": modulo_id,
                "blueprint": bp_name,
            }
        )

    # Orden opcional por nombre de módulo
    modulos.sort(key=lambda m: m["modulo"])
    return {
        "panel": panel_id,
        "modulos": modulos,
    }

@panel_control_via_publica_bp.route("/panel", methods=["GET"])
@rol_required("gestor", "super_admin")
def api_panel_control_via_publica():
    """
    API JSON · PANEL CONTROL VÍA PÚBLICA

    Agrupa todos los módulos cuyo blueprint sea:
        modulo_control_via_publica_<modulo_id>_bp
    """
    data = _descubrir_modulos_control_via_publica()
    return jsonify(data)