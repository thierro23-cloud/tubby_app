# =============================================================================
# 🚀 TUBBY APP · ENTRY POINT (VERSIÓN UNIFICADA LOCAL + SERVIDOR)
# =============================================================================
#
# 🎯 PROPÓSITO:
# Este archivo es el núcleo de la aplicación Flask.
# Controla TODO el flujo de ejecución:
#   ✔ Inicialización de Flask
#   ✔ Configuración global
#   ✔ Carga dinámica de Blueprints
#   ✔ Seguridad global (pipeline centralizado)
#   ✔ Auditoría automática integrada
#   ✔ Arranque de watchers (una sola vez por proceso)
#   ✔ Compatibilidad local/remoto mediante variables de entorno
#
# ⚠️ REGLAS:
#   ❗ SOLO existe un @before_request → seguridad_global
#   ❗ Auditoría se ejecuta desde seguridad_global y registrar_evento
#   ❗ Rutas públicas (login/logout/registro/static/debug) se excluyen explícitamente
#   ❗ Watchers se arrancan una única vez por proceso
#
# 🖥️ ENTORNO LOCAL:
#   - Ejecutar:
#         python app.py
#   - Se usa HOST/PORT desde entorno (fallback 127.0.0.1:5000)
#   - use_reloader=False para evitar duplicar watchers
#
# 🏭 ENTORNO SERVIDOR:
#   - WSGI:
#         gunicorn -w 3 "app:app"
#   - No tocar código: configurar variables de entorno
#
# =============================================================================


# =============================================================================
# 1️⃣ CONFIGURACIÓN DEL ENTORNO · PATHS Y BASE DEL SISTEMA
# =============================================================================
import sys
import os
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Carga opcional de .env (si python-dotenv está disponible).
# En servidor, normalmente se inyectan variables de entorno sin .env.
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass


# =============================================================================
# 2️⃣ IMPORTS PRINCIPALES · CORE DEL FRAMEWORK
# =============================================================================
from flask import (
    Flask,
    redirect,
    url_for,
    current_app,
    render_template,
    request,
    session,
)

import logging
import importlib.util
import traceback

from flask_login import LoginManager, UserMixin


# =============================================================================
# 3️⃣ IMPORTS DE NEGOCIO · CONFIG, SEGURIDAD, AUDITORÍA Y WATCHERS
# =============================================================================
from config import Config
from core.permisos import endpoint_activo, tiene_permiso
from core.audit import registrar_evento

# DB helpers
from db import ejecutar_query

# Watcher de contenedores
from watchers.contenedores_watcher import (
    iniciar_watcher_contenedores,
    watcher_activo as watcher_contenedores_activo,
)

# Watcher de carpeta inicial de PDFs (bandeja de entrada)
from watchers.bandeja_inicial_watcher import (
    iniciar_watcher_carpeta_inicial,
    watcher_inicial_activo,
)

# Watcher de terrazas
from watchers.terrazas_watcher import (
    iniciar_watcher_terrazas,
    watcher_terrazas_activo,
)

# Watcher de obras
from watchers.obras_watcher import (
    iniciar_watcher_obras,
    watcher_obras_activo,
)


# =============================================================================
# 4️⃣ HELPERS WATCHERS · ARRANQUE Y COLA EXISTENTE
# =============================================================================
def procesar_pdfs_existentes(app):
    """
    Procesa PDFs que ya existan en carpetas al arrancar la app.

    NOTA:
      Está preparado para enganchar procesos de reprocesado industrial
      según tu implementación en watchers.utils_async.
    """
    with app.app_context():
        app.logger.info("🔁 Procesando PDFs existentes en carpetas de trabajo...")
        app.logger.info(
            "ℹ procesar_pdfs_existentes: pendiente de implementación industrial."
        )


def iniciar_watchers(app):
    """
    Arranca watchers necesarios de forma segura (sin duplicidad).

    Orden:
      1) carpeta inicial
      2) contenedores
      3) terrazas
      4) obras
    """
    with app.app_context():
        app.logger.info("🚀 Iniciando watchers de PDFs...")

        if not watcher_inicial_activo:
            iniciar_watcher_carpeta_inicial(app)
        else:
            app.logger.info("ℹ Watcher carpeta_inicial ya estaba activo")

        if not watcher_contenedores_activo:
            iniciar_watcher_contenedores(app)
        else:
            app.logger.info("ℹ Watcher contenedores ya estaba activo")

        if not watcher_terrazas_activo:
            iniciar_watcher_terrazas(app)
        else:
            app.logger.info("ℹ Watcher terrazas ya estaba activo")

        if not watcher_obras_activo:
            iniciar_watcher_obras(app)
        else:
            app.logger.info("ℹ Watcher obras ya estaba activo")

        app.logger.info("✅ Watchers iniciados")


# =============================================================================
# 5️⃣ CREACIÓN APP FLASK · CONFIG BASE + LOGIN
# =============================================================================
app = Flask(__name__)
app.config.from_object(Config)

# Auto-recarga de templates (útil en desarrollo)
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.auto_reload = True

# -----------------------------------------------------------------------------
# 5.1) Configuración runtime (local/remoto) vía entorno
# -----------------------------------------------------------------------------
# No rompe tu Config; solo añade soporte explícito por entorno.
FLASK_ENV = os.getenv("FLASK_ENV", "development").strip().lower()
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "1" if FLASK_ENV == "development" else "0") == "1"

# LLM local
app.config["LLM_BACKEND"] = os.getenv("LLM_BACKEND", "ollama")
app.config["LLM_MODEL"] = os.getenv("LLM_MODEL", "gemma3:4b")
app.config["LLM_TIMEOUT"] = int(os.getenv("LLM_TIMEOUT", "90"))

# Datos informativos de DB (para logs/diagnóstico)
app.config["DB_HOST"] = os.getenv("DB_HOST", "127.0.0.1")
app.config["DB_PORT"] = int(os.getenv("DB_PORT", "3306"))
app.config["DB_USER"] = os.getenv("DB_USER", "")
app.config["DB_NAME"] = os.getenv("DB_NAME", "parquin_camiones")
app.config["DB_COMMON_NAME"] = os.getenv("DB_COMMON_NAME", "bd_tbl_comunes")

# Login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth_bp.login"
login_manager.login_message_category = "info"


# =============================================================================
# 6️⃣ MODELO LOGIN + USER LOADER
# =============================================================================
class UsuarioLogin(UserMixin):
    """
    Representación mínima de usuario para Flask-Login.
    """

    def __init__(
        self,
        idtbl_usuarios: int,
        idtbl_proveedores: int | None,
        rol: str | None,
        nombre_proveedor: str | None = None,
        numero_cuenta: str | None = None,
    ):
        self.id = idtbl_usuarios
        self.idtbl_proveedores = idtbl_proveedores
        self.rol = rol
        self.nombre_proveedor = nombre_proveedor
        self.numero_cuenta = numero_cuenta

    def get_id(self) -> str:
        return str(self.id)


@login_manager.user_loader
def load_user(user_id: str) -> UsuarioLogin | None:
    """
    Reconstruye current_user desde id de sesión.
    """
    if not user_id:
        return None

    filas = ejecutar_query(
        """
        SELECT
            u.idtbl_usuarios,
            u.idtbl_proveedores,
            u.numero_cuenta,
            u.activo_baja,
            u.fecha_inicio,
            u.fecha_baja,
            u.rol,
            p.Nombre_Razon_Social AS nombre_proveedor
        FROM parquin_camiones.tbl_usuarios AS u
        LEFT JOIN bd_tbl_comunes.tbl_proveedores AS p
          ON u.idtbl_proveedores = p.Idtbl_proveedores
        WHERE u.idtbl_usuarios = %s
          AND u.activo_baja = 1
        """,
        (user_id,),
        "parquin_camiones",
    )

    if not filas:
        return None

    fila = filas[0]
    return UsuarioLogin(
        idtbl_usuarios=fila["idtbl_usuarios"],
        idtbl_proveedores=fila.get("idtbl_proveedores"),
        rol=fila.get("rol"),
        nombre_proveedor=fila.get("nombre_proveedor"),
        numero_cuenta=fila.get("numero_cuenta"),
    )


# =============================================================================
# 7️⃣ LOGGING GLOBAL
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
app.logger.info("✅ App iniciada correctamente")
app.logger.info("🌍 FLASK_ENV=%s | DEBUG=%s", FLASK_ENV, FLASK_DEBUG)
app.logger.info(
    "🗄️ DB_HOST=%s DB_PORT=%s DB_NAME=%s",
    app.config["DB_HOST"],
    app.config["DB_PORT"],
    app.config["DB_NAME"],
)


# =============================================================================
# 8️⃣ HELPERS JINJA
# =============================================================================
def endpoint_existe(nombre_endpoint):
    """Verifica si un endpoint existe en la app."""
    return nombre_endpoint in current_app.view_functions


def url_segura(endpoint, **kwargs):
    """Devuelve URL solo si el endpoint existe, si no, '#'."""
    try:
        if endpoint in current_app.view_functions:
            return url_for(endpoint, **kwargs)
        return "#"
    except Exception:
        return "#"


app.jinja_env.globals["endpoint_existe"] = endpoint_existe
app.jinja_env.globals["url_segura"] = url_segura

from datetime import datetime


@app.template_filter("fecha")
def formato_fecha(valor):
    """
    Convierte string o datetime a formato dd/mm/yyyy.
    """
    if valor is None:
        return ""

    if isinstance(valor, str):
        for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y"]:
            try:
                valor = datetime.strptime(valor, fmt)
                break
            except ValueError:
                continue

    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y")

    return str(valor)


app.jinja_env.filters["fecha"] = formato_fecha


# =============================================================================
# 9️⃣ DEBUG TEMPLATE
# =============================================================================
@app.route("/__debug_template__")
def debug_template():
    tpl = request.args.get("tpl")
    if not tpl:
        return "❌ Falta tpl", 400
    try:
        return render_template(tpl)
    except Exception as e:
        return f"<pre>{e}</pre>"


# =============================================================================
# 🔟 CARGA UNIVERSAL DE BLUEPRINTS *_bp.py
# =============================================================================
def cargar_blueprints(app):
    """
    Descubre e importa todos los blueprints *_bp.py recursivamente.
    """
    from flask import Blueprint

    CARPETAS_EXCLUIDAS = {
        "venv", "env", ".venv", ".env",
        "__pycache__", ".pytest_cache",
        ".git", ".svn", ".hg",
        "node_modules",
        "static", "templates",
        "instance",
        "migrations",
        ".idea", ".vscode",
        "dist", "build", "*.egg-info",
    }

    encontrados = 0
    registrados = 0
    duplicados = 0
    errores = 0

    app.logger.info("🔍 Iniciando escaneo universal de blueprints...")

    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in CARPETAS_EXCLUIDAS and not d.startswith(".")]

        for file in files:
            if not file.endswith("_bp.py"):
                continue

            encontrados += 1
            path = os.path.join(root, file)
            ruta_relativa = os.path.relpath(path, BASE_DIR)
            module_name = file[:-3]

            try:
                spec = importlib.util.spec_from_file_location(module_name, path)
                if spec is None or spec.loader is None:
                    app.logger.error("❌ No se pudo crear spec para: %s", ruta_relativa)
                    errores += 1
                    continue

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                blueprints_en_modulo = 0
                for attr in dir(module):
                    if attr.startswith("_"):
                        continue
                    obj = getattr(module, attr)
                    if isinstance(obj, Blueprint):
                        blueprints_en_modulo += 1
                        if obj.name not in app.blueprints:
                            app.register_blueprint(obj)
                            registrados += 1
                            app.logger.info("✅ Blueprint registrado: %s <- %s", obj.name, ruta_relativa)
                        else:
                            duplicados += 1
                            app.logger.warning("⚠️ Blueprint duplicado ignorado: %s <- %s", obj.name, ruta_relativa)

                if blueprints_en_modulo == 0:
                    app.logger.warning("⚠️ Archivo *_bp.py sin blueprints: %s", ruta_relativa)

            except Exception as e:
                errores += 1
                app.logger.error(
                    "❌ Error cargando blueprint desde %s:\n%s\n%s",
                    ruta_relativa,
                    str(e),
                    traceback.format_exc(),
                )

    app.logger.info("📊 Blueprints encontrados=%s | registrados=%s | duplicados=%s | errores=%s",
                    encontrados, registrados, duplicados, errores)


cargar_blueprints(app)

# Debug opcional de reglas
with app.app_context():
    for rule in app.url_map.iter_rules():
        if str(rule).startswith("/parquin/rio_torio/accesos/"):
            print("DEBUG RULE:", rule, "endpoint:", rule.endpoint, "methods:", rule.methods)


# =============================================================================
# 1️⃣1️⃣ ARRANQUE DE WATCHERS
# =============================================================================
with app.app_context():
    # Cola vieja desactivada por diseño actual
    # try:
    #     procesar_pdfs_existentes(app)
    # except Exception:
    #     app.logger.error("❌ Error al procesar PDFs existentes", exc_info=True)

    try:
        iniciar_watchers(app)
        app.logger.info("🚀 Watchers iniciados correctamente")
    except Exception:
        app.logger.error("❌ Error al iniciar watchers", exc_info=True)


# =============================================================================
# 1️⃣2️⃣ SEGURIDAD GLOBAL · ÚNICO before_request
# =============================================================================
@app.before_request
def seguridad_global():
    """
    Pipeline central de seguridad:
      - Excluye rutas públicas.
      - Bypass total para super_admin por rol.
      - Verifica si endpoint está activo.
      - Verifica permisos del usuario.
      - Registra auditoría.
    """
    endpoint = request.endpoint
    if not endpoint:
        return

    rutas_publicas = [
        "auth_bp.login",
        "auth_bp.logout",
        "auth_bp.register",
        "static",
        "__debug_template__",
    ]

    if any(endpoint.startswith(r) for r in rutas_publicas):
        return

    rol = session.get("rol")
    if rol == "super_admin":
        return

    if not endpoint_activo(endpoint):
        registrar_evento("endpoint_desactivado", endpoint)
        if request.path.startswith("/api"):
            return {"error": "Endpoint desactivado"}, 403
        return "⛔ Endpoint desactivado", 403

    rol_id = session.get("rol_id")
    if not tiene_permiso(endpoint, rol_id):
        registrar_evento("acceso_denegado", endpoint)
        return redirect(url_for("auth_bp.login"))

    registrar_evento("acceso_permitido", endpoint)


# =============================================================================
# 1️⃣3️⃣ RUTA PRINCIPAL
# =============================================================================
@app.route("/")
def index():
    """Redirección al login."""
    return redirect(url_for("auth_bp.login"))


# =============================================================================
# 1️⃣4️⃣ ARRANQUE DEV (python app.py)
# =============================================================================
if __name__ == "__main__":
    # Para trabajar en local y remoto sin tocar código:
    # - HOST y PORT vienen de entorno.
    # - use_reloader=False evita duplicar watchers.
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))

    app.run(
        host=host,
        port=port,
        debug=FLASK_DEBUG,
        use_reloader=False,
    )

# =============================================================================
# 1️⃣2️⃣ FIN · app.py UNIFICADO (SEGURIDAD + AUDITORÍA + BLUEPRINTS + WATCHERS)
# =============================================================================
