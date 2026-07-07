# blueprints/inventario/modulo_inventario_edificios_bp.py
"""
================================================================================
MÓDULO: Inventario > Edificios
================================================================================
Descripción: Módulo organizador de edificios (sin plantilla propia)
Función: Solo organiza los botones hijos, redirige al listado
Ruta: /inventario/
================================================================================
"""

# ============================================================================
# IMPORTS
# ============================================================================
from flask import Blueprint, redirect, url_for

# ============================================================================
# BLUEPRINT
# ============================================================================
modulo_inventario_edificios_bp = Blueprint(
    "modulo_inventario_edificios_bp", __name__, url_prefix="/inventario/"
)


# ============================================================================
# RUTA PRINCIPAL: REDIRECCIÓN
# ============================================================================
@modulo_inventario_edificios_bp.route("/")
def index():
    """
    Redirige al listado de edificios

    Nota:
    -----
    Este módulo no tiene plantilla propia, solo organiza los botones.
    Al acceder a /inventario/edificios/ redirige automáticamente al listado.
    """
    return redirect(url_for("btn_edificios_listado_bp.btn_edificios_listado"))
