from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from services.helpers import (
    login_required,
    rol_required,
    ejecutar_consulta,
    ejecutar_non_query,
)

# =============================================================================
# 1. BLUEPRINT: BTN_VADOS_FORM_BP
# =============================================================================
# Este blueprint gestiona el formulario de alta/edición de vados:
#
#   RUTAS:
#   - GET  /vados/form/nuevo
#       Muestra el formulario vacío para crear un vado (modo = "nuevo").
#
#   - GET  /vados/form/editar/<idtbl_vados>
#       Muestra el formulario con datos de un vado existente (modo = "editar").
#
#   - POST /vados/form/guardar
#       Procesa el formulario y decide automáticamente:
#         * INSERT en tbl_vados si no viene idtbl_vados (alta).
#         * UPDATE en tbl_vados si viene idtbl_vados (edición).
#
# PLANTILLA USADA:
#   templates/control_via_publica/control_vados/vados_form.html
#
# VARIABLES QUE ENVÍA A LA PLANTILLA:
#   - modo: "nuevo" o "editar"
#   - vado: dict con datos del vado o None
#   - tipos_de_vias: lista de tipos de vía (para <select>)
#   - calles: lista de calles (municipio=395; filtrable por tipo en JS)
#   - proveedores: lista de proveedores/titulares (para <select>)
#   - municipios: lista de municipios (para <select>, por defecto 395)
#
# NOTA IMPORTANTE:
#   - idtbl_gestores NUNCA se pide en el formulario.
#     Se rellena siempre con el gestor logueado: g.user["idtbl_gestores"].
# =============================================================================

btn_vados_form_bp = Blueprint(
    "btn_vados_form_bp",
    __name__,
    url_prefix="/vados/form",
)


# =============================================================================
# 2. HELPERS DE CARGA DE DATOS (TIPOS, CALLES, PROVEEDORES, MUNICIPIOS, VADO)
# =============================================================================


def cargar_tipos_de_vias() -> list[dict]:
    """
    Devuelve la lista de tipos de vía desde bd_tbl_comunes.tbl_tipos_de_vias.
    Se usa para rellenar el <select> de tipo de vía.
    """
    return ejecutar_consulta(
        """
        SELECT idtbl_tipos_de_vias, Tipo_Via
        FROM bd_tbl_comunes.tbl_tipos_de_vias
        ORDER BY Tipo_Via
        """,
        devolver_dict=True,
        database="bd_tbl_comunes",
    )


def cargar_calles_municipio_395() -> list[dict]:
    """
    Devuelve la lista de calles del municipio 395 desde bd_tbl_comunes.tbl_calles.
    Se usa para rellenar el <select> de calles en el formulario.
    Si tu tabla o campo de municipio cambian, ajusta la consulta.
    """
    return ejecutar_consulta(
        """
        SELECT idtbl_calles, idtbl_tipos_de_vias, Nombre_Calle
        FROM bd_tbl_comunes.tbl_calles
        WHERE idtbl_municipios = 395
        ORDER BY Nombre_Calle
        """,
        devolver_dict=True,
        database="bd_tbl_comunes",
    )


def cargar_proveedores() -> list[dict]:
    """
    Devuelve una lista de proveedores/titulares desde bd_tbl_comunes.tbl_proveedores.
    Esta lista alimenta el <select> de titulares en el formulario.
    """
    return ejecutar_consulta(
        """
        SELECT idtbl_proveedores, NIF, Nombre_Razon_Social
        FROM bd_tbl_comunes.tbl_proveedores
        ORDER BY Nombre_Razon_Social
        """,
        devolver_dict=True,
        database="bd_tbl_comunes",
    )


def cargar_municipios() -> list[dict]:
    """
    Devuelve la lista de municipios desde bd_tbl_comunes.tbl_municipios.
    Se usa para el <select> de municipio (aunque normalmente usarás 395 por defecto).
    """
    return ejecutar_consulta(
        """
        SELECT idtbl_municipios, Nombre_Municipio
        FROM bd_tbl_comunes.tbl_municipios
        ORDER BY Nombre_Municipio
        """,
        devolver_dict=True,
        database="bd_tbl_comunes",
    )


def cargar_vado_por_id(idtbl_vados: int) -> dict | None:
    """
    Devuelve un vado por idtbl_vados desde control_via_publica.tbl_vados.
    Si no existe, devuelve None.
    """
    filas = ejecutar_consulta(
        """
        SELECT
            idtbl_vados,
            idtbl_tipos_de_vias,
            idtbl_calles,
            Puerta,
            idtbl_municipios,
            idtbl_proveedores,
            numero_vado,
            idtbl_vado_anterior,
            idtbl_propietario_anterior,
            fecha_alta,
            fecha_baja,
            fecha_cambio,
            idtbl_gestores,
            tipo_operacion,
            baja,
            Desc_OT,
            superficie,
            anchura,
            Via_OT,
            NIF_SP_OT,
            Nombre_SP_OT
        FROM tbl_vados
        WHERE idtbl_vados = %s
        """,
        params=(idtbl_vados,),
        devolver_dict=True,
        database="control_via_publica",
    )
    return filas[0] if filas else None


# =============================================================================
# 3. RUTAS GET: NUEVO Y EDITAR
# =============================================================================


@btn_vados_form_bp.get("/nuevo")
@login_required
@rol_required("gestor", "super_admin")
def btn_vado_form_nuevo():
    """
    GET /vados/form/nuevo
    Muestra el formulario de creación de un vado (modo = "nuevo"), sin datos previos.
    """
    tipos = cargar_tipos_de_vias()
    calles = cargar_calles_municipio_395()
    proveedores = cargar_proveedores()
    municipios = cargar_municipios()

    return render_template(
        "control_via_publica/control_vados/vados_form.html",
        modo="nuevo",
        vado=None,
        tipos_de_vias=tipos,
        calles=calles,
        proveedores=proveedores,
        municipios=municipios,
    )


@btn_vados_form_bp.get("/editar/<int:idtbl_vados>")
@login_required
@rol_required("gestor", "super_admin")
def vado_editar_form(idtbl_vados: int):
    """
    GET /vados/form/editar/<idtbl_vados>
    Muestra el formulario de edición de un vado existente (modo = "editar").
    Carga los datos del vado y las listas necesarias para los <select>.
    """
    vado = cargar_vado_por_id(idtbl_vados)
    if not vado:
        flash("Vado no encontrado", "danger")
        return redirect(url_for("btn_vados_form_bp.btn_vado_form_nuevo"))

    tipos = cargar_tipos_de_vias()
    calles = cargar_calles_municipio_395()
    proveedores = cargar_proveedores()
    municipios = cargar_municipios()

    return render_template(
        "control_via_publica/control_vados/vados_form.html",
        modo="editar",
        vado=vado,  # ← aquí debe ir la variable vado, no dict
        tipos_de_vias=tipos,
        calles=calles,
        proveedores=proveedores,
        municipios=municipios,
    )


# =============================================================================
# 4. POST /guardar: GUARDAR ALTA O EDICIÓN
# =============================================================================
# El formulario vados_form.html debe enviar (method="POST" action="/vados/form/guardar")
# al menos los siguientes campos:
#
#   - idtbl_vados             (hidden; vacío si es nuevo)
#   - numero_vado             (texto, obligatorio)
#   - idtbl_tipos_de_vias     (select, obligatorio)
#   - idtbl_calles            (select, obligatorio)
#   - idtbl_proveedores       (select, opcional)
#   - idtbl_municipios        (select, opcional; por defecto 395)
#   - Puerta                  (texto)
#   - Desc_OT                 (texto)
#   - superficie              (texto/numérico; se convierte a float)
#   - anchura                 (texto/numérico; se convierte a float)
#   - Via_OT, NIF_SP_OT, Nombre_SP_OT (textos opcionales)
#
# LÓGICA:
#   - Si idtbl_vados está vacío → INSERT (es_nuevo = True).
#   - Si idtbl_vados tiene valor → UPDATE sobre ese registro.
#
# El idtbl_gestores se obtiene SIEMPRE de g.user["idtbl_gestores"] y se guarda
# en la columna idtbl_gestores del vado.
# =============================================================================


@btn_vados_form_bp.post("/guardar")
@login_required
@rol_required("gestor", "super_admin")
def vado_guardar():
    """
    Procesa el formulario de alta/edición de vado.
    Decide automáticamente si es un INSERT o UPDATE según venga idtbl_vados.
    """
    form = request.form

    # -------------------------------------------------------------------------
    # 4.1 Determinar si es alta (INSERT) o edición (UPDATE)
    # -------------------------------------------------------------------------
    idtbl_vados_raw = form.get("idtbl_vados") or ""
    idtbl_vados = int(idtbl_vados_raw) if idtbl_vados_raw.isdigit() else None
    es_nuevo = idtbl_vados is None

    # -------------------------------------------------------------------------
    # 4.2 Lectura de campos del formulario
    # -------------------------------------------------------------------------
    numero_vado = (form.get("numero_vado") or "").strip()
    idtbl_tipos_de_vias = form.get("idtbl_tipos_de_vias") or None
    idtbl_calles = form.get("idtbl_calles") or None
    idtbl_proveedores = form.get("idtbl_proveedores") or None
    idtbl_municipios = form.get("idtbl_municipios") or "395"  # por defecto 395

    puerta = (form.get("Puerta") or "").strip()
    desc_ot = (form.get("Desc_OT") or "").strip()
    via_ot = (form.get("Via_OT") or "").strip()
    nif_sp_ot = (form.get("NIF_SP_OT") or "").strip()
    nombre_sp_ot = (form.get("Nombre_SP_OT") or "").strip()

    # Superficie y anchura permiten coma decimal; se convierten a float si hay valor
    superficie_raw = (form.get("superficie") or "").replace(",", ".").strip()
    anchura_raw = (form.get("anchura") or "").replace(",", ".").strip()
    superficie = float(superficie_raw) if superficie_raw else None
    anchura = float(anchura_raw) if anchura_raw else None

    # -------------------------------------------------------------------------
    # 4.3 Validaciones mínimas (puedes ampliarlas según tus reglas de negocio)
    # -------------------------------------------------------------------------
    if not numero_vado or not idtbl_tipos_de_vias or not idtbl_calles:
        flash(
            "Faltan datos obligatorios (número de vado, tipo de vía o calle).", "danger"
        )
        if es_nuevo:
            return redirect(url_for("btn_vados_form_bp.btn_vado_form_nuevo"))
        else:
            return redirect(
                url_for("btn_vados_form_bp.vado_editar_form", idtbl_vados=idtbl_vados)
            )

    # -------------------------------------------------------------------------
    # 4.4 Obtener el idtbl_gestores del usuario logueado
    # -------------------------------------------------------------------------
    idtbl_gestores = getattr(g, "user", {}).get("idtbl_gestores", None)
    if not idtbl_gestores:
        flash("No se ha podido determinar el gestor logueado.", "danger")
        if es_nuevo:
            return redirect(url_for("btn_vados_form_bp.btn_vado_form_nuevo"))
        else:
            return redirect(
                url_for("btn_vados_form_bp.vado_editar_form", idtbl_vados=idtbl_vados)
            )

    # -------------------------------------------------------------------------
    # 4.5 INSERT o UPDATE en base de datos
    # -------------------------------------------------------------------------
    try:
        if es_nuevo:
            # -----------------------------------------------------------------
            # 4.5.1 INSERT (ALTA DE NUEVO VADO)
            # -----------------------------------------------------------------
            sql = """
                INSERT INTO tbl_vados (
                    idtbl_tipos_de_vias,
                    idtbl_calles,
                    idtbl_municipios,
                    idtbl_proveedores,
                    numero_vado,
                    idtbl_vado_anterior,
                    idtbl_propietario_anterior,
                    fecha_alta,
                    fecha_baja,
                    fecha_cambio,
                    idtbl_gestores,
                    tipo_operacion,
                    baja,
                    Desc_OT,
                    superficie,
                    anchura,
                    Via_OT,
                    Puerta,
                    NIF_SP_OT,
                    Nombre_SP_OT
                )
                VALUES (
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    CURDATE(), %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s
                )
            """
            params = (
                int(idtbl_tipos_de_vias),
                int(idtbl_calles),
                int(idtbl_municipios),
                int(idtbl_proveedores) if idtbl_proveedores else None,
                numero_vado,
                None,  # idtbl_vado_anterior
                None,  # idtbl_propietario_anterior
                None,  # fecha_baja
                None,  # fecha_cambio
                idtbl_gestores,
                "ALTA",
                0,  # baja = 0 (activo)
                desc_ot,
                superficie,
                anchura,
                via_ot,
                puerta,
                nif_sp_ot,
                nombre_sp_ot,
            )
            ejecutar_non_query(sql, params=params, database="control_via_publica")
            flash("Vado creado correctamente.", "success")

        else:
            # -----------------------------------------------------------------
            # 4.5.2 UPDATE (EDICIÓN DE VADO EXISTENTE)
            # -----------------------------------------------------------------
            sql = """
                UPDATE tbl_vados
                SET
                    idtbl_tipos_de_vias = %s,
                    idtbl_calles = %s,
                    idtbl_municipios = %s,
                    idtbl_proveedores = %s,
                    numero_vado = %s,
                    fecha_cambio = NOW(),
                    idtbl_gestores = %s,
                    Desc_OT = %s,
                    superficie = %s,
                    anchura = %s,
                    Via_OT = %s,
                    Puerta = %s,
                    NIF_SP_OT = %s,
                    Nombre_SP_OT = %s
                WHERE idtbl_vados = %s
            """
            params = (
                int(idtbl_tipos_de_vias),
                int(idtbl_calles),
                int(idtbl_municipios),
                int(idtbl_proveedores) if idtbl_proveedores else None,
                numero_vado,
                idtbl_gestores,
                desc_ot,
                superficie,
                anchura,
                via_ot,
                puerta,
                nif_sp_ot,
                nombre_sp_ot,
                idtbl_vados,
            )
            ejecutar_non_query(sql, params=params, database="control_via_publica")
            flash("Vado actualizado correctamente.", "success")

    except Exception as exc:
        # Cualquier error en BD se comunica al usuario y se redirige al formulario
        flash(f"Error al guardar el vado: {exc}", "danger")
        if es_nuevo:
            return redirect(url_for("btn_vados_form_bp.btn_vado_form_nuevo"))
        else:
            return redirect(
                url_for("btn_vados_form_bp.vado_editar_form", idtbl_vados=idtbl_vados)
            )

    # -------------------------------------------------------------------------
    # 4.6 Redirección tras guardar
    # -------------------------------------------------------------------------
    # Aquí puedes:
    #   - Redirigir a un listado de vados.
    #   - Volver al formulario en blanco (nuevo).
    #   - Volver al formulario del vado recién guardado.
    #
    # Por simplicidad:
    #   - En alta volvemos al formulario nuevo.
    #   - En edición volvemos al propio formulario de ese vado.
    # -------------------------------------------------------------------------
    if es_nuevo:
        return redirect(url_for("btn_vados_form_bp.btn_vado_form_nuevo"))
    else:
        return redirect(
            url_for("btn_vados_form_bp.vado_editar_form", idtbl_vados=idtbl_vados)
        )
