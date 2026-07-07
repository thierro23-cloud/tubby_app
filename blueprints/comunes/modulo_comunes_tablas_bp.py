# =============================================================================
# 🧩 MÓDULO · COMUNES TABLAS (CONTENEDOR DE BOTONES)
# Archivo: blueprints/comunes/modulo_comunes_tablas_bp.py
# =============================================================================
"""
MÓDULO: comunes/tablas

Módulo ligero cuyo único propósito es:
  - Definir el endpoint `modulo_comunes_tablas`.
  - Colgarse del panel `panel_comunes` o del super_admin.
  - Servir como nodo intermedio para que el super_admin agrupe los
    botones relacionados con tablas bajo este módulo.

IMPORTANTE:
  - Este módulo NO pinta ninguna plantilla HTML propia.
  - Su función es meramente estructural: existir como nodo para que
    el sistema auto-descubrible pueda colgar aquí los btn_tablas_xxx.
"""

from flask import Blueprint
from services.helpers import login_required, rol_required

# =============================================================================
# 1️⃣ BLUEPRINT DEL MÓDULO
# =============================================================================

modulo_comunes_tablas_bp = Blueprint(
    "modulo_comunes_tablas_bp",
    __name__,
    url_prefix="/comunes/tablas",
)
# Rutas: /comunes/tablas/...


# =============================================================================
# 2️⃣ VISTA DEL MÓDULO (SIN LÓGICA, SOLO CONTENEDOR)
# =============================================================================


@modulo_comunes_tablas_bp.route("/", methods=["GET"])
@login_required
@rol_required("super_admin")
def modulo_comunes_tablas():
    """
    Endpoint: modulo_comunes_tablas
    URL     : /comunes/tablas/

    Esta vista no tiene lógica de negocio ni renderiza plantillas;
    simplemente existe para que el sistema auto-descubrible detecte
    el módulo "tablas" dentro del panel y pueda colgar aquí los
    botones relacionados con tablas (btn_tablas_xxx).

    Al ser un nodo lógico:
      - El super_admin no verá una página específica de este módulo.
      - Las acciones visibles se gestionan a través de los botones
        que cuelgan de él.
    """
    # No renderizamos ninguna plantilla porque este módulo es solo
    # un contenedor lógico en el árbol de navegación.
    # Devolvemos 204 (No Content) para indicar que la petición fue
    # correcta pero sin contenido HTML asociado.
    return "", 204
