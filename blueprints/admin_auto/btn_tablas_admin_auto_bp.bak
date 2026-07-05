# =============================================================================
# 🧩 BOTÓN · TABLAS → ADMIN AUTO (SELECTOR + DETALLE + ESQUEMA + REGISTROS)
# Archivo: blueprints/tablas/btn_tablas_admin_auto_bp.py
# =============================================================================
"""
MÓDULO PYTHON
-------------
Admin automático de tablas (nivel super_admin):

1) Selector visual de tablas por esquema.
2) Detalle de tabla:
   - Mostrar columnas (metadatos).
   - Mostrar datos de la tabla (SELECT * con paginación).
   - Botones: Añadir, Editar, Borrar registro.
   - Borrar múltiple: seleccionar varios registros y eliminarlos juntos.
3) Gestión de esquema (ALTER TABLE) con doble confirmación:
     - Añadir columnas.
     - Cambiar tipo de columna.
     - Eliminar columna.
4) (Futuro) Creación de nuevas tablas.

TODAS LAS RUTAS:
- Requieren login.
- Requieren rol super_admin.
"""

from __future__ import annotations

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
)
from services.helpers import login_required, rol_required
from db import ejecutar_query, ejecutar_non_query
import logging

# =============================================================================
# 🧩 1️⃣ CONSTANTES Y CONFIGURACIÓN
# =============================================================================

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

TABLAS_SOLO_LECTURA_ESQUEMA_MANUAL: set[tuple[str, str]] = {
    # ("control_via_publica", "tbl_historico_plazas"),
}

PATRONES_CRITICOS = (
    "tbl_historico_",
    "tbl_auditoria_",
    "tbl_log_",
)

TIPOS_PERMITIDOS = {
    "INT",
    "BIGINT",
    "VARCHAR(255)",
    "TEXT",
    "DATE",
    "DATETIME",
    "BOOLEAN",
    "DECIMAL(10,2)",
}

REGISTROS_POR_PAGINA = 100

# =============================================================================
# 📌 2️⃣ LOGGING
# =============================================================================

logger = logging.getLogger(__name__)


def log_esquema_apply(
    schema: str,
    tabla: str,
    accion: str,
    sql_full: str,
    resultado: str,
    error: str | None = None,
    usuario: str | None = None,
):
    """
    2.1️⃣ log_esquema_apply
    -----------------------
    Log para ALTER TABLE (add_column, change_type, drop_column).
    resultado: "ok" → info, "error" → error.
    """
    msg = (
        f"[ADMIN_AUTO_ESQUEMA] schema={schema} tabla={tabla} accion={accion} "
        f"sql={sql_full} resultado={resultado}"
    )
    if error:
        msg += f" error={error}"
    if usuario:
        msg += f" usuario={usuario}"

    if resultado == "ok":
        logger.info(msg)
    else:
        logger.error(msg)


def log_accion_datos(
    schema: str,
    tabla: str,
    accion: str,
    sql: str,
    params: dict | None = None,
    resultado: str = "ok",
    error: str | None = None,
    usuario: str | None = None,
):
    """
    2.2️⃣ log_accion_datos
    ----------------------
    Log para acciones sobre datos (SELECT, INSERT, UPDATE, DELETE).
    """
    msg = (
        f"[ADMIN_AUTO_DATOS] schema={schema} tabla={tabla} accion={accion} sql={sql}"
    )
    if params:
        msg += f" params={params}"
    msg += f" resultado={resultado}"
    if error:
        msg += f" error={error}"
    if usuario:
        msg += f" usuario={usuario}"

    if resultado == "ok":
        logger.info(msg)
    else:
        logger.error(msg)


# =============================================================================
# 🧠 3️⃣ FUNCIONES AUXILIARES
# =============================================================================

def obtener_tablas_por_esquema() -> dict[str, list[str]]:
    """
    3.1️⃣ obtener_tablas_por_esquema
    --------------------------------
    Devuelve dict agrupando tablas por esquema para ESQUEMAS_PERMITIDOS.
    """
    esquemas = "', '".join(ESQUEMAS_PERMITIDOS)
    filas = ejecutar_query(
        f"""
        SELECT
            table_schema AS schema_name,
            table_name   AS table_name
        FROM information_schema.tables
        WHERE table_schema IN ('{esquemas}')
          AND table_type = 'BASE TABLE'
        ORDER BY table_schema, table_name
        """
    )

    tablas_por_esquema: dict[str, list[str]] = {}
    for fila in filas:
        schema = fila["schema_name"]
        tabla = fila["table_name"]
        tablas_por_esquema.setdefault(schema, []).append(tabla)

    return tablas_por_esquema


def es_tabla_critica(schema: str, tabla: str) -> bool:
    """
    3.2️⃣ es_tabla_critica
    ----------------------
    Marca como críticas tablas de auditoría/histórico/logs.
    """
    if (schema, tabla) in TABLAS_SOLO_LECTURA_ESQUEMA_MANUAL:
        return True

    nombre = tabla.lower()
    for patron in PATRONES_CRITICOS:
        if nombre.startswith(patron):
            return True

    return False


def es_tabla_solo_esquema(schema: str, tabla: str) -> bool:
    """
    3.3️⃣ es_tabla_solo_esquema
    ---------------------------
    True → solo lectura de esquema (no ALTER TABLE).
    """
    return es_tabla_critica(schema, tabla)


def obtener_columnas(schema: str, tabla: str) -> list[dict]:
    """
    3.4️⃣ obtener_columnas
    ----------------------
    Obtiene metadatos de columnas de una tabla.
    """
    columnas = ejecutar_query(
        """
        SELECT
            COLUMN_NAME,
            DATA_TYPE,
            IS_NULLABLE,
            COLUMN_DEFAULT,
            COLUMN_KEY
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ORDINAL_POSITION
        """,
        (schema, tabla),
    )
    return columnas


def obtener_datos_tabla(schema: str, tabla: str, pagina: int = 1) -> list[dict]:
    """
    3.5️⃣ obtener_datos_tabla
    -------------------------
    Obtiene datos de una tabla con paginación simple.
    """
    limit = REGISTROS_POR_PAGINA
    offset = (pagina - 1) * limit

    sql = f"""
        SELECT *
        FROM `{schema}`.`{tabla}`
        LIMIT {limit} OFFSET {offset}
    """

    try:
        usuario = session.get("usuario", "unknown") if session else "unknown"
        datos = ejecutar_query(sql, None)
        log_accion_datos(
            schema=schema,
            tabla=tabla,
            accion="select_datos",
            sql=sql,
            params=None,
            resultado="ok",
            usuario=usuario,
        )
        return datos
    except Exception as e:
        usuario = session.get("usuario", "unknown") if session else "unknown"
        log_accion_datos(
            schema=schema,
            tabla=tabla,
            accion="select_datos",
            sql=sql,
            params=None,
            resultado="error",
            error=str(e),
            usuario=usuario,
        )
        return []


def obtener_id_principal(fila: dict, columnas: list[dict]) -> any:
    """
    3.6️⃣ obtener_id_principal
    --------------------------
    Obtiene el valor de la clave primaria de un registro.
    Si no hay PK explícita, usa la primera columna.
    """
    for col in columnas:
        if col["COLUMN_KEY"] == "PRI":
            return fila[col["COLUMN_NAME"]]
    
    # Si no hay PK, usa la primera columna
    return fila[columnas[0]["COLUMN_NAME"]]


# =============================================================================
# 🧩 4️⃣ DEFINICIÓN DEL BLUEPRINT
# =============================================================================

btn_tablas_admin_auto_bp = Blueprint(
    "btn_tablas_admin_auto_bp",
    __name__,
    url_prefix="/tablas",
)


# =============================================================================
# 🧩 5️⃣ RUTA PRINCIPAL · SELECTOR DE TABLAS
# =============================================================================

@btn_tablas_admin_auto_bp.route("/admin_auto", methods=["GET"])
@login_required
@rol_required("super_admin")
def btn_tablas_admin_auto():
    """
    5.1️⃣ Selector de tablas (vista principal)
    """
    tablas_por_esquema = obtener_tablas_por_esquema()
    return render_template(
        "admin_auto/tablas_admin_auto.html",
        tablas_por_esquema=tablas_por_esquema,
    )


# =============================================================================
# 🧩 6️⃣ DETALLE DE TABLA · DATOS + ACCIONES (añadir/editar/borrar)
# =============================================================================

@btn_tablas_admin_auto_bp.route("/admin_auto_detalle", methods=["GET"])
@login_required
@rol_required("super_admin")
def admin_auto_detalle():
    """
    6.1️⃣ admin_auto_detalle
    ------------------------
    Detalle de tabla:
      - Columnas (metadatos).
      - Datos (SELECT * con paginación).
      - Acciones: añadir, editar, borrar (individual y múltiple).
    """
    schema = request.args.get("schema", "").strip()
    tabla = request.args.get("tabla", "").strip()
    pagina = int(request.args.get("pagina", "1"))
    origem = request.args.get("origem", "")

    if not schema or not tabla:
        tablas_por_esquema = obtener_tablas_por_esquema()
        flash("Debes seleccionar un esquema y una tabla.", "warning")
        return render_template(
            "admin_auto/tablas_admin_auto.html",
            tablas_por_esquema=tablas_por_esquema,
        )

    if schema not in ESQUEMAS_PERMITIDOS:
        flash("Esquema no permitido para admin automático.", "danger")
        tablas_por_esquema = obtener_tablas_por_esquema()
        return render_template(
            "admin_auto/tablas_admin_auto.html",
            tablas_por_esquema=tablas_por_esquema,
        )

    solo_esquema = es_tabla_solo_esquema(schema, tabla)
    columnas = obtener_columnas(schema, tabla)
    datos = obtener_datos_tabla(schema, tabla, pagina=pagina)

    return render_template(
        "admin_auto/admin_auto_detalle_placeholder.html",
        schema=schema,
        tabla=tabla,
        columnas=columnas,
        datos=datos,
        solo_esquema=solo_esquema,
        pagina=pagina,
        origem=origem,
    )


# =============================================================================
# 🧩 7️⃣ FORMULARIO DE REGISTRO · ALTA / EDICIÓN
# =============================================================================

@btn_tablas_admin_auto_bp.route(
    "/registro_form/<schema>/<tabla>", methods=["GET", "POST"]
)
@btn_tablas_admin_auto_bp.route(
    "/registro_form/<schema>/<tabla>/<reg_id>", methods=["GET", "POST"]
)
@login_required
@rol_required("super_admin")
def admin_auto_registro_form(schema: str, tabla: str, reg_id: any = None):
    """
    7.1️⃣ admin_auto_registro_form
    ------------------------------
    Formulario para:
      - Alta: reg_id=None, POST → INSERT.
      - Edición: reg_id=..., POST → UPDATE.
    """
    schema = request.values.get("schema", schema).strip()
    tabla = request.values.get("tabla", tabla).strip()
    origen = request.values.get("origen", "")

    if schema not in ESQUEMAS_PERMITIDOS:
        flash("Esquema no permitido.", "danger")
        return redirect(
            url_for("btn_tablas_admin_auto_bp.btn_tablas_admin_auto")
        )

    columnas = obtener_columnas(schema, tabla)
    
    # Detectar columna primaria
    col_primary = None
    for col in columnas:
        if col["COLUMN_KEY"] == "PRI":
            col_primary = col["COLUMN_NAME"]
            break
    
    if not col_primary:
        col_primary = columnas[0]["COLUMN_NAME"]

    # -------------------------------------------------------------------------
    # 7.1.1️⃣ GET: cargar registro (edición) o mostrar formulario vacío (alta)
    # -------------------------------------------------------------------------
    if request.method == "GET":
        registro = None
        if reg_id is not None:
            sql_select = f"""
                SELECT *
                FROM `{schema}`.`{tabla}`
                WHERE `{col_primary}` = %s
                LIMIT 1
            """
            try:
                usuario = session.get("usuario", "unknown") if session else "unknown"
                registro = ejecutar_query(sql_select, (reg_id,))
                if registro:
                    registro = registro[0]
                log_accion_datos(
                    schema=schema,
                    tabla=tabla,
                    accion="select_registro_edicion",
                    sql=sql_select,
                    params={"id": reg_id},
                    resultado="ok",
                    usuario=usuario,
                )
            except Exception as e:
                usuario = session.get("usuario", "unknown") if session else "unknown"
                log_accion_datos(
                    schema=schema,
                    tabla=tabla,
                    accion="select_registro_edicion",
                    sql=sql_select,
                    params={"id": reg_id},
                    resultado="error",
                    error=str(e),
                    usuario=usuario,
                )
                flash("Error cargando registro para edición.", "error")
                registro = None

        return render_template(
            "admin_auto/admin_auto_registro_form.html",
            schema=schema,
            tabla=tabla,
            columnas=columnas,
            registro=registro,
            reg_id=reg_id,
            col_primary=col_primary,
            origen=origen,
        )

    # -------------------------------------------------------------------------
    # 7.1.2️⃣ POST: procesar alta/edición
    # -------------------------------------------------------------------------
    # Recoger datos del formulario
    datos_form = {}
    for col in columnas:
        nombre = col["COLUMN_NAME"]
        # Skip PK autoincrement
        if col["COLUMN_KEY"] == "PRI" and col["COLUMN_DEFAULT"] is None:
            continue
        valor = request.form.get(nombre, "")
        datos_form[nombre] = valor

    # Detectar si es alta o edición
    is_insert = reg_id is None
    is_update = reg_id is not None

    if is_insert:
        # ---------------------------------------------------------------------
        # INSERT
        # ---------------------------------------------------------------------
        cols = ", ".join([f"`{c}`" for c in datos_form.keys()])
        vals = ", ".join([f":{c}" for c in datos_form.keys()])
        sql_insert = f"""
            INSERT INTO `{schema}`.`{tabla}` ({cols})
            VALUES ({vals})
        """

        params = datos_form

        try:
            usuario = session.get("usuario", "unknown") if session else "unknown"
            ejecutar_non_query(sql_insert, params)
            log_accion_datos(
                schema=schema,
                tabla=tabla,
                accion="insert",
                sql=sql_insert,
                params=params,
                resultado="ok",
                usuario=usuario,
            )
            flash("Registro creado correctamente.", "success")
        except Exception as e:
            usuario = session.get("usuario", "unknown") if session else "unknown"
            log_accion_datos(
                schema=schema,
                tabla=tabla,
                accion="insert",
                sql=sql_insert,
                params=params,
                resultado="error",
                error=str(e),
                usuario=usuario,
            )
            flash("Error creando el registro.", "error")

    elif is_update:
        # ---------------------------------------------------------------------
        # UPDATE
        # ---------------------------------------------------------------------
        set_clause = ", ".join([f"`{c}` = :{c}" for c in datos_form.keys()])
        sql_update = f"""
            UPDATE `{schema}`.`{tabla}`
            SET {set_clause}
            WHERE `{col_primary}` = :reg_id
        """
        params = datos_form.copy()
        params["reg_id"] = reg_id

        try:
            usuario = session.get("usuario", "unknown") if session else "unknown"
            ejecutar_non_query(sql_update, params)
            log_accion_datos(
                schema=schema,
                tabla=tabla,
                accion="update",
                sql=sql_update,
                params=params,
                resultado="ok",
                usuario=usuario,
            )
            flash("Registro actualizado correctamente.", "success")
        except Exception as e:
            usuario = session.get("usuario", "unknown") if session else "unknown"
            log_accion_datos(
                schema=schema,
                tabla=tabla,
                accion="update",
                sql=sql_update,
                params=params,
                resultado="error",
                error=str(e),
                usuario=usuario,
            )
            flash("Error actualizando el registro.", "error")

    # Redirigir al detalle (o a la origen si se indicó)
    if origen:
        return redirect(origen)
    return redirect(
        url_for(
            "btn_tablas_admin_auto_bp.admin_auto_detalle",
            schema=schema,
            tabla=tabla,
        )
    )


# =============================================================================
# 🧩 8️⃣ CONFIRMACIÓN Y ELIMINACIÓN DE REGISTRO(S)
# =============================================================================

@btn_tablas_admin_auto_bp.route(
    "/registro_confirm/<schema>/<tabla>/<reg_id>", methods=["GET", "POST"]
)
@login_required
@rol_required("super_admin")
def admin_auto_registro_confirm(schema: str, tabla: str, reg_id: any):
    """
    8.1️⃣ admin_auto_registro_confirm (individual)
    ----------------------------------------------
    Confirmar eliminación de un registro:
      - GET: muestra confirmación.
      - POST: ejecuta DELETE.
    """
    schema = request.values.get("schema", schema).strip()
    tabla = request.values.get("tabla", tabla).strip()
    origen = request.values.get("origen", "")

    if schema not in ESQUEMAS_PERMITIDOS:
        flash("Esquema no permitido.", "danger")
        return redirect(
            url_for("btn_tablas_admin_auto_bp.btn_tablas_admin_auto")
        )

    columnas = obtener_columnas(schema, tabla)
    
    # Detectar columna primaria
    col_primary = None
    for col in columnas:
        if col["COLUMN_KEY"] == "PRI":
            col_primary = col["COLUMN_NAME"]
            break
    
    if not col_primary:
        col_primary = columnas[0]["COLUMN_NAME"]

    # -------------------------------------------------------------------------
    # 8.1.1️⃣ GET: mostrar confirmación
    # -------------------------------------------------------------------------
    if request.method == "GET":
        sql_select = f"""
            SELECT *
            FROM `{schema}`.`{tabla}`
            WHERE `{col_primary}` = %s
            LIMIT 1
        """
        try:
            usuario = session.get("usuario", "unknown") if session else "unknown"
            registro = ejecutar_query(sql_select, (reg_id,))
            if registro:
                registro = registro[0]
            log_accion_datos(
                schema=schema,
                tabla=tabla,
                accion="select_confirm_delete",
                sql=sql_select,
                params={"id": reg_id},
                resultado="ok",
                usuario=usuario,
            )
        except Exception as e:
            usuario = session.get("usuario", "unknown") if session else "unknown"
            log_accion_datos(
                schema=schema,
                tabla=tabla,
                accion="select_confirm_delete",
                sql=sql_select,
                params={"id": reg_id},
                resultado="error",
                error=str(e),
                usuario=usuario,
            )
            flash("Error cargando registro para confirmar eliminación.", "error")
            registro = None

        return render_template(
            "admin_auto/admin_auto_registro_confirm.html",
            schema=schema,
            tabla=tabla,
            reg_id=reg_id,
            col_primary=col_primary,
            registro=registro,
            origen=origen,
        )

    # -------------------------------------------------------------------------
    # 8.1.2️⃣ POST: ejecutar DELETE
    # -------------------------------------------------------------------------
    sql_delete = f"""
        DELETE FROM `{schema}`.`{tabla}`
        WHERE `{col_primary}` = :reg_id
    """
    params = {"reg_id": reg_id}

    try:
        usuario = session.get("usuario", "unknown") if session else "unknown"
        ejecutar_non_query(sql_delete, params)
        log_accion_datos(
            schema=schema,
            tabla=tabla,
            accion="delete",
            sql=sql_delete,
            params=params,
            resultado="ok",
            usuario=usuario,
        )
        flash("Registro eliminado correctamente.", "success")
    except Exception as e:
        usuario = session.get("usuario", "unknown") if session else "unknown"
        log_accion_datos(
            schema=schema,
            tabla=tabla,
            accion="delete",
            sql=sql_delete,
            params=params,
            resultado="error",
            error=str(e),
            usuario=usuario,
        )
        flash("Error eliminando el registro.", "error")

    if origen:
        return redirect(origen)
    return redirect(
        url_for(
            "btn_tablas_admin_auto_bp.admin_auto_detalle",
            schema=schema,
            tabla=tabla,
        )
    )


@btn_tablas_admin_auto_bp.route(
    "/registro_confirm_multiple/<schema>/<tabla>", methods=["POST"]
)
@login_required
@rol_required("super_admin")
def admin_auto_registro_confirm_multiple(schema: str, tabla: str):
    """
    8.2️⃣ admin_auto_registro_confirm_multiple
    ------------------------------------------
    Eliminar múltiples registros seleccionados.
    """
    schema = request.values.get("schema", schema).strip()
    tabla = request.values.get("tabla", tabla).strip()
    origen = request.values.get("origen", "")
    
    # Recoger IDs (puede venir como lista o como string separado por comas)
    ids_lista = request.form.getlist("ids[]")
    if not ids_lista:
        ids_str = request.form.get("ids", "")
        ids_lista = [id.strip() for id in ids_str.split(",") if id.strip()]

    if not ids_lista:
        flash("No se seleccionaron registros para eliminar.", "warning")
        if origen:
            return redirect(origen)
        return redirect(
            url_for(
                "btn_tablas_admin_auto_bp.admin_auto_detalle",
                schema=schema,
                tabla=tabla,
            )
        )

    if schema not in ESQUEMAS_PERMITIDOS:
        flash("Esquema no permitido.", "danger")
        return redirect(
            url_for("btn_tablas_admin_auto_bp.btn_tablas_admin_auto")
        )

    columnas = obtener_columnas(schema, tabla)
    
    # Detectar columna primaria
    col_primary = None
    for col in columnas:
        if col["COLUMN_KEY"] == "PRI":
            col_primary = col["COLUMN_NAME"]
            break
    
    if not col_primary:
        col_primary = columnas[0]["COLUMN_NAME"]

    # Construir DELETE con IN
    placeholders = ", ".join([":id" + str(i) for i in range(len(ids_lista))])
    sql_delete = f"""
        DELETE FROM `{schema}`.`{tabla}`
        WHERE `{col_primary}` IN ({placeholders})
    """
    
    params = {f"id{i}": ids_lista[i] for i in range(len(ids_lista))}

    try:
        usuario = session.get("usuario", "unknown") if session else "unknown"
        ejecutar_non_query(sql_delete, params)
        log_accion_datos(
            schema=schema,
            tabla=tabla,
            accion="delete_multiple",
            sql=sql_delete,
            params=params,
            resultado="ok",
            usuario=usuario,
        )
        flash(f"{len(ids_lista)} registros eliminados correctamente.", "success")
    except Exception as e:
        usuario = session.get("usuario", "unknown") if session else "unknown"
        log_accion_datos(
            schema=schema,
            tabla=tabla,
            accion="delete_multiple",
            sql=sql_delete,
            params=params,
            resultado="error",
            error=str(e),
            usuario=usuario,
        )
        flash("Error eliminando los registros.", "error")

    if origen:
        return redirect(origen)
    return redirect(
        url_for(
            "btn_tablas_admin_auto_bp.admin_auto_detalle",
            schema=schema,
            tabla=tabla,
        )
    )


# =============================================================================
# 🧩 9️⃣ FORMULARIO DE ESQUEMA · ALTER TABLE
# =============================================================================

@btn_tablas_admin_auto_bp.route(
    "/admin_auto_esquema", methods=["GET", "POST"]
)
@login_required
@rol_required("super_admin")
def admin_auto_esquema_form():
    """
    9.1️⃣ admin_auto_esquema_form
    -----------------------------
    Formulario para añadir/cambiar/eliminar columna.
    """
    schema = request.values.get("schema", "").strip()
    tabla = request.values.get("tabla", "").strip()

    if not schema or not tabla:
        flash("Esquema y tabla son obligatorios.", "warning")
        return redirect(
            url_for("btn_tablas_admin_auto_bp.btn_tablas_admin_auto")
        )

    if schema not in ESQUEMAS_PERMITIDOS:
        flash("Esquema no permitido para admin automático.", "danger")
        return redirect(
            url_for("btn_tablas_admin_auto_bp.btn_tablas_admin_auto")
        )

    if es_tabla_solo_esquema(schema, tabla):
        flash("Esta tabla está en modo solo lectura de esquema.", "warning")
        return redirect(
            url_for(
                "btn_tablas_admin_auto_bp.admin_auto_detalle",
                schema=schema,
                tabla=tabla,
            )
        )

    if request.method == "GET":
        columnas = obtener_columnas(schema, tabla)

        return render_template(
            "admin_auto/admin_auto_esquema_form.html",
            schema=schema,
            tabla=tabla,
            columnas=columnas,
            tipos_permitidos=sorted(TIPOS_PERMITIDOS),
        )

    accion = request.form.get("accion")

    if accion == "add_column":
        nombre_columna = request.form.get("nombre_columna", "").strip()
        tipo_columna = request.form.get("tipo_columna")
        permitir_null = request.form.get("permitir_null") == "1"
        valor_defecto = request.form.get("valor_defecto", "").strip()
        posicion = request.form.get("posicion")

        if not nombre_columna:
            flash("El nombre de la nueva columna es obligatorio.", "danger")
            return redirect(
                url_for(
                    "btn_tablas_admin_auto_bp.admin_auto_esquema_form",
                    schema=schema,
                    tabla=tabla,
                )
            )
        if tipo_columna not in TIPOS_PERMITIDOS:
            flash("Tipo de columna no permitido.", "danger")
            return redirect(
                url_for(
                    "btn_tablas_admin_auto_bp.admin_auto_esquema_form",
                    schema=schema,
                    tabla=tabla,
                )
            )

        return render_template(
            "admin_auto/admin_auto_esquema_confirm.html",
            schema=schema,
            tabla=tabla,
            accion=accion,
            nombre_columna=nombre_columna,
            tipo_columna=tipo_columna,
            permitir_null=permitir_null,
            valor_defecto=valor_defecto,
            posicion=posicion,
        )

    if accion == "change_type":
        columna_objetivo = request.form.get("columna_objetivo")
        tipo_nuevo = request.form.get("tipo_columna")

        if not columna_objetivo:
            flash("Debes seleccionar la columna a modificar.", "danger")
            return redirect(
                url_for(
                    "btn_tablas_admin_auto_bp.admin_auto_esquema_form",
                    schema=schema,
                    tabla=tabla,
                )
            )
        if tipo_nuevo not in TIPOS_PERMITIDOS:
            flash("Tipo de columna no permitido.", "danger")
            return redirect(
                url_for(
                    "btn_tablas_admin_auto_bp.admin_auto_esquema_form",
                    schema=schema,
                    tabla=tabla,
                )
            )

        return render_template(
            "admin_auto/admin_auto_esquema_confirm.html",
            schema=schema,
            tabla=tabla,
            accion=accion,
            columna_objetivo=columna_objetivo,
            tipo_columna=tipo_nuevo,
        )

    if accion == "drop_column":
        columna_objetivo = request.form.get("columna_objetivo")

        if not columna_objetivo:
            flash("Debes seleccionar la columna a eliminar.", "danger")
            return redirect(
                url_for(
                    "btn_tablas_admin_auto_bp.admin_auto_esquema_form",
                    schema=schema,
                    tabla=tabla,
                )
            )

        return render_template(
            "admin_auto/admin_auto_esquema_confirm.html",
            schema=schema,
            tabla=tabla,
            accion=accion,
            columna_objetivo=columna_objetivo,
        )

    flash("Acción de esquema no soportada.", "warning")
    return redirect(
        url_for(
            "btn_tablas_admin_auto_bp.admin_auto_detalle",
            schema=schema,
            tabla=tabla,
        )
    )


@btn_tablas_admin_auto_bp.route(
    "/admin_auto_esquema_apply", methods=["POST"]
)
@login_required
@rol_required("super_admin")
def admin_auto_esquema_apply():
    """
    9.2️⃣ admin_auto_esquema_apply
    ------------------------------
    Ejecutar ALTER TABLE.
    """
    schema = request.form.get("schema", "").strip()
    tabla = request.form.get("tabla", "").strip()
    accion = request.form.get("accion")
    confirmar = request.form.get("confirmar") == "1"

    usuario = session.get("usuario", "unknown") if session else "unknown"

    if not confirmar:
        flash("Debes marcar la casilla de confirmación para aplicar el cambio.", "warning")
        return redirect(
            url_for(
                "btn_tablas_admin_auto_bp.admin_auto_detalle",
                schema=schema,
                tabla=tabla,
            )
        )

    if schema not in ESQUEMAS_PERMITIDOS:
        flash("Esquema no permitido para admin automático.", "danger")
        return redirect(
            url_for("btn_tablas_admin_auto_bp.btn_tablas_admin_auto")
        )

    if accion == "add_column":
        nombre_columna = request.form.get("nombre_columna", "").strip()
        tipo_columna = request.form.get("tipo_columna")
        permitir_null = request.form.get("permitir_null") == "1"
        valor_defecto = request.form.get("valor_defecto", "").strip()
        posicion = request.form.get("posicion")

        if not nombre_columna or tipo_columna not in TIPOS_PERMITIDOS:
            flash("Datos de columna no válidos.", "danger")
            return redirect(
                url_for(
                    "btn_tablas_admin_auto_bp.admin_auto_detalle",
                    schema=schema,
                    tabla=tabla,
                )
            )

        sql_parts = [
            f"ALTER TABLE `{schema}`.`{tabla}` "
            f"ADD COLUMN `{nombre_columna}` {tipo_columna}"
        ]
        if not permitir_null:
            sql_parts.append("NOT NULL")
        if valor_defecto:
            sql_parts.append(f"DEFAULT {valor_defecto}")
        if posicion and posicion != "final":
            sql_parts.append(f"AFTER `{posicion}`")

        sql_full = " ".join(sql_parts) + ";"

        try:
            ejecutar_non_query(sql_full, None)
            log_esquema_apply(
                schema=schema,
                tabla=tabla,
                accion="add_column",
                sql_full=sql_full,
                resultado="ok",
                usuario=usuario,
            )
            flash("Columna añadida correctamente.", "success")
        except Exception as e:
            log_esquema_apply(
                schema=schema,
                tabla=tabla,
                accion="add_column",
                sql_full=sql_full,
                resultado="error",
                error=str(e),
                usuario=usuario,
            )
            flash("Error añadiendo la columna.", "danger")

        return redirect(
            url_for(
                "btn_tablas_admin_auto_bp.admin_auto_detalle",
                schema=schema,
                tabla=tabla,
            )
        )

    if accion == "change_type":
        columna_objetivo = request.form.get("columna_objetivo")
        tipo_columna = request.form.get("tipo_columna")

        if not columna_objetivo or tipo_columna not in TIPOS_PERMITIDOS:
            flash("Datos de columna no válidos.", "danger")
            return redirect(
                url_for(
                    "btn_tablas_admin_auto_bp.admin_auto_detalle",
                    schema=schema,
                    tabla=tabla,
                )
            )

        sql_full = (
            f"ALTER TABLE `{schema}`.`{tabla}` "
            f"MODIFY COLUMN `{columna_objetivo}` {tipo_columna};"
        )

        try:
            ejecutar_non_query(sql_full, None)
            log_esquema_apply(
                schema=schema,
                tabla=tabla,
                accion="change_type",
                sql_full=sql_full,
                resultado="ok",
                usuario=usuario,
            )
            flash("Tipo de columna cambiado correctamente.", "success")
        except Exception as e:
            log_esquema_apply(
                schema=schema,
                tabla=tabla,
                accion="change_type",
                sql_full=sql_full,
                resultado="error",
                error=str(e),
                usuario=usuario,
            )
            flash("Error cambiando el tipo de la columna.", "danger")

        return redirect(
            url_for(
                "btn_tablas_admin_auto_bp.admin_auto_detalle",
                schema=schema,
                tabla=tabla,
            )
        )

    if accion == "drop_column":
        columna_objetivo = request.form.get("columna_objetivo")

        if not columna_objetivo:
            flash("Debes indicar la columna a eliminar.", "danger")
            return redirect(
                url_for(
                    "btn_tablas_admin_auto_bp.admin_auto_detalle",
                    schema=schema,
                    tabla=tabla,
                )
            )

        sql_full = (
            f"ALTER TABLE `{schema}`.`{tabla}` "
            f"DROP COLUMN `{columna_objetivo}`;"
        )

        try:
            ejecutar_non_query(sql_full, None)
            log_esquema_apply(
                schema=schema,
                tabla=tabla,
                accion="drop_column",
                sql_full=sql_full,
                resultado="ok",
                usuario=usuario,
            )
            flash("Columna eliminada correctamente.", "success")
        except Exception as e:
            log_esquema_apply(
                schema=schema,
                tabla=tabla,
                accion="drop_column",
                sql_full=sql_full,
                resultado="error",
                error=str(e),
                usuario=usuario,
            )
            flash("Error eliminando la columna.", "danger")

        return redirect(
            url_for(
                "btn_tablas_admin_auto_bp.admin_auto_detalle",
                schema=schema,
                tabla=tabla,
            )
        )

    flash("Acción de esquema no soportada.", "warning")
    return redirect(
        url_for(
            "btn_tablas_admin_auto_bp.admin_auto_detalle",
            schema=schema,
            tabla=tabla,
        )
    )