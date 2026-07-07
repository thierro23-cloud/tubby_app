"""
Utilidades generales para la aplicación Tubby.
Contiene funciones de ayuda para el manejo de endpoints, datos, y operaciones comunes.
"""

from flask import current_app
from typing import List, Dict, Any


def obtener_todos_los_endpoints() -> List[Dict[str, Any]]:
    """
    Obtiene una lista de todos los endpoints registrados en la aplicación Flask.

    Returns:
        List[Dict[str, Any]]: Lista de diccionarios con información de cada endpoint.
                             Cada diccionario contiene:
                             - 'rule': La ruta del endpoint (str)
                             - 'methods': Métodos HTTP permitidos (list)
                             - 'endpoint': Nombre del endpoint (str)
                             - 'view_func': Nombre de la función de vista (str)
    """
    endpoints = []

    with current_app.app_context():
        for rule in current_app.url_map.iter_rules():
            # Ignorar opciones y rutas estáticas
            if rule.endpoint != "static":
                endpoint_info = {
                    "rule": str(rule.rule),
                    "methods": sorted(list(rule.methods - {"HEAD", "OPTIONS"})),
                    "endpoint": rule.endpoint,
                    "view_func": rule.endpoint,
                }
                endpoints.append(endpoint_info)

    # Ordenar por regla (ruta)
    endpoints.sort(key=lambda x: x["rule"])

    return endpoints


def obtener_endpoints_por_blueprint(blueprint_name: str) -> List[Dict[str, Any]]:
    """
    Obtiene todos los endpoints de un blueprint específico.

    Args:
        blueprint_name: Nombre del blueprint (ej: 'super_admin.super_admin_bp')

    Returns:
        List[Dict[str, Any]]: Lista de endpoints del blueprint especificado.
    """
    todos_los_endpoints = obtener_todos_los_endpoints()

    # Filtrar endpoints que pertenecen al blueprint
    endpoints_filtrados = [
        ep
        for ep in todos_los_endpoints
        if ep["endpoint"].startswith(f"{blueprint_name}.")
        or blueprint_name in ep["endpoint"]
    ]

    return endpoints_filtrados


def formatear_endpoints_para_tabla(
    endpoints: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """
    Formatea la lista de endpoints para mostrarlos en una tabla HTML.
    """
    tabla_data = []

    for ep in endpoints:
        métodos_str = ", ".join(ep["methods"])
        tabla_data.append(
            {
                "rule": ep["rule"],  # ← Cambiar 'ruta' por 'rule'
                "métodos": métodos_str,
                "endpoint": ep["endpoint"],
                "view_func": ep["view_func"],
            }
        )

    return tabla_data
