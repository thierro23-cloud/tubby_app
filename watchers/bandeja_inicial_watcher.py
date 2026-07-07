# watchers/bandeja_inicial_watcher.py
"""
WATCHER · BANDEJA INICIAL DE PDFs DE VÍA PÚBLICA (ÁVILA)

OBJETIVO
--------
Vigilar la carpeta física `carpeta_inicial_pdf` y reaccionar cada vez
que aparece un nuevo PDF:

  1. Detectar la creación del archivo (*.pdf) en tiempo casi real.
  2. Registrar el evento en el log de la aplicación (Flask).
  3. Delegar TODA la lógica de clasificación y distribución en
     `blueprints.control_via_publica.utils_async.procesar_pdf_inicial(nombre_pdf)`.

A grandes rasgos:
  - Este watcher es un "trigger" de sistema de ficheros.
  - NO decide si el PDF es de contenedores, obras, terrazas, vados, etc.
  - Solo vigila la bandeja general y llama a la función industrial
    que sabe qué hacer con cada PDF.

TECNOLOGÍA
----------
  - watchdog.observers.Observer:
      Hilo de background que monitoriza una carpeta y genera eventos
      (creación, modificación, borrado, movimiento, etc.). [web:34][web:69]
  - watchdog.events.PatternMatchingEventHandler:
      Handler que filtra eventos por patrón de nombre (en este caso "*.pdf")
      e ignora directorios. [web:13][web:15]
  - Flask application context:
      El watcher corre en un hilo externo al servidor HTTP, por lo que
      se necesita `with app.app_context()` para poder usar:
        · app.logger
        · current_app
        · configuración
        · extensiones (db, etc.). [web:70]
"""

import os

from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

from flask import current_app
from watchers.utils_async import procesar_pdf_inicial


# =============================================================================
# 1️⃣ RUTAS BÁSICAS · CARPETA INICIAL
# =============================================================================
# Este watcher está pensado para ejecutarse dentro del proyecto Flask.
# Se parte de la ubicación de este archivo:
#   watchers/bandeja_inicial_watcher.py
# y se sube dos niveles para llegar a la raíz del proyecto:
#   watchers/
#   <root_path>/ (p.ej. C:\Users\thier\Desktop\tubby_app)
#
# A partir de ahí, se define la carpeta física de bandeja general:
#   <root_path>/carpeta_inicial_pdf
#
# Esa carpeta es donde otros procesos (usuarios, importadores, scripts)
# dejan los PDFs que deben clasificarse (contenedores, obras, terrazas, vados, otros).
# =============================================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARPETA_INICIAL = os.path.join(BASE_DIR, "carpeta_inicial_pdf")


# =============================================================================
# 2️⃣ ESTADO GLOBAL DEL WATCHER
# =============================================================================
# El watcher se basa en un Observer (hilo background) que queda vivo mientras
# el proceso Flask esté en ejecución.
#
# - watcher_inicial_activo:
#       bandera booleana para evitar arrancar múltiples observers sobre la
#       misma carpeta (carpeta_inicial_pdf).
# - observer_inicial:
#       referencia al objeto Observer para mantenerlo en vida y, si lo deseas,
#       pararlo en algún shutdown controlado.
#
# IMPORTANTE:
#   - Estas variables viven en memoria del proceso (no en la base de datos).
#   - Si usas varios workers (uWSGI, Gunicorn con múltiples procesos),
#     cada proceso puede tener su propio watcher; conviene coordinarlos
#     si no quieres comportamiento duplicado.
# =============================================================================

watcher_inicial_activo = False
observer_inicial = None


# =============================================================================
# 3️⃣ HANDLER · SOLO ARCHIVOS *.pdf EN CARPETA_INICIAL
# =============================================================================
# watchdog ofrece distintos tipos de handlers:
#   - FileSystemEventHandler (genérico)
#   - LoggingEventHandler (solo log)
#   - PatternMatchingEventHandler (filtra por patrón de nombre)
#
# Aquí usamos PatternMatchingEventHandler para:
#   - Escuchar SOLO creaciones de archivos que encajen con el patrón "*.pdf".
#   - Ignorar directorios (subcarpetas).
#
# El método clave es on_created(self, event), que watchdog llama cuando
# detecta que se ha creado un nuevo archivo en la carpeta vigilada. [web:13][web:34]
# =============================================================================


class BandejaInicialHandler(PatternMatchingEventHandler):
    """
    Handler especializado para la BANDEJA INICIAL de PDFs.

    RESPONSABILIDADES:
      - Filtrar eventos a ficheros con extensión .pdf.
      - Ignorar cualquier directorio.
      - Por cada nuevo PDF en `carpeta_inicial_pdf`:
          1. Entrar en contexto de aplicación Flask.
          2. Registrar en el log que se ha detectado el PDF.
          3. Llamar a `procesar_pdf_inicial(nombre_pdf)` para que:
               · lea el PDF,
               · lo clasifique (contenedores/obras/terrazas/vados/otros),
               · lo mueva a la carpeta entrada_pdf del módulo correspondiente,
               · y devuelva un dict con el resultado.

    Este handler NO contiene lógica de negocio de vía pública.
    Su único cometido es "recibir evento de creación" y delegar el trabajo.
    """

    def __init__(self, app):
        """
        Constructor del handler.

        Parámetros:
          - app: instancia de Flask, necesaria para:
              · app.app_context() (contexto de aplicación),
              · app.logger (registro estructurado),
              · acceso a configuración/extensiones si fuese necesario.

        Configuración:
          - patterns=["*.pdf"]:
              solo se procesan archivos cuyo nombre termine en ".pdf".
          - ignore_directories=True:
              se descartan eventos que afecten a carpetas.
        """
        super().__init__(patterns=["*.pdf"], ignore_directories=True)
        self.app = app

    def on_created(self, event):
        """
        Método llamado automáticamente por watchdog cuando se crea
        un nuevo archivo en la carpeta vigilada que cumple el patrón.

        Flujo:
          1. Ignora eventos de directorios (defensa extra).
          2. Obtiene ruta absoluta del PDF y su nombre físico.
          3. Entra en contexto de aplicación Flask:
               · necesario para usar app.logger, current_app, etc. en un hilo.
          4. Loguea la detección del PDF.
          5. Invoca procesar_pdf_inicial(nombre_pdf) y recoge su resultado.
          6. Loguea el resultado (estado, motivo, tipo, rutas).
        """
        # 3.1️⃣ Seguridad adicional: aunque ignore_directories=True ya filtra,
        # volvemos a comprobar que el evento no es de una carpeta.
        if event.is_directory:
            return

        # 3.2️⃣ Ruta y nombre del PDF recién creado.
        ruta_pdf = event.src_path
        nombre_pdf = os.path.basename(ruta_pdf)

        # 3.3️⃣ Contexto de aplicación Flask en hilo watchdog.
        # Flask no ve este código como parte de una petición HTTP estándar;
        # por eso necesitamos abrir el contexto manualmente para acceder
        # a app.logger y demás. [web:70]
        with self.app.app_context():
            # Log de detección en la bandeja inicial.
            self.app.logger.info(
                f"[WATCHER_INICIAL] PDF detectado en carpeta_inicial_pdf: {ruta_pdf}"
            )

            # Delegar toda la lógica en utils_async.procesar_pdf_inicial():
            #   - clasificación (contenedores / obras / terrazas / vados / otros),
            #   - movimiento a la carpeta entrada_pdf correspondiente,
            #   - ejecución del backend industrial de cada módulo cuando exista.
            resultado = procesar_pdf_inicial(nombre_pdf)

            # Log del resultado devuelto por la lógica industrial.
            # Se incluyen campos clave para trazabilidad:
            #   - estado: ok / error / pendiente / etc.
            #   - motivo: texto explicativo.
            #   - tipo: tipo de expediente detectado.
            #   - ruta_final_pdf: dónde ha acabado el PDF.
            #   - ruta_csv: CSV asociado si aplica (contenedores) o None.
            self.app.logger.info(
                "[WATCHER_INICIAL] Resultado procesar_pdf_inicial -> "
                f"estado={resultado.get('estado')} "
                f"motivo={resultado.get('motivo')} "
                f"tipo={resultado.get('tipo')} "
                f"ruta_final_pdf={resultado.get('ruta_final_pdf')} "
                f"ruta_csv={resultado.get('ruta_csv')}"
            )


# =============================================================================
# 4️⃣ FUNCIÓN PÚBLICA DE ARRANQUE · iniciar_watcher_carpeta_inicial
# =============================================================================
# Esta función se concibe como punto único de arranque del watcher desde
# la app Flask (por ejemplo, en el factory o en un hook de inicio).
#
# Características:
#   - Solo arranca el watcher una vez (usa watcher_inicial_activo).
#   - Crea la carpeta física `carpeta_inicial_pdf` si no existe.
#   - Construye el handler y el observer de watchdog.
#   - Programa la vigilancia sobre CARPETA_INICIAL (no recursivo).
#   - Arranca el hilo observer.start().
#   - Registra logs de inicio para diagnóstico.
#
# IMPORTANTE:
#   - El observer corre en un hilo paralelo al servidor web.
#   - No bloquea el manejo de peticiones HTTP.
#   - Si el proceso se detiene, el observer se detiene con él.
# =============================================================================


def iniciar_watcher_carpeta_inicial(app):
    """
    Arranca el watcher de la carpeta_inicial_pdf SI AÚN NO ESTÁ ACTIVO.

    Parámetros:
      - app: instancia de Flask desde la que se arranca el watcher.

    Flujo:
      1) Comprueba watcher_inicial_activo:
           - Si True → se registra en log y se retorna sin hacer nada.
           - Si False → continúa con el arranque.
      2) Crea la carpeta física CARPETA_INICIAL si no existe.
      3) Instancia el BandejaInicialHandler(app).
      4) Crea observer_inicial = Observer().
      5) Asocia observer_inicial.schedule(handler, CARPETA_INICIAL, recursive=False).
      6) Arranca observer_inicial.start().
      7) Marca watcher_inicial_activo = True.
      8) Registra en log las rutas vigiladas.
    """
    global watcher_inicial_activo, observer_inicial

    # 4.1️⃣ No reiniciar si ya está activo.
    if watcher_inicial_activo:
        app.logger.info(
            "ℹ Watcher de carpeta_inicial_pdf ya estaba activo; no se reinicia"
        )
        return

    # 4.2️⃣ Garantizar existencia de la carpeta física de bandeja inicial.
    os.makedirs(CARPETA_INICIAL, exist_ok=True)

    # 4.3️⃣ Crear handler especializado para PDFs en bandeja inicial.
    handler = BandejaInicialHandler(app)

    # 4.4️⃣ Crear observer (hilo watchdog).
    observer_inicial = Observer()

    # 4.5️⃣ Programar vigilancia:
    #   - path=CARPETA_INICIAL: solo esta carpeta.
    #   - recursive=False: no se vigilan subcarpetas.
    observer_inicial.schedule(handler, path=CARPETA_INICIAL, recursive=False)

    # 4.6️⃣ Arrancar el hilo de observación.
    observer_inicial.start()

    # 4.7️⃣ Marcar el watcher como activo.
    watcher_inicial_activo = True

    # 4.8️⃣ Logs de arranque para trazabilidad.
    app.logger.info(f"🚀 Watcher inicial iniciado: {CARPETA_INICIAL}")
    app.logger.info(f"👁 [carpeta_inicial_pdf] Vigilando carpeta: {CARPETA_INICIAL}")