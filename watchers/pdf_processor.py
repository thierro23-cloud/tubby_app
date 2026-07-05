# =============================================================================
# ⚙️ MÓDULO · PROCESADO ASÍNCRONO DE PDFs
# =============================================================================
# Este módulo proporciona una pequeña utilidad genérica para ejecutar
# el procesado de un PDF en segundo plano usando un pool de hilos
# (ThreadPoolExecutor).
#
# 🎯 OBJETIVO:
#   - Evitar bloquear el hilo principal de la aplicación Flask cuando
#     se procesan PDFs pesados (lectura, OCR, acceso a BD, etc.).
#   - Encapsular el patrón:
#       · Entrar en app.app_context().
#       · Loguear inicio / fin del procesado.
#       · Llamar a una función de negocio pasada como parámetro.
#       · Capturar y loguear cualquier excepción.
#
# 🧩 USO TÍPICO:
#   - Otros módulos pueden importar esta función y pasarle la lógica de
#     negocio que corresponda. Ejemplo clásico (patrón antiguo):
#
#       from watchers.procesador_async_pdfs import procesar_pdf_async
#
#       def on_created(...):
#           procesar_pdf_async(self.app, ruta_pdf, procesar_pdf_contenedor)
#
#   - En la arquitectura nueva de contenedores se ha optado por
#     centralizar la lógica en watchers.utils_async + backend_contenedores.
#     Aun así, este módulo sigue estando disponible para cualquier otro
#     watcher o flujo que quiera ejecutar trabajo pesado en segundo plano.
# =============================================================================


# =============================================================================
# 1️⃣ IMPORTS Y POOL DE HILOS
# =============================================================================
# 1.1) Imports estándar y Flask (COMIENZA)
# -----------------------------------------------------------------------------
#   - concurrent.futures.ThreadPoolExecutor:
#       · Pool de hilos para ejecutar tareas en paralelo sin bloquear
#         el hilo principal.
#   - flask.current_app:
#       · Para acceder al logger de la app dentro del contexto.
# -----------------------------------------------------------------------------
import concurrent.futures

from flask import current_app
# 1.1) Imports estándar y Flask (TERMINA)
# -----------------------------------------------------------------------------

# 1.2) Creación del ThreadPoolExecutor (COMIENZA)
# -----------------------------------------------------------------------------
# Creamos un pool de hilos a nivel de módulo para reutilizarlo en todas
# las llamadas a procesar_pdf_async. El parámetro max_workers se puede
# ajustar según la carga esperada del servidor.
# -----------------------------------------------------------------------------
executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
# 1.2) Creación del ThreadPoolExecutor (TERMINA)
# -----------------------------------------------------------------------------


# =============================================================================
# 2️⃣ FUNCIÓN GENÉRICA PARA PROCESAR UN PDF EN SEGUNDO PLANO
# =============================================================================
# 2.1) procesar_pdf_async(app, ruta_pdf, funcion_procesado) (COMIENZA)
# -----------------------------------------------------------------------------
# Esta función:
#   - Recibe:
#       · app:
#           Instancia de Flask (para usar app.app_context()).
#       · ruta_pdf:
#           Ruta (string) al PDF que se quiere procesar.
#       · funcion_procesado:
#           Función de negocio que recibe (app, ruta_pdf) y se encarga de:
#             · leer / parsear el PDF,
#             · actualizar la BD,
#             · mover el archivo a la carpeta que corresponda.
#
#   - Crea una tarea interna (tarea) que:
#       · Entra en app.app_context().
#       · Loguea el inicio del procesamiento en segundo plano.
#       · Llama a funcion_procesado(app, ruta_pdf).
#       · Captura y loguea cualquier excepción con traceback completo.
#
#   - Envía esa tarea al pool de hilos con executor.submit(), sin
#     bloquear el hilo llamante.
#
# USO CLÁSICO (PATRÓN ANTIGUO):
#   - Desde un watcher simple:
#
#         from watchers.procesador_async_pdfs import procesar_pdf_async
#
#         def on_created(self, event):
#             if event.is_directory:
#                 return
#             ruta_pdf = event.src_path
#             procesar_pdf_async(self.app, ruta_pdf, procesar_pdf_contenedor)
#
#   - Donde procesar_pdf_contenedor(app, ruta_pdf) es tu lógica de negocio.
#
# NOTA:
#   - En la arquitectura ACTUAL para contenedores se está usando
#     watchers.utils_async.procesar_pdf_entrada(nombre_pdf) directamente
#     desde el watcher, delegando allí tanto el backend industrial como
#     el movimiento de archivos y la creación de pendientes.
#   - Este helper sigue siendo útil para otros módulos que quieran
#     aplicar el mismo patrón asíncrono.
# -----------------------------------------------------------------------------
def procesar_pdf_async(app, ruta_pdf, funcion_procesado):
    """
    Ejecuta funcion_procesado(app, ruta_pdf) en un hilo del pool, con contexto
    de Flask y logging de inicio / fin / errores.
    """

    def tarea():
        """Tarea que se ejecutará en un hilo del pool."""
        with app.app_context():
            try:
                current_app.logger.info(
                    "⚡ Procesando PDF en hilo: %s",
                    ruta_pdf,
                )

                # IMPORTANTE:
                #   - funcion_procesado debe aceptar (app, ruta_pdf)
                #     para ser compatible con el patrón clásico de
                #     lógica de negocio en watchers.
                funcion_procesado(app, ruta_pdf)

                current_app.logger.info(
                    "✅ Procesado PDF en hilo completado: %s",
                    ruta_pdf,
                )

            except Exception:
                # logger.exception captura el traceback completo
                current_app.logger.exception(
                    "❌ Error procesando PDF en hilo: %s",
                    ruta_pdf,
                )

    # Enviamos la tarea al pool sin bloquear el hilo llamante
    executor.submit(tarea)
# 2.1) procesar_pdf_async(app, ruta_pdf, funcion_procesado) (TERMINA)
# -----------------------------------------------------------------------------


# =============================================================================
# 3️⃣ FIN · watchers/procesador_async_pdfs.py
# =============================================================================