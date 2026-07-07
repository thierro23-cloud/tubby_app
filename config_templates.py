# =============================================================================
# 🧠 SISTEMA CENTRALIZADO DE TEMPLATES + MAPEO DE PERMISOS (NIVEL DIOS+++++++)
# =============================================================================
# 📌 EXPLICACIÓN GENERAL (ANTES DE EMPEZAR)
# -----------------------------------------------------------------------------
# Este archivo NO contiene lógica de negocio, ni rutas, ni acceso a base de datos.
#
# 👉 Su objetivo es:
#    ✔ Centralizar TODAS las plantillas HTML del proyecto
#    ✔ Evitar errores por strings repetidos
#    ✔ Permitir conectar automáticamente las vistas con el sistema de permisos
#    ✔ Servir como "cerebro visual" del sistema (paneles, módulos, etc.)
#
# 👉 Filosofía:
#    🔹 "Define aquí, usa en blueprints"
#    🔹 "Un solo punto de verdad"
#
# 👉 Este archivo debe ubicarse en:
#    📁 core/templates_config.py
#
# 👉 Este archivo se conecta con:
#    - core/permisos.py        → control de acceso
#    - blueprints/...          → uso en rutas
#    - panel super_admin       → gestión visual de permisos
#
# =============================================================================


# =============================================================================
# 🌍 SECCIÓN 1 — BASE GLOBAL DE TEMPLATES
# =============================================================================
# 📌 Plantillas comunes en toda la aplicación
# -----------------------------------------------------------------------------
# Estas plantillas se usan en múltiples módulos o son base del sistema.
# -----------------------------------------------------------------------------

TPL_BASE = "base.html"  # 🧱 Plantilla base (layout general)
TPL_LOGIN = "login.html"  # 🔐 Pantalla de login


# =============================================================================
# 🔐 SECCIÓN 2 — AUTENTICACIÓN (AUTH)
# =============================================================================
# 📌 Plantillas relacionadas con usuarios, acceso y recuperación de cuenta
# -----------------------------------------------------------------------------

TPL_AUTH_REGISTER = "auth/register.html"  # 📝 Registro de usuario
TPL_AUTH_FORGOT = "auth/forgot_password.html"  # 🔑 Recuperar contraseña
TPL_AUTH_RESET = "auth/reset_password.html"  # 🔁 Resetear contraseña


# =============================================================================
# 🚛 SECCIÓN 3 — MÓDULO PARQUIN
# =============================================================================
# 📌 Todas las vistas relacionadas con gestión de plazas y camiones
# -----------------------------------------------------------------------------

# 🏠 Panel principal del parquin (vista resumen)
TPL_PARQUIN_PANEL = "parquin/parquin.html"

# 🧱 Gestión de plazas (edición, filas, etc.)
TPL_PARQUIN_GESTIONAR = "plazas/fila_plazas.html"

# 🗺️ Plano visual (camiones en mapa)
TPL_PARQUIN_PLANO = "parquin/plano_camiones.html"


# -----------------------------------------------------------------------------
# 🔁 SUBSECCIÓN 3.1 — ALIAS LEGACY (IMPORTANTE)
# -----------------------------------------------------------------------------
# 📌 Mantiene compatibilidad con código antiguo
# 📌 Evita romper imports existentes
# -----------------------------------------------------------------------------

PANEL_PLAZAS_HTML = TPL_PARQUIN_PANEL
GESTIONAR_PLAZAS_HTML = TPL_PARQUIN_GESTIONAR
PARQUIN_PLANO_HTML = TPL_PARQUIN_PLANO


# =============================================================================
# 👑 SECCIÓN 4 — SUPER ADMIN
# =============================================================================
# 📌 Panel principal de administración global del sistema
# -----------------------------------------------------------------------------

TPL_ADMIN_PANEL = "super_admin/super_admin.html"


# =============================================================================
# 🔐 SECCIÓN 5 — MAPEO DE PERMISOS POR PANEL (CLAVE DEL SISTEMA)
# =============================================================================
# 📌 AQUÍ OCURRE LA MAGIA
# -----------------------------------------------------------------------------
# Este diccionario conecta:
#
#    TEMPLATE → PERMISO
#
# 👉 Esto permite:
#    ✔ Controlar acceso sin hardcodear strings en rutas
#    ✔ Cambiar permisos sin tocar blueprints
#    ✔ Generar paneles dinámicos automáticamente
# -----------------------------------------------------------------------------

PERMISOS_PANELES = {
    # 🚛 PARQUIN
    TPL_PARQUIN_PANEL: "panel_parquin",
    TPL_PARQUIN_GESTIONAR: "panel_gestion_plazas",
    TPL_PARQUIN_PLANO: "panel_plano_camiones",
    # 👑 ADMIN
    TPL_ADMIN_PANEL: "panel_super_admin",
}


# =============================================================================
# 🧱 SECCIÓN 6 — MAPEO DE MÓDULOS (ESCALABILIDAD)
# =============================================================================
# 📌 Permite controlar acceso a bloques completos del sistema
# -----------------------------------------------------------------------------

PERMISOS_MODULOS = {
    "parquin": "modulo_parquin",
    "super_admin": "modulo_admin",
    "auth": "modulo_auth",
}


# =============================================================================
# ⚙️ SECCIÓN 7 — FUNCIÓN AUXILIAR: OBTENER PERMISO DESDE TEMPLATE
# =============================================================================
# 📌 Convierte automáticamente un template en su permiso asociado
# -----------------------------------------------------------------------------
# 👉 Uso:
#
#    permiso = permiso_por_template(TPL_PARQUIN_PANEL)
#
# -----------------------------------------------------------------------------


def permiso_por_template(template):
    """
    🔍 Devuelve el permiso asociado a un template

    :param template: str (ruta del template)
    :return: str | None
    """
    return PERMISOS_PANELES.get(template, None)


# =============================================================================
# ⚙️ SECCIÓN 8 — FUNCIÓN AUXILIAR: OBTENER MÓDULO DESDE TEMPLATE
# =============================================================================
# 📌 Detecta el módulo automáticamente a partir de la ruta del template
# -----------------------------------------------------------------------------
# 👉 Ejemplo:
#    "parquin/parquin.html" → "parquin"
# -----------------------------------------------------------------------------


def obtener_modulo_desde_template(template):
    """
    🔍 Extrae el módulo desde la ruta del template

    :param template: str
    :return: str
    """
    return template.split("/")[0] if "/" in template else "base"


# =============================================================================
# ⚙️ SECCIÓN 9 — FUNCIÓN COMBINADA (PERMISO + MÓDULO)
# =============================================================================
# 📌 Devuelve ambos niveles de control para usar en seguridad avanzada
# -----------------------------------------------------------------------------


def obtener_contexto_seguridad(template):
    """
    🔐 Devuelve:
        - permiso de panel
        - permiso de módulo

    :param template: str
    :return: dict
    """
    modulo = obtener_modulo_desde_template(template)

    return {
        "permiso_panel": PERMISOS_PANELES.get(template),
        "permiso_modulo": PERMISOS_MODULOS.get(modulo),
    }


# =============================================================================
# 🧪 SECCIÓN 10 — EJEMPLO DE USO (BLUEPRINT REAL)
# =============================================================================
# 📌 ESTO NO SE EJECUTA AQUÍ → ES SOLO REFERENCIA
# -----------------------------------------------------------------------------
"""
from core.templates_config import TPL_PARQUIN_PANEL, permiso_por_template
from core.permisos import permiso_requerido

@parquin_bp.route("/parquin")
@permiso_requerido("panel", permiso_por_template(TPL_PARQUIN_PANEL))
def parquin():
    return render_template(TPL_PARQUIN_PANEL)
"""
# =============================================================================


# =============================================================================
# 🧠 SECCIÓN 11 — RESUMEN FINAL
# =============================================================================
# 📌 ESTE ARCHIVO:
# -----------------------------------------------------------------------------
# ✔ Centraliza templates
# ✔ Conecta vistas con permisos
# ✔ Permite automatización
# ✔ Evita errores
#
# 📌 NO HACE:
# ❌ lógica de negocio
# ❌ consultas a BD
# ❌ control de rutas
#
# 📌 ES:
# 💀 El cerebro estructural del sistema visual + permisos
#
# =============================================================================
