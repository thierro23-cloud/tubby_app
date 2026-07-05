# =============================================================================
# 🏭 APP FACTORY · create_app() CON BD
# =============================================================================
#
# 📌 INTRODUCCIÓN
# ---------------------------------------------------------------------------
# Este archivo crea la aplicación Flask, inicializa la base de datos
# y registra automáticamente todos los blueprints del proyecto.
#
# Mantiene:
# - Configuración de SECRET_KEY.
# - Configuración de SQLALCHEMY_DATABASE_URI.
# - Llamada a init_db(app) de tu módulo db.
#
# Debe usarse con:
#   export FLASK_APP=app
#   flask run
#
# =============================================================================

import importlib
import pkgutil
from flask import Flask, Blueprint
from db import init_db   # 👈 tu función actual

# =============================================================================
# 1️⃣ REGISTRO AUTOMÁTICO DE BLUEPRINTS
# =============================================================================

def registrar_blueprints_auto(app: Flask, paquete_blueprints: str = "app.blueprints"):
    """
    Recorre app.blueprints e importa cada módulo que tenga un atributo `bp`
    que sea instancia de Blueprint, y lo registra en la app.
    """
    try:
        paquete = importlib.import_module(paquete_blueprints)
    except ModuleNotFoundError:
        # Si todavía no tienes carpeta blueprints, evita reventar.
        return

    for _, nombre_modulo, es_pkg in pkgutil.iter_modules(paquete.__path__):
        if es_pkg:
            continue

        ruta_modulo = f"{paquete_blueprints}.{nombre_modulo}"
        modulo = importlib.import_module(ruta_modulo)

        bp = getattr(modulo, "bp", None)

        if isinstance(bp, Blueprint):
            app.register_blueprint(bp)
            print(f"✅ Blueprint registrado automáticamente: {bp.name} ({ruta_modulo})")

# =============================================================================
# 2️⃣ FUNCIÓN PRINCIPAL create_app()
# =============================================================================

def create_app():
    """
    Crea y configura la app Flask, inicializa la BD e incorpora blueprints.
    """
    app = Flask(__name__)

    # --- Configuración base (tu configuración actual) ---
    app.config["SECRET_KEY"] = "lo-que-sea"
    app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+mysqlconnector://user:pass@host/bd"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # --- Inicializar base de datos ---
    init_db(app)  # 👈 sigues usando tu init_db actual

    # --- Registrar blueprints automáticamente ---
    registrar_blueprints_auto(app, "app.blueprints")

    return app

# =============================================================================
# 3️⃣ OPCIONAL · MODO DEBUG DIRECTO (python app/__init__.py)
# =============================================================================
if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)