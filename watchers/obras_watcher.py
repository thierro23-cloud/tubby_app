# watchers/obras_watcher.py

import os

from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

from flask import current_app

from watchers.utils_async import procesar_pdf_entrada_obras

# =============================================================================
# 1️⃣ RUTAS DE CARPETAS DE OBRAS
# =============================================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CARPETA_OBRAS = os.path.join(BASE_DIR, "obras")
CARPETA_ENTRADA_OBRAS = os.path.join(CARPETA_OBRAS, "entrada_pdf")
CARPETA_PAPELERA_OBRAS = os.path.join(CARPETA_OBRAS, "papelera")
CARPETA_REVISION_OBRAS = os.path.join(CARPETA_OBRAS, "para_revision")
CARPETA_PENDIENTES_OBRAS = os.path.join(CARPETA_OBRAS, "pendientes_validacion")


# =============================================================================
# 2️⃣ ESTADO DEL WATCHER · OBRAS
# =============================================================================

watcher_obras_activo = False
observer_obras = None


# =============================================================================
# 3️⃣ HANDLER DE EVENTOS · OBRAS
# =============================================================================


class ObrasHandler(PatternMatchingEventHandler):
    """
    Handler que vigila OBRAS/entrada_pdf y reacciona a nuevos PDFs.

    RESPONSABILIDADES:
      - Escuchar SOLO eventos de creación de archivos *.pdf.
      - Ignorar directorios.
      - Por cada PDF nuevo:
          · Loguear la detección.
          · Llamar a procesar_pdf_entrada_obras(nombre_pdf).
    """

    def __init__(self, app):
        super().__init__(patterns=["*.pdf"], ignore_directories=True)
        self.app = app

    def on_created(self, event):
        if event.is_directory:
            return

        ruta_pdf = event.src_path
        nombre_pdf = os.path.basename(ruta_pdf)

        with self.app.app_context():
            self.app.logger.info(
                f"[WATCHER_OBRAS] PDF detectado en obras/entrada_pdf: {ruta_pdf}"
            )

            resultado = procesar_pdf_entrada_obras(nombre_pdf)

            self.app.logger.info(
                "[WATCHER_OBRAS] Resultado procesar_pdf_entrada_obras -> "
                f"estado={resultado.get('estado')} "
                f"motivo={resultado.get('motivo')} "
                f"id_pendiente={resultado.get('id_pendiente')} "
                f"ruta_final_pdf={resultado.get('ruta_final_pdf')}"
            )


# =============================================================================
# 4️⃣ INICIAR WATCHER · OBRAS
# =============================================================================


def iniciar_watcher_obras(app):
    """
    Arranca el watcher de obras SI AÚN NO ESTÁ ACTIVO.

    PASOS:
      1) Comprobar watcher_obras_activo.
      2) Asegurar que las carpetas existen:
           - OBRAS/entrada_pdf
           - OBRAS/papelera
           - OBRAS/para_revision
           - OBRAS/pendientes_validacion
      3) Crear handler y observer.
      4) Arrancar observer.
    """
    global watcher_obras_activo, observer_obras

    if watcher_obras_activo:
        app.logger.info("ℹ Watcher de obras ya estaba activo; no se reinicia")
        return

    os.makedirs(CARPETA_ENTRADA_OBRAS, exist_ok=True)
    os.makedirs(CARPETA_PAPELERA_OBRAS, exist_ok=True)
    os.makedirs(CARPETA_REVISION_OBRAS, exist_ok=True)
    os.makedirs(CARPETA_PENDIENTES_OBRAS, exist_ok=True)

    handler = ObrasHandler(app)
    observer_obras = Observer()
    observer_obras.schedule(handler, path=CARPETA_ENTRADA_OBRAS, recursive=False)
    observer_obras.start()

    watcher_obras_activo = True
    app.logger.info(f"🚀 Watcher de obras iniciado: {CARPETA_ENTRADA_OBRAS}")
    app.logger.info(f"👁 [obras/entrada_pdf] Vigilando carpeta: {CARPETA_ENTRADA_OBRAS}")
