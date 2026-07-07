# =============================================================================
# 📦 ADMIN AUTO · LISTADO DINÁMICO (por schema + tabla)
# Archivo: blueprints/admin_auto/btn_tablas_admin_auto_bp.py
# =============================================================================

from flask import Blueprint, render_template, request, current_app, abort
from db import ejecutar_query
from services.helpers import login_required, rol_required

ESQUEMAS_PERMITIDOS = {
    "bd_tbl_comunes",
    "control_via_publica",
    "inventario",
    "mobiliario_urbano",
    "parquin_camiones",
    "patrulla_verde",
    "personal_vestuario",
    "plan_de_emergencias",
}


def obtener_tablas_permitidas():
    esquemas = "', '".join(ESQUEMAS_PERMITIDOS)
    filas = ejecutar_query(f"""
        SELECT
            table_schema AS schema_name,
            table_name   AS table_name
        FROM information_schema.tables
        WHERE table_schema IN ('{esquemas}')
          AND table_type = 'BASE TABLE'
    """)
    return {f"{f['schema_name']}.{f['table_name']}" for f in filas}


# Blueprint para listado genérico → nombre estándar: bp
bp = Blueprint(
    "tablas_admin_auto_bp",
    __name__,
    url_prefix="/tablas_admin_auto",
)
# Ruta efectiva: /tablas_admin_auto/<schema>/<tabla>


@bp.route("/<schema>/<tabla>", methods=["GET"])
@login_required
@rol_required("super_admin")
def tablas_admin_auto_listado(schema, tabla):
    identificador = f"{schema}.{tabla}"

    if schema not in ESQUEMAS_PERMITIDOS:
        abort(404)

    tablas_permitidas = obtener_tablas_permitidas()
    if identificador not in tablas_permitidas:
        abort(404)

    q = request.args.get("q", "").strip()

    datos = ejecutar_query(f"SELECT * FROM {schema}.{tabla} LIMIT 50")
    columnas = datos[0].keys() if datos else []
    endpoints = current_app.view_functions

    return render_template(
        "admin_auto/tablas_admin_auto_listado.html",
        schema=schema,
        tabla=tabla,
        columnas=columnas,
        datos=datos,
        q=q,
        endpoints=endpoints,
    )
