"""
===============================================================================
RÍO TORÍO · HISTÓRICO DE PLAZAS (Blueprint Flask)
===============================================================================

[0] INTRODUCCIÓN GENERAL
------------------------
Este módulo implementa el blueprint de Flask responsable de la gestión del
histórico de ocupación de plazas del parking de camiones de Río Torío.

Centraliza en una única unidad de código:
- listado global del histórico;
- detalle por plaza;
- alta y edición de intervalos;
- validaciones de coherencia temporal y funcional;
- carga de catálogos para desplegables de la plantilla;
- control de acceso por rol (super_admin).

El propósito funcional es asegurar integridad del histórico:
- sin solapamientos en una misma plaza,
- sin intervalos incoherentes (inicio > fin),
- sin intervalos abiertos simultáneos para una misma plaza,
- con forma de pago obligatoria.

Además, el catálogo de proveedores se obtiene de `bd_tbl_comunes` y se filtra
por presencia en parking mediante `parquin_camiones.tbl_usuarios` para poblar
selectores con datos relevantes.

Autor: Tinito
Fecha: 07/07/2026
Repositorio: thierro23-cloud/tubby_app
Archivo: blueprints/parquin/btn_rio_torio_historico_plazas_bp.py
"""

from __future__ import annotations

# =============================================================================
# [1] IMPORTACIONES Y DEPENDENCIAS
# =============================================================================
# 1.1. Librería estándar
#      - date: validaciones y comparación de intervalos temporales.
#      - Any: tipado flexible en resultados de consultas.
from datetime import date
from typing import Any

# 1.2. Flask
#      - Blueprint: encapsula rutas de esta funcionalidad.
#      - render_template: render de vistas HTML.
#      - current_app: logging centralizado.
#      - request: lectura de datos de formulario.
#      - redirect / url_for: patrón PRG tras persistencia.
from flask import (
    Blueprint,
    render_template,
    current_app,
    request,
    redirect,
    url_for,
)

# 1.3. Acceso a datos
#      - ejecutar_query: consultas SELECT.
#      - ejecutar_non_query: INSERT/UPDATE.
from db import ejecutar_query, ejecutar_non_query

# 1.4. Seguridad/autorización
#      - rol_required("super_admin"): restringe acceso a perfiles autorizados.
from services.helpers import rol_required


# =============================================================================
# [2] BLUEPRINT Y RUTA BASE
# =============================================================================
# 2.1. Definición del blueprint principal para histórico de plazas.
#      URL base:
#      /parquin/rio_torio/historico_plazas
btn_rio_torio_historico_plazas_bp = Blueprint(
    "btn_rio_torio_historico_plazas_bp",
    __name__,
    url_prefix="/parquin/rio_torio/historico_plazas",
)


# =============================================================================
# [3] SQL BASE · LISTADO GLOBAL DE HISTÓRICO
# =============================================================================
# 3.1. Consulta principal del listado global:
#      - histórico (tbl_historico_plazas)
#      - catálogo de plazas (tbl_plazas)
#      - datos de proveedor (bd_tbl_comunes.tbl_proveedores)
#
# 3.2. Se incorpora:
#      - NIF
#      - nombre/apellidos
#      - nombre_razon_social
#      - campo "proveedor" normalizado con COALESCE para mostrar texto amigable
SQL_HISTORICO_PLAZAS = """
    SELECT
        h.idtbl_historico_plazas,
        h.idtbl_plazas,
        pz.codigo_plazas AS codigo_plaza,
        h.idtbl_proveedores,
        pr.NIF AS nif,
        pr.nombre AS nombre,
        pr.apellidos AS apellidos,
        pr.Nombre_Razon_Social AS nombre_razon_social,
        COALESCE(
            NULLIF(pr.Nombre_Razon_Social, ''),
            CONCAT_WS(' ', pr.apellidos, pr.nombre)
        ) AS proveedor,
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
# [4] HELPERS DE FECHAS E INTEGRIDAD DE INTERVALOS
# =============================================================================
def _parse_fecha(fecha_str: str | None) -> date | None:
    """
    [4.1] Convierte fecha ISO (YYYY-MM-DD) a date.

    Args:
        fecha_str: Fecha en cadena o None.

    Returns:
        date | None
    """
    if not fecha_str:
        return None
    return date.fromisoformat(fecha_str)


def _validar_intervalo_fechas(
    fecha_inicio: date | None,
    fecha_fin: date | None,
) -> None:
    """
    [4.2] Valida coherencia básica del intervalo temporal.

    Reglas:
    - fecha_inicio obligatoria;
    - si fecha_fin existe, no puede ser anterior a fecha_inicio.

    Raises:
        ValueError si falla validación.
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
    [4.3] Determina si dos intervalos se solapan.

    Nota:
    - Un intervalo abierto (fin=None) se trata como fin=date.max.

    Returns:
        True si hay solape, False si no.
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
    [4.4] Valida coherencia completa de histórico antes de guardar.

    Reglas aplicadas:
    - forma_pago obligatoria;
    - intervalo temporal válido;
    - sin solapamiento para la misma plaza;
    - sin doble intervalo abierto para la misma plaza;
    - no permitir otro abierto del mismo proveedor con forma_pago distinta.

    Raises:
        ValueError ante inconsistencia.
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

        # Ignorar auto-colisión cuando se edita el mismo registro.
        if id_historico and id_hist_existente == id_historico:
            continue

        fi_exist = fila["fecha_inicio"]
        ff_exist = fila["fecha_fin"]
        forma_pago_exist = fila.get("forma_pago")
        id_prov_exist = fila["idtbl_proveedores"]

        # Marcar existencia de otro abierto.
        if ff_exist is None and fecha_fin is None:
            hay_abierto_distinto = True

        # Validar solapamiento temporal.
        if _intervalos_se_solapan(fecha_inicio, fecha_fin, fi_exist, ff_exist):
            raise ValueError(
                "El periodo indicado se solapa con otro periodo ya registrado para esta plaza."
            )

        # Validar cambio de forma de pago en abierto del mismo proveedor.
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
# [5] HELPERS DE CATÁLOGOS PARA DESPLEGABLES
# =============================================================================
def _obtener_catalogo_plazas() -> list[dict[str, Any]]:
    """
    [5.1] Catálogo de plazas para combo/select.

    Returns:
        [{id, codigo_plaza}, ...]
    """
    return ejecutar_query(
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


def _obtener_catalogo_proveedores_parking() -> list[dict[str, Any]]:
    """
    [5.2] Catálogo de proveedores para combo/select.

    Origen:
    - bd_tbl_comunes.tbl_proveedores

    Filtro:
    - Solo proveedores vinculados al entorno parking, mediante EXISTS sobre
      parquin_camiones.tbl_usuarios.

    Campos:
    - id, nif, nombre, apellidos, nombre_razon_social, etiqueta

    Nota importante:
    Si en tu esquema el vínculo NO es `tbl_usuarios.idtbl_proveedores`,
    sustituir ese campo por el real.
    """
    return ejecutar_query(
        """
        SELECT
            p.Idtbl_proveedores AS id,
            p.NIF AS nif,
            p.nombre AS nombre,
            p.apellidos AS apellidos,
            p.Nombre_Razon_Social AS nombre_razon_social,
            COALESCE(
                NULLIF(p.Nombre_Razon_Social, ''),
                CONCAT_WS(' ', p.apellidos, p.nombre)
            ) AS etiqueta
        FROM bd_tbl_comunes.tbl_proveedores AS p
        WHERE EXISTS (
            SELECT 1
            FROM parquin_camiones.tbl_usuarios u
            WHERE u.idtbl_proveedores = p.Idtbl_proveedores
        )
        ORDER BY etiqueta
        """,
        params=(),
        nombre_bd="bd_tbl_comunes",
    )


# =============================================================================
# [6] RUTA GET · LISTADO GLOBAL DEL HISTÓRICO
# =============================================================================
@btn_rio_torio_historico_plazas_bp.route("/", methods=["GET"])
@rol_required("super_admin")
def btn_rio_torio_historico_plazas():
    """
    [6.1] Vista de listado global.

    Carga:
    - filas de histórico global;
    - catálogo de plazas;
    - catálogo de proveedores filtrado para parking.

    Render:
    - parquin/rio_torio/rio_torio_historico_plazas.html
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
        plazas = _obtener_catalogo_plazas()
    except Exception as e:
        current_app.logger.exception("Error al cargar catálogo de plazas (Río Torío)")
        plazas = []
        error = (error or "") + f" Error al cargar plazas: {e}"

    try:
        proveedores = _obtener_catalogo_proveedores_parking()
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
# [7] RUTA GET/POST · DETALLE POR PLAZA + ALTA/EDICIÓN
# =============================================================================
@btn_rio_torio_historico_plazas_bp.route(
    "/plaza/<int:id_plaza>",
    methods=["GET", "POST"],
)
@rol_required("super_admin")
def rio_torio_historico_plazas(id_plaza: int) -> str:
    """
    [7.1] Detalle de una plaza concreta y persistencia de formulario.

    GET:
    - carga catálogos y filas de la plaza;
    - renderiza plantilla de detalle.

    POST:
    - parsea formulario;
    - valida reglas de negocio;
    - UPDATE si accion=editar;
    - INSERT en caso contrario;
    - redirige (patrón PRG).

    Template:
    - parquin/rio_torio/rio_torio_historico_plaza.html
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

            # [7.1.1] Conversión de ids
            id_plaza_final = int(id_plaza_form) if id_plaza_form else id_plaza
            id_proveedor_int = int(id_proveedor) if id_proveedor else None
            id_historico_int = int(id_historico_str) if id_historico_str else None
            id_usuario_int = int(id_usuario) if id_usuario else None

            if not id_proveedor_int:
                raise ValueError(
                    "Debes seleccionar un proveedor antes de guardar el histórico."
                )

            # [7.1.2] Conversión + validación de fechas
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

            # [7.1.3] Persistencia
            if accion == "editar" and id_historico_int:
                # UPDATE de registro existente.
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
                # INSERT de nuevo intervalo.
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

            # [7.1.4] Patrón PRG (Post/Redirect/Get)
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

    # [7.2] Carga de catálogos para GET y para POST con error
    try:
        proveedores = _obtener_catalogo_proveedores_parking()
    except Exception as e:
        current_app.logger.exception(
            "Error al cargar proveedores para detalle (Río Torío)"
        )
        proveedores = []
        error = (error or "") + f" Error al cargar proveedores: {e}"

    try:
        plazas = _obtener_catalogo_plazas()
    except Exception as e:
        current_app.logger.exception("Error al cargar plazas para detalle (Río Torío)")
        plazas = []
        error = (error or "") + f" Error al cargar plazas: {e}"

    # [7.3] Carga de filas históricas de la plaza, incluyendo nif/nombre/apellidos
    try:
        filas = ejecutar_query(
            """
            SELECT
                h.idtbl_historico_plazas,
                h.idtbl_plazas,
                pz.codigo_plazas AS codigo_plaza,
                h.idtbl_proveedores,
                pr.NIF AS nif,
                pr.nombre AS nombre,
                pr.apellidos AS apellidos,
                pr.Nombre_Razon_Social AS nombre_razon_social,
                COALESCE(
                    NULLIF(pr.Nombre_Razon_Social, ''),
                    CONCAT_WS(' ', pr.apellidos, pr.nombre)
                ) AS proveedor,
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

    # [7.4] Render final con todos los datos requeridos por la plantilla
    return render_template(
        "parquin/rio_torio/rio_torio_historico_plaza.html",
        error=error,
        filas=filas,
        proveedores=proveedores,
        plazas=plazas,
        id_plaza=id_plaza,
        codigo_plaza=codigo_plaza,
    )
