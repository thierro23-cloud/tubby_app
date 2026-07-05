# =============================================================================
# 1️⃣ INTRODUCCIÓN · WATCHER DE PDFs DE CONTENEDORES
# =============================================================================
# Este módulo implementa el "ojo" que vigila la carpeta de entrada de PDFs
# de contenedores y conecta con la lógica asíncrona de procesado:
#
#   1.1) RUTAS ROBUSTAS PARA LA GESTIÓN DE CONTENEDORES:
#        ------------------------------------------------
#        Se basa en una estructura de carpetas estable:
#
#          tubby_app/
#              app.py
#              watchers/
#                  contenedores_watcher.py   ← este módulo
#              contenedores/
#                  entrada_pdf/              ← carpeta vigilada por el watcher
#                  papelera/                 ← PDFs descartados o auto-guardados
#                  para_revision/            ← pendientes en revisión manual
#                  pendientes_validacion/    ← pendientes ya "en cola" de validación
#
#        Variables clave:
#          - BASE_DIR            → raíz del proyecto (tubby_app).
#          - CARPETA_CONTENEDORES→ base de contenedores (BASE_DIR/contenedores).
#          - CARPETA_ENTRADA     → contenedores/entrada_pdf.
#          - CARPETA_PAPELERA    → contenedores/papelera.
#          - CARPETA_REVISION    → contenedores/para_revision.
#          - CARPETA_PENDIENTES  → contenedores/pendientes_validacion.
#
#   1.2) WATCHER BASADO EN watchdog:
#        ---------------------------
#        - Usa watchdog.Observer + PatternMatchingEventHandler.
#        - Solo escucha archivos *.pdf dentro de CARPETA_ENTRADA.
#        - Cada vez que aparece un PDF nuevo:
#             · Entra en contexto de la aplicación Flask.
#             · Registra un log de detección.
#             · Llama a watchers.utils_async.procesar_pdf_entrada(nombre_pdf),
#               que se encarga de:
#                   - Llamar al backend industrial (procesar_pdf_core).
#                   - Validar unicidad de CSV (pendientes + control).
#                   - Decidir si el PDF:
#                       · se auto‑guarda (control),
#                       · se descarta (papelera),
#                       · o genera un pendiente (para_revision / solo_retirada).
#                   - Mover el PDF a la carpeta final adecuada.
#                   - Insertar/actualizar tbl_contenedores_pendientes según caso.
#
#        IMPORTANTE:
#        - El watcher SOLO vigila entrada_pdf.
#        - Nunca re-procesa PDFs de para_revision / pendientes_validacion /
#          papelera: esas carpetas no están bajo vigilancia.
#
#   1.3) MECANISMO PARA EVITAR MÚLTIPLES INSTANCIAS:
#        -------------------------------------------
#        - watcher_activo:
#             · Bandera de módulo que indica si el watcher ya está en marcha.
#        - observer:
#             · Instancia única de watchdog.Observer.
#        - iniciar_watcher_contenedores(app):
#             · Solo arranca el watcher si watcher_activo es False.
#
# OBJETIVO:
#   - Que el watcher funcione igual en local y en servidor, siempre que
#     se mantenga la misma estructura relativa de carpetas.
#
# 🏭 PASO A SERVIDOR (PRODUCCIÓN):
#   - BASE_DIR se calcula como la raíz del proyecto "tubby_app":
#
#         tubby_app/
#             app.py
#             watchers/
#             contenedores/
#                 entrada_pdf/
#                 papelera/
#                 para_revision/
#                 pendientes_validacion/
#
#   - Para desplegar en un servidor:
#         1) Copiar esta estructura en una ruta fija (ej: /opt/tubby_app).
#         2) Asegurarse de que existen las carpetas:
#               contenedores/entrada_pdf
#               contenedores/papelera
#               contenedores/para_revision
#               contenedores/pendientes_validacion
#         3) Arrancar la app desde la raíz del proyecto con WSGI, por ejemplo:
#               gunicorn -w 3 "app:app"
#
#   - NO es necesario modificar rutas ni código del watcher entre
#     entorno local y producción: todo se calcula de forma relativa.
# =============================================================================


# =============================================================================
# 2️⃣ IMPORTS Y DEPENDENCIAS · WATCHER
# =============================================================================
# - os                       → manejo de rutas y directorios.
# - watchdog.observers       → Observer para vigilar el sistema de ficheros.
# - watchdog.events          → PatternMatchingEventHandler para filtrar PDFs.
# - flask.current_app        → acceso a la app Flask para logging y contexto.
# - procesar_pdf_entrada     → lógica asíncrona de procesado en watchers.utils_async.
# =============================================================================

import os

from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

from flask import current_app

from watchers.utils_async import procesar_pdf_entrada


# =============================================================================
# 3️⃣ RUTAS DE CARPETAS DE CONTENEDORES
# =============================================================================
# 3.1) BASE_DIR Y CARPETAS DE TRABAJO (COMIENZA)
# -----------------------------------------------------------------------------
# BASE_DIR:
#   - Raíz lógica del proyecto "tubby_app".
#   - Se calcula como el directorio padre del directorio donde está este módulo:
#
#         tubby_app/
#             app.py
#             watchers/
#                 contenedores_watcher.py  ← __file__
#
# CARPETAS:
#   - CARPETA_CONTENEDORES = BASE_DIR/contenedores
#   - CARPETA_ENTRADA      = contenedores/entrada_pdf
#   - CARPETA_PAPELERA     = contenedores/papelera
#   - CARPETA_REVISION     = contenedores/para_revision
#   - CARPETA_PENDIENTES   = contenedores/pendientes_validacion
#
# Estas rutas se usan solo para:
#   - Crear las carpetas si no existen (iniciar_watcher_contenedores).
#   - Configurar el path que el Observer va a vigilar (solo CARPETA_ENTRADA).
# -----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CARPETA_CONTENEDORES = os.path.join(BASE_DIR, "contenedores")
CARPETA_ENTRADA = os.path.join(CARPETA_CONTENEDORES, "entrada_pdf")
CARPETA_PAPELERA = os.path.join(CARPETA_CONTENEDORES, "papelera")
CARPETA_REVISION = os.path.join(CARPETA_CONTENEDORES, "para_revision")
CARPETA_PENDIENTES = os.path.join(CARPETA_CONTENEDORES, "pendientes_validacion")
# 3.1) BASE_DIR Y CARPETAS DE TRABAJO (TERMINA)
# -----------------------------------------------------------------------------


# =============================================================================
# 4️⃣ ESTADO DEL WATCHER · VARIABLES DE MÓDULO
# =============================================================================
# 4.1) BANDERAS DE CONTROL (COMIENZA)
# -----------------------------------------------------------------------------
# watcher_activo:
#   - Booleano a nivel de módulo.
#   - Indica si el watcher ya ha sido iniciado en este proceso.
#   - Previene que iniciar_watcher_contenedores() arranque múltiples
#     Observers sobre la misma carpeta, lo que podría duplicar eventos.
#
# observer:
#   - Instancia global de watchdog.Observer.
#   - Se crea en iniciar_watcher_contenedores().
#   - Se asocia al handler ContenedoresHandler.
#   - Se arranca en segundo plano con observer.start().
# -----------------------------------------------------------------------------
watcher_activo = False
observer = None
# 4.1) BANDERAS DE CONTROL (TERMINA)
# -----------------------------------------------------------------------------


# =============================================================================
# 5️⃣ HANDLER DE EVENTOS · PatternMatchingEventHandler
# =============================================================================
# 5.1) ContenedoresHandler (COMIENZA)
# -----------------------------------------------------------------------------
# RESPONSABILIDADES:
#   - Escuchar SOLO eventos de creación de archivos *.pdf en la carpeta
#     CARPETA_ENTRADA (contendores/entrada_pdf).
#   - Ignorar directorios (ignore_directories=True).
#   - Por cada nuevo PDF detectado:
#       1) Entrar en contexto de app (with self.app.app_context()).
#       2) Loguear la detección.
#       3) Delegar el procesado en watchers.utils_async.procesar_pdf_entrada:
#            · Se encarga de:
#                - Llamar al core (procesar_pdf_core).
#                - Validar unicidad de CSV.
#                - Insertar en tbl_contenedores_pendientes si procede.
#                - Mover el PDF a:
#                      · papelera
#                      · para_revision
#                      · solo_retirada
#            · Devuelve un dict con:
#                - estado
#                - motivo
#                - id_pendiente (si se ha creado)
#                - ruta_final_pdf
#
# NOTA:
#   - Este handler NO toca la BD ni decide nada de negocio.
#   - Toda la lógica se delega en utils_async, que es el módulo industrial.
# -----------------------------------------------------------------------------
class ContenedoresHandler(PatternMatchingEventHandler):
    def __init__(self, app):
        super().__init__(patterns=["*.pdf"], ignore_directories=True)
        self.app = app

    def on_created(self, event):
        """
        (5.2) Evento de creación de archivo:
              - Solo actúa si es un archivo (no un directorio).
              - Extrae el nombre del PDF.
              - Registra logs y lanza procesar_pdf_entrada(nombre_pdf).
        """
        if event.is_directory:
            return

        ruta_pdf = event.src_path
        nombre_pdf = os.path.basename(ruta_pdf)

        # Log inmediato de detección (no bloquea el hilo principal)
        with self.app.app_context():
            self.app.logger.info(f"[WATCHER] PDF detectado en entrada_pdf: {ruta_pdf}")

            # Delegamos TODO el procesado en utils_async
            resultado = procesar_pdf_entrada(nombre_pdf)

            self.app.logger.info(
                "[WATCHER] Resultado procesar_pdf_entrada -> "
                f"estado={resultado.get('estado')} "
                f"motivo={resultado.get('motivo')} "
                f"id_pendiente={resultado.get('id_pendiente')} "
                f"ruta_final_pdf={resultado.get('ruta_final_pdf')}"
            )
# 5.1) ContenedoresHandler (TERMINA)
# -----------------------------------------------------------------------------


# =============================================================================
# 6️⃣ INICIAR WATCHER DE CONTENEDORES
# =============================================================================
# 6.1) iniciar_watcher_contenedores(app) (COMIENZA)
# -----------------------------------------------------------------------------
# FUNCIÓN:
#   - Arranca el watcher de contenedores SI AÚN NO ESTÁ ACTIVO.
#
# PASOS:
#   1) Comprobar watcher_activo:
#        - Si es True → loguear y salir (ya está en marcha).
#        - Si es False → continuar.
#
#   2) Asegurar que las carpetas existen:
#        - CARPETA_ENTRADA
#        - CARPETA_PAPELERA
#        - CARPETA_REVISION
#        - CARPETA_PENDIENTES
#
#   3) Crear handler = ContenedoresHandler(app).
#
#   4) Crear observer = Observer() y asociarlo al handler:
#        observer.schedule(handler, path=CARPETA_ENTRADA, recursive=False)
#
#      IMPORTANTE:
#        - Solo se vigila CARPETA_ENTRADA.
#        - recursive=False → no se entra en subcarpetas de entrada_pdf.
#
#   5) Arrancar el observer:
#        observer.start()
#
#   6) Marcar watcher_activo = True y registrar logs informativos:
#        - Ruta de la carpeta vigilada.
#
# USO TÍPICO:
#   - Llamar a iniciar_watcher_contenedores(app) desde la factory principal
#     (por ejemplo, al iniciar la app Flask en modo servidor).
# -----------------------------------------------------------------------------
def iniciar_watcher_contenedores(app):
    global watcher_activo, observer

    if watcher_activo:
        app.logger.info("ℹ Watcher de contenedores ya estaba activo; no se reinicia")
        return

    # 6.2 Asegurarnos de que las carpetas existen
    os.makedirs(CARPETA_ENTRADA, exist_ok=True)
    os.makedirs(CARPETA_PAPELERA, exist_ok=True)
    os.makedirs(CARPETA_REVISION, exist_ok=True)
    os.makedirs(CARPETA_PENDIENTES, exist_ok=True)

    # 6.3 Crear handler y observer
    handler = ContenedoresHandler(app)
    observer = Observer()
    observer.schedule(handler, path=CARPETA_ENTRADA, recursive=False)
    observer.start()

    watcher_activo = True
    app.logger.info(f"🚀 Watcher iniciado: {CARPETA_ENTRADA}")
    app.logger.info(f"👁 [entrada_pdf] Vigilando carpeta: {CARPETA_ENTRADA}")
# 6.1) iniciar_watcher_contenedores(app) (TERMINA)
# -----------------------------------------------------------------------------


# =============================================================================
# 7️⃣ FIN · watchers/contenedores_watcher.py
# =============================================================================
# Este módulo:
#   - NO implementa lógica de negocio.
#   - Solo:
#       · define rutas de trabajo,
#       · mantiene el estado del watcher,
#       · vigila entrada_pdf,
#       · y delega todo en utils_async.procesar_pdf_entrada().
#
# La responsabilidad de borrar/mover PDFs una vez validados (en la UI de
# pendientes) recae en:
#   - El blueprint de pendientes (validar / descartar).
#   - Las funciones descartar_pendiente / lógica de validación en utils_async.
#
# Con esto se garantiza que un PDF se procesa exactamente una vez desde
# entrada_pdf, y luego su ciclo de vida se gestiona desde la lógica de
# negocio, no desde el watcher.
# =============================================================================