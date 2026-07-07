# =============================================================================
# 🚀 TUBBY APP · ENTRY POINT (VERSIÓN SERVIDOR + SEGURIDAD + AUDITORÍA + WATCHER)
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
#   ✔ Arranque del watcher de PDFs de contenedores
#
# ⚠️ REGLAS:
#   ❗ SOLO existe un @before_request → seguridad_global
#   ❗ Auditoría se ejecuta desde seguridad_global y registrar_evento
#   ❗ Rutas públicas (login/logout/registro) se excluyen explícitamente
#   ❗ El watcher se arranca una única vez por proceso
#
# 🖥️ ENTORNO LOCAL:
#   - Ejecutar:
#         python app.py
#   - El servidor de desarrollo se arranca en 127.0.0.1:5000
#   - use_reloader=False para evitar duplicar watchers.
#
# 🏭 ENTORNO SERVIDOR (PRODUCCIÓN):
#   - Copiar el proyecto manteniendo la arquitectura de carpetas:
#         /opt/tubby_app/
#             app.py
#             watchers/
#             blueprints/
#             contenedores/
#                 entrada_pdf/
#                 papelera/
#                 para_revision/
#                 pendientes_validacion/
#
#   - Configurar un servidor WSGI (ejemplo Gunicorn + Nginx) y arrancar con:
#         gunicorn -w 3 "app:app"
#
#   - NO es necesario tocar código al pasar a servidor:
#         · BASE_DIR se calcula automáticamente.
#         · Las rutas de contenedores son relativas a BASE_DIR.
#         · Blueprints y watchers se cargan dinámicamente.
#
# =============================================================================


# =============================================================================
# 1️⃣ CONFIGURACIÓN DEL ENTORNO · PATHS Y BASE DEL SISTEMA
# =============================================================================
# 1.1) BASE_DIR Y sys.path (COMIENZA)
# -----------------------------------------------------------------------------
# Obtenemos la ruta base de la app (carpeta raíz del proyecto) y la
# añadimos a sys.path para permitir imports absolutos coherentes tanto
# en local como en servidor.
# -----------------------------------------------------------------------------
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
# 1.1) BASE_DIR Y sys.path (TERMINA)
# -----------------------------------------------------------------------------


# =============================================================================
# 2️⃣ IMPORTS PRINCIPALES · CORE DEL FRAMEWORK
# =============================================================================
# 2.1) Imports de Flask y librerías base (COMIENZA)
# -----------------------------------------------------------------------------
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

# Imports de autenticación Flask-Login (COMIENZA)
# -----------------------------------------------------------------------------
from flask_login import LoginManager

# Imports de autenticación Flask-Login (TERMINA)
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# 2.1) Imports de Flask y librerías base (TERMINA)
# -----------------------------------------------------------------------------


# =============================================================================
# 3️⃣ IMPORTS DE NEGOCIO · CONFIG, SEGURIDAD, AUDITORÍA Y WATCHERS
# =============================================================================
# 3.1) Configuración, seguridad y auditoría (COMIENZA)
# -----------------------------------------------------------------------------
from config import Config  # Configuración personalizada de la app
from core.permisos import endpoint_activo, tiene_permiso  # Seguridad y permisos
from core.audit import registrar_evento  # Auditoría

# 3.1) Configuración, seguridad y auditoría (TERMINA)
# -----------------------------------------------------------------------------

# =============================================================================
# 3.2) Watchers de PDFs y gestor genérico de watchers (COMIENZA)
# =============================================================================
# RESPONSABILIDADES:
#   - Importar e inicializar:
#       · Watcher de carpeta inicial de PDFs (bandeja de entrada general).
#       · Watcher de contenedores.
#       · Watcher de terrazas.
#       · Watcher de obras.
#   - Exponer:
#       · procesar_pdfs_existentes(app)
#       · iniciar_watchers(app)
#
# NOTA:
#   - Cada watcher tiene su propia función iniciar_* y su bandera watcher_*_activo.
#   - iniciar_watchers(app) se llama una sola vez al iniciar la app Flask.
# =============================================================================

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


def procesar_pdfs_existentes(app):
    """
    Procesa PDFs que ya existan en las carpetas de trabajo al arrancar la app.

    USO TÍPICO:
      - Llamar a esta función justo después de iniciar_watchers(app).
      - Recorre (según implementes en utils_async):
          · carpeta_inicial_pdf (bandeja general).
          · contenedores/entrada_pdf.
          · terrazas/entrada_pdf.
          · obras/entrada_pdf.
    """
    with app.app_context():
        app.logger.info("🔁 Procesando PDFs existentes en las carpetas de trabajo...")

        # Aquí puedes enganchar funciones industriales de reprocesado que
        # implementes en watchers.utils_async, por ejemplo:
        #
        # from watchers.utils_async import (
        #     reprocesar_carpeta_inicial,
        #     reprocesar_contenedores_entrada,
        #     reprocesar_terrazas_entrada,
        #     reprocesar_obras_entrada,
        # )
        #
        # reprocesar_carpeta_inicial()
        # reprocesar_contenedores_entrada()
        # reprocesar_terrazas_entrada()
        # reprocesar_obras_entrada()
        #
        # De momento dejamos solo el log para no forzar una implementación
        # concreta.
        app.logger.info(
            "ℹ procesar_pdfs_existentes: implementar según lógica industrial "
            "(reprocesar carpeta_inicial / entrada_pdf de cada módulo)"
        )


def iniciar_watchers(app):
    """
    Arranca todos los watchers necesarios para la app, de forma segura.

    PASOS:
      1) Iniciar watcher de carpeta inicial de PDFs:
           - Vigila carpeta_inicial_pdf y delega en procesar_pdf_inicial().
      2) Iniciar watcher de contenedores:
           - Vigila contenedores/entrada_pdf y delega en procesar_pdf_entrada().
      3) Iniciar watcher de terrazas:
           - Vigila terrazas/entrada_pdf y delega en procesar_pdf_entrada_terrazas().
      4) Iniciar watcher de obras:
           - Vigila obras/entrada_pdf y delega en procesar_pdf_entrada_obras().
    """
    with app.app_context():
        app.logger.info("🚀 Iniciando watchers de PDFs...")

        # 1) Watcher carpeta inicial (bandeja de entrada general)
        if not watcher_inicial_activo:
            iniciar_watcher_carpeta_inicial(app)
        else:
            app.logger.info("ℹ Watcher de carpeta_inicial_pdf ya estaba activo")

        # 2) Watcher de contenedores
        if not watcher_contenedores_activo:
            iniciar_watcher_contenedores(app)
        else:
            app.logger.info("ℹ Watcher de contenedores ya estaba activo")

        # 3) Watcher de terrazas
        if not watcher_terrazas_activo:
            iniciar_watcher_terrazas(app)
        else:
            app.logger.info("ℹ Watcher de terrazas ya estaba activo")

        # 4) Watcher de obras
        if not watcher_obras_activo:
            iniciar_watcher_obras(app)
        else:
            app.logger.info("ℹ Watcher de obras ya estaba activo")

        app.logger.info("✅ Todos los watchers necesarios han sido iniciados")


# =============================================================================
# 3.2) Watchers de PDFs y gestor genérico de watchers (TERMINA)
# =============================================================================

# =============================================================================
# 4️⃣ CREACIÓN DE LA APP · INICIALIZACIÓN DE FLASK + LOGIN_MANAGER
# =============================================================================
# 4.1) Instancia de Flask y configuración (COMIENZA)
# -----------------------------------------------------------------------------
app = Flask(__name__)
app.config.from_object(Config)

# Auto-recarga de templates en desarrollo
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.auto_reload = True
# 4.1) Instancia de Flask y configuración (TERMINA)
# 4.1.bis) Configuración de LLM local (Ollama / LM Studio) (COMIENZA)
# -------------------------------------------------------------------
app.config["LLM_BACKEND"] = "ollama"
app.config["LLM_MODEL"] = "gemma3:4b"

# ⏱️ Timeout en segundos para llamadas a Ollama (por defecto eran 30 en el helper)
app.config["LLM_TIMEOUT"] = 90
# 4.1.bis) Configuración de LLM local (TERMINA)
# ---------------------------------------------------------------------

# 4.2) Inicialización de Flask-Login (COMIENZA)
# -----------------------------------------------------------------------------
login_manager = LoginManager()
login_manager.init_app(app)

# Endpoint al que redirigirá Flask-Login si no hay usuario autenticado
# Ajusta "auth_bp.login" al nombre real de tu blueprint/vista de login.
login_manager.login_view = "auth_bp.login"
# (Opcional) Mensaje de categoría 'info' o 'warning' si quieres usar flash()
login_manager.login_message_category = "info"
# 4.2) Inicialización de Flask-Login (TERMINA)
# -----------------------------------------------------------------------------

# 4.3) MODELO LIGERO DE USUARIO + user_loader PARA FLASK-LOGIN (COMIENZA)
# -----------------------------------------------------------------------------
# Esta sección define:
#   - Una clase UsuarioLogin que representa al usuario logueado
#     a ojos de Flask-Login (basada en parquin_camiones.tbl_usuarios
#     + bd_tbl_comunes.tbl_proveedores).
#   - La función load_user(user_id) que Flask-Login usará en cada
#     petición para reconstruir current_user a partir del id guardado
#     en la cookie de sesión.
#
# Alineación con BD:
#   - parquin_camiones.tbl_usuarios:
#       · idtbl_usuarios       (PK usuario)
#       · idtbl_proveedores    (FK proveedor)
#       · numero_cuenta
#       · activo_baja
#       · fecha_inicio
#       · fecha_baja
#       · rol
#   - bd_tbl_comunes.tbl_proveedores:
#       · Idtbl_proveedores
#       · Nombre_Razon_Social
# -----------------------------------------------------------------------------
from flask_login import UserMixin
from db import ejecutar_query


class UsuarioLogin(UserMixin):
    """
    Representación mínima de un usuario de parquin para Flask-Login.

    Campos principales expuestos:
      - id               : idtbl_usuarios (PK en tbl_usuarios)
      - idtbl_proveedores: FK al proveedor en bd_tbl_comunes.tbl_proveedores
      - rol              : rol de la tabla tbl_usuarios
      - nombre_proveedor : Nombre/Razón Social del proveedor (para mostrar)
      - numero_cuenta    : cuenta asociada al usuario, si aplica
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
        """
        Devuelve el identificador único del usuario.

        Flask-Login espera siempre un string, por eso se castea.
        """
        return str(self.id)


@login_manager.user_loader
def load_user(user_id: str) -> UsuarioLogin | None:
    """
    Cargador de usuario para Flask-Login.

    - Recibe el idtbl_usuarios (como string) que se guardó en la cookie
      cuando se hizo login (login_user).
    - Consulta parquin_camiones.tbl_usuarios y bd_tbl_comunes.tbl_proveedores
      para reconstruir la información básica del usuario.
    - Devuelve una instancia de UsuarioLogin si el usuario existe y está activo,
      o None si no existe / está de baja.
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

    # Si no hay resultados o el usuario no está activo, devolvemos None
    if not filas:
        return None

    fila = filas[0]

    # Construimos el objeto UsuarioLogin que usará Flask-Login como current_user
    return UsuarioLogin(
        idtbl_usuarios=fila["idtbl_usuarios"],
        idtbl_proveedores=fila.get("idtbl_proveedores"),
        rol=fila.get("rol"),
        nombre_proveedor=fila.get("nombre_proveedor"),
        numero_cuenta=fila.get("numero_cuenta"),
    )


# 4.3) MODELO LIGERO DE USUARIO + user_loader PARA FLASK-LOGIN (TERMINA)
# ----------------------------------------------------------------------------------------------------------------------------------------------------------
# =============================================================================
# 5️⃣ SISTEMA DE LOGS · PRODUCCIÓN Y DEBUG
# =============================================================================
# 5.1) Configuración global de logging (COMIENZA)
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
app.logger.info("✅ App iniciada correctamente")
# 5.1) Configuración global de logging (TERMINA)
# -----------------------------------------------------------------------------


# =============================================================================
# 6️⃣ HELPERS JINJA · UTILIDADES PARA TEMPLATES
# =============================================================================
# 6.1) Helpers endpoint_existe y url_segura (COMIENZA)
# -----------------------------------------------------------------------------
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


# Registramos helpers en Jinja
app.jinja_env.globals["endpoint_existe"] = endpoint_existe
app.jinja_env.globals["url_segura"] = url_segura
# 6.1) Helpers endpoint_existe y url_segura (TERMINA)
# -----------------------------------------------------------------------------
# =============================================================================
# 6.2) Filtro personalizado para formateo de fechas (COMIENZA)
# =============================================================================
from datetime import datetime


@app.template_filter("fecha")
def formato_fecha(valor):
    """
    Convierte string o datetime a formato dd/mm/yyyy.

    Uso en plantillas:
        {{ fecha_desde|fecha }}
        {{ fecha_hasta|fecha }}

    Parámetros:
        valor: Puede ser:
            - datetime object
            - string en formato 'YYYY-MM-DD'
            - string en formato 'YYYY-MM-DD HH:MM:SS'

    Devuelve:
        string: Fecha en formato 'dd/mm/yyyy'
    """
    if valor is None:
        return ""

    if isinstance(valor, str):
        # Intentar parsear diferentes formatos de fecha
        for fmt in ["%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y"]:
            try:
                valor = datetime.strptime(valor, fmt)
                break
            except ValueError:
                continue

    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y")

    # Si no se pudo convertir, devolver el valor original
    return str(valor)


# Registrar el filtro en Jinja
app.jinja_env.filters["fecha"] = formato_fecha
# 6.2) Filtro personalizado para formateo de fechas (TERMINA)
# -----------------------------------------------------------------------------


# =============================================================================
# 7️⃣ DEBUG TEMPLATE · RENDER DINÁMICO
# =============================================================================
# 7.1) Ruta de debug de templates (COMIENZA)
# -----------------------------------------------------------------------------
@app.route("/__debug_template__")
def debug_template():
    tpl = request.args.get("tpl")
    if not tpl:
        return "❌ Falta tpl", 400
    try:
        return render_template(tpl)
    except Exception as e:
        return f"<pre>{e}</pre>"


# 7.1) Ruta de debug de templates (TERMINA)
# -----------------------------------------------------------------------------


# =============================================================================
# 8️⃣ CARGA AUTOMÁTICA DE BLUEPRINTS + WATCHERS
# =============================================================================
# En esta sección gestionamos:
#
#   8.1) Carga automática de TODOS los blueprints *_bp.py
#   8.2) Arranque explícito del watcher de contenedores
#   8.3) Procesado de PDFs existentes + arranque de TODOS los watchers genéricos
#
# Objetivos:
#   - La app descubre y registra todos los módulos/paneles/botones sin
#     configuración manual.
#   - Los watchers (programas que observan carpetas) quedan activos desde
#     el arranque, procesando lo que ya hay y lo nuevo que llegue.
# =============================================================================
# =============================================================================
# 8️⃣ CARGA AUTOMÁTICA DE BLUEPRINTS *_bp.py (SISTEMA UNIVERSAL)
# =============================================================================
# PROPÓSITO:
#   Sistema de auto-registro universal de blueprints que escanea TODA la
#   estructura del proyecto en busca de archivos que terminen en '_bp.py'
#   y registra automáticamente los blueprints que encuentre.
#
# ESTRATEGIA:
#   - Escanea recursivamente desde la raíz del proyecto (BASE_DIR)
#   - Procesa cualquier archivo *_bp.py sin importar su ubicación
#   - Permite organización modular sin restricciones de carpetas
#
# CARPETAS TÍPICAS ESCANEADAS:
#   - blueprints/              → Blueprints generales
#   - agenda_core/             → Módulo de agenda
#   - obras_core/              → Módulo de obras
#   - contenedores_core/       → Módulo de contenedores
#   - terrazas_core/           → Módulo de terrazas
#   - [cualquier otra carpeta con *_bp.py]
#
# EXCLUSIONES:
#   - venv/, env/, .venv/      → Entornos virtuales
#   - __pycache__/             → Cache de Python
#   - .git/                    → Control de versiones
#   - node_modules/            → Dependencias JavaScript (si aplica)
#   - static/                  → Archivos estáticos
#   - instance/                → Configuración de instancia Flask
#
# REGLAS:
#   - Solo archivos que terminen en '_bp.py' son procesados
#   - Solo objetos de tipo Blueprint son registrados
#   - Se evita duplicados: si un blueprint ya está registrado, se ignora
#
# VENTAJAS:
#   - Cero configuración: crear *_bp.py en cualquier carpeta = auto-registro
#   - Escalabilidad: añadir nuevos módulos no requiere tocar app.py
#   - Mantenibilidad: cada módulo gestiona sus propios blueprints
#   - Debugging: logs claros de qué se registró y qué se ignoró
#
# IMPLEMENTACIÓN (2026-05-24):
#   - Migrado de sistema de carpetas específicas a escaneo universal
#   - Añadidas exclusiones inteligentes para evitar escanear carpetas innecesarias
#   - Optimizado para proyectos grandes con múltiples módulos core
# =============================================================================


def cargar_blueprints(app):
    """
    Descubre e importa todos los blueprints *_bp.py del proyecto y los registra.

    Escanea recursivamente TODA la estructura del proyecto desde BASE_DIR,
    importa dinámicamente cada archivo *_bp.py que encuentre y registra
    todos los objetos Blueprint que contenga.

    Args:
        app: Instancia de la aplicación Flask
    """
    from flask import Blueprint

    # =========================================================================
    # CONFIGURACIÓN DE EXCLUSIONES
    # =========================================================================
    # Carpetas que NO deben escanearse (mejora rendimiento y evita errores)
    CARPETAS_EXCLUIDAS = {
        "venv",
        "env",
        ".venv",
        ".env",  # Entornos virtuales
        "__pycache__",
        ".pytest_cache",  # Cache de Python
        ".git",
        ".svn",
        ".hg",  # Control de versiones
        "node_modules",  # Dependencias JS
        "static",
        "templates",  # Archivos Flask estáticos
        "instance",  # Configuración de instancia
        "migrations",  # Migraciones de BD (Alembic)
        ".idea",
        ".vscode",  # IDEs
        "dist",
        "build",
        "*.egg-info",  # Builds y distribuciones
    }

    blueprints_encontrados = 0
    blueprints_registrados = 0
    blueprints_duplicados = 0
    errores = 0

    app.logger.info("🔍 Iniciando escaneo universal de blueprints...")

    # =========================================================================
    # ESCANEO RECURSIVO DESDE LA RAÍZ DEL PROYECTO
    # =========================================================================
    for root, dirs, files in os.walk(BASE_DIR):

        # =====================================================================
        # FILTRAR CARPETAS EXCLUIDAS (modifica dirs in-place para no entrar)
        # =====================================================================
        # Nota: modificar 'dirs' in-place hace que os.walk NO entre en esas carpetas
        dirs[:] = [
            d for d in dirs if d not in CARPETAS_EXCLUIDAS and not d.startswith(".")
        ]

        # =====================================================================
        # PROCESAR ARCHIVOS *_bp.py EN LA CARPETA ACTUAL
        # =====================================================================
        for file in files:
            if not file.endswith("_bp.py"):
                continue

            blueprints_encontrados += 1
            path = os.path.join(root, file)

            # Calcular ruta relativa para logging más legible
            ruta_relativa = os.path.relpath(path, BASE_DIR)
            module_name = file[:-3]  # Quitar extensión .py

            try:
                # =============================================================
                # IMPORTACIÓN DINÁMICA DEL MÓDULO
                # =============================================================
                spec = importlib.util.spec_from_file_location(module_name, path)
                if spec is None or spec.loader is None:
                    app.logger.error(f"❌ No se pudo crear spec para: {ruta_relativa}")
                    errores += 1
                    continue

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # =============================================================
                # BÚSQUEDA Y REGISTRO DE BLUEPRINTS EN EL MÓDULO
                # =============================================================
                blueprints_en_modulo = 0

                for attr in dir(module):
                    # Ignorar atributos privados y especiales
                    if attr.startswith("_"):
                        continue

                    obj = getattr(module, attr)

                    if isinstance(obj, Blueprint):
                        blueprints_en_modulo += 1

                        # =================================================
                        # REGISTRO CON PROTECCIÓN ANTI-DUPLICADOS
                        # =================================================
                        if obj.name not in app.blueprints:
                            app.register_blueprint(obj)
                            blueprints_registrados += 1
                            app.logger.info(
                                f"✅ Blueprint registrado: {obj.name:30s} <- {ruta_relativa}"
                            )
                        else:
                            blueprints_duplicados += 1
                            app.logger.warning(
                                f"⚠️  Blueprint duplicado ignorado: {obj.name:30s} <- {ruta_relativa}"
                            )

                # Advertir si el archivo *_bp.py no contenía blueprints
                if blueprints_en_modulo == 0:
                    app.logger.warning(
                        f"⚠️  Archivo *_bp.py sin blueprints: {ruta_relativa}"
                    )

            except Exception as e:
                errores += 1
                app.logger.error(
                    f"❌ Error cargando blueprint desde {ruta_relativa}:\n"
                    f"   {str(e)}\n"
                    f"{traceback.format_exc()}"
                )

    # =========================================================================
    # RESUMEN FINAL DEL ESCANEO
    # =========================================================================
    app.logger.info("=" * 80)
    app.logger.info("📊 RESUMEN DE CARGA DE BLUEPRINTS")
    app.logger.info("=" * 80)
    app.logger.info(f"   Archivos *_bp.py encontrados: {blueprints_encontrados}")
    app.logger.info(f"   ✅ Blueprints registrados:     {blueprints_registrados}")
    app.logger.info(f"   ⚠️  Blueprints duplicados:      {blueprints_duplicados}")
    app.logger.info(f"   ❌ Errores:                     {errores}")
    app.logger.info("=" * 80)

    if errores > 0:
        app.logger.warning(
            f"⚠️  Se encontraron {errores} errores durante la carga de blueprints. "
            f"Revisa los logs anteriores para más detalles."
        )


# =============================================================================
# EJECUCIÓN DEL AUTO-REGISTRO UNIVERSAL
# =============================================================================
cargar_blueprints(app)


# =============================================================================
# DEBUG OPCIONAL: Verificación de rutas críticas
# =============================================================================
# Útil para confirmar que rutas específicas se registraron correctamente
# Comentar o eliminar en producción
with app.app_context():
    # Ejemplo: verificar rutas del módulo de accesos de parking
    for rule in app.url_map.iter_rules():
        if str(rule).startswith("/parquin/rio_torio/accesos/"):
            print(
                "DEBUG RULE:",
                rule,
                "endpoint:",
                rule.endpoint,
                "methods:",
                rule.methods,
            )  # -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# 8.2) INICIAR WATCHER DE CONTENEDORES (ARRANQUE EXPLÍCITO) (COMIENZA)
# -----------------------------------------------------------------------------
# - Arranca de forma explícita el watcher de PDFs de contenedores,
#   definido en watchers/contenedores_watcher.py (función iniciar_watcher_contenedores).
#
#   ✔ Se ejecuta dentro de app.app_context().
#   ✔ Deja trazas claras en logs:
#       · "🚀 Watcher iniciado: ..."
#       · "👁 [entrada_pdf] Vigilando carpeta: ..."
# -----------------------------------------------------------------------------
# with app.app_context():
#   if not watcher_activo:
#        iniciar_watcher_contenedores(app)
#       app.logger.info("🚀 Watcher contenedores iniciado explícitamente")
#   else:
#       app.logger.info("ℹ Watcher contenedores ya estaba activo; no se reinicia")
# 8.2) INICIAR WATCHER DE CONTENEDORES (ARRANQUE EXPLÍCITO) (TERMINA)
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# 8.3) PROCESAR PDFs EXISTENTES + INICIAR TODOS LOS WATCHERS GENÉRICOS (COMIENZA)
# -----------------------------------------------------------------------------
# Aquí usamos el sistema genérico definido en watchers/__init__.py:
#
#   - procesar_pdfs_existentes(app):
#       Escanea la carpeta de contenedores al arrancar la app y procesa
#         todos los PDFs que ya estén allí.
#
#   - iniciar_watchers(app):
#       Busca módulos watcher_*.py en la carpeta watchers y, si exponen
#       una función iniciar_watcher(app), la ejecuta.
#
# Esto permite:
#   ✔ Procesar "cola vieja" de PDFs pendientes.
#   ✔ Arrancar múltiples watchers especializados sin tocar app.py.
# -----------------------------------------------------------------------------
# 8.3) PROCESAR PDFs EXISTENTES + INICIAR TODOS LOS WATCHERS GENÉRICOS (COMIENZA)
with app.app_context():
    # ⚠️ Cola vieja desactivada: el flujo moderno usa solo el watcher +
    # utils_async.procesar_pdf_entrada() sobre contenedores/entrada_pdf.
    # Si necesitas una migración puntual, reactiva procesar_pdfs_existentes
    # tras adaptar el esquema de tbl_contenedores_pendientes.
    # try:
    #     procesar_pdfs_existentes(app)
    #     app.logger.info("📄 PDFs existentes procesados correctamente")
    # except Exception:
    #     app.logger.error("❌ Error al procesar PDFs existentes", exc_info=True)

    try:
        iniciar_watchers(app)
        app.logger.info("🚀 Watchers genéricos iniciados correctamente")
    except Exception:
        app.logger.error("❌ Error al iniciar watchers genéricos", exc_info=True)
# 8.3) PROCESAR PDFs EXISTENTES + INICIAR TODOS LOS WATCHERS GENÉRICOS (TERMINA)# -----------------------------------------------------------------------------


# =============================================================================
# 9️⃣ SEGURIDAD GLOBAL · PIPELINE CENTRAL
# =============================================================================
# 9.1) seguridad_global · único @before_request (COMIENZA)
# -----------------------------------------------------------------------------
@app.before_request
def seguridad_global():
    """
    Pipeline central de seguridad:
      - Excluye rutas públicas.
      - Bypass total para super_admin por rol.
      - Verifica si el endpoint está activo.
      - Verifica permisos del usuario.
      - Registra eventos de auditoría.
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

    # Rutas públicas → sin controles ni auditoría de acceso denegado
    if any(endpoint.startswith(r) for r in rutas_publicas):
        return

    # SUPER ADMIN → BYPASS TOTAL POR ROL
    rol = session.get("rol")
    if rol == "super_admin":
        return

    # VALIDAR SI EL ENDPOINT ESTÁ ACTIVO
    if not endpoint_activo(endpoint):
        registrar_evento("endpoint_desactivado", endpoint)
        if request.path.startswith("/api"):
            return {"error": "Endpoint desactivado"}, 403
        return "⛔ Endpoint desactivado", 403

    # VALIDAR PERMISOS DEL USUARIO
    rol_id = session.get("rol_id")
    if not tiene_permiso(endpoint, rol_id):
        registrar_evento("acceso_denegado", endpoint)
        return redirect(url_for("auth_bp.login"))

    # ACCESO CORRECTO → AUDITORÍA POSITIVA
    registrar_evento("acceso_permitido", endpoint)


# 9.1) seguridad_global · único @before_request (TERMINA)
# -----------------------------------------------------------------------------


# =============================================================================
# 🔟 RUTA PRINCIPAL · REDIRECCIÓN
# =============================================================================
# 10.1) index → redirección a login (COMIENZA)
# -----------------------------------------------------------------------------
@app.route("/")
def index():
    """
    🔹 Redirige siempre al login principal.
    """
    return redirect(url_for("auth_bp.login"))


# 10.1) index → redirección a login (TERMINA)
# -----------------------------------------------------------------------------


# =============================================================================
# 1️⃣1️⃣ ARRANQUE DE LA APP · SOLO DESARROLLO
# =============================================================================
# 11.1) app.run() sin reloader automático (COMIENZA)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    # IMPORTANTE: use_reloader=False para NO duplicar watchers.
    app.run(debug=True, use_reloader=False)
# 11.1) app.run() sin reloader automático (TERMINA)
# -----------------------------------------------------------------------------


# =============================================================================
# 1️⃣2️⃣ FIN · app.py UNIFICADO (SEGURIDAD + AUDITORÍA + BLUEPRINTS + WATCHERS)
# =============================================================================
