# =============================================================================
# 🏢 BLUEPRINT · INVENTARIO → LISTADO DE EDIFICIOS MUNICIPALES
# =============================================================================
# - Muestra una tabla con todos los edificios
# - Permite filtrar por nombre (campo "inmueble")
# - Desde aquí se navega a:
#     · Nuevo edificio  → formulario en blanco
#     · Editar edificio → formulario con datos
# =============================================================================

from flask import Blueprint, render_template, request, url_for, redirect
from db import ejecutar_query

btn_edificios_listado_bp = Blueprint(
    "btn_edificios_listado_bp",
    __name__,
    url_prefix="/inventario/edificios",
)

@btn_edificios_listado_bp.route("/listado", methods=["GET"])
def btn_edificios_listado():
    """
    📄 LISTADO DE EDIFICIOS MUNICIPALES

    - Lista todos los edificios de tbl_edificios_municipales.
    - Permite filtrar por nombre del inmueble usando ?q= en la URL.
    """
    # Leer texto de búsqueda (filtro por nombre de edificio)
    q = request.args.get("q", "", type=str).strip()

    # Consulta base
    base_sql = """
        SELECT 
            `Idtbl_edificios_municipales` AS id,
            inmueble,
            idtbl_numero_catastro,
            alarma
        FROM tbl_edificios_municipales
    """

    params = []
    # Si hay filtro, añadimos WHERE con LIKE
    if q:
        base_sql += " WHERE inmueble LIKE %s"
        params.append(f"%{q}%")

    # Ordenar por nombre de inmueble
    base_sql += " ORDER BY inmueble ASC"

    edificios = ejecutar_query(
        base_sql,
        tuple(params) if params else None,
        nombre_bd="inventario",
    )

    return render_template(
        "inventario/edificios_listado.html",
        edificios=edificios,
        q=q,  # para mantener el valor en la caja de búsqueda
    )