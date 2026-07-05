# =============================================================================
# 🧩 MÓDULO · COMUNES UBICACIÓN (CONTENEDOR DE BOTONES)
# Archivo: blueprints/comunes/modulo_comunes_ubicacion_bp.py
# =============================================================================
"""
MÓDULO: comunes/ubicacion

Módulo ligero cuyo único propósito es:
  - Definir el endpoint `modulo_comunes_ubicacion`.
  - Colgarse del panel `panel_comunes`.
  - Servir como nodo intermedio para que el super_admin agrupe los
    botones `btn_ubicacion_*` bajo este módulo.
"""

from flask import Blueprint, render_template
from services.helpers import login_required, rol_required


# =============================================================================
# 1️⃣ BLUEPRINT DEL MÓDULO
# =============================================================================

modulo_comunes_ubicacion_bp = Blueprint(
    "modulo_comunes_ubicacion_bp",
    __name__,
    url_prefix="/comunes/ubicacion",
)
# Rutas: /comunes/ubicacion/...


# =============================================================================
# 2️⃣ VISTA DEL MÓDULO (SIN LÓGICA, SOLO CONTENEDOR)
# =============================================================================

@modulo_comunes_ubicacion_bp.route("/", methods=["GET"])
@login_required
@rol_required("super_admin")
def modulo_comunes_ubicacion():
    """
    Endpoint: modulo_comunes_ubicacion
    URL     : /comunes/ubicacion/

    Esta vista no tiene lógica de negocio; simplemente existe para que
    el sistema auto-descubrible detecte el módulo "ubicacion" dentro
    del panel "comunes" y pueda colgar aquí los botones `btn_ubicacion_*`.
    """
    # Puedes apuntar a una plantilla muy simple o reutilizar una genérica.
    return render_template("comunes/modulo_comunes_ubicacion.html")