# =============================================================================
# 🧠 generador_ia_bp.py – Endpoint HTTP para Generador IA (SUPER_ADMIN)
# =============================================================================
# 🎯 OBJETIVO:
#   Exponer un endpoint:
#       POST /super_admin/generador_ia/
#   que:
#       1) Recibe un prompt desde el panel SUPER_ADMIN (JS fetch).
#       2) Llama a generar_codigo(prompt) del archivo generador_codigo_ia.py.
#       3) Devuelve JSON con el código generado o error.
# =============================================================================


# =============================================================================
# 1️⃣ IMPORTACIONES PRINCIPALES
# =============================================================================
from flask import Blueprint, request, jsonify  # 🌐 Peticiones y JSON
from services.helpers import login_required, rol_required  # 🔐 Seguridad

import importlib.util  # 🧩 Carga dinámica
import os  # 📁 Rutas de archivos

# =============================================================================


# =============================================================================
# 2️⃣ CARGA DINÁMICA DEL MÓDULO generador_codigo_ia.py
# =============================================================================
# COMIENZA: resolución de ruta y carga del archivo.
# TERMINA: obtención de la función generar_codigo.
# -----------------------------------------------------------------------------
CURRENT_DIR = os.path.dirname(__file__)  # 📁 Carpeta actual: blueprints/super_admin

ruta_modulo_ia = os.path.join(CURRENT_DIR, "generador_codigo_ia.py")

if not os.path.exists(ruta_modulo_ia):
    raise FileNotFoundError(f"No existe: {ruta_modulo_ia}")

spec_ia = importlib.util.spec_from_file_location("generador_codigo_ia", ruta_modulo_ia)

if spec_ia is None or spec_ia.loader is None:
    raise ImportError("No se pudo cargar el módulo generador_codigo_ia")

modulo_ia = importlib.util.module_from_spec(spec_ia)
spec_ia.loader.exec_module(modulo_ia)

if not hasattr(modulo_ia, "generar_codigo"):
    raise AttributeError("generador_codigo_ia.py no tiene la función 'generar_codigo'")

generar_codigo = modulo_ia.generar_codigo  # 🧠 Función de IA que usaremos
# =============================================================================


# =============================================================================
# 3️⃣ DEFINICIÓN DEL BLUEPRINT
# =============================================================================
# COMIENZA: creación del blueprint generador_ia_bp.
# TERMINA: justo antes de la función de vista.
# -----------------------------------------------------------------------------
generador_ia_bp = Blueprint(
    "generador_ia_bp",  # 🏷 Nombre interno del blueprint
    __name__,
    url_prefix="/super_admin/generador_ia",  # 🌐 Prefijo de URL
)
# =============================================================================


# =============================================================================
# 4️⃣ ENDPOINT PRINCIPAL · POST /super_admin/generador_ia/
# =============================================================================
# COMIENZA: definición de la ruta y lógica del endpoint.
# TERMINA: retorno del JSON.
# -----------------------------------------------------------------------------
@generador_ia_bp.route("/", methods=["POST"])
@login_required
@rol_required("super_admin")
def generador_ia():
    """
    Endpoint de generación de código por IA para SUPER_ADMIN.
    """

    # 4.1 LEER PROMPT
    prompt = request.form.get("prompt", "").strip()
    if not prompt:
        return jsonify({"ok": False, "error": "Prompt vacío"}), 400

    # 4.2 LLAMAR AL MOTOR DE IA
    try:
        codigo = generar_codigo(prompt)
    except Exception as e:
        return jsonify({"ok": False, "error": f"Error generando código: {str(e)}"}), 500

    # 4.3 RESPUESTA OK
    return (
        jsonify(
            {
                "ok": True,
                "codigo": codigo,
            }
        ),
        200,
    )


# =============================================================================
