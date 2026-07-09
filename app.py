# =============================================================================
# 🚀 TUBBY APP · ENTRY POINT (VERSIÓN UNIFICADA LOCAL + SERVIDOR)
# =============================================================================
#
# 🧾 METADATOS DE MODIFICACIÓN
#   - Autor: Supertinito
#   - Fecha de modificación: 2026-07-09
#   - Hora de modificación: 00:00 (UTC)  # ← actualiza al guardar
#
# 🎯 PROPÓSITO:
# Este archivo centraliza:
#   ✔ Inicialización Flask
#   ✔ Configuración runtime local/servidor
#   ✔ Registro dinámico de blueprints
#   ✔ Seguridad global + auditoría
#   ✔ Arranque seguro de watchers (idempotente por proceso)
#
# 🛡️ GARANTÍAS:
#   - Único @before_request: seguridad_global
#   - Exclusión explícita de rutas públicas
#   - Bypass de super_admin
#   - Control de endpoint activo + permisos
#   - Trazabilidad por registrar_evento
#
# =============================================================================

# =============================================================================
# 1) ENTORNO Y BASE DEL PROYECTO
# =============================================================================
from __future__ import annotations

import os
import sys
import logging
import traceback
import importlib.util
from datetime import datetime
from typing import Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Carga opcional de variables desde .env (si existe python-dotenv).
try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass


# =============================================================================
# 2) IMPORTS CORE FLASK
# =============================================================================
from flask import (
    Flask,
    redirect,
    url_for,
    current_app,
    render_template,
    request,
    session,
    jsonify,
)
from flask_login import LoginManager, UserMixin


# =============================================================================
# 3) IMPORTS NEGOCIO
# =============================================================================
from config import Config
from db import ejecutar_query
from core.permisos import endpoint_activo, tiene_permiso
from core.audit import registrar_evento

from watchers.bandeja_inicial_watcher import (
    iniciar_watcher_carpeta_inicial,
    watcher_inicial_activo,
)
from watchers.contenedores_watcher import (
    iniciar_watcher_contenedores,
    watcher_activo as watcher_contenedores_activo,
)
from watchers.terrazas_watcher import (
    iniciar_watcher_terrazas,
    watcher_terrazas_activo,
)
from watchers.obras_watcher import (
    iniciar_watcher_obras,
    watcher_obras_activo,
)


# =============================================================================
# 4) APP + CONFIGURACIÓN RUNTIME
# =============================================================================
app = Flask(__name__)
app.config.from_object(Config)

# Runtime environment
FLASK_ENV = os.getenv("FLASK_ENV", "development").strip().lower()
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "1" if FLASK_ENV == "development" else "0") == "1"

app.config["TEMPLATES_AUTO_RELOAD"] = FLASK_DEBUG
app.jinja_env.auto_reload = FLASK_DEBUG

# Toggle de debug template endpoint
app.config["ENABLE_DEBUG_TEMPLATE"] = os.getenv(
    "ENABLE_DEBUG_TEMPLATE",
    "1" if FLASK_ENV == "development" else "0",
) == "1"

# LLM runtime
app.config["LLM_BACKEND"] = os.getenv("LLM_BACKEND", "ollama")
app.config["LLM_MODEL"] = os.getenv("LLM_MODEL", "gemma3:4b")
app.config["LLM_TIMEOUT"] = int(os.getenv("LLM_TIMEOUT", "90"))

# DB runtime (diagnóstico)
app.config["DB_HOST"] = os.getenv("DB_HOST", "127.0.0.1")
app.config["DB_PORT"] = int(os.getenv("DB_PORT", "3306"))
app.config["DB_USER"] = os.getenv("DB_USER", "")
app.config["DB_NAME"] = os.getenv("DB_NAME", "parquin_camiones")
app.config["DB_COMMON_NAME"] = os.getenv("DB_COMMON_NAME", "bd_tbl_comunes")

# Guard de watchers por proceso
app.config.setdefault("_WATCHERS_STARTED", False)


# =============================================================================
# 5) LOGGING PROFESIONAL
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app.logger.info("✅ App iniciada correctamente")
app.logger.info("🌍 FLASK_ENV=%s | FLASK_DEBUG=%s", FLASK_ENV, FLASK_DEBUG)
app.logger.info(
    "🗄️ DB_HOST=%s DB_PORT=%s DB_NAME=%s DB_COMMON_NAME=%s",
    app.config["DB_HOST"],
    app.config["DB_PORT"],
    app.config["DB_NAME"],
    app.config["DB_COMMON_NAME"],
)
app.logger.info(
    "🤖 LLM_BACKEND=%s LLM_MODEL=%s LLM_TIMEOUT=%s",
    app.config["LLM_BACKEND"],
    app.config["LLM_MODEL"],
    app.config["LLM_TIMEOUT"],
)


# =============================================================================
# 6) LOGIN MANAGER + USER MODEL
# =============================================================================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth_bp.login"
login_manager.login_message_category = "info"


class UsuarioLogin(UserMixin):
    """Representación mínima y estable de usuario para Flask-Login."""

    def __init__(
        self,
        idtbl_usuarios: int,
        idtbl_proveedores: Optional[int],
        rol: Optional[str],
        nombre_proveedor: Optional[str] = None,
        numero_cuenta: Optional[str] = None,
    ):
        self.id = idtbl_usuarios
        self.idtbl_proveedores = idtbl_proveedores
        self.rol = rol
        self.nombre_proveedor = nombre_proveedor
        self.numero_cuenta = numero_cuenta

    def get_id(self) -> str:
        return str(self.id)


@login_manager.user_loader
def load_user(user_id: str) -> Optional[UsuarioLogin]:
    """Reconstruye current_user desde id de sesión."""
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
# 7) HELPERS JINJA
# =============================================================================
def endpoint_existe(nombre_endpoint: str) -> bool:
    """Verifica si un endpoint existe en la app."""
    return nombre_endpoint in current_app.view_functions


def url_segura(endpoint: str, **kwargs) -> str:
    """Devuelve URL solo si endpoint existe; en caso contrario '#'."""
    try:
        if endpoint in current_app.view_functions:
            return url_for(endpoint, **kwargs)
        return "#"
    except Exception:
        return "#"


@app.template_filter("fecha")
def formato_fecha(valor):
    """Convierte string o datetime a formato dd/mm/yyyy."""
    if valor is None:
        return ""

    if isinstance(valor, str):
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y"):
            try:
                valor = datetime.strptime(valor, fmt)
                break
            except ValueError:
                continue

    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y")

    return str(valor)


app.jinja_env.globals["endpoint_existe"] = endpoint_existe
app.jinja_env.globals["url_segura"] = url_segura
app.jinja_env.filters["fecha"] = formato_fecha


# =============================================================================
# 8) ENDPOINT DEBUG TEMPLATE (CONTROLADO)
# =============================================================================
@app.route("/__debug_template__")
def debug_template():
    """
    Renderiza plantilla para depuración manual.
    Desactivado fuera de desarrollo salvo override por entorno.
    """
    if not app.config.get("ENABLE_DEBUG_TEMPLATE", False):
        return "⛔ Debug template deshabilitado", 404

    tpl = request.args.get("tpl")
    if not tpl:
        return "❌ Falta tpl", 400

    try:
        return render_template(tpl)
    except Exception as e:
        return f"<pre>{e}</pre>", 500


# =============================================================================
# 9) CARGA DINÁMICA DE BLUEPRINTS *_bp.py
# =============================================================================
def cargar_blueprints(app: Flask) -> None:
    """Descubre e importa blueprints *_bp.py de forma recursiva."""
    from flask import Blueprint

    carpetas_excluidas = {
        "venv", "env", ".venv", ".env",
        "__pycache__", ".pytest_cache",
        ".git", ".svn", ".hg",
        "node_modules",
        "static", "templates",
        "instance",
        "migrations",
        ".idea", ".vscode",
        "dist", "build",
    }

    encontrados = 0
    registrados = 0
    duplicados = 0
    errores = 0

    app.logger.info("🔍 Iniciando escaneo universal de blueprints...")

    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in carpetas_excluidas and not d.startswith(".")]

        for file in files:
            if not file.endswith("_bp.py"):
                continue

            encontrados += 1
            path = os.path.join(root, file)
            ruta_relativa = os.path.relpath(path, BASE_DIR)

            # Nombre único por ruta para evitar colisiones de módulos
            module_name = "auto_bp_" + ruta_relativa.replace(os.sep, "_").replace(".", "_")

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

    app.logger.info(
        "📊 Blueprints encontrados=%s | registrados=%s | duplicados=%s | errores=%s",
        encontrados, registrados, duplicados, errores
    )


cargar_blueprints(app)


# =============================================================================
# 10) WATCHERS BOOTSTRAP (ORDENADO + IDEMPOTENTE)
# =============================================================================
def iniciar_watchers(app: Flask) -> None:
    """
    Arranque seguro de watchers en orden:
      1) carpeta inicial
      2) contenedores
      3) terrazas
      4) obras
    """
    with app.app_context():
        if app.config.get("_WATCHERS_STARTED", False):
            app.logger.info("ℹ Watchers ya iniciados en este proceso")
            return

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

        app.config["_WATCHERS_STARTED"] = True
        app.logger.info("✅ Watchers iniciados")


with app.app_context():
    try:
        iniciar_watchers(app)
        app.logger.info("🚀 Watchers iniciados correctamente")
    except Exception:
        app.logger.error("❌ Error al iniciar watchers", exc_info=True)


# =============================================================================
# 11) SEGURIDAD GLOBAL · ÚNICO before_request
# =============================================================================
@app.before_request
def seguridad_global():
    """
    Pipeline central de seguridad:
      - Excluye rutas públicas
      - Bypass para super_admin
      - Verifica endpoint activo
      - Verifica permiso por rol
      - Registra auditoría de resultado
    """
    endpoint = request.endpoint
    if not endpoint:
        return None

    rutas_publicas = (
        "auth_bp.login",
        "auth_bp.logout",
        "auth_bp.register",
        "static",
        "__debug_template__",
    )

    if any(endpoint.startswith(r) for r in rutas_publicas):
        return None

    rol = session.get("rol")
    if rol == "super_admin":
        return None

    if not endpoint_activo(endpoint):
        registrar_evento("endpoint_desactivado", endpoint)
        if request.path.startswith("/api"):
            return jsonify({"error": "Endpoint desactivado"}), 403
        return "⛔ Endpoint desactivado", 403

    rol_id = session.get("rol_id")
    if not tiene_permiso(endpoint, rol_id):
        registrar_evento("acceso_denegado", endpoint)
        return redirect(url_for("auth_bp.login"))

    registrar_evento("acceso_permitido", endpoint)
    return None


# =============================================================================
# 12) RUTA RAÍZ
# =============================================================================
@app.route("/")
def index():
    """Redirección al login."""
    return redirect(url_for("auth_bp.login"))


# =============================================================================
# 13) ARRANQUE LOCAL
# =============================================================================
if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))

    app.run(
        host=host,
        port=port,
        debug=FLASK_DEBUG,
        use_reloader=False,  # evita duplicidad de watchers en dev
    )

# =============================================================================
# FIN · APP ENTRYPOINT SUPER MEGA ULTRA PROFESIONAL
# =============================================================================
