# =============================================================================
# 🧩 btn_vados_gestion_bp.py - VERSIÓN FINAL CORREGIDA Y DOCUMENTADA
# =============================================================================
# INTRODUCCIÓN
# -----------------------------------------------------------------------------
# Esta vista ofrece una panorámica de los vados, divididos en:
#   - Vados normalizados (con calle/municipio/proveedor)
#   - Vados OT (con NIF_SP_OT / Nombre_SP_OT)
#
# FUNCIONALIDADES PRINCIPALES:
#   1. Búsqueda por nº de vado y NIF_SP_OT.
#   2. Carga de un vado seleccionado y sus históricos (números y titulares).
#   3. Listas auxiliares (NIF OT, nombre OT, fechas, estados, tipos operación).
#   4. Contadores y datos para el panel de formulario, históricos y OT.
#   5. (NUEVO) Carga de:
#        - TIPOS DE VÍA desde control_via_publica.tbl_tipos_de_vias
#        - CALLES del municipio 395 desde control_via_publica.tbl_calles
#      De forma que:
#        - Siempre se traen solo las calles del municipio 395.
#        - Opcionalmente se filtran por tipo de vía seleccionado.
#
# IMPORTANTE:
#   - Se respeta TODO lo que ya tienes funcionando.
#   - Solo se AÑADE lo necesario para tipos_de_vias y calles.
#   - El código está claramente separado y documentado por bloques.
# =============================================================================

from flask import Blueprint, render_template, request, redirect, url_for, flash
from services.helpers import login_required, rol_required
from db import ejecutar_query, ejecutar_non_query

btn_vados_gestion_bp = Blueprint(
    "btn_vados_gestion_bp",
    __name__,
    url_prefix="/vados",
)


@btn_vados_gestion_bp.route("/", methods=["GET"])
@login_required
@rol_required("gestor", "super_admin")
def btn_vados_gestion():
    """Vista panorámica de vados - VERSIÓN FINAL"""

    # =========================================================================
    # [A] PARÁMETROS DE BÚSQUEDA (INICIO / FIN)
    # -------------------------------------------------------------------------
    # - numero_vado_q: filtro por nº de vado
    # - nif_q: filtro por NIF_SP_OT
    # - tipo_via_q: filtro por tipo de vía (NUEVO)
    # - calle_q: filtro por calle (NUEVO)
    # =========================================================================
    numero_vado_q = request.args.get("numero_vado", "").strip()
    nif_q = request.args.get("nif", "").strip()
    tipo_via_q = request.args.get("tipo_via", "").strip()   # NUEVO
    calle_q = request.args.get("calle", "").strip()         # NUEVO
    # =========================================================================

    # =========================================================================
    # [B] QUERY PRINCIPAL DE VADOS (INICIO / FIN)
    # -------------------------------------------------------------------------
    # - Se obtienen vados desde control_via_publica.tbl_vados
    # - Filtros:
    #       * nº de vado exacto (si numero_vado_q)
    #       * NIF_SP_OT exacto (si nif_q)
    # - Ordenados por numero_vado
    # =========================================================================
    sql = """
        SELECT
            `tbl_vados`.`idtbl_vados`,
            `tbl_vados`.`idtbl_tipos_de_vias`,
            `tbl_vados`.`idtbl_calles`,
            `tbl_vados`.`Puerta`,
            `tbl_vados`.`idtbl_municipios`,
            `tbl_vados`.`idtbl_proveedores`,
            `tbl_vados`.`numero_vado`,
            `tbl_vados`.`idtbl_vado_anterior`,
            `tbl_vados`.`idtbl_propietario_anterior`,
            `tbl_vados`.`fecha_alta`,
            `tbl_vados`.`fecha_baja`,
            `tbl_vados`.`fecha_cambio`,
            `tbl_vados`.`idtbl_gestores`,
            `tbl_vados`.`tipo_operacion`,
            `tbl_vados`.`baja`,
            `tbl_vados`.`superficie`,
            `tbl_vados`.`anchura`,
            `tbl_vados`.`Desc_OT`,
            `tbl_vados`.`Via_OT`,
            `tbl_vados`.`NIF_SP_OT`,
            `tbl_vados`.`Nombre_SP_OT`
        FROM control_via_publica.tbl_vados
        WHERE 1 = 1
    """
    params = []

    if numero_vado_q:
        sql += " AND `tbl_vados`.`numero_vado` = %s"
        params.append(numero_vado_q)

    if nif_q:
        sql += " AND `tbl_vados`.`NIF_SP_OT` = %s"
        params.append(nif_q)

    sql += " ORDER BY `tbl_vados`.`numero_vado`"

    vados = ejecutar_query(sql, tuple(params))
    # =========================================================================

    # =========================================================================
    # [C] DIVISIÓN DE VADOS: NORMALIZADOS VS OT (INICIO / FIN)
    # -------------------------------------------------------------------------
    # - vados_normalizados:
    #       * Tienen al menos idtbl_calles o idtbl_municipios o idtbl_proveedores
    # - vados_ot:
    #       * Tienen NIF_SP_OT o Nombre_SP_OT
    # - vado_seleccionado:
    #       * Primer vado normalizado (si existe)
    # =========================================================================
    vados_normalizados = []
    vados_ot = []

    for vado in vados:
        # Normalizado = tiene datos de calle/municipio/proveedor
        if vado.get("idtbl_calles") or vado.get("idtbl_municipios") or vado.get("idtbl_proveedores"):
            vados_normalizados.append(vado)
        # OT = tiene NIF_SP_OT o Nombre_SP_OT
        if vado.get("NIF_SP_OT") or vado.get("Nombre_SP_OT"):
            vados_ot.append(vado)

    vado_seleccionado = vados_normalizados[0] if vados_normalizados else None
    # =========================================================================

    # =========================================================================
    # [D] HISTÓRICOS (NÚMEROS Y TITULARES) (INICIO / FIN)
    # -------------------------------------------------------------------------
    # - historico_numeros: cambios de número de vado
    # - historico_titulares: cambios de titular/proveedor
    # - Ambos filtrados por idtbl_vados del vado seleccionado
    # =========================================================================
    historico_numeros = []
    historico_titulares = []

    if vado_seleccionado:
        historico_numeros = ejecutar_query(
            """SELECT idtbl_vados_historico_numeros, idtbl_vados, numero_anterior, numero_nuevo, 
                      fecha_cambio, idtbl_gestores, observaciones
               FROM control_via_publica.tbl_vados_historico_numeros 
               WHERE idtbl_vados = %s ORDER BY fecha_cambio DESC""",
            (vado_seleccionado["idtbl_vados"],),
        )

        historico_titulares = ejecutar_query(
            """SELECT idtbl_vados_historico_titulares, idtbl_vados, idtbl_proveedor_anterior, 
                      idtbl_proveedor_nuevo, fecha_cambio, idtbl_gestores, observaciones
               FROM control_via_publica.tbl_vados_historico_titulares 
               WHERE idtbl_vados = %s ORDER BY fecha_cambio DESC""",
            (vado_seleccionado["idtbl_vados"],),
        )
    # =========================================================================

    # =========================================================================
    # [E] LISTAS AUXILIARES + TIPOS DE VÍA Y CALLES (INICIO / FIN)
    # -------------------------------------------------------------------------
    # Sub-bloques:
    #   [E.1] Listas basadas en tbl_vados (NIF OT, Nombre OT, fechas, estados...)
    #   [E.2] NUEVO: listas de TIPOS DE VÍA y CALLES (municipio 395),
    #         filtrando calles por tipo de vía si se ha seleccionado.
    # =========================================================================

    # [E.1] Listas desde tbl_vados (YA EXISTENTES - NO SE CAMBIAN)
    # ----------------------------------------------------------------------
    # Lista de NIF_SP_OT (desde tbl_vados)
    try:
        lista_nif_sp_ot = ejecutar_query(
            "SELECT DISTINCT NIF_SP_OT FROM control_via_publica.tbl_vados "
            "WHERE NIF_SP_OT IS NOT NULL ORDER BY NIF_SP_OT"
        )
        lista_nif_sp_ot = [{'nif_ot': row[0]} for row in lista_nif_sp_ot]
    except Exception:
        lista_nif_sp_ot = []

    # Lista de Nombre_SP_OT (desde tbl_vados)
    try:
        lista_nombre_sp_ot = ejecutar_query(
            "SELECT DISTINCT Nombre_SP_OT FROM control_via_publica.tbl_vados "
            "WHERE Nombre_SP_OT IS NOT NULL ORDER BY Nombre_SP_OT"
        )
        lista_nombre_sp_ot = [{'nombre_ot': row[0]} for row in lista_nombre_sp_ot]
    except Exception:
        lista_nombre_sp_ot = []

    # Lista de fechas (desde tbl_vados)
    try:
        lista_fechas = ejecutar_query(
            "SELECT DISTINCT fecha_alta FROM control_via_publica.tbl_vados "
            "WHERE fecha_alta IS NOT NULL ORDER BY fecha_alta DESC"
        )
        lista_fechas = [row[0] for row in lista_fechas]
    except Exception:
        lista_fechas = []

    # Lista de estados (fija)
    lista_estados = ['Activo', 'Inactivo', 'Pendiente', 'Cancelado', 'Baja']

    # Lista de tipos de operación (fija)
    lista_tipos_operacion = ['Alta', 'Cambio', 'Baja']

    # [E.2] NUEVO: TIPOS DE VÍA Y CALLES (municipio = 395) 
    # ----------------------------------------------------------------------
    # OBJETIVO:
    #   - lista_tipos_vias: viene de control_via_publica.tbl_tipos_de_vias
    #   - lista_calles: viene de control_via_publica.tbl_calles
    #       * siempre restringido a idtbl_municipios = 395 (Ávila)
    #       * si tipo_via_q tiene valor, se filtra además por idtbl_tipos_de_vias
    #
    # NOTA:
    #   - No se modifica nada del comportamiento existente,
    #     solo se rellenan estas listas que antes estaban vacías.
    # ----------------------------------------------------------------------
    # Lista de tipos de vía
    try:
        lista_tipos_vias = ejecutar_query(
            """
            SELECT idtbl_tipos_de_vias, tipos_de_vias
            FROM control_via_publica.tbl_tipos_de_vias
            ORDER BY tipos_de_vias
            """
        )
        lista_tipos_vias = [
            {"id": row[0], "nombre": row[1]} for row in lista_tipos_vias
        ]
    except Exception:
        lista_tipos_vias = []

    # Lista de calles (municipio 395, opcionalmente filtradas por tipo_via_q)
    try:
        # Base: solo municipio 395
        sql_calles = """
            SELECT idtbl_calles, calles
            FROM control_via_publica.tbl_calles
            WHERE idtbl_municipios = %s
        """
        params_calles = [395]

        # Si el usuario ha elegido tipo de vía, filtramos por idtbl_tipos_de_vias
        if tipo_via_q:
            sql_calles += " AND idtbl_tipos_de_vias = %s"
            params_calles.append(tipo_via_q)

        sql_calles += " ORDER BY calles"

        lista_calles_raw = ejecutar_query(sql_calles, tuple(params_calles)) \
            if params_calles else []

        lista_calles = [
            {"id": row[0], "nombre": row[1]} for row in lista_calles_raw
        ]
    except Exception:
        lista_calles = []

    # En caso de que quieras seguir usando estas listas como antes, las mantenemos:
    lista_municipios = []     # (siguen vacías porque no las habías definido)
    lista_proveedores = []    # (idem)
    # =========================================================================

    # =========================================================================
    # [F] COMBINAR HISTÓRICOS EN UNA LISTA UNIFICADA (INICIO / FIN)
    # -------------------------------------------------------------------------
    # - historiales: mezcla de histórico de números y de titulares
    #   para uso futuro si quieres una sola tabla de movimientos.
    # =========================================================================
    historiales = []
    for h_num in historico_numeros:
        historiales.append({
            'id': h_num[0],
            'tipo': 'cambio_numero',
            'idtbl_vados': h_num[1],
            'numero_anterior': h_num[2],
            'numero_nuevo': h_num[3],
            'fecha': h_num[4],
            'gestor': h_num[5],
            'observaciones': h_num[6],
        })
    for h_tit in historico_titulares:
        historiales.append({
            'id': h_tit[0],
            'tipo': 'cambio_titular',
            'idtbl_vados': h_tit[1],
            'titular_anterior': h_tit[2],
            'titular_nuevo': h_tit[3],
            'fecha': h_tit[4],
            'gestor': h_tit[5],
            'observaciones': h_tit[6],
        })
    # =========================================================================

    # =========================================================================
    # [G] TOTAL REGISTROS (INICIO / FIN)
    # -------------------------------------------------------------------------
    # - Se mantiene tu lógica: suma normalizados + OT
    #   (para el header ya estamos usando solo vados_normalizados en la plantilla)
    # =========================================================================
    total_registros = len(vados_normalizados) + len(vados_ot)
    # =========================================================================

    # =========================================================================
    # [H] RENDER DE LA PLANTILLA (INICIO / FIN)
    # -------------------------------------------------------------------------
    # - Se pasan TODOS los datos necesarios:
    #     * vados, vado_seleccionado
    #     * historico_numeros, historico_titulares, historiales
    #     * filtros (numero_vado_q, nif_q, tipo_via_q, calle_q)
    #     * vados_normalizados, vados_ot, total_registros
    #     * listas auxiliares (nif/nombres OT, fechas, estados, tipos operación)
    #     * NUEVO: lista_tipos_vias, lista_calles
    # =========================================================================
    return render_template(
        "control_via_publica/control_vados/vados_gestion.html",
        vados=vados,
        vado_seleccionado=vado_seleccionado,
        historico_numeros=historico_numeros,
        historico_titulares=historico_titulares,
        historiales=historiales,
        # filtros
        numero_vado_q=numero_vado_q,
        nif_q=nif_q,
        tipo_via_q=tipo_via_q,
        calle_q=calle_q,
        # datos principales
        vados_normalizados=vados_normalizados,
        vados_ot=vados_ot,
        total_registros=total_registros,
        # listas auxiliares
        lista_calles=lista_calles,
        lista_municipios=lista_municipios,
        lista_proveedores=lista_proveedores,
        lista_tipos_vias=lista_tipos_vias,
        lista_nif_sp_ot=lista_nif_sp_ot,
        lista_nombre_sp_ot=lista_nombre_sp_ot,
        lista_fechas=lista_fechas,
        lista_estados=lista_estados,
        lista_tipos_operacion=lista_tipos_operacion,
    )