# =============================================================================
# 🔥 AUTO CRUD DINÁMICO POR TABLA (VERSIÓN PRO SEGURA)
# =============================================================================

from flask import Blueprint, render_template, request, redirect, url_for, abort, session
from db import ejecutar_query, ejecutar_non_query
from core.audit import registrar_evento


admin_auto_bp = Blueprint(
    "admin_auto_bp",
    __name__,
    url_prefix="/admin"
)


# =============================================================================
# 🛡️ TABLAS PERMITIDAS (🔥 CLAVE SEGURIDAD)
# =============================================================================
TABLAS_PERMITIDAS = {
    "usuarios",
    "proveedores",
    "plazas",
    "camiones",
    "contenedores"
}


def validar_tabla(tabla):
    if tabla not in TABLAS_PERMITIDAS:
        abort(403)


# =============================================================================
# 🧠 1️⃣ LISTADO + FILTRO
# =============================================================================
@admin_auto_bp.route("/<tabla>")
def ver_tabla(tabla):

    validar_tabla(tabla)

    busqueda = request.args.get("q", "")

    columnas = ejecutar_query(f"SHOW COLUMNS FROM {tabla}")
    campos = [c["Field"] for c in columnas]

    where = ""
    valores = []

    if busqueda:
        filtros = [f"{c} LIKE %s" for c in campos]
        where = "WHERE " + " OR ".join(filtros)
        valores = [f"%{busqueda}%"] * len(campos)

    datos = ejecutar_query(
        f"SELECT * FROM {tabla} {where} LIMIT 100",
        valores
    )

    return render_template(
        "admin_auto/listado.html",
        tabla=tabla,
        columnas=campos,
        datos=datos
    )


# =============================================================================
# ➕ 2️⃣ CREAR REGISTRO
# =============================================================================
@admin_auto_bp.route("/<tabla>/nuevo", methods=["GET", "POST"])
def crear(tabla):

    validar_tabla(tabla)

    columnas = ejecutar_query(f"SHOW COLUMNS FROM {tabla}")
    campos = [c["Field"] for c in columnas if c["Field"] != "id"]

    if request.method == "POST":

        valores = [request.form.get(c) for c in campos]

        sql = f"""
            INSERT INTO {tabla} ({",".join(campos)})
            VALUES ({",".join(["%s"]*len(campos))})
        """

        ejecutar_non_query(sql, valores)

        # 📊 AUDIT
        registrar_evento("crear", tabla)

        return redirect(url_for("admin_auto_bp.ver_tabla", tabla=tabla))

    return render_template(
        "admin_auto/form.html",
        tabla=tabla,
        campos=campos
    )


# =============================================================================
# ✏️ 3️⃣ EDITAR
# =============================================================================
@admin_auto_bp.route("/<tabla>/editar/<id>", methods=["GET", "POST"])
def editar(tabla, id):

    validar_tabla(tabla)

    columnas = ejecutar_query(f"SHOW COLUMNS FROM {tabla}")
    campos = [c["Field"] for c in columnas if c["Field"] != "id"]

    if request.method == "POST":

        valores = [request.form.get(c) for c in campos]

        set_sql = ", ".join([f"{c}=%s" for c in campos])

        ejecutar_non_query(
            f"UPDATE {tabla} SET {set_sql} WHERE id=%s",
            valores + [id]
        )

        registrar_evento("editar", tabla)

        return redirect(url_for("admin_auto_bp.ver_tabla", tabla=tabla))

    datos = ejecutar_query(
        f"SELECT * FROM {tabla} WHERE id=%s",
        [id]
    )

    if not datos:
        abort(404)

    return render_template(
        "admin_auto/form.html",
        tabla=tabla,
        campos=campos,
        dato=datos[0]
    )


# =============================================================================
# ❌ 4️⃣ BORRAR
# =============================================================================
@admin_auto_bp.route("/<tabla>/borrar/<id>")
def borrar(tabla, id):

    validar_tabla(tabla)

    ejecutar_non_query(
        f"DELETE FROM {tabla} WHERE id=%s",
        [id]
    )

    registrar_evento("borrar", tabla)

    return redirect(url_for("admin_auto_bp.ver_tabla", tabla=tabla))