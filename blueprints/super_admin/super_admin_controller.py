# =============================================================================
# 🔐 1️⃣ SUPER ADMIN CONTROLLER (NIVEL PRO)
# =============================================================================
#
# 🎯 RESPONSABILIDAD GLOBAL:
#   Este módulo actúa como CONTROLADOR de seguridad de alto nivel
#   para el ecosistema Super Admin.
#
#   Su función principal es responder a la pregunta:
#       "¿Este endpoint está ACTIVO o BLOQUEADO?"
#
# 🧠 CAPAS EN LA ARQUITECTURA ACTUAL:
#   - Capa SERVICE  (persistencia / BD):
#       · super_admin_service.py o similar
#       · función: obtener_endpoints_desactivados()
#         - Devuelve una lista de endpoints (strings) desactivados.
#         - Ejemplo: ["panel_parquin_bp.panel_parquin", "/panel_parquin/"]
#
#   - Capa CONTROLLER (este archivo):
#       · Orquesta la lógica de negocio simple:
#           - Pregunta al service qué endpoints están desactivados.
#           - Decide (True/False) si un endpoint concreto está activo.
#
# 💡 ENCAJE CON LA ARQUITECTURA DISCOVERY:
#   - Discovery (SuperAdminService.construir_sistema()) detecta TODOS
#     los endpoints activos "teóricamente".
#   - Este controller añade una capa de "feature flag" / activación
#     para poder bloquear endpoints concretos sin tocar rutas ni código.
#   - Puedes usarlo en:
#       · Decoradores @check_endpoint_activo
#       · Hooks before_request
#       · Lógica de plantillas (mostrar/ocultar botones en SuperAdmin)
# =============================================================================


# =============================================================================
# 2️⃣ IMPORTS · DEPENDENCIAS DE LA CAPA SERVICE
# =============================================================================
# 📦 Importamos la función de la capa de servicio (persistencia).
#    Este módulo NO sabe cómo se guardan los endpoints desactivados,
#    solo sabe que `obtener_endpoints_desactivados()` le devuelve una lista.
# =============================================================================
from blueprints.super_admin.super_admin_service import obtener_endpoints_desactivados


# =============================================================================
# 3️⃣ FUNCIÓN PRINCIPAL DEL CONTROLLER · endpoint_activo()
# =============================================================================
# RESPONSABILIDAD:
#   - Dado un identificador de endpoint (string), decide si está activo o no.
#
#   IDENTIFICADOR:
#     - Puede ser:
#         · El endpoint de Flask: "panel_parquin_bp.panel_parquin"
#         · Una URL: "/panel_parquin/"
#       Siempre que coincida con lo que devuelve `obtener_endpoints_desactivados`.
#
#   CONTRATO:
#     - Entrada: endpoint (str)
#     - Salida:  bool
#         · True  → endpoint ACTIVO (permitido)
#         · False → endpoint BLOQUEADO (denegado)
#
#   FILOSOFÍA:
#     - Si algo falla (error de BD, etc.), se aplica un FAIL SAFE:
#         → Devuelve True (no bloquea por fallo interno).
# =============================================================================
def endpoint_activo(endpoint: str) -> bool:
    """
    🔥 Determina si un endpoint está ACTIVO según configuración Super Admin.

    Parámetros:
      - endpoint (str): identificador del endpoint a verificar.
                        Ejemplos:
                          "panel_parquin_bp.panel_parquin"
                          "/panel_parquin/"

    Retorno:
      - True  → El endpoint está permitido (no está en la lista de desactivados).
      - False → El endpoint está desactivado (bloqueado).

    Errores:
      - Cualquier excepción interna se captura y se registra por consola.
      - En caso de error, aplica FAIL SAFE → devuelve True.
    """

    try:
        # ---------------------------------------------------------------------
        # 3.1 🧠 OBTENER LISTA DE ENDPOINTS DESACTIVADOS DESDE LA CAPA SERVICE
        # ---------------------------------------------------------------------
        # Esta función debe devolver una colección iterable de strings,
        # por ejemplo:
        #   ["panel_parquin_bp.panel_parquin", "/panel_parquin/"]
        # Cómo se obtiene esa lista (BD, JSON, cache...) es responsabilidad
        # de la capa service, NO de este controller.
        # ---------------------------------------------------------------------
        desactivados = obtener_endpoints_desactivados()

        # Aseguramos que sea una colección para evitar sorpresas
        if desactivados is None:
            desactivados = []

        # ---------------------------------------------------------------------
        # 3.2 🔍 COMPROBACIÓN LÓGICA
        # ---------------------------------------------------------------------
        # Caso sencillo:
        #   - Si el endpoint está en la lista de desactivados → BLOQUEADO (False)
        #   - Si no está → ACTIVO (True)
        #
        # Puedes ampliar la lógica si hay alias, patrones, etc.
        # ---------------------------------------------------------------------
        if endpoint in desactivados:
            # 🔴 Endpoint explicitamente desactivado
            return False

        # 🟢 Si no está en la lista, se considera activo
        return True

    except Exception as e:
        # ---------------------------------------------------------------------
        # 3.3 ⚠️ MANEJO DE ERRORES · FAIL SAFE
        # ---------------------------------------------------------------------
        # Si algo falla (por ejemplo, error de conexión a BD), se registra
        # el error por consola pero se evita bloquear el sistema entero.
        #
        # Decisión de diseño:
        #   - FAIL SAFE → PERMITIR acceso si el controlador no puede decidir.
        #   - Alternativa (FAIL CLOSE): bloquear todo si falla.
        #     (no recomendable en panel de administración salvo casos extremos)
        # ---------------------------------------------------------------------
        print(f"❌ Error en endpoint_activo: {e}")

        # ⚠️ FAIL SAFE: devolver True implica NO bloquear por fallo interno
        return True
