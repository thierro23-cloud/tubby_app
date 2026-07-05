# watchers/bandeja_inicial_watcher.py

import os

from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

from flask import current_app

from watchers.utils_async import procesar_pdf_inicial


# =============================================================================
# 1️⃣ RUTAS · BASE_DIR + CARPETA_INICIAL
# =============================================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Puedes ajustar el nombre de la carpeta a lo que decidas:
# p.ej. "bandeja_inicial_pdf" o "carpeta_inicial_pdf"
CARPETA_INICIAL = os.path.join(BASE_DIR, "carpeta_inicial_pdf")

# Si prefieres "bandeja_inicial_pdf":
# CARPETA_INICIAL = os.path.join(BASE_DIR, "bandeja_inicial_pdf")


# =============================================================================
# 2️⃣ ESTADO DEL WATCHER
# =============================================================================

watcher_inicial_activo = False
observer_inicial = None


# =============================================================================
# 3️⃣ HANDLER · SOLO ARCHIVOS *.pdf
# =============================================================================

class BandejaInicialHandler(PatternMatchingEventHandler):
    """
    Handler que vigila CARPETA_INICIAL y reacciona cuando se crea un PDF nuevo.

    RESPONSABILIDADES:
      - Escuchar SOLO eventos de creación de archivos *.pdf.
      - Ignorar directorios.
      - Por cada PDF nuevo:
          · Loguear la detección.
          · Llamar a procesar_pdf_inicial(nombre_pdf).
    """

    def __init__(self, app):
        super().__init__(patterns=["*.pdf"], ignore_directories=True)
        self.app = app

    def on_created(self, event):
        if event.is_directory:
            return

        ruta_pdf = event.src_path
        nombre_pdf = os.path.basename(ruta_pdf)

        # Entrar en contexto de app para logs y cualquier configuración de Flask
        with self.app.app_context():
            self.app.logger.info(
                f"[WATCHER_INICIAL] PDF detectado en carpeta_inicial_pdf: {ruta_pdf}"
            )

            # Delegar TODO en la lógica industrial
            # Esta función la defines tú en watchers.utils_async
            # y se encarga de:
            #   - extraer datos,
            #   - generar CSV,
            #   - renombrar a ...csv.pdf,
            #   - clasificar (vados/terrazas/obras/contendores/otros),
            #   - mover el PDF y CSV a la carpeta destino.
            resultado = procesar_pdf_inicial(nombre_pdf)

            self.app.logger.info(
                "[WATCHER_INICIAL] Resultado procesar_pdf_inicial -> "
                f"estado={resultado.get('estado')} "
                f"motivo={resultado.get('motivo')} "
                f"tipo={resultado.get('tipo')} "
                f"ruta_final_pdf={resultado.get('ruta_final_pdf')} "
                f"ruta_csv={resultado.get('ruta_csv')}"
            )


# =============================================================================
# 4️⃣ FUNCIÓN DE INICIO · iniciar_watcher_carpeta_inicial
# =============================================================================

def iniciar_watcher_carpeta_inicial(app):
    """
    Arranca el watcher de la carpeta_inicial_pdf SI AÚN NO ESTÁ ACTIVO.

    PASOS:
      1) Comprueba watcher_inicial_activo:
           - Si True → log y return.
      2) Crea CARPETA_INICIAL si no existe.
      3) Crea handler = BandejaInicialHandler(app).
      4) Crea observer = Observer(), schedule(handler, CARPETA_INICIAL).
      5) Arranca observer.start().
      6) Marca watcher_inicial_activo = True.
    """
    global watcher_inicial_activo, observer_inicial

    if watcher_inicial_activo:
        app.logger.info(
            "ℹ Watcher de carpeta_inicial_pdf ya estaba activo; no se reinicia"
        )
        return

    # Asegurarnos de que la carpeta existe
    os.makedirs(CARPETA_INICIAL, exist_ok=True)

    handler = BandejaInicialHandler(app)
    observer_inicial = Observer()
    observer_inicial.schedule(handler, path=CARPETA_INICIAL, recursive=False)
    observer_inicial.start()

    watcher_inicial_activo = True
    app.logger.info(f"🚀 Watcher inicial iniciado: {CARPETA_INICIAL}")
    app.logger.info(f"👁 [carpeta_inicial_pdf] Vigilando carpeta: {CARPETA_INICIAL}")