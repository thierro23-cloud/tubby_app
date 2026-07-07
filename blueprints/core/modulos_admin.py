# =============================================================================
# 🧠 REGISTRY DINÁMICO (AUTO ACTUALIZADO CON BD)
# =============================================================================

from db import ejecutar_query


def obtener_modulos():
    """
    🔥 GENERACIÓN DINÁMICA EN TIEMPO REAL

    ✔ Cada vez que se llama → consulta la BD
    ✔ Si hay tabla nueva → aparece automáticamente
    ✔ No necesita reinicio
    """

    modulos = []

    tablas = ejecutar_query("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = DATABASE()
    """)

    for t in tablas:

        nombre_tabla = t["table_name"]

        # 🔹 Limpiar nombre
        nombre_limpio = nombre_tabla.replace("tbl_", "").replace("_", " ").capitalize()

        modulos.append(
            {
                "nombre": nombre_limpio,
                "tabla": nombre_tabla,
                "icono": _icono_auto(nombre_tabla),
                "url": f"/admin/{nombre_tabla}",
                "activo": True,
            }
        )

    return modulos


# =============================================================================
# 🎨 ICONOS AUTOMÁTICOS
# =============================================================================


def _icono_auto(nombre):
    if "usuario" in nombre:
        return "👤"
    if "vado" in nombre:
        return "🚧"
    if "obra" in nombre:
        return "🏗️"
    if "contenedor" in nombre:
        return "🗑️"
    if "parquin" in nombre:
        return "🅿️"
    return "📦"
