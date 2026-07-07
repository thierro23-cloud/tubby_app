# =============================================================================
# 👀 WATCHERS MANAGER PRO
# =============================================================================

import importlib
import os

WATCHERS = []


def cargar_watchers():
    base_path = os.path.dirname(__file__)

    for file in os.listdir(base_path):

        if file.endswith("_watcher.py"):

            module_name = f"watchers.{file[:-3]}"

            try:
                module = importlib.import_module(module_name)

                if hasattr(module, "Watcher"):
                    WATCHERS.append(module.Watcher())

                    print(f"👀 Watcher cargado: {module_name}")

            except Exception as e:
                print(f"❌ Error watcher {module_name}: {e}")

    return WATCHERS


def iniciar_watchers(app):
    activos = []

    for watcher in WATCHERS:

        try:
            watcher.start(app)
            activos.append(watcher.nombre)

            print(f"🚀 Watcher iniciado: {watcher.nombre}")

        except Exception as e:
            print(f"❌ Error iniciando watcher {watcher.nombre}: {e}")

    return activos
