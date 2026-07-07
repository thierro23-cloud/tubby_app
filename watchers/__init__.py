import os
import importlib
from flask import Flask

# =============================================================================
# 1️⃣ INTRODUCCIÓN · GESTOR DE WATCHERS Y COLA VIEJA DE PDFs
# =============================================================================
# Este módulo implementa dos piezas clave:
#
#   1.1) procesar_pdfs_existentes(app)
#        - Escanea la carpeta de ENTRADA de contenedores al arrancar
#          la app y procesa todos los PDFs que ya están allí ("cola vieja").
#
#   1.2) iniciar_watchers(app)
#        - Busca módulos watcher_*.py en la carpeta watchers/ y, si exponen
#          una función de inicio estándar, la ejecuta (permite añadir nuevos
#          watchers sin tocar app.py).
#
# 🎯 OBJETIVO:
#   - Unificar el tratamiento de PDFs de contenedores para que:
#       · La COLA VIEJA se lea desde la MISMA carpeta que el watcher
#         en tiempo real (entrada_pdf).
#       · Se use la MISMA lógica de negocio industrial (procesar_pdf_core)
#         encapsulada en watchers.utils_async.procesar_pdf_entrada(), tanto
#         para la cola vieja como para el watcher.
#
# 🏭 PENSANDO EN PRODUCCIÓN:
#   - Las rutas se calculan de forma relativa a la raíz del proyecto
#     (tubby_app), por lo que basta con replicar la misma estructura:
#
#       tubby_app/
#           app.py
#           watchers/
#               __init__.py          ← ESTE archivo
#               contenedores_watcher.py
#               utils_async.py
#           contenedores/
#               entrada_pdf/
#               papelera/
#               para_revision/
#               pendientes_validacion/
#
#   - Al desplegar en servidor, no es necesario cambiar código:
#       · Solo copiar la estructura.
#       · Arrancar con un WSGI server (ej: gunicorn "app:app").
# =============================================================================


# =============================================================================
# 2️⃣ IMPORTS LAZIES · EVITAR IMPORTS CIRCULARES
# =============================================================================
# IMPORTANTE:
#   - NO importamos contenedores_watcher ni utils_async a nivel de módulo
#     para evitar ciclos:
#
#       app.py → importa watchers.contenedores_watcher
#       watchers.__init__ → importaba contenedores_watcher
#       contenedores_watcher → importaba watchers.utils_async
#
#     Esto daba el ImportError.
#
#   - En su lugar, definimos helpers que hacen imports PEREZOSOS dentro
#     de las funciones que los necesitan.
# =============================================================================


def _get_carpeta_entrada() -> str:
    """
    Helper interno para obtener CARPETA_ENTRADA desde contenedores_watcher
    sin crear imports circulares.
    """
    from watchers.contenedores_watcher import CARPETA_ENTRADA

    return CARPETA_ENTRADA


def _procesar_pdf_entrada(nombre_pdf: str):
    """
    Helper interno para llamar a watchers.utils_async.procesar_pdf_entrada
    sin importar utils_async a nivel de módulo.
    """
    from watchers.utils_async import procesar_pdf_entrada

    return procesar_pdf_entrada(nombre_pdf)


# =============================================================================
# 3️⃣ PROCESAR PDFs EXISTENTES · COLA VIEJA DESDE ENTRADA_PDF
# =============================================================================


def procesar_pdfs_existentes(app: Flask):
    """
    Escanea la carpeta de ENTRADA de contenedores (CARPETA_ENTRADA) al
    arrancar la app y procesa todos los PDFs que ya estén allí ("cola vieja"),
    usando la misma lógica que el watcher en tiempo real.
    """
    from watchers.contenedores_watcher import CARPETA_ENTRADA  # import lazy

    # Verificar que existe la carpeta de entrada
    if not os.path.isdir(CARPETA_ENTRADA):
        app.logger.warning(
            "⚠️ Carpeta de entrada de contenedores no existe: %s",
            CARPETA_ENTRADA,
        )
        return

    app.logger.info(
        "🔎 Escaneando PDFs existentes en carpeta de entrada: %s",
        CARPETA_ENTRADA,
    )

    for archivo in os.listdir(CARPETA_ENTRADA):
        # Solo archivos PDF (ignoramos otros tipos)
        if not archivo.lower().endswith(".pdf"):
            continue

        ruta_pdf = os.path.join(CARPETA_ENTRADA, archivo)

        try:
            app.logger.info(
                "📄 Procesando PDF existente (cola vieja): %s",
                ruta_pdf,
            )

            # Entramos en contexto de app para poder usar:
            #   - logs de app
            #   - conexiones a BD
            #   - cualquier otro recurso de Flask
            with app.app_context():
                # Usamos la misma lógica que el watcher:
                #   - procesar_pdf_entrada(nombre_pdf)
                #     se encarga de llamar al backend industrial,
                #     mover el PDF y crear pendientes si es necesario.
                from watchers.utils_async import procesar_pdf_entrada  # import lazy

                resultado = procesar_pdf_entrada(archivo)

                app.logger.info(
                    "[COLA_VIEJA] Resultado procesar_pdf_entrada -> "
                    f"estado={resultado.get('estado')} "
                    f"motivo={resultado.get('motivo')} "
                    f"id_pendiente={resultado.get('id_pendiente')} "
                    f"ruta_final_pdf={resultado.get('ruta_final_pdf')}"
                )

        except Exception as e:
            app.logger.error(
                "❌ Error procesando PDF existente %s: %s",
                ruta_pdf,
                e,
            )


# =============================================================================
# 4️⃣ CARGAR WATCHERS GENÉRICOS · watcher_*.py
# =============================================================================


def iniciar_watchers(app: Flask):
    """
    Busca ficheros watcher_*.py dentro de la carpeta watchers/ e intenta
    iniciar cualquier watcher adicional que siga esta convención:
      - Nombre de archivo: watcher_lo_que_sea.py
      - Debe definir al menos una función estándar:
            iniciar_watcher_contenedores(app)
    """

    carpeta_watchers = os.path.join(os.path.dirname(__file__))

    app.logger.info(
        "🔎 Buscando watchers en: %s",
        carpeta_watchers,
    )

    for archivo in os.listdir(carpeta_watchers):
        # Necesitamos archivos watcher_*.py
        if not archivo.startswith("watcher_"):
            continue

        if not archivo.endswith(".py"):
            continue

        nombre_modulo = f"watchers.{archivo[:-3]}"

        try:
            modulo = importlib.import_module(nombre_modulo)

            # Convención actual:
            #   - Si el módulo define iniciar_watcher_contenedores(app),
            #     lo llamamos.
            if hasattr(modulo, "iniciar_watcher_contenedores"):
                modulo.iniciar_watcher_contenedores(app)

                app.logger.info(
                    "👀 Watcher iniciado desde módulo: %s",
                    nombre_modulo,
                )
            else:
                app.logger.info(
                    "ℹ Módulo %s no define iniciar_watcher_contenedores(app); se ignora",
                    nombre_modulo,
                )

        except Exception as e:
            app.logger.error(
                "❌ Error iniciando watcher %s: %s",
                nombre_modulo,
                e,
            )


# =============================================================================
# 5️⃣ FIN · watchers/__init__.py (COLA VIEJA + WATCHERS GENÉRICOS)
# =============================================================================
