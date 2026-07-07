# watch_endpoints.py
"""
Sistema de vigilancia automática de endpoints Flask.

INTEGRACIÓN CON TU PROYECTO:
    - Compatible con tu estructura de config.py
    - Usa DATABASES["bd_tbl_comunes"] automáticamente
    - Respeta tu configuración de múltiples bases de datos

Este script detecta automáticamente cambios en archivos .py del proyecto
y sincroniza los endpoints con la base de datos en tiempo real.

Uso:
    python watch_endpoints.py

Detener:
    Ctrl+C

Autor: Sistema de vigilancia automática
Fecha: 2026-05-22
"""

import time
import os
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Importar funciones del módulo de sincronización
from sync_endpoints import get_flask_app, extract_endpoints, sync_to_database

# Importar configuración
from config import WatcherConfig

# ============================================================
# CONFIGURACIÓN DEL SISTEMA DE LOGGING
# ============================================================


def setup_logging():
    """
    Configura el sistema de logging dual (consola + archivo).

    Returns:
        Logger: Instancia configurada del logger

    Usa la configuración de WatcherConfig:
        - LOG_FILE: archivo donde se guardan los logs
        - LOG_FORMAT: formato de las entradas
        - LOG_LEVEL: nivel de detalle
    """

    # Crear logger principal
    logger = logging.getLogger("EndpointWatcher")
    logger.setLevel(getattr(logging, WatcherConfig.LOG_LEVEL))

    # Limpiar handlers previos
    logger.handlers.clear()

    # Handler 1: Archivo de log (registro completo)
    file_handler = logging.FileHandler(WatcherConfig.LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        WatcherConfig.LOG_FORMAT, WatcherConfig.LOG_DATE_FORMAT
    )
    file_handler.setFormatter(file_formatter)

    # Handler 2: Consola (registro simplificado)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)

    # Añadir ambos handlers al logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# ============================================================
# CLASE DE VIGILANCIA DE ARCHIVOS
# ============================================================


class EndpointFileWatcher(FileSystemEventHandler):
    """
    Vigila cambios en archivos Python y sincroniza endpoints automáticamente.

    Attributes:
        app (Flask): Instancia de la aplicación Flask
        project_path (str): Ruta raíz del proyecto a vigilar
        logger (Logger): Sistema de logging configurado
        last_sync (float): Timestamp de la última sincronización
        debounce_seconds (int): Segundos mínimos entre sincronizaciones
    """

    def __init__(self, app, project_path, logger):
        """
        Inicializa el watcher.

        Args:
            app (Flask): Instancia de Flask
            project_path (str): Directorio a vigilar
            logger (Logger): Sistema de logging
        """
        self.app = app
        self.project_path = project_path
        self.logger = logger
        self.last_sync = 0
        self.debounce_seconds = WatcherConfig.DEBOUNCE_SECONDS

    def _should_process(self, file_path):
        """
        Determina si un archivo debe procesarse o ignorarse.

        Args:
            file_path (str): Ruta completa del archivo

        Returns:
            bool: True si debe procesarse, False si debe ignorarse
        """
        # Verificar extensión .py
        if not file_path.endswith(".py"):
            return False

        # Ignorar __pycache__
        if "__pycache__" in file_path:
            return False

        # Ignorar archivos compilados
        if file_path.endswith((".pyc", ".pyo")):
            return False

        # Ignorar backups
        if file_path.endswith((".py~", ".bak")):
            return False

        return True

    def _can_sync(self):
        """
        Verifica si puede ejecutar una nueva sincronización (debouncing).

        Returns:
            bool: True si han pasado suficientes segundos desde la última sync
        """
        current_time = time.time()
        elapsed = current_time - self.last_sync
        return elapsed > self.debounce_seconds

    def on_modified(self, event):
        """
        Evento: Se modificó un archivo.

        Args:
            event: Objeto de evento de watchdog
        """
        if not self._should_process(event.src_path):
            return

        if not self._can_sync():
            return

        file_name = os.path.basename(event.src_path)
        self.logger.info(f"📝 Cambio detectado en: {file_name}")
        self._sync_endpoints()

    def on_created(self, event):
        """
        Evento: Se creó un nuevo archivo.

        Args:
            event: Objeto de evento de watchdog
        """
        if not self._should_process(event.src_path):
            return

        file_name = os.path.basename(event.src_path)
        self.logger.info(f"📄 Nuevo archivo creado: {file_name}")
        self._sync_endpoints()

    def on_deleted(self, event):
        """
        Evento: Se eliminó un archivo.

        Args:
            event: Objeto de evento de watchdog
        """
        if not self._should_process(event.src_path):
            return

        file_name = os.path.basename(event.src_path)
        self.logger.warning(f"🗑️ Archivo eliminado: {file_name}")
        self._sync_endpoints()

    def _sync_endpoints(self):
        """
        Ejecuta la sincronización de endpoints con manejo completo de errores.
        """
        try:
            self.logger.info("🔄 Iniciando sincronización...")

            # Extraer endpoints de Flask
            endpoints = extract_endpoints(self.app)

            # Sincronizar con base de datos (pasando app para config)
            result = sync_to_database(endpoints, self.app, self.logger)

            # Registrar resultado
            if result["success"]:
                self.logger.info(
                    f"✓ Sincronización completada: "
                    f"{result['inserted']} nuevos, "
                    f"{result['updated']} actualizados, "
                    f"{result['deactivated']} desactivados"
                )
            else:
                self.logger.error(f"✗ Error en sincronización: {result['error']}")

            # Actualizar timestamp
            self.last_sync = time.time()

        except Exception as e:
            self.logger.error(
                f"✗ Excepción durante sincronización: {str(e)}", exc_info=True
            )


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================


def main():
    """
    Función principal del sistema de vigilancia.
    """
    observer = None

    try:
        # Paso 1: Configurar logging
        logger = setup_logging()

        logger.info("=" * 70)
        logger.info("SISTEMA DE VIGILANCIA DE ENDPOINTS - INICIANDO")
        logger.info("=" * 70)

        # Paso 2: Cargar aplicación Flask
        logger.info("Paso 1/4: Cargando aplicación Flask...")
        app = get_flask_app()
        logger.info("  ✓ Aplicación Flask cargada correctamente")

        # Mostrar configuración de BD
        logger.info(f"  ✓ Base de datos: {WatcherConfig.ENDPOINTS_DATABASE}")
        logger.info(f"  ✓ Tabla: {WatcherConfig.ENDPOINTS_TABLE}")

        # Paso 3: Sincronización inicial
        logger.info("Paso 2/4: Ejecutando sincronización inicial...")
        endpoints = extract_endpoints(app)
        logger.info(f"  ✓ Encontrados {len(endpoints)} endpoints")

        result = sync_to_database(endpoints, app, logger)

        if result["success"]:
            logger.info(
                f"  ✓ Sincronización inicial exitosa: "
                f"{result['inserted']} nuevos, "
                f"{result['updated']} actualizados"
            )
        else:
            logger.error(f"  ✗ Error en sincronización inicial: {result['error']}")

        # Paso 4: Configurar y arrancar watcher
        logger.info("Paso 3/4: Configurando vigilancia de archivos...")

        project_path = os.getcwd()
        event_handler = EndpointFileWatcher(app, project_path, logger)
        observer = Observer()
        observer.schedule(
            event_handler, path=project_path, recursive=WatcherConfig.WATCH_RECURSIVE
        )
        observer.start()

        logger.info(f"  ✓ Vigilando: {project_path}")
        logger.info(
            f"  ✓ Modo recursivo: {'Sí' if WatcherConfig.WATCH_RECURSIVE else 'No'}"
        )
        logger.info(f"  ✓ Archivo de log: {os.path.abspath(WatcherConfig.LOG_FILE)}")
        logger.info(f"  ✓ Debounce: {WatcherConfig.DEBOUNCE_SECONDS} segundos")

        # Paso 5: Mantener ejecución
        logger.info("Paso 4/4: Iniciando vigilancia continua...")
        logger.info("=" * 70)
        logger.info("✓ WATCHER ACTIVO - Presiona Ctrl+C para detener")
        logger.info("=" * 70)
        logger.info("")

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        if "logger" in locals():
            logger.info("")
            logger.info("=" * 70)
            logger.info("🛑 Señal de interrupción recibida (Ctrl+C)")
            logger.info("Deteniendo watcher...")
        else:
            print("\n🛑 Deteniendo watcher...")

    except Exception as e:
        if "logger" in locals():
            logger.error(f"✗ Error fatal: {str(e)}", exc_info=True)
        else:
            print(f"✗ Error fatal: {str(e)}")
            import traceback

            traceback.print_exc()

    finally:
        if observer:
            observer.stop()
            observer.join()

            if "logger" in locals():
                logger.info("✓ Watcher detenido correctamente")
                logger.info("=" * 70)
                logger.info("FIN DE EJECUCIÓN")
                logger.info("=" * 70)
            else:
                print("✓ Watcher detenido correctamente")


# ============================================================
# PUNTO DE ENTRADA
# ============================================================

if __name__ == "__main__":
    main()
