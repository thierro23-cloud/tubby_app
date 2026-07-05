def _construir_modulos_lista():
    """
    Detecta módulos a nivel global:
      - blueprint: panel_*_bp  (módulos de primer nivel, tipo 'modulo_control_vias_publicas')
      - view:      modulo_*
    Devuelve lista de dicts listos para pintar.
    """
    app = current_app
    modulos_lista: list[dict] = []

    for rule in app.url_map.iter_rules():
        endpoint = rule.endpoint  # ej: 'panel_control_vias_publicas_bp.modulo_control_vias_publicas'
        ruta = str(rule.rule)

        if endpoint.startswith("static"):
            continue

        partes = endpoint.split(".", 1)
        if len(partes) == 2:
            bp_name, view_name = partes
        else:
            bp_name, view_name = None, partes[0]

        # blueprint tipo panel_*_bp (igual que tus paneles)
        if not bp_name or not bp_name.startswith("panel_") or not bp_name.endswith("_bp"):
            continue

        # vista tipo modulo_*
        if not view_name.startswith("modulo_"):
            continue

        try:
            url = url_for(endpoint)
        except Exception:
            url = "#"

        categoria = _categoria_para_blueprint(bp_name)

        modulos_lista.append(
            {
                "blueprint": bp_name,
                "titulo": view_name,   # lo “bonificas” en plantilla
                "url": url,
                "ruta": ruta,
                "categoria": categoria,
                "descripcion": f"{bp_name} · {view_name}",
            }
        )

    modulos_lista.sort(key=lambda m: m["titulo"].lower())
    return modulos_lista
