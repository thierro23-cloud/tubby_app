# blueprints/modulo_gestores_administrar_bp.py
"""
================================================================================
MÓDULO: Administración > Gestores · Tableros
================================================================================
Descripción:
    Módulo organizador de tableros de gestores (sin plantilla propia).

Función:
    - Solo agrupa los botones hijos relacionados con la administración
      de tableros de gestores.
    - No tiene plantilla propia.
    - Al acceder a /gestores_admin/ redirige automáticamente al botón
      principal: btn_administrar_gestores.

Ruta base:
    /gestores_admin/
================================================================================
"""

# ============================================================================
# IMPORTS
# ============================================================================
from flask import Blueprint, redirect, url_for

# ============================================================================
# BLUEPRINT
# ============================================================================
modulo_gestores_administrar = Blueprint(
    "modulo_gestores_administrar_bp",
    __name__,
    url_prefix="/gestores_admin",
)

# ============================================================================
# RUTA PRINCIPAL: REDIRECCIÓN
# ============================================================================
@modulo_gestores_administrar.route("/")
def modulo_gestores_administrar_bp():
    """
    Redirige al botón principal de administración de tableros de gestores.

    Nota:
    -----
    Este módulo NO tiene plantilla propia.
    Su única responsabilidad es agrupar los botones hijos bajo el prefijo
    /gestores_admin/ y redirigir al botón principal:

        btn_administrar_gestores_bp.btn_administrar_gestores
    """
    return redirect(
        url_for("btn_administrar_gestores_bp.btn_administrar_gestores")
    )