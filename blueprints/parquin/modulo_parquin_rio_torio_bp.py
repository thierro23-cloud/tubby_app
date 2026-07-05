# =============================================================================
# 🌉 1️⃣ MÓDULO RIO_TORIO · AGRUPADOR DE BOTONES DEL PARQUIN (COMPATIBLE DISCOVERY)
# =============================================================================
# 🎯 OBJETIVO
# -----------------------------------------------------------------------------
# Este blueprint representa el **MÓDULO RIO_TORIO** dentro del panel `panel_parquin_bp`.
#
# - NO gestiona tablas ni hace SQL.
# - SOLO pinta la “home” del módulo con botones (enlaces) a:
#     · btn_rio_torio_listado_usuarios
#     · btn_rio_torio_padron
#     · btn_rio_torio_plano
#     · etc.
#
# 🧠 INTEGRACIÓN CON SUPER ADMIN / DISCOVERY
# -----------------------------------------------------------------------------
# El SuperAdminService, con la nueva función `_resolver_panel_para_blueprint`,
# va a asociar ESTE blueprint al **panel_parquin_bp** gracias al patrón:
#
#   blueprint_name = "modulo_parquin_rio_torio_bp"
#   → empieza por "modulo_parquin_" → pertenece a panel_parquin_bp
#
# De este modo, en el Super Admin aparecerá:
#
#   PANEL:  panel_parquin_bp
#   MÓDULO: modulo_parquin_rio_torio
#   BOTONES: todos los endpoints de este módulo y de los blueprints de botones
#            `botones_rio_torio_*_bp` que cuelgan de /parquin/rio_torio.
#
# =============================================================================


# =============================================================================
# 🧩 2️⃣ IMPORTS BÁSICOS DEL MÓDULO
# =============================================================================
# - Blueprint: para definir el módulo.
# - render_template: para pintar la home del módulo.
# - rol_required: para restringir el acceso a gestores/super_admin.
# =============================================================================

from flask import Blueprint, render_template
from services.helpers import rol_required


# =============================================================================
# 🧱 3️⃣ DEFINICIÓN DEL BLUEPRINT · modulo_parquin_rio_torio_bp
# =============================================================================
# 🔹 NOMBRE:
#     "modulo_parquin_rio_torio_bp"
#
#     - Empieza por "modulo_parquin_" → el discovery lo mapeará al panel:
#           panel_parquin_bp
#
# 🔹 PREFIJO:
#     url_prefix="/parquin/rio_torio"
#
#     - La URL base del módulo será:
#           /parquin/rio_torio/
#
# 🔹 TEMPLATES:
#     template_folder="templates/parquin/rio_torio"
#
#     - Se espera una plantilla:
#           templates/parquin/rio_torio/modulo_rio_torio.html
# =============================================================================

modulo_parquin_rio_torio_bp = Blueprint(
    "modulo_parquin_rio_torio_bp",
    __name__,
    url_prefix="/parquin/rio_torio",
    template_folder="templates/parquin/rio_torio",
)


# =============================================================================
# 🖼 4️⃣ VISTA PRINCIPAL DEL MÓDULO · HOME (AGRUPADOR DE BOTONES)
# =============================================================================
# RUTA:
#   GET /parquin/rio_torio/
#
# RESPONSABILIDAD:
#   - Pintar la página principal del módulo Rio Torío.
#   - Mostrar botones/enlaces a los endpoints reales:
#       · botones_rio_torio_usuarios_bp.btn_rio_torio_listado_usuarios
#       · botones_rio_torio_padron_bp.btn_rio_torio_padron
#       · otros futuros btn_rio_torio_*.
#
# SEGURIDAD:
#   - Restricción a roles "gestor" y "super_admin".
#
# DISCOVERY:
#   - Endpoint registrado como:
#       "modulo_parquin_rio_torio_bp.modulo_parquin_rio_torio"
#   - El SuperAdminService lo agrupará bajo panel_parquin_bp como módulo
#     "modulo_parquin_rio_torio".
# =============================================================================

@modulo_parquin_rio_torio_bp.route("/", methods=["GET"])
@rol_required("gestor", "super_admin")
def modulo_parquin_rio_torio():
    """
    🎯 HOME MÓDULO RIO_TORIO · AGRUPADOR DE BOTONES DEL PARQUIN

    Esta vista NO hace consultas a BD ni lógica de negocio.
    Solo se encarga de:

      - Mostrar título y descripción del recinto Rio Torío.
      - Poner botones que apuntan a endpoints btn_rio_torio_* que sí
        gestionan datos (otros blueprints):

          · botones_rio_torio_usuarios_bp.btn_rio_torio_listado_usuarios
          · botones_rio_torio_padron_bp.btn_rio_torio_padron
          · etc.
    """
    return render_template(
        "parquin/rio_torio/modulo_rio_torio.html",
    )


# =============================================================================
# 🔗 5️⃣ NOTAS DE INTEGRACIÓN (PANEL, BOTONES, DISCOVERY)
# =============================================================================
# ➤ REGISTRO AUTOMÁTICO
# -----------------------------------------------------------------------------
# Como el archivo se llama:
#   modulo_parquin_rio_torio_bp.py
#
# y el objeto Blueprint se llama:
#   modulo_parquin_rio_torio_bp
#
# tu loader de blueprints (cargar_blueprints) lo detectará porque:
#   - el nombre del archivo termina en "_bp.py"
#   - dentro hay un objeto Blueprint
#
# ➤ PANEL → MÓDULO → BOTONES
# -----------------------------------------------------------------------------
# - PANEL:
#     panel_parquin_bp
#
# - MÓDULO:
#     modulo_parquin_rio_torio_bp.modulo_parquin_rio_torio
#
# - BOTONES (otros blueprints):
#     /parquin/rio_torio/btn_rio_torio_listado_usuarios
#     /parquin/rio_torio/btn_rio_torio_padron
#     /parquin/rio_torio/btn_rio_torio_plano
#     ...
#
# ➤ SUPER ADMIN / DISCOVERY
# -----------------------------------------------------------------------------
# En SuperAdminService._resolver_panel_para_blueprint tienes la regla:
#
#   if blueprint_name.startswith("modulo_parquin_"):
#       return "panel_parquin_bp"
#
# Por eso, este módulo aparecerá correctamente agrupado dentro del
# panel_parquin_bp, y sus botones asociados (otros blueprints de tipo
# botones_rio_torio_*) también se podrán mapear a ese mismo panel.
# =============================================================================
