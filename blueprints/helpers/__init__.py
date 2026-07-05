# blueprints/helpers/__init__.py
# =============================================================================
# 🧩 PAQUETE BLUEPRINTS.HELPERS
# =============================================================================
# Este paquete agrupa blueprints y helpers relacionados con:
#   - Gestión de vías, municipios, calles, etc. (helpers_vias).
#   - Cualquier otro helper transversal que no pertenezca a un módulo concreto.
#
# NOTAS:
# ------
# - No ejecutamos lógica aquí para evitar errores y bucles de importación.
# - Cada módulo (helpers_vias_bp, helpers_vias, ...) se importa directamente
#   desde la aplicación principal cuando se necesita.
# =============================================================================

# Por ahora no es necesario exportar nada desde aquí.
# tubby_app/__init__.py (ejemplo)
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CONFIG_DIRECCIONES_XML = DATA_DIR / "config_direcciones.xml"
