# =============================================================================
# 🅿️ 0️⃣ INICIO · PANEL PARQUIN
# =============================================================================
# 🎯 OBJETIVO
# -----------------------------------------------------------------------------
# Definir el PANEL de PARQUIN para el sistema de SUPER ADMIN con discovery
# por convención, siguiendo la arquitectura global:
#
#   SUPER ADMIN:
#     - PANEL  (columna 1) → panel_parquin_bp
#     - MÓDULOS (columna 2) → modulo_parquin_..._bp
#     - BOTONES (columna 3) → btn_rio_torio_... (etc.)
#
# Este archivo define:
#   1) El blueprint del PANEL:
#        panel_parquin_bp
#
#   2) Una vista opcional de "home" del panel:
#        /parquin/
#
# El SUPER ADMIN detectará este PANEL automáticamente porque:
#   - El nombre del blueprint empieza por 'panel_' y termina en '_bp':
#         panel_parquin_bp
#
#   - Cualquier módulo del panel deberá llamarse:
#         modulo_parquin_<modulo_id>_bp
#     y será descubierto por el servicio SuperAdminSimpleService.
#
#   - Los BOTONES de cada módulo se descubrirán y serán ejecutables mediante
#     las vistas 'btn_...' de sus blueprints correspondientes.
# =============================================================================

from flask import Blueprint, render_template


# =============================================================================
# 1️⃣ BLUEPRINT DEL PANEL PARQUIN
# =============================================================================
# Definimos el blueprint principal del panel PARQUIN:
#
#   panel_parquin_bp → /parquin/...
#
# Este blueprint representa el "contexto" del panel en la columna 1 del
# SUPER ADMIN. Los módulos asociados deberán seguir la convención:
#
#   modulo_parquin_<modulo_id>_bp
#
# Ejemplos:
#   - modulo_parquin_rio_torio_bp
#   - modulo_parquin_otro_bp
# =============================================================================

panel_parquin_bp = Blueprint(
    "panel_parquin_bp",
    __name__,
    url_prefix="/parquin",
)


# =============================================================================
# 2️⃣ VISTA OPCIONAL · HOME DEL PANEL PARQUIN
# =============================================================================
# Esta vista es opcional, pero muy útil:
#
#   - Permite acceder directamente al panel parquin entrando en:
#       /parquin/
#
#   - Puede renderizar una plantilla propia como resumen del panel,
#     o simplemente una página básica.
#
# El SUPER ADMIN no depende de esta vista para el discovery, pero es un buen
# punto de entrada para navegar directamente el panel fuera del super_admin.
# =============================================================================

@panel_parquin_bp.route("/")
def panel_parquin():
    """
    🅿️ HOME · Panel Parquin

    Vista sencilla que renderiza la página principal del panel de parquin.
    Aquí puedes mostrar enlaces, métricas o simplemente un mensaje de
    bienvenida al panel.
    """
    


# =============================================================================
# 3️⃣ INTEGRACIÓN CON SUPER ADMIN · DISCOVERY AUTOMÁTICO
# =============================================================================
# ¿CÓMO SE CONECTA ESTO CON EL SUPER ADMIN?
# -----------------------------------------------------------------------------
# 1) El blueprint se registra en app.py:
#
#     from .panel_parquin_bp import panel_parquin_bp
#     app.register_blueprint(panel_parquin_bp)
#
# 2) El SUPER ADMIN, mediante SuperAdminSimpleService.obtener_paneles(), recorrerá
#    current_app.url_map y encontrará 'panel_parquin_bp' como PANEL válido:
#
#     - 'panel_parquin_bp' → Columna 1.
#
# 3) Para este PANEL, se descubrirán los MÓDULOS:
#
#     - modulo_parquin_rio_torio_bp
#     - modulo_parquin_otro_bp
#     - etc.
#
# 4) Cada MÓDULO tendrá sus BOTONES propios (vistas 'btn_...') que el SUPER ADMIN
#    detectará con obtener_botones(), y que serán EJECUTABLES: al hacer clic en
#    ellos, se llamará a la vista Flask correspondiente que:
#
#       - Normalmente hará render_template("...") para abrir una plantilla.
#       - O realizará la acción (descarga Excel, etc.).
#
# De esta forma, el panel de PARQUIN queda perfectamente integrado en tu
# sistema de navegación de 3 columnas del SUPER ADMIN.
# =============================================================================
# 🛑 FIN · PANEL PARQUIN
# =============================================================================