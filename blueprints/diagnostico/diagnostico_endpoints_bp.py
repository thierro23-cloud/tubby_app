# =============================================================================
# 🩺 BLUEPRINT · DIAGNÓSTICO DE ENDPOINTS
# =============================================================================
# OBJETIVO:
#   - Exponer un pequeño panel JSON/HTML con:
#       · Todas las rutas registradas en la app Flask.
#       · Información básica de la aplicación (config mínima).
#
# RUTAS:
#   · GET /diagnostico/endpoints      → JSON con TODAS las rutas.
#   · GET /diagnostico/endpoints/html → Tabla HTML sencilla con las rutas.
#   · GET /diagnostico/ping           → Ping de salud (simple "ok").
# =============================================================================

from flask import Blueprint, jsonify, render_template_string, current_app
from services.helpers import login_required, rol_required

# Importa la utilidad que ya tienes en diagnostico/utils.py
from blueprints.diagnostico.utils import obtener_todos_los_endpoints
diagnostico_endpoints_bp = Blueprint(
    "diagnostico_endpoints_bp",
    __name__,
    url_prefix="/diagnostico",
)

# -----------------------------------------------------------------------------
# 1️⃣ PING BÁSICO
# -----------------------------------------------------------------------------

@diagnostico_endpoints_bp.route("/ping", methods=["GET"])
@login_required
@rol_required("super_admin")
def ping():
    """Endpoint simple para comprobar que el módulo de diagnóstico responde."""
    return jsonify({"status": "ok", "module": "diagnostico_endpoints"}), 200


# -----------------------------------------------------------------------------
# 2️⃣ ENDPOINTS EN JSON
# -----------------------------------------------------------------------------

@diagnostico_endpoints_bp.route("/endpoints", methods=["GET"])
@login_required
@rol_required("super_admin")
def listar_endpoints_json():
    """
    Devuelve todos los endpoints registrados en la app en formato JSON.
    Usa obtener_todos_los_endpoints() para recorrer app.url_map.
    """
    rutas = obtener_todos_los_endpoints()
    # Opcional: filtrar rutas internas de Flask (static, etc.)
    rutas_filtradas = [
        r for r in rutas
        if not r["ruta"].startswith("/static")
    ]
    return jsonify({
        "total": len(rutas_filtradas),
        "endpoints": rutas_filtradas,
    })


# -----------------------------------------------------------------------------
# 3️⃣ ENDPOINTS EN HTML (TABLA SIMPLE)
# -----------------------------------------------------------------------------

_HTML_TEMPLATE = """
<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8">
    <title>Diagnóstico de endpoints</title>
    <style>
      body { font-family: system-ui, sans-serif; margin: 1rem 2rem; }
      table { border-collapse: collapse; width: 100%; font-size: 0.9rem; }
      th, td { border: 1px solid #ddd; padding: 6px 8px; }
      th { background: #f5f5f5; text-align: left; }
      tr:nth-child(even) { background: #fafafa; }
      code { font-family: "SFMono-Regular", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }
    </style>
  </head>
  <body>
    <h1>Diagnóstico de endpoints</h1>
    <p>Total de rutas: <strong>{{ total }}</strong></p>
    <table>
      <thead>
        <tr>
          <th>Ruta</th>
          <th>Métodos</th>
          <th>Endpoint</th>
        </tr>
      </thead>
      <tbody>
      {% for r in rutas %}
        <tr>
          <td><code>{{ r.ruta }}</code></td>
          <td>{{ ", ".join(r.methods) }}</td>
          <td><code>{{ r.endpoint }}</code></td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
  </body>
</html>
"""

@diagnostico_endpoints_bp.route("/endpoints/html", methods=["GET"])
@login_required
@rol_required("super_admin")
def listar_endpoints_html():
    """
    Renderiza una tabla HTML con todas las rutas registradas.
    Ideal para que un super_admin vea de un vistazo qué hay en la app.
    """
    rutas = obtener_todos_los_endpoints()
    rutas_filtradas = [
        r for r in rutas
        if not r["ruta"].startswith("/static")
    ]
    # Ordenar por ruta para que sea más legible
    rutas_ordenadas = sorted(rutas_filtradas, key=lambda r: r["ruta"])
    return render_template_string(
        _HTML_TEMPLATE,
        total=len(rutas_ordenadas),
        rutas=rutas_ordenadas,
    )