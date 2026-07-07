# watchers/terrazas_watcher.py

import os

from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

from flask import current_app

from watchers.utils_async import procesar_pdf_entrada_terrazas

# =============================================================================
# 1️⃣ RUTAS DE CARPETAS DE TERRAZAS
# =============================================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CARPETA_TERRAZAS = os.path.join(BASE_DIR, "terrazas")
CARPETA_ENTRADA_TERRAZAS = os.path.join(CARPETA_TERRAZAS, "entrada_pdf")
CARPETA_PAPELERA_TERRAZAS = os.path.join(CARPETA_TERRAZAS, "papelera")
CARPETA_REVISION_TERRAZAS = os.path.join(CARPETA_TERRAZAS, "para_revision")
CARPETA_PENDIENTES_TERRAZAS = os.path.join(CARPETA_TERRAZAS, "pendientes_validacion")


# =============================================================================
# 2️⃣ ESTADO DEL WATCHER · TERRAZAS
# =============================================================================

watcher_terrazas_activo = False
observer_terrazas = None


# =============================================================================
# 3️⃣ HANDLER DE EVENTOS · TERRAZAS
# =============================================================================


class TerrazasHandler(PatternMatchingEventHandler):
    """
    Handler que vigila TERRAZAS/entrada_pdf y reacciona a nuevos PDFs.

    RESPONSABILIDADES:
      - Escuchar SOLO eventos de creación de archivos *.pdf.
      - Ignorar directorios.
      - Por cada PDF nuevo:
          · Loguear la detección.
          · Llamar a procesar_pdf_entrada_terrazas(nombre_pdf).
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
                f"[WATCHER_TERRAZAS] PDF detectado en terrazas/entrada_pdf: {ruta_pdf}"
            )

            resultado = procesar_pdf_entrada_terrazas(nombre_pdf)

            self.app.logger.info(
                "[WATCHER_TERRAZAS] Resultado procesar_pdf_entrada_terrazas -> "
                f"estado={resultado.get('estado')} "
                f"motivo={resultado.get('motivo')} "
                f"id_pendiente={resultado.get('id_pendiente')} "
                f"ruta_final_pdf={resultado.get('ruta_final_pdf')}"
            )


# =============================================================================
# 4️⃣ INICIAR WATCHER · TERRAZAS
# =============================================================================


def iniciar_watcher_terrazas(app):
    """
    Arranca el watcher de terrazas SI AÚN NO ESTÁ ACTIVO.

    PASOS:
      1) Comprobar watcher_terrazas_activo.
      2) Asegurar que las carpetas existen:
           - TERRAZAS/entrada_pdf
           - TERRAZAS/papelera
           - TERRAZAS/para_revision
           - TERRAZAS/pendientes_validacion
      3) Crear handler y observer.
      4) Arrancar observer.
    """
    global watcher_terrazas_activo, observer_terrazas

    if watcher_terrazas_activo:
        app.logger.info("ℹ Watcher de terrazas ya estaba activo; no se reinicia")
        return

    os.makedirs(CARPETA_ENTRADA_TERRAZAS, exist_ok=True)
    os.makedirs(CARPETA_PAPELERA_TERRAZAS, exist_ok=True)
    os.makedirs(CARPETA_REVISION_TERRAZAS, exist_ok=True)
    os.makedirs(CARPETA_PENDIENTES_TERRAZAS, exist_ok=True)

    handler = TerrazasHandler(app)
    observer_terrazas = Observer()
    observer_terrazas.schedule(handler, path=CARPETA_ENTRADA_TERRAZAS, recursive=False)
    observer_terrazas.start()

    watcher_terrazas_activo = True
    app.logger.info(f"🚀 Watcher de terrazas iniciado: {CARPETA_ENTRADA_TERRAZAS}")
    app.logger.info(
        f"👁 [terrazas/entrada_pdf] Vigilando carpeta: {CARPETA_ENTRADA_TERRAZAS}"
    )
