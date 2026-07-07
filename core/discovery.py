# core/discovery.py
# =============================================================================
# 🧠 DISCOVERY PROFESIONAL · PANEL / MÓDULO / BOTONES POR CONVENCIÓN
# =============================================================================
#
# Convenciones:
#   - Blueprint panel:  panel_xxx_bp
#   - Vistas de módulo: modulo_xxx_yyyy...
#   - Vistas botón:     btn_yyyy_zzzz...
#
# Resultado:
#   [
#     {
#       "panel": "control_via_publica",
#       "modulos": [
#         {
#           "nombre": "contenedores",
#           "endpoints_modulo": [...],
#           "botones": [...]
#         },
#         ...
#       ]
#     },
#     ...
#   ]
# =============================================================================

from flask import current_app


def descubrir_sistema():
    """
    Escanea current_app.url_map y construye la estructura jerárquica:

        panel → módulos → botones

    usando exclusivamente las convenciones de nombres indicadas.
    """

    # panel_id -> { "panel": str, "modulos": { modulo_id: {...} } }
    sistema = {}

    # 1️⃣ PRIMER PASO: detectar paneles a partir de blueprints panel_xxx_bp
    for bp_name, bp in current_app.blueprints.items():
        if bp_name.startswith("panel_") and bp_name.endswith("_bp"):
            panel_id = bp_name.replace("panel_", "", 1).replace("_bp", "")
            if panel_id not in sistema:
                sistema[panel_id] = {"panel": panel_id, "modulos": {}}

    # 2️⃣ SEGUNDO PASO: recorrer TODAS las reglas de URL
    for rule in current_app.url_map.iter_rules():
        endpoint = rule.endpoint  # ej: "contenedores_bp.btn_contenedores_listado"
        if endpoint == "static":
            continue

        partes = endpoint.split(".")
        if len(partes) != 2:
            continue

        bp_name, func_name = partes
        url = str(rule)
        metodos = list(rule.methods)

        # ---------------------------------------------------------------------
        # 2.1️⃣ MÓDULOS: funciones modulo_xxx_yyyy...
        # ---------------------------------------------------------------------
        if func_name.startswith("modulo_"):
            # Ej: modulo_control_via_publica_contenedores
            resto = func_name.replace(
                "modulo_", "", 1
            )  # control_via_publica_contenedores
            trozos = resto.split("_")
            if len(trozos) < 2:
                continue

            # panel_id = todo menos el último fragmento
            panel_id = "_".join(trozos[:-1])  # control_via_publica
            modulo_id = trozos[-1]  # contenedores

            panel = sistema.setdefault(panel_id, {"panel": panel_id, "modulos": {}})

            modulo = panel["modulos"].setdefault(
                modulo_id, {"nombre": modulo_id, "endpoints_modulo": [], "botones": []}
            )

            modulo["endpoints_modulo"].append(
                {
                    "url": url,
                    "endpoint": endpoint,
                    "metodos": metodos,
                }
            )

        # ---------------------------------------------------------------------
        # 2.2️⃣ BOTONES: funciones btn_yyyy_zzzz...
        # ---------------------------------------------------------------------
        if func_name.startswith("btn_"):
            # Ej: btn_contenedores_listado → modulo_id = contenedores
            resto = func_name.replace("btn_", "", 1)  # contenedores_listado
            modulo_id = resto.split("_", 1)[0]  # contenedores

            # El botón se asocia a TODOS los paneles que tengan este módulo
            for panel in sistema.values():
                if modulo_id in panel["modulos"]:
                    panel["modulos"][modulo_id]["botones"].append(
                        {
                            "nombre": func_name,
                            "url": url,
                            "endpoint": endpoint,
                            "metodos": metodos,
                        }
                    )

    # 3️⃣ Convertir modulos dict → lista para facilitar las plantillas
    paneles = []
    for panel in sistema.values():
        panel["modulos"] = list(panel["modulos"].values())
        paneles.append(panel)

    return paneles
