# blueprints/super_admin/helpers_paneles.py

from flask import current_app

# =============================================================================
# ENDPOINTS QUE NO SE DEBEN AUTODETECTAR
# =============================================================================
EXCLUIR_ENDPOINTS = {
    "super_admin_bp.super_admin",
    "super_admin_bp.super_admin_auto",
}


# =============================================================================
# BLUEPRINTS INTERNOS A IGNORAR
# =============================================================================
EXCLUIR_BLUEPRINTS = {
    "static",
}


# =============================================================================
# DETECTOR AUTOMÁTICO DE PANELES
# =============================================================================
def detectar_paneles() -> dict:

    url_map = current_app.url_map
    paneles: dict = {}

    for rule in url_map.iter_rules():

        endpoint = rule.endpoint

        # Ignorar endpoints sin blueprint
        if "." not in endpoint:
            continue

        blueprint, vista = endpoint.split(".", 1)

        # Ignorar blueprints internos
        if blueprint in EXCLUIR_BLUEPRINTS:
            continue

        # Ignorar endpoints excluidos
        if endpoint in EXCLUIR_ENDPOINTS:
            continue

        # Solo paneles
        if not vista.startswith("panel_"):
            continue

        # Solo rutas navegables
        if "GET" not in rule.methods:
            continue

        paneles[vista] = {
            "endpoint": endpoint,
            "rule": rule.rule,
            "blueprint": blueprint,
            "view": vista,
        }

    # Ordenar paneles por nombre
    paneles_ordenados = dict(sorted(paneles.items()))

    return paneles_ordenados
