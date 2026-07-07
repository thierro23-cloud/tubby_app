from __future__ import annotations

from typing import List, Dict, Any
import datetime

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

from blueprints.parquin.btn_rio_torio_asignar_plaza_bp import (
    _generar_pdf_y_docx_adjudicacion,
)

# =============================================================================
# 0. INTRODUCCIÓN Y OBJETIVO DEL MÓDULO
# =============================================================================
# 0.1. Descripción general
#      Este módulo define el blueprint Flask encargado de gestionar las
#      solicitudes de plazas del parking "Río Torío". Incluye:
#      - Navegación y helpers de consulta (solicitudes, proveedores, plazas).
#      - Helpers de escritura (inserción de solicitudes, actualización de
#        forma de pago, alta en histórico de plazas).
#      - Lógica de aprobación y rechazo de solicitudes, con comprobaciones
#        adicionales de coherencia (plaza libre e histórico por expediente).
#      - Vista principal GET/POST para operar desde una única pantalla:
#        alta, listado, aprobación, rechazo y asignación desde expediente.
#
# 0.2. Contexto funcional
#      El flujo típico de uso es:
#      - El gestor accede al módulo con permisos adecuados.
#      - Da de alta nuevas solicitudes vinculadas a un expediente.
#      - Desde esta misma vista puede aprobarlas (asignando plazas) o
#        rechazarlas, y también asignar plazas libres a partir de un
#        expediente con histórico ya existente.
#
# 0.3. Notas de diseño
#      - Se usa el patrón PRG (Post/Redirect/Get) para evitar reenviar
#        formularios si el usuario refresca la página.
#      - Las operaciones sobre BD se delegan en helpers ejecutar_query y
#        ejecutar_non_query, que deben gestionar conexiones, errores y
#        seguridad (parametrización) de forma centralizada.
#      - La coherencia avanzada de intervalos de histórico (solapamientos,
#        cierres de periodos, etc.) se gestiona a nivel de módulo de
#        histórico, no aquí.


# =============================================================================
# 1. BLUEPRINT Y CONFIGURACIÓN BÁSICA
# =============================================================================
# 1.1. Definición del blueprint para el botón de solicitudes Río Torío
#      Este blueprint agrupa todas las rutas y lógica relacionadas con
#      la gestión de solicitudes de plazas del parking "Río Torío".
btn_rio_torio_solicitud_plazas_bp = Blueprint(
    "btn_rio_torio_solicitud_plazas_bp",
    __name__,
    url_prefix="/parquin/rio_torio/solicitud_plazas",
)


# =============================================================================
# 2. HELPERS DE NAVEGACIÓN Y CONSULTA
# =============================================================================


def obtener_url_retorno_rio_torio() -> str:
    """
    2.1. obtener_url_retorno_rio_torio
    ---------------------------------
    Determina la URL de retorno para el botón "Volver" en la pantalla
    de solicitudes, en función del origen almacenado en sesión.

    Valores posibles:
    - "super"          → panel_comunes_bp.panel_comunes
    - "panel_gestores" → panel_gestores_bp.panel_gestores
    - Otro / None      → panel_comunes por defecto.

    Uso:
    - Se pasa como parámetro a la plantilla para que el botón "Volver"
      retorne de forma coherente al origen desde el que se llegó a esta
      vista (super admin, panel de gestores, etc.).
    """
    origen = session.get("origen_rio_torio")
    if origen == "super":
        return url_for("panel_comunes_bp.panel_comunes")
    if origen == "panel_gestores":
        return url_for("panel_gestores_bp.panel_gestores")
    return url_for("panel_comunes_bp.panel_comunes")


def _rt_obtener_solicitudes() -> List[Dict[str, Any]]:
    """
    2.2. _rt_obtener_solicitudes
    ----------------------------
    Recupera el listado completo de solicitudes de plazas, incluyendo
    información del proveedor y de la plaza asociada si la hubiera.

    JOINs:
    - parquin_camiones.tbl_solicitudes_plazas AS s
    - bd_tbl_comunes.tbl_proveedores AS p
    - parquin_camiones.tbl_plazas AS pl

    Campos relevantes:
    - s.idtbl_solicitudes_plazas    : ID de la solicitud.
    - s.idtbl_usuarios              : ID de usuario/parquin.
    - s.idtbl_plazas                : ID de plaza solicitada/asignada.
    - s.n_expediente                : número de expediente administrativo.
    - s.fecha_solicitud             : fecha de alta de la solicitud.
    - s.idtbl_gestores              : ID del gestor que la trata.
    - s.solicita                    : tipo de solicitud (plaza_libre, cambio, etc.).
    - s.estado                      : pendiente | aprobada | rechazada.
    - s.motivo_rechazo              : texto de motivo, si rechazada.
    - p.NIF, p.ALIAS, p.Nombre_Razon_Social: datos del proveedor.
    - pl.codigo_plazas, pl.fila, pl.observaciones, pl.numero_expediente:
      datos de la plaza vinculada.

    Uso:
    - Se emplea en la vista GET para mostrar el listado de solicitudes
      con toda la información necesaria para la gestión desde la pantalla.
    """
    sql = """
        SELECT
            s.idtbl_solicitudes_plazas,
            s.idtbl_usuarios,
            s.idtbl_plazas,
            s.n_expediente,
            s.fecha_solicitud,
            s.idtbl_gestores,
            s.solicita,
            s.estado,
            s.motivo_rechazo,
            p.NIF,
            p.ALIAS AS proveedor_alias,
            p.Nombre_Razon_Social AS proveedor_nombre_razon_social,
            pl.codigo_plazas,
            pl.fila,
            pl.observaciones,
            pl.numero_expediente,
            pl.idtbl_usuarios AS plaza_usuario_id,
            pl.fecha_inicio,
            pl.fecha_fin,
            pl.exp_solicitud,
            pl.exp_solicitud_fin,
            pl.idtbl_inventario
        FROM parquin_camiones.tbl_solicitudes_plazas s
        LEFT JOIN bd_tbl_comunes.tbl_proveedores p
            ON s.idtbl_usuarios = p.idtbl_proveedores
        LEFT JOIN parquin_camiones.tbl_plazas pl
            ON s.idtbl_plazas = pl.idtbl_plazas
        ORDER BY s.fecha_solicitud DESC, pl.fila, pl.codigo_plazas
    """
    return ejecutar_query(sql, (), nombre_bd="parquin_camiones")


def _rt_proveedores_parquin() -> List[Dict[str, Any]]:
    """
    2.3. _rt_proveedores_parquin
    ----------------------------
    Devuelve los proveedores que tienen el flag `parquin = 1` en
    bd_tbl_comunes.tbl_proveedores, para poblar el combo de selección
    de proveedor en la pantalla.

    Campos devueltos:
    - id    : idtbl_proveedores
    - NIF   : NIF del proveedor
    - nombre: Nombre_Razon_Social (denominación completa)

    Uso:
    - Se usa en la vista GET para construir el select de proveedores
      que pueden ser abonados en el parquin de camiones.
    """
    sql = """
        SELECT
            idtbl_proveedores AS id,
            NIF,
            Nombre_Razon_Social AS nombre
        FROM bd_tbl_comunes.tbl_proveedores
        WHERE parquin = 1
        ORDER BY Nombre_Razon_Social
    """
    return ejecutar_query(sql, (), nombre_bd="bd_tbl_comunes")


def _rt_plazas_libres() -> List[Dict[str, Any]]:
    """
    2.4. _rt_plazas_libres
    ----------------------
    Devuelve las plazas actualmente libres en el parquin de camiones.

    Criterio:
    - Una plaza se considera libre si idtbl_usuarios IS NULL.

    Campos devueltos:
    - id            : idtbl_plazas.
    - codigo_plazas : identificador interno/código de la plaza.
    - fila          : fila dentro del parquin.
    - observaciones : notas asociadas a la plaza.

    Uso:
    - Se utiliza para que el gestor pueda seleccionar una plaza libre
      a la que adjudicar un abonado (solicitud nueva o asignación desde
      expediente).
    """
    sql = """
        SELECT
            idtbl_plazas AS id,
            codigo_plazas,
            fila,
            observaciones
        FROM parquin_camiones.tbl_plazas
        WHERE idtbl_usuarios IS NULL
        ORDER BY fila, codigo_plazas
    """
    return ejecutar_query(sql, (), nombre_bd="parquin_camiones")


def _rt_totales_plazas() -> Dict[str, int]:
    """
    2.5. _rt_totales_plazas
    -----------------------
    Calcula KPIs globales de plazas:

    - total_plazas          : número total de plazas registradas.
    - total_plazas_libres   : plazas libres (idtbl_usuarios IS NULL).
    - total_plazas_ocupadas : plazas ocupadas (idtbl_usuarios IS NOT NULL).

    Uso:
    - Se muestra en la interfaz para dar una visión rápida del estado
      del parquin (capacidad, ocupación y plazas disponibles).
    """
    filas = ejecutar_query(
        """
        SELECT
            COUNT(*) AS total_plazas,
            SUM(CASE WHEN idtbl_usuarios IS NULL THEN 1 ELSE 0 END)
                AS total_plazas_libres,
            SUM(CASE WHEN idtbl_usuarios IS NOT NULL THEN 1 ELSE 0 END)
                AS total_plazas_ocupadas
        FROM parquin_camiones.tbl_plazas
        """,
        (),
        nombre_bd="parquin_camiones",
    )
    if not filas:
        return {
            "total_plazas": 0,
            "total_plazas_libres": 0,
            "total_plazas_ocupadas": 0,
        }
    return filas[0]


# =============================================================================
# 3. HELPERS DE ESCRITURA: SOLICITUDES, USUARIOS, HISTÓRICO
# =============================================================================


def _rt_insertar_solicitud(datos: Dict[str, Any]) -> None:
    """
    3.1. _rt_insertar_solicitud
    ---------------------------
    Inserta una nueva solicitud en parquin_camiones.tbl_solicitudes_plazas.

    Campos esperados en `datos`:
    - idtbl_usuarios : ID del proveedor/usuario solicitante.
    - idtbl_plazas   : ID de la plaza solicitada (puede ser None).
    - n_expediente   : número de expediente administrativo.
    - idtbl_gestores : ID del gestor que registra.
    - solicita       : tipo de solicitud (plaza_libre, cambio, etc.).
    - estado         : estado inicial (normalmente 'pendiente').

    Nota:
    - fecha_solicitud se fija a NOW() directamente en el SQL.

    Uso:
    - Se llama desde la vista POST cuando se da de alta una nueva
      solicitud a través del formulario superior de la plantilla.
    """
    sql = """
        INSERT INTO parquin_camiones.tbl_solicitudes_plazas (
            idtbl_usuarios,
            idtbl_plazas,
            n_expediente,
            fecha_solicitud,
            idtbl_gestores,
            solicita,
            estado
        ) VALUES (
            %(idtbl_usuarios)s,
            %(idtbl_plazas)s,
            %(n_expediente)s,
            NOW(),
            %(idtbl_gestores)s,
            %(solicita)s,
            %(estado)s
        )
    """
    ejecutar_non_query(sql, datos, nombre_bd="parquin_camiones")


def _rt_obtener_forma_pago_usuario(id_usuario: int) -> str | None:
    """
    3.2. _rt_obtener_forma_pago_usuario
    ----------------------------------
    Recupera la forma de pago vigente del usuario en parquin_camiones.tbl_usuarios.

    Devuelve:
    - cadena con la forma de pago (mensual, trimestral, etc.) o None si
      no existe el usuario o el campo es nulo.

    Uso:
    - Se utiliza al aprobar una solicitud para reflejar la forma de pago
      vigente en el histórico de plazas.
    """
    filas = ejecutar_query(
        """
        SELECT forma_pago
        FROM parquin_camiones.tbl_usuarios
        WHERE idtbl_usuarios = %s
        """,
        (id_usuario,),
        nombre_bd="parquin_camiones",
    )
    if not filas:
        return None
    return filas[0].get("forma_pago")


def _rt_actualizar_forma_pago_usuario(id_usuario: int, forma_pago: str) -> None:
    """
    3.3. _rt_actualizar_forma_pago_usuario
    --------------------------------------
    Actualiza la forma de pago del usuario en parquin_camiones.tbl_usuarios.

    Se puede usar si quieres que la aprobación de la solicitud establezca
    una nueva forma de pago para el abonado.

    Uso:
    - Este helper está disponible para futuras ampliaciones en las que
      la aprobación de la solicitud implique un cambio de modalidad de
      pago del abonado (por ejemplo, pasar de mensual a trimestral).
    """
    ejecutar_non_query(
        """
        UPDATE parquin_camiones.tbl_usuarios
        SET forma_pago = %s
        WHERE idtbl_usuarios = %s
        """,
        (forma_pago, id_usuario),
        nombre_bd="parquin_camiones",
    )


def _rt_insertar_alta_historico(
    id_plaza: int,
    id_proveedor: int,
    fecha_inicio: str,
    forma_pago: str | None,
    exp_inicio: str,
    id_usuario: int | None = None,
) -> None:
    """
    3.4. _rt_insertar_alta_historico
    --------------------------------
    Inserta un registro de ALTA de ocupación en parquin_camiones.tbl_historico_plazas.

    Parámetros:
    - id_plaza     : ID de la plaza adjudicada.
    - id_proveedor : ID del proveedor (Idtbl_proveedores).
    - fecha_inicio : fecha (YYYY-MM-DD) de inicio de ocupación.
    - forma_pago   : forma de pago asociada al intervalo (puede ser None).
    - exp_inicio   : número de expediente de solicitud/cambio/inicio.
    - id_usuario   : ID del usuario interno (tbl_usuarios), opcional.

    Uso:
    - Se llama al aprobar una solicitud o al asignar una plaza desde
      expediente existente para dejar constancia de la ocupación en el
      histórico de plazas.
    """
    ejecutar_non_query(
        """
        INSERT INTO parquin_camiones.tbl_historico_plazas (
            idtbl_plazas,
            idtbl_proveedores,
            fecha_inicio,
            fecha_fin,
            exp_solicitud_fin,
            forma_pago,
            observaciones,
            idtbl_usuarios,
            exp_solicitud_inicio,
            exp_solicitud_cambio
        ) VALUES (
            %s, %s, %s, NULL, NULL, %s, NULL, %s, %s, NULL
        )
        """,
        (id_plaza, id_proveedor, fecha_inicio, forma_pago, id_usuario, exp_inicio),
        nombre_bd="parquin_camiones",
    )


def _rt_marcar_solicitudes_atendidas_por_historico() -> None:
    """
    3.5. _rt_marcar_solicitudes_atendidas_por_historico
    ---------------------------------------------------
    Revisa las solicitudes y marca como 'aprobada' (o 'tramitada')
    aquellas que ya tienen algún registro en tbl_historico_plazas
    asociado a su n_expediente, aunque la asignación se haya hecho
    desde otros botones o plantillas.

    Criterio:
    - s.estado = 'pendiente' y
    - existe h en tbl_historico_plazas tal que:
        h.exp_solicitud_inicio = s.n_expediente
        OR h.exp_solicitud_cambio = s.n_expediente
        OR h.exp_solicitud_fin    = s.n_expediente

    Uso:
    - Permite sincronizar las solicitudes con el histórico cuando la
      plaza se ha adjudicado desde otro flujo, evitando solicitudes
      pendientes que en realidad ya están atendidas.
    """
    ejecutar_non_query(
        """
        UPDATE parquin_camiones.tbl_solicitudes_plazas AS s
        SET s.estado           = 'aprobada',
            s.fecha_aprobacion = NOW()
        WHERE s.estado = 'pendiente'
          AND EXISTS (
            SELECT 1
            FROM parquin_camiones.tbl_historico_plazas AS h
            WHERE h.exp_solicitud_inicio = s.n_expediente
               OR h.exp_solicitud_cambio = s.n_expediente
               OR h.exp_solicitud_fin    = s.n_expediente
          )
        """,
        (),
        nombre_bd="parquin_camiones",
    )


# =============================================================================
# 4. APROBAR Y RECHAZAR SOLICITUDES
# =============================================================================


def _rt_aprobar_solicitud(
    id_solicitud: int,
    id_plaza: int,
    id_gestor: int,
    fecha_inicio_str: str,
    generar_informe: bool = False,
) -> None:
    """
    4.1. _rt_aprobar_solicitud
    --------------------------
    Aprueba una solicitud concreta y realiza la adjudicación efectiva
    de la plaza, registrando también el alta en el histórico.

    Flujo detallado:
    1) Obtiene desde tbl_solicitudes_plazas y tbl_usuarios:
       - idtbl_usuarios (abonado),
       - n_expediente,
       - idtbl_proveedores asociado al usuario.
    2) Verifica en tbl_historico_plazas si ya existe algún movimiento
       para el mismo expediente (inicio/cambio/fin). Si existe:
           - NO reasigna la plaza.
           - Marca la solicitud como 'aprobada' porque ya ha sido
             atendida desde otra plantilla/flujo.
    3) Verifica que la plaza sigue libre (idtbl_usuarios IS NULL) en
       parquin_camiones.tbl_plazas. Si está ocupada:
           - Lanza ValueError y no realiza la asignación.
    4) Si no existe histórico previo para el expediente y la plaza está
       libre:
       - Recupera la forma de pago vigente del usuario.
       - Actualiza la plaza en parquin_camiones.tbl_plazas:
           · idtbl_usuarios    = abonado,
           · fecha_inicio      = fecha_inicio_str,
           · numero_expediente = n_expediente.
       - Inserta un registro de alta en tbl_historico_plazas.
       - Marca la solicitud como 'aprobada', asignando plaza y gestor.
       - Si generar_informe=True, genera el Word+PDF mediante
         _generar_pdf_y_docx_adjudicacion.

    Errores:
    - Lanza ValueError si:
        · la solicitud no existe,
        · no tiene usuario/proveedor válido asociado,
        · la plaza ya está ocupada,
        · la plaza no existe.
    """
    # 4.1.1. Recuperar solicitud + usuario/proveedor
    solicitud = ejecutar_query(
        """
        SELECT
            s.idtbl_usuarios,
            s.n_expediente,
            u.idtbl_proveedores
        FROM parquin_camiones.tbl_solicitudes_plazas AS s
        LEFT JOIN parquin_camiones.tbl_usuarios AS u
            ON s.idtbl_usuarios = u.idtbl_usuarios
        WHERE s.idtbl_solicitudes_plazas = %s
        """,
        (id_solicitud,),
        nombre_bd="parquin_camiones",
    )

    if not solicitud:
        raise ValueError("Solicitud no encontrada")

    fila = solicitud[0]
    id_usuario = fila["idtbl_usuarios"]
    n_expediente = fila["n_expediente"]
    id_proveedor = fila["idtbl_proveedores"]

    if id_usuario is None or id_proveedor is None:
        raise ValueError("La solicitud no tiene usuario/proveedor válido asociado.")

    # 4.1.2. Comprobar si ya existe movimiento histórico para el mismo expediente
    #        (exp_solicitud_inicio / cambio / fin). Si existe, no reasignamos.
    datos_historico = ejecutar_query(
        """
        SELECT
            h.idtbl_historico_plazas,
            h.idtbl_plazas,
            h.exp_solicitud_inicio,
            h.exp_solicitud_cambio,
            h.exp_solicitud_fin
        FROM parquin_camiones.tbl_historico_plazas AS h
        WHERE h.exp_solicitud_inicio = %s
           OR h.exp_solicitud_cambio = %s
           OR h.exp_solicitud_fin    = %s
        LIMIT 1
        """,
        (n_expediente, n_expediente, n_expediente),
        nombre_bd="parquin_camiones",
    )

    if datos_historico:
        # 4.1.2.a. Caso: ya existe histórico para ese expediente.
        #            Interpretamos que la plaza ya se ha adjudicado
        #            desde otra plantilla / flujo.
        #            -> Marcamos la solicitud como 'aprobada' sin tocar la plaza.
        ejecutar_non_query(
            """
            UPDATE parquin_camiones.tbl_solicitudes_plazas
            SET
                estado           = 'aprobada',
                idtbl_gestores   = %s,
                fecha_aprobacion = NOW()
            WHERE idtbl_solicitudes_plazas = %s
            """,
            (id_gestor, id_solicitud),
            nombre_bd="parquin_camiones",
        )
        return

    # 4.1.3. Comprobar que la plaza está libre antes de asignar:
    #        idtbl_usuarios debe ser NULL.
    datos_plaza = ejecutar_query(
        """
        SELECT
            idtbl_plazas,
            idtbl_usuarios,
            numero_expediente,
            fecha_inicio,
            fecha_fin
        FROM parquin_camiones.tbl_plazas
        WHERE idtbl_plazas = %s
        """,
        (id_plaza,),
        nombre_bd="parquin_camiones",
    )

    if not datos_plaza:
        raise ValueError("La plaza indicada no existe.")

    fila_plaza = datos_plaza[0]
    if fila_plaza["idtbl_usuarios"] is not None:
        # 4.1.3.a. Plaza ocupada: no se puede asignar de nuevo.
        raise ValueError("La plaza seleccionada ya está ocupada y no puede asignarse.")

    # 4.1.4. Forma de pago actual del usuario (se usa para reflejarla en el histórico)
    forma_pago = _rt_obtener_forma_pago_usuario(id_usuario)

    # 4.1.5. Actualización de la plaza: asignación al usuario con fecha y expediente
    ejecutar_non_query(
        """
        UPDATE parquin_camiones.tbl_plazas
        SET
            idtbl_usuarios    = %s,
            fecha_inicio      = %s,
            numero_expediente = %s
        WHERE idtbl_plazas = %s
        """,
        (id_usuario, fecha_inicio_str, n_expediente, id_plaza),
        nombre_bd="parquin_camiones",
    )

    # 4.1.6. Registro del alta en el histórico de plazas
    _rt_insertar_alta_historico(
        id_plaza=id_plaza,
        id_proveedor=id_proveedor,
        fecha_inicio=fecha_inicio_str,
        forma_pago=forma_pago,
        exp_inicio=n_expediente,
        id_usuario=id_usuario,
    )

    # 4.1.7. Marcar solicitud como aprobada
    ejecutar_non_query(
        """
        UPDATE parquin_camiones.tbl_solicitudes_plazas
        SET
            idtbl_plazas     = %s,
            estado           = 'aprobada',
            idtbl_gestores   = %s,
            fecha_aprobacion = NOW()
        WHERE idtbl_solicitudes_plazas = %s
        """,
        (id_plaza, id_gestor, id_solicitud),
        nombre_bd="parquin_camiones",
    )

    # 4.1.8. Generación de informe de adjudicación, si se ha solicitado
    if generar_informe:
        _generar_pdf_y_docx_adjudicacion(id_plaza)


def _rt_rechazar_solicitud(id_solicitud: int, motivo: str) -> None:
    """
    4.2. _rt_rechazar_solicitud
    ---------------------------
    Marca una solicitud como 'rechazada' e indica el motivo textual
    en el campo `motivo_rechazo`.

    Uso:
    - Se llama desde la vista cuando el gestor decide no aprobar una
      solicitud y quiere dejar constancia del motivo.
    """
    ejecutar_non_query(
        """
        UPDATE parquin_camiones.tbl_solicitudes_plazas
        SET estado = 'rechazada',
            motivo_rechazo = %s
        WHERE idtbl_solicitudes_plazas = %s
        """,
        (motivo, id_solicitud),
        nombre_bd="parquin_camiones",
    )


# =============================================================================
# 5. VISTA PRINCIPAL: GET / POST
# =============================================================================


@btn_rio_torio_solicitud_plazas_bp.route(
    "/btn_rio_torio_solicitud_plazas",
    methods=["GET", "POST"],
)
@login_required
@rol_required("gestor", "super_admin")
def btn_rio_torio_solicitud_plazas():
    """
    5.1. btn_rio_torio_solicitud_plazas
    -----------------------------------
    Vista principal de gestión de solicitudes de plazas del parking
    Río Torío.

    POST:
    -----
    - accion = "nueva"
        · Alta de nueva solicitud (usa formulario de la parte superior
          de la plantilla).

    - accion = "aprobar"
        · Aprueba una solicitud pendiente:
            · comprueba que la plaza está libre y que no existe ya
              histórico para el expediente,
            · asigna plaza al usuario y registra alta en tbl_historico_plazas
              si procede,
            · genera informe de adjudicación si se marca la casilla.

    - accion = "rechazar"
        · Marca la solicitud como rechazada, con motivo.

    - accion = "asignar_desde_expediente"
        · Asigna una plaza libre a partir de un expediente ya existente
          en tbl_historico_plazas, utilizando los datos del proveedor y
          forma de pago asociados al expediente.

    GET:
    ----
    - Carga solicitudes, proveedores y plazas libres.
    - Calcula KPIs de plazas y nº de solicitudes pendientes.
    - Prepara fecha_hoy y now para la plantilla de frontend.

    Comportamiento:
    - Se usa el patrón PRG (Post/Redirect/Get): tras un POST siempre se
      realiza un redirect a la propia vista para evitar reenvío de
      formularios al refrescar la página.
    """
    if request.method == "POST":
        accion = request.form.get("accion")

        # 5.2. Alta de nueva solicitud
        if accion == "nueva":
            datos = {
                "idtbl_usuarios": request.form.get("idtbl_usuarios") or None,
                "idtbl_plazas": request.form.get("idtbl_plazas") or None,
                "n_expediente": request.form.get("n_expediente") or None,
                "idtbl_gestores": session.get("idtbl_gestores"),
                "solicita": request.form.get("solicita") or "plaza_libre",
                "estado": request.form.get("estado") or "pendiente",
            }

            if not datos["idtbl_usuarios"]:
                flash("Debe seleccionar un proveedor.", "danger")
            elif not datos["n_expediente"]:
                flash("El expediente es obligatorio.", "danger")
            else:
                _rt_insertar_solicitud(datos)
                flash("Solicitud creada correctamente.", "success")

        # 5.3. Aprobar solicitud y asignar plaza
        elif accion == "aprobar":
            id_solicitud = request.form.get("id_solicitud")
            id_plaza = request.form.get("id_plaza")
            fecha_inicio_str = request.form.get("fecha_inicio_asignacion") or ""
            generar_informe = request.form.get("generar_informe") == "1"

            if not id_solicitud or not id_plaza:
                flash("Debe seleccionar solicitud y plaza.", "danger")
            elif not fecha_inicio_str:
                flash("Debe indicar la fecha de inicio de la asignación.", "danger")
            else:
                try:
                    _rt_aprobar_solicitud(
                        id_solicitud=int(id_solicitud),
                        id_plaza=int(id_plaza),
                        id_gestor=int(session.get("idtbl_gestores") or 0),
                        fecha_inicio_str=fecha_inicio_str,
                        generar_informe=generar_informe,
                    )
                    flash("Solicitud aprobada y plaza asignada.", "success")
                except ValueError as exc:
                    flash(str(exc), "danger")
                except Exception as exc:
                    flash(f"Error al aprobar la solicitud: {exc}", "danger")

        # 5.4. Rechazar solicitud
        elif accion == "rechazar":
            id_solicitud = request.form.get("id_solicitud")
            motivo = request.form.get("motivo_rechazo") or ""
            if not id_solicitud:
                flash("Debe seleccionar una solicitud.", "danger")
            else:
                _rt_rechazar_solicitud(int(id_solicitud), motivo)
                flash("Solicitud rechazada.", "warning")

        # 5.5. Asignar plaza libre desde expediente existente
        elif accion == "asignar_desde_expediente":
            n_expediente = request.form.get("n_expediente_existente") or ""
            id_plaza = request.form.get("idtbl_plazas_libre") or ""
            fecha_inicio_str = request.form.get("fecha_inicio_asignacion") or ""
            generar_informe = request.form.get("generar_informe") == "1"

            if not n_expediente:
                flash("Debes indicar el número de expediente existente.", "danger")
            elif not id_plaza:
                flash("Debes seleccionar una plaza libre para asignar.", "danger")
            elif not fecha_inicio_str:
                flash("Debes indicar la fecha de inicio de la asignación.", "danger")
            else:
                try:
                    datos_exp = ejecutar_query(
                        """
                        SELECT
                            h.idtbl_plazas,
                            h.idtbl_proveedores,
                            h.fecha_inicio,
                            h.fecha_fin,
                            h.forma_pago,
                            pr.NIF,
                            pr.Nombre_Razon_Social,
                            pl.codigo_plazas,
                            pl.fila,
                            pl.observaciones
                        FROM parquin_camiones.tbl_historico_plazas AS h
                        LEFT JOIN bd_tbl_comunes.tbl_proveedores AS pr
                            ON pr.Idtbl_proveedores = h.idtbl_proveedores
                        LEFT JOIN parquin_camiones.tbl_plazas AS pl
                            ON pl.idtbl_plazas = h.idtbl_plazas
                        WHERE h.exp_solicitud_inicio = %s
                           OR h.exp_solicitud_cambio  = %s
                           OR h.exp_solicitud_fin     = %s
                        ORDER BY h.idtbl_historico_plazas DESC
                        LIMIT 1
                        """,
                        (n_expediente, n_expediente, n_expediente),
                        nombre_bd="parquin_camiones",
                    )

                    if not datos_exp:
                        flash(
                            "No se han encontrado datos para ese expediente.", "danger"
                        )
                    else:
                        fila_exp = datos_exp[0]
                        id_proveedor = fila_exp["idtbl_proveedores"]
                        forma_pago_exp = fila_exp.get("forma_pago")

                        # Asignación directa de plaza al proveedor encontrado
                        ejecutar_non_query(
                            """
                            UPDATE parquin_camiones.tbl_plazas
                            SET idtbl_usuarios = %s,
                                fecha_inicio   = %s,
                                numero_expediente = %s
                            WHERE idtbl_plazas = %s
                            """,
                            (
                                id_proveedor,
                                fecha_inicio_str,
                                n_expediente,
                                int(id_plaza),
                            ),
                            nombre_bd="parquin_camiones",
                        )

                        # Registro del alta en el histórico desde expediente
                        _rt_insertar_alta_historico(
                            id_plaza=int(id_plaza),
                            id_proveedor=id_proveedor,
                            fecha_inicio=fecha_inicio_str,
                            forma_pago=forma_pago_exp,
                            exp_inicio=n_expediente,
                            id_usuario=None,
                        )

                        # Generación de informe desde expediente, si procede
                        if generar_informe:
                            _generar_pdf_y_docx_adjudicacion(int(id_plaza))

                        flash(
                            "Plaza asignada correctamente desde expediente.", "success"
                        )

                except Exception as exc:
                    flash(f"Error al asignar plaza desde expediente: {exc}", "danger")

        # 5.6. PRG: redirigir siempre tras POST para evitar reenvío de formularios
        return redirect(
            url_for("btn_rio_torio_solicitud_plazas_bp.btn_rio_torio_solicitud_plazas")
        )

    # 5.7. Lógica GET: carga de datos para la plantilla
    solicitudes = _rt_obtener_solicitudes()
    proveedores = _rt_proveedores_parquin()
    plazas_libres = _rt_plazas_libres()
    totales = _rt_totales_plazas()

    total_plazas = totales.get("total_plazas", 0)
    total_plazas_libres = totales.get("total_plazas_libres", 0)
    total_plazas_ocupadas = totales.get("total_plazas_ocupadas", 0)

    total_solicitudes_pendientes = sum(
        1 for s in solicitudes if s["estado"] == "pendiente"
    )

    hoy = datetime.date.today()
    fecha_hoy = hoy.strftime("%Y-%m-%d")
    now_str = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    # 5.8. Render de la plantilla principal
    return render_template(
        "parquin/rio_torio/rio_torio_solicitud_plazas.html",
        solicitudes=solicitudes,
        proveedores=proveedores,
        plazas_libres=plazas_libres,
        total_plazas=total_plazas,
        total_plazas_libres=total_plazas_libres,
        total_plazas_ocupadas=total_plazas_ocupadas,
        total_solicitudes_pendientes=total_solicitudes_pendientes,
        url_volver=obtener_url_retorno_rio_torio(),
        fecha_hoy=fecha_hoy,
        now=now_str,
    )
