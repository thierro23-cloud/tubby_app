# =============================================================================
# 🧠 utils.py – Herramientas de diagnóstico
# =============================================================================
# Este archivo tiene funciones para mirar "desde fuera" a tu app Flask
# y ver todas las rutas (endpoints) que tiene registradas.
# Así el super_admin o un panel de diagnóstico puede listar y agrupar
# todo lo que existe sin tocar cada blueprint a mano.
# =============================================================================


# =============================================================================
# 1️⃣ FUNCIÓN PRINCIPAL: obtener_todos_los_endpoints
# -----------------------------------------------------------------------------
# 🔍 OBJETIVO:
#   - Recorrer el mapa de rutas de Flask (app.url_map)
#   - Construir una lista de diccionarios con:
#       • ruta     → "/panel/policias"
#       • methods  → ["GET", "POST", ...]
#       • endpoint → "panel_policias_bp.panel_policias"
#
# 📌 CONTEXTO:
#   - Si no se pasa 'app', se intenta usar flask.current_app
#   - Esto funciona dentro de un contexto de aplicación Flask
# =============================================================================
def obtener_todos_los_endpoints(app=None):
    """
    Devuelve una lista de todos los endpoints de la aplicación Flask.
    Cada elemento es un dict con:
        - ruta:    str (por ejemplo: "/panel/policias")
        - methods: list de str (por ejemplo: ["GET"])
        - endpoint: str (nombre interno de Flask, por ejemplo: "panel_policias_bp.panel_policias")
    """
    import flask  # ⛽ Importamos aquí para no obligar a que utils.py se cargue siempre con Flask

    # -------------------------------------------------------------------------
    # 🧱 1. CONSEGUIR LA APP FLASK
    #    - Si nos pasan app explícita, usamos esa.
    #    - Si no, intentamos usar la app actual (current_app).
    #    - Si no hay contexto de app, lanzamos un error claro.
    # -------------------------------------------------------------------------
    if app is None:
        try:
            # Intentamos obtener la app actual desde el contexto de Flask
            app = flask.current_app._get_current_object()
        except Exception:
            # Si no hay contexto de app, no podemos acceder a url_map
            raise RuntimeError("No se pudo obtener la app Flask (no hay contexto de aplicación activo)")

    # -------------------------------------------------------------------------
    # 📦 2. PREPARAMOS LA LISTA DONDE GUARDAREMOS TODAS LAS RUTAS
    #    - 'routes' será una lista de dicts con info de cada endpoint.
    # -------------------------------------------------------------------------
    routes = []

    # -------------------------------------------------------------------------
    # 🗺️ 3. RECORRER EL MAPA DE RUTAS (app.url_map.iter_rules())
    #    - Cada 'rule' representa una ruta registrada en Flask.
    #    - De cada rule sacamos:
    #         • rule.rule    → la URL (por ejemplo "/panel/policias")
    #         • rule.methods → métodos HTTP permitidos
    #         • rule.endpoint→ nombre interno del endpoint
    # -------------------------------------------------------------------------
    for rule in app.url_map.iter_rules():
        routes.append({
            "ruta":    str(rule),                   # URL de la ruta (por ejemplo "/panel/policias")
            "methods": sorted(list(rule.methods)),  # Lista ordenada de métodos HTTP (GET, POST, ...)
            "endpoint": rule.endpoint               # Nombre interno del endpoint en Flask
        })

    # -------------------------------------------------------------------------
    # 📤 4. DEVOLVER EL RESULTADO
    #    - Devolvemos la lista completa de rutas detectadas.
    # -------------------------------------------------------------------------
    return routes