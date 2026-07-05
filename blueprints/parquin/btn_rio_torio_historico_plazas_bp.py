"""
Río Torío · Histórico de plazas
================================

0. INTRODUCCIÓN
---------------
Este módulo gestiona el histórico de ocupación de plazas del parking de camiones
de Río Torío. Centraliza las operaciones de:
- listado global del histórico;
- detalle por plaza;
- alta y edición de registros individuales;
- validación de coherencia de intervalos de fechas y forma de pago;
- restricción de acceso a usuarios con rol super_admin.

El objetivo es garantizar que los periodos de ocupación por plaza y proveedor
sean consistentes (sin solapamientos, sin más de un intervalo abierto por plaza,
con forma de pago definida) y ofrecer una interfaz única para consultar y editar
dicho histórico.

Author: Tino Hierro
Date: 2026-06-24
"""

from __future__ import annotations

from datetime import date
from typing import Any

from flask import (
    Blueprint,
    render_template,
    current_app,
    request,
    redirect,
    url_for,
)

from db import ejecutar_query, ejecutar_non_query
from services.helpers import rol_required


# =============================================================================
# 1. BLUEPRINT: HISTÓRICO DE PLAZAS RÍO TORÍO
# =============================================================================
# 1.1. Definición del blueprint
#      Este blueprint agrupa las rutas relacionadas con la consulta y
#      edición del histórico de ocupación de plazas del parking de
#      camiones Río Torío. Incluye:
#      - listado global de histórico;
#      - detalle por plaza (listado + alta/edición).
btn_rio_torio_historico_plazas_bp = Blueprint(
    "btn_rio_torio_historico_plazas_bp",
    __name__,
    url_prefix="/parquin/rio_torio/historico_plazas",
)


# =============================================================================
# 2. SQL BASE: CONSULTA GLOBAL DE HISTÓRICO
# =============================================================================
# 2.1. SQL_HISTORICO_PLAZAS
#      Consulta el listado completo de histórico, uniendo:
#      - tbl_historico_plazas (Río Torío),
#      - tbl_plazas (para código de plaza),
#      - bd_tbl_comunes.tbl_proveedores (para razón social del proveedor).
SQL_HISTORICO_PLAZAS = """
    SELECT
        h.idtbl_historico_plazas,
        h.idtbl_plazas,
        pz.codigo_plazas        AS codigo_plaza,
        h.idtbl_proveedores,
        pr.Nombre_Razon_Social  AS proveedor,
        h.fecha_inicio,
        h.fecha_fin,
        h.exp_solicitud_fin,
        h.forma_pago,
        h.observaciones,
        h.idtbl_usuarios,
        h.exp_solicitud_inicio,
        h.exp_solicitud_cambio
    FROM tbl_historico_plazas AS h
    LEFT JOIN tbl_plazas AS pz
           ON pz.idtbl_plazas = h.idtbl_plazas
    LEFT JOIN bd_tbl_comunes.tbl_proveedores AS pr
           ON pr.Idtbl_proveedores = h.idtbl_proveedores
    ORDER BY h.idtbl_historico_plazas DESC
"""


# =============================================================================
# 3. HELPERS DE FECHAS E INTERVALOS
# =============================================================================

def _parse_fecha(fecha_str: str | None) -> date | None:
    """
    3.1. _parse_fecha
    -----------------
    Convierte una fecha ISO `YYYY-MM-DD` en un objeto `date`.

    Args:
        fecha_str (str | None): Fecha en formato ISO o None.

    Returns:
        date | None: Fecha convertida o None si la entrada está vacía.

    Uso:
        Se emplea en la vista de detalle por plaza para convertir las
        fechas recibidas desde el formulario antes de validarlas y
        almacenarlas.
    """
    if not fecha_str:
        return None
    return date.fromisoformat(fecha_str)


def _validar_intervalo_fechas(
    fecha_inicio: date | None,
    fecha_fin: date | None,
) -> None:
    """
    3.2. _validar_intervalo_fechas
    ------------------------------
    Valida la coherencia básica entre fecha_inicio y fecha_fin.

    Reglas:
        - fecha_inicio es obligatoria;
        - si hay fecha_fin, fecha_inicio no puede ser posterior.

    Args:
        fecha_inicio (date | None): Fecha de inicio del intervalo.
        fecha_fin (date | None): Fecha de fin del intervalo.

    Raises:
        ValueError: Si falta fecha_inicio o si fecha_inicio > fecha_fin.

    Uso:
        Se invoca desde _validar_historico_plaza antes de comprobar
        solapamientos o intervalos abiertos.
    """
    if not fecha_inicio:
        raise ValueError("La fecha de inicio es obligatoria.")

    if fecha_fin and fecha_inicio > fecha_fin:
        raise ValueError("La fecha de inicio no puede ser posterior a la fecha de fin.")


def _intervalos_se_solapan(
    inicio1: date,
    fin1: date | None,
    inicio2: date,
    fin2: date | None,
) -> bool:
    """
    3.3. _intervalos_se_solapan
    ---------------------------
    Comprueba si dos intervalos de fechas se solapan.

    Definición:
        - Un intervalo [inicio, fin] se considera abierto si fin es None.
        - Para comparar, se sustituye None por date.max.

    Args:
        inicio1 (date): Inicio del primer intervalo.
        fin1 (date | None): Fin del primer intervalo.
        inicio2 (date): Inicio del segundo intervalo.
        fin2 (date | None): Fin del segundo intervalo.

    Returns:
        bool: True si los intervalos se solapan, False en caso contrario.

    Uso:
        Se usa en _validar_historico_plaza para detectar solapamientos
        entre el nuevo intervalo y los existentes en la misma plaza.
    """
    fin1_real = fin1 or date.max
    fin2_real = fin2 or date.max
    return inicio1 <= fin2_real and inicio2 <= fin1_real


def _validar_historico_plaza(
    *,
    id_historico: int | None,
    id_plaza: int,
    id_proveedor: int,
    fecha_inicio: date,
    fecha_fin: date | None,
    forma_pago: str | None,
) -> None:
    """
    3.4. _validar_historico_plaza
    ------------------------------
    Valida que el histórico de una plaza sea coherente antes de guardar.

    Reglas:
        - la forma de pago es obligatoria;
        - la fecha de inicio es obligatoria;
        - no puede haber fecha_inicio posterior a fecha_fin;
        - no puede haber solapamientos para la misma plaza;
        - no puede haber más de un intervalo abierto (sin fecha_fin) por plaza;
        - si cambia la forma de pago para un intervalo abierto del mismo proveedor,
          debe tratarse como un nuevo intervalo (no se permite dos abiertos
          con distinta forma de pago).

    Args:
        id_historico (int | None): ID del registro en edición o None si es alta.
        id_plaza (int): ID de la plaza.
        id_proveedor (int): ID del proveedor.
        fecha_inicio (date): Fecha de inicio del intervalo.
        fecha_fin (date | None): Fecha de fin del intervalo.
        forma_pago (str | None): Forma de pago.

    Raises:
        ValueError: Si alguna regla de coherencia se incumple.

    Uso:
        Se invoca tanto en altas como en ediciones de registros de
        tbl_historico_plazas antes de ejecutar el INSERT/UPDATE.
    """
    if not forma_pago:
        raise ValueError("La forma de pago es obligatoria.")

    _validar_intervalo_fechas(fecha_inicio, fecha_fin)

    filas: list[dict[str, Any]] = ejecutar_query(
        """
        SELECT
            idtbl_historico_plazas,
            idtbl_plazas,
            idtbl_proveedores,
            fecha_inicio,
            fecha_fin,
            forma_pago
        FROM tbl_historico_plazas
        WHERE idtbl_plazas = %s
        """,
        params=(id_plaza,),
        nombre_bd="parquin_camiones",
    )

    hay_abierto_distinto = False

    for fila in filas:
        id_hist_existente = fila["idtbl_historico_plazas"]

        # Ignoramos el propio registro en edición
        if id_historico and id_hist_existente == id_historico:
            continue

        fi_exist = fila["fecha_inicio"]
        ff_exist = fila["fecha_fin"]
        forma_pago_exist = fila.get("forma_pago")
        id_prov_exist = fila["idtbl_proveedores"]

        # Marcamos si hay otro intervalo abierto
        if ff_exist is None and fecha_fin is None:
            hay_abierto_distinto = True

        # Comprobamos solapamientos
        if _intervalos_se_solapan(fecha_inicio, fecha_fin, fi_exist, ff_exist):
            raise ValueError(
                "El periodo indicado se solapa con otro periodo ya registrado para esta plaza."
            )

        # Comprobamos cambio de forma de pago en intervalo abierto del mismo proveedor
        if (
            ff_exist is None
            and fecha_fin is None
            and id_prov_exist == id_proveedor
            and forma_pago_exist != forma_pago
        ):
            raise ValueError(
                "Ya existe un intervalo abierto para esta plaza y proveedor con otra forma de pago."
            )

    if hay_abierto_distinto:
        raise ValueError(
            "Ya existe otra fila abierta (sin fecha de fin) para esta plaza."
        )


# =============================================================================
# 4. VISTA: LISTADO GLOBAL DEL HISTÓRICO
# =============================================================================

@btn_rio_torio_historico_plazas_bp.route("/", methods=["GET"])
@rol_required("super_admin")
def btn_rio_torio_historico_plazas():
    """
    4.1. btn_rio_torio_historico_plazas
    -----------------------------------
    Muestra el listado global del histórico de plazas de Río Torío.

    Comportamiento:
        - Carga todas las filas del histórico de plazas usando SQL_HISTORICO_PLAZAS.
        - Carga catálogo de plazas (id + código).
        - Carga catálogo de proveedores (id + NIF + razón social).
        - Gestiona errores mediante logging y un mensaje en pantalla.

    Returns:
        str: Render del template del listado global.
    """
    error = None

    try:
        filas = ejecutar_query(
            SQL_HISTORICO_PLAZAS,
            params=(),
            nombre_bd="parquin_camiones",
        )
    except Exception as e:
        current_app.logger.exception("Error al obtener histórico de plazas (Río Torío)")
        filas = []
        error = f"Error al consultar el histórico de plazas: {e}"

    try:
        plazas = ejecutar_query(
            """
            SELECT
                idtbl_plazas AS id,
                codigo_plazas AS codigo_plaza
            FROM tbl_plazas
            ORDER BY codigo_plazas
            """,
            params=(),
            nombre_bd="parquin_camiones",
        )
    except Exception as e:
        current_app.logger.exception("Error al cargar catálogo de plazas (Río Torío)")
        plazas = []
        error = (error or "") + f" Error al cargar plazas: {e}"

    try:
        proveedores = ejecutar_query(
            """
            SELECT
                Idtbl_proveedores AS id,
                NIF AS nif,
                Nombre_Razon_Social AS nombre
            FROM tbl_proveedores
            ORDER BY Nombre_Razon_Social
            """,
            params=(),
            nombre_bd="bd_tbl_comunes",
        )
    except Exception as e:
        current_app.logger.exception("Error al cargar proveedores (Río Torío)")
        proveedores = []
        error = (error or "") + f" Error al cargar proveedores: {e}"

    return render_template(
        "parquin/rio_torio/rio_torio_historico_plazas.html",
        error=error,
        filas=filas,
        plazas=plazas,
        proveedores=proveedores,
    )


# =============================================================================
# 5. VISTA: DETALLE Y EDICIÓN POR PLAZA
# =============================================================================

@btn_rio_torio_historico_plazas_bp.route(
    "/plaza/<int:id_plaza>",
    methods=["GET", "POST"],
)
@rol_required("super_admin")
def rio_torio_historico_plazas(id_plaza: int) -> str:
    """
    5.1. rio_torio_historico_plazas
    --------------------------------
    Muestra y edita el histórico de una plaza concreta.

    Comportamiento:
        - GET:
            · Carga proveedores, plazas y filas de histórico de la plaza.
            · Muestra el detalle y permite seleccionar registros para edición.
        - POST:
            · Lee los campos del formulario (alta o edición).
            · Valida coherencia mediante _validar_historico_plaza.
            · Si accion == "editar" y hay id_historico_int, hace UPDATE.
            · Si no, hace INSERT.
            · Redirige de nuevo al detalle de la plaza (PRG).

    Args:
        id_plaza (int): ID de la plaza recibida por URL.

    Returns:
        str: Render del template de detalle por plaza.
    """
    error: str | None = None

    if request.method == "POST":
        try:
            accion = request.form.get("accion")
            id_historico_str = request.form.get("idtbl_historico_plazas")
            id_plaza_form = request.form.get("idtbl_plazas")
            id_proveedor = request.form.get("idtbl_proveedores")
            fecha_inicio_str = request.form.get("fecha_inicio")
            fecha_fin_str = request.form.get("fecha_fin") or None
            exp_fin = request.form.get("exp_solicitud_fin") or None
            forma_pago = request.form.get("forma_pago") or None
            observaciones = request.form.get("observaciones") or None
            exp_inicio = request.form.get("exp_solicitud_inicio") or None
            exp_cambio = request.form.get("exp_solicitud_cambio") or None
            id_usuario = request.form.get("idtbl_usuarios") or None

            # 5.1.1. Conversión básica de IDs
            id_plaza_final = int(id_plaza_form) if id_plaza_form else id_plaza
            id_proveedor_int = int(id_proveedor) if id_proveedor else None
            id_historico_int = int(id_historico_str) if id_historico_str else None
            id_usuario_int = int(id_usuario) if id_usuario else None

            if not id_proveedor_int:
                raise ValueError(
                    "Debes seleccionar un proveedor antes de guardar el histórico."
                )

            # 5.1.2. Conversión y validación de fechas
            fecha_inicio = _parse_fecha(fecha_inicio_str)
            fecha_fin = _parse_fecha(fecha_fin_str)

            _validar_historico_plaza(
                id_historico=id_historico_int,
                id_plaza=id_plaza_final,
                id_proveedor=id_proveedor_int,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
                forma_pago=forma_pago,
            )

            # 5.1.3. Persistencia: UPDATE vs INSERT
            if accion == "editar" and id_historico_int:
                # EDICIÓN: actualizar el registro existente en tbl_historico_plazas.
                ejecutar_non_query(
                    """
                    UPDATE tbl_historico_plazas
                    SET
                        idtbl_plazas = %s,
                        idtbl_proveedores = %s,
                        fecha_inicio = %s,
                        fecha_fin = %s,
                        exp_solicitud_fin = %s,
                        forma_pago = %s,
                        observaciones = %s,
                        idtbl_usuarios = %s,
                        exp_solicitud_inicio = %s,
                        exp_solicitud_cambio = %s
                    WHERE idtbl_historico_plazas = %s
                    """,
                    params=(
                        id_plaza_final,
                        id_proveedor_int,
                        fecha_inicio_str,
                        fecha_fin_str,
                        exp_fin,
                        forma_pago,
                        observaciones,
                        id_usuario_int,
                        exp_inicio,
                        exp_cambio,
                        id_historico_int,
                    ),
                    nombre_bd="parquin_camiones",
                )
            else:
                # ALTA: insertar nuevo registro en tbl_historico_plazas.
                ejecutar_non_query(
                    """
                    INSERT INTO tbl_historico_plazas
                        (idtbl_plazas, idtbl_proveedores, fecha_inicio, fecha_fin,
                         exp_solicitud_fin, forma_pago, observaciones, idtbl_usuarios,
                         exp_solicitud_inicio, exp_solicitud_cambio)
                    VALUES
                        (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    params=(
                        id_plaza_final,
                        id_proveedor_int,
                        fecha_inicio_str,
                        fecha_fin_str,
                        exp_fin,
                        forma_pago,
                        observaciones,
                        id_usuario_int,
                        exp_inicio,
                        exp_cambio,
                    ),
                    nombre_bd="parquin_camiones",
                )

            # 5.1.4. PRG: redirigir al detalle de la plaza tras guardar
            return redirect(
                url_for(
                    "btn_rio_torio_historico_plazas_bp.rio_torio_historico_plazas",
                    id_plaza=id_plaza_final,
                )
            )

        except Exception as e:
            current_app.logger.exception(
                "Error al guardar histórico de la plaza (Río Torío)"
            )
            error = f"Error al guardar histórico de la plaza: {e}"

    # 5.2. GET: carga de catálogos y filas de histórico para la plaza
    try:
        proveedores = ejecutar_query(
            """
            SELECT
                Idtbl_proveedores AS id,
                NIF AS nif,
                Nombre_Razon_Social AS nombre
            FROM tbl_proveedores
            ORDER BY Nombre_Razon_Social
            """,
            params=(),
            nombre_bd="bd_tbl_comunes",
        )
    except Exception as e:
        current_app.logger.exception(
            "Error al cargar proveedores para detalle (Río Torío)"
        )
        proveedores = []
        error = (error or "") + f" Error al cargar proveedores: {e}"

    try:
        plazas = ejecutar_query(
            """
            SELECT
                idtbl_plazas AS id,
                codigo_plazas AS nombre
            FROM tbl_plazas
            ORDER BY codigo_plazas
            """,
            params=(),
            nombre_bd="parquin_camiones",
        )
    except Exception as e:
        current_app.logger.exception(
            "Error al cargar plazas para detalle (Río Torío)"
        )
        plazas = []
        error = (error or "") + f" Error al cargar plazas: {e}"

    try:
        filas = ejecutar_query(
            """
            SELECT
                h.idtbl_historico_plazas,
                h.idtbl_plazas,
                pz.codigo_plazas AS codigo_plaza,
                h.idtbl_proveedores,
                pr.Nombre_Razon_Social AS proveedor,
                h.fecha_inicio,
                h.fecha_fin,
                h.exp_solicitud_fin,
                h.forma_pago,
                h.observaciones,
                h.idtbl_usuarios,
                h.exp_solicitud_inicio,
                h.exp_solicitud_cambio
            FROM tbl_historico_plazas AS h
            LEFT JOIN tbl_plazas AS pz
                   ON pz.idtbl_plazas = h.idtbl_plazas
            LEFT JOIN bd_tbl_comunes.tbl_proveedores AS pr
                   ON pr.Idtbl_proveedores = h.idtbl_proveedores
            WHERE h.idtbl_plazas = %s
            ORDER BY h.fecha_inicio DESC, h.idtbl_historico_plazas DESC
            """,
            params=(id_plaza,),
            nombre_bd="parquin_camiones",
        )
    except Exception as e:
        current_app.logger.exception(
            "Error al obtener histórico de la plaza (Río Torío)"
        )
        filas = []
        error = (error or "") + f" Error al consultar histórico de la plaza: {e}"

    codigo_plaza = filas[0]["codigo_plaza"] if filas else None

    return render_template(
        "parquin/rio_torio/rio_torio_historico_plaza.html",
        error=error,
        filas=filas,
        proveedores=proveedores,
        plazas=plazas,
        id_plaza=id_plaza,
        codigo_plaza=codigo_plaza,
    )