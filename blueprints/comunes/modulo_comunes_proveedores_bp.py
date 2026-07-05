# =============================================================================
# 🧩 MÓDULO · COMUNES PROVEEDORES (CONTENEDOR DE BOTONES)
# Archivo: blueprints/comunes/modulo_comunes_proveedores_bp.py
# =============================================================================
"""
MÓDULO: comunes/proveedores

Módulo ligero cuyo único propósito es:
  - Definir el endpoint `modulo_comunes_proveedores`.
  - Colgarse del panel `panel_comunes`.
  - Servir como nodo intermedio para que el super_admin agrupe los
    botones `btn_proveedores_*` bajo este módulo.
"""

from flask import Blueprint, render_template
from services.helpers import login_required, rol_required


# =============================================================================
# 1️⃣ BLUEPRINT DEL MÓDULO
# =============================================================================

modulo_comunes_proveedores_bp = Blueprint(
    "modulo_comunes_proveedores_bp",
    __name__,
    url_prefix="/comunes/proveedores",
)
# Rutas: /comunes/proveedores/...


# =============================================================================
# 2️⃣ VISTA DEL MÓDULO (SIN LÓGICA, SOLO CONTENEDOR)
# =============================================================================

@modulo_comunes_proveedores_bp.route("/", methods=["GET"])
@login_required
@rol_required("super_admin")
def modulo_comunes_proveedores():
    """
    Endpoint: modulo_comunes_proveedores
    URL     : /comunes/proveedores/

    Esta vista no tiene lógica de negocio; simplemente existe para que
    el sistema auto-descubrible detecte el módulo "proveedores" dentro
    del panel "comunes" y pueda colgar aquí los botones `btn_proveedores_*`.
    """
    # Puedes apuntar a una plantilla muy simple o incluso reutilizar una genérica.
    return render_template("comunes/modulo_comunes_proveedores.html")