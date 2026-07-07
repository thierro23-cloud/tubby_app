# ================================================================
# 🔎 HELPER ESTADO DEL SISTEMA
# Archivo: blueprints/super_admin/helpers_estado_sistema.py
# ================================================================

# ================================================================
# 1️⃣ IMPORTACIONES
# ================================================================

from flask import current_app
import os
import platform
import psutil

# ================================================================
# 2️⃣ FUNCIÓN PRINCIPAL
# obtener_estado_sistema()
# ================================================================


def obtener_estado_sistema():
    """
    Devuelve un diccionario con el estado global del sistema
    para el panel de administración.
    """

    # ------------------------------------------------------------
    # 2.1 BLUEPRINTS CARGADOS
    # ------------------------------------------------------------

    blueprints = list(current_app.blueprints.keys())

    # ------------------------------------------------------------
    # 2.2 RUTAS REGISTRADAS
    # ------------------------------------------------------------

    rutas = [rule.rule for rule in current_app.url_map.iter_rules()]

    # ------------------------------------------------------------
    # 2.3 WATCHERS ACTIVOS
    # ------------------------------------------------------------

    watchers = current_app.config.get("WATCHERS_ACTIVOS", [])

    # ------------------------------------------------------------
    # 2.4 CARPETAS MONITORIZADAS
    # ------------------------------------------------------------

    carpetas = current_app.config.get("WATCHERS_CARPETAS", [])

    # ------------------------------------------------------------
    # 2.5 ESTADO DEL SERVIDOR
    # ------------------------------------------------------------

    proceso = psutil.Process(os.getpid())

    servidor = {
        "pid": proceso.pid,
        "cpu": psutil.cpu_percent(),
        "memoria": proceso.memory_info().rss // (1024 * 1024),
        "python": platform.python_version(),
        "sistema": platform.system(),
    }

    # ------------------------------------------------------------
    # 2.6 ESTRUCTURA FINAL
    # ------------------------------------------------------------

    estado = {
        "watchers_total": len(watchers),
        "watchers": watchers,
        "blueprints_total": len(blueprints),
        "blueprints": blueprints,
        "rutas_total": len(rutas),
        "rutas": rutas,
        "carpetas_total": len(carpetas),
        "carpetas": carpetas,
        "servidor": servidor,
    }

    return estado
