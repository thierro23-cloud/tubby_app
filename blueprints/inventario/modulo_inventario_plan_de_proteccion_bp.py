# blueprints/inventario/modulo_inventario_plan_de_proteccion_bp.py
"""
================================================================================
MÓDULO: Inventario > Planes de protección
================================================================================
Descripción:
    Módulo organizador de los planes de protección dentro del panel de
    inventario. No tiene plantilla propia.

Función:
    - Solo organiza el botón / menú de "Planes de protección".
    - Redirige a la vista principal del módulo de planes de protección.

Ruta base:
    /inventario/plan_de_proteccion/
================================================================================
"""

# ============================================================================
# IMPORTS
# ============================================================================
from flask import Blueprint, redirect, url_for

# ============================================================================
# BLUEPRINT
# ============================================================================
modulo_inventario_plan_de_proteccion_bp = Blueprint(
    "modulo_inventario_plan_de_proteccion_bp",
    __name__,
    # Cuélgate del mismo prefijo general de inventario
    url_prefix="/inventario/plan_de_proteccion/"
)

# ============================================================================
# RUTA PRINCIPAL: REDIRECCIÓN
# ============================================================================
@modulo_inventario_plan_de_proteccion_bp.route("/")
def index():
    """
    Redirige al módulo de gestión de planes de protección.

    Notas:
    ------
    - Este módulo no tiene plantilla propia, solo sirve para que el
      panel de inventario tenga un "módulo padre" para planes de
      protección, igual que el de edificios.
    - Al acceder a /inventario/plan_de_proteccion/ se redirige
      automáticamente a la vista principal del blueprint de
      plan de protección (`btn_plan_de_proteccion_form_bp`).
    """

    # IMPORTANTE:
    #   - "btn_plan_de_proteccion_form_bp" debe ser el nombre de la blueprint
    #     donde definiste las rutas del formulario/listado de planes.
    #   - "index" es el nombre de la función de vista que sirve el listado
    #     (ajústalo si tu endpoint se llama distinto).
    return redirect(
        url_for("btn_plan_de_proteccion_form_bp.index")
    )