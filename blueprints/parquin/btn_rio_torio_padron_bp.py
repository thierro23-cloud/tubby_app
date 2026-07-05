# =============================================================================
# 1) IMPORTS BÁSICOS
# =============================================================================
from __future__ import annotations

from datetime import date, timedelta
from collections import defaultdict
import calendar

from flask import Blueprint, current_app

from db import ejecutar_query  # Ajusta si tu helper está en otro módulo


# =============================================================================
# 2) DEFINICIÓN DEL BLUEPRINT
# =============================================================================
rio_torio_padron_bp = Blueprint(
    "rio_torio_padron_bp",
    __name__,
    url_prefix="/parquin/rio_torio/padron",
)


# =============================================================================
# 3) HELPER: CÁLCULO DEL PERIODO DEL PADRÓN
# =============================================================================
def obtener_periodo_padron(fecha_base: date | None = None) -> dict:
    """
    3.1) Calcula el periodo del padrón en función de una fecha base.

    REGLA:
      - El padrón se refiere al mes anterior al primer día laborable
        del mes siguiente.
      - Ejemplo: si hoy es 10/06/2026:
          · Mes siguiente: julio 2026.
          · Primer día laborable de julio.
          · Padrón: junio 2026 (1–30).

    Devuelve un dict con:
      - inicio_mes: date
      - fin_mes: date
      - anio: int
      - mes_num: int (1–12)
      - mes_nombre: str (nombre del mes en inglés)
      - primer_laborable_mes_siguiente: date
    """
    # 3.1.1) Si no se pasa fecha_base, usamos hoy
    if fecha_base is None:
        fecha_base = date.today()

    # 3.1.2) Determinar mes siguiente
    if fecha_base.month == 12:
        anio_siguiente = fecha_base.year + 1
        mes_siguiente = 1
    else:
        anio_siguiente = fecha_base.year
        mes_siguiente = fecha_base.month + 1

    # 3.1.3) Primer día del mes siguiente
    primer_dia_mes_siguiente = date(anio_siguiente, mes_siguiente, 1)

    # 3.1.4) Primer laborable (lunes–viernes) del mes siguiente
    d = primer_dia_mes_siguiente
    while d.weekday() >= 5:  # 5 = sábado, 6 = domingo
        d += timedelta(days=1)
    primer_laborable = d

    # 3.1.5) Mes del padrón = mes anterior al mes_siguiente
    if mes_siguiente == 1:
        anio_padron = anio_siguiente - 1
        mes_padron = 12
    else:
        anio_padron = anio_siguiente
        mes_padron = mes_siguiente - 1

    # 3.1.6) Inicio y fin de ese mes
    inicio_mes = date(anio_padron, mes_padron, 1)
    _, ultimo_dia = calendar.monthrange(anio_padron, mes_padron)
    fin_mes = date(anio_padron, mes_padron, ultimo_dia)

    # 3.1.7) Nombre del mes (en inglés por defecto)
    mes_nombre = calendar.month_name[mes_padron]

    return {
        "inicio_mes": inicio_mes,
        "fin_mes": fin_mes,
        "anio": anio_padron,
        "mes_num": mes_padron,
        "mes_nombre": mes_nombre,
        "primer_laborable_mes_siguiente": primer_laborable,
    }


# =============================================================================
# 4) CONSULTA: OBTENER HISTÓRICO DEL PERIODO PARA RÍO TORÍO
# =============================================================================
def obtener_historico_periodo(inicio_mes: date, fin_mes: date) -> list[dict]:
    """
    Devuelve las filas de tbl_historico_plazas que están activas
    en el periodo [inicio_mes, fin_mes], con:

      - Proveedor (desde tbl_usuarios -> tbl_proveedores)
      - Plaza (codigo_plazas)
      - Forma de pago (desde tbl_usuarios)
    """

    query = """
        SELECT
            h.idtbl_historico_plazas,
            h.idtbl_plazas,
            h.fecha_inicio,
            h.fecha_fin,
            h.exp_solicitud_fin,
            h.forma_pago,
            pl.codigo_plazas,
            h.idtbl_proveedores AS idtbl_usuarios,
            h.idtbl_proveedores,
            h.forma_pago AS forma_pago_usuario,
            CONCAT_WS(' ', p.apellidos, p.nombre) AS nombre_proveedor,
            p.NIF AS nif_proveedor
        FROM parquin_camiones.tbl_historico_plazas AS h
        JOIN parquin_camiones.tbl_plazas AS pl
          ON h.idtbl_plazas = pl.idtbl_plazas
        JOIN bd_tbl_comunes.tbl_proveedores AS p
          ON h.idtbl_proveedores = p.Idtbl_proveedores
        WHERE
          -- Intersección de la vigencia histórica con el mes del padrón
          h.fecha_inicio <= %s
          AND (h.fecha_fin IS NULL OR h.fecha_fin >= %s)
        ORDER BY p.apellidos, p.nombre, pl.codigo_plazas, h.fecha_inicio
    """

    filas = ejecutar_query(
        query,
        params=(fin_mes, inicio_mes),
        nombre_bd="parquin_camiones",
    )
    return filas


# =============================================================================
# 5) CONSTRUCCIÓN DEL PADRÓN PRINCIPAL (TABLA PRINCIPAL)
# =============================================================================
def construir_padron_principal(filas: list[dict]) -> list[dict]:
    """
    5.1) Agrupa por proveedor para construir la tabla principal del padrón.

    Devuelve una lista de dicts:
      [
        {
          "nombre_proveedor": str,
          "nif": str,
          "plazas": [ "A01", "A02", ... ],
          "total_plazas": int,
        },
        ...
      ]
    """

    por_proveedor: dict[int, dict] = {}

    for f in filas:
        id_prov = f["idtbl_proveedores"]
        if id_prov not in por_proveedor:
            por_proveedor[id_prov] = {
                "nombre_proveedor": f["nombre_proveedor"],
                "nif": f["nif_proveedor"],
                "plazas": set(),  # usamos set para evitar duplicados
            }
        # aquí cambiamos codigo_plazas -> codigo_plazas
        por_proveedor[id_prov]["plazas"].add(f["codigo_plazas"])

    resultado = []
    for prov in por_proveedor.values():
        plazas_ordenadas = sorted(prov["plazas"], key=str)
        resultado.append(
            {
                "nombre_proveedor": prov["nombre_proveedor"],
                "nif": prov["nif"],
                "plazas": plazas_ordenadas,
                "total_plazas": len(plazas_ordenadas),
            }
        )

    return resultado
# =============================================================================
# 6) DETECCIÓN DE VARIACIONES (TABLA DE VARIACIONES)
# =============================================================================
def construir_variaciones(
    filas: list[dict],
    inicio_mes: date,
    fin_mes: date,
) -> list[dict]:
    """
    6.1) Construye la tabla de variaciones para el periodo.

    TIPOS DE CAMBIO:
      - "BAJA":
          · Fila con fecha_fin dentro del mes
          · Y SIN alta al día siguiente en otra plaza (mismo proveedor/usuario).
      - "Cambio de plaza":
          · Baja con fecha_fin = D
          · Alta con fecha_inicio = D+1
            para el mismo proveedor/usuario y otra plaza.
      - "Forma de pago":
          · Cambio de forma_pago dentro del mes para la misma plaza.

    Devuelve lista de dicts:
      [
        {
          "nombre_proveedor": str,
          "nif": str,
          "codigo_plazas": str,
          "tipo_cambio": "BAJA" | "Cambio de plaza" | "Forma de pago",
          "fecha": date,
        },
        ...
      ]
    """

    variaciones: list[dict] = []

    # 6.1) Agrupar por proveedor+usuario para detectar movimientos entre plazas
    por_prov_usuario: dict[tuple[int, int], list[dict]] = defaultdict(list)

    for f in filas:
        clave = (f["idtbl_proveedores"], f["idtbl_usuarios"])
        por_prov_usuario[clave].append(f)

    # 6.2) Recorrer cada proveedor+usuario
    for (id_prov, id_usuario), registros in por_prov_usuario.items():
        # Ordenar por fecha_inicio y por plaza
        registros.sort(key=lambda r: (r["fecha_inicio"], r["idtbl_plazas"]))

        bajas: list[dict] = []
        altas: list[dict] = []

        # 6.3) Clasificar filas como ALTAS y BAJAS dentro del mes
        for r in registros:
            fi = r["fecha_inicio"]
            ff = r["fecha_fin"]

            # Alta dentro del mes (fecha_inicio dentro del periodo)
            if inicio_mes <= fi <= fin_mes:
                altas.append(r)

            # Baja dentro del mes (fecha_fin dentro del periodo)
            if ff is not None and inicio_mes <= ff <= fin_mes:
                bajas.append(r)

        # 6.4) Detectar "Cambio de plaza": baja D, alta D+1 (para mismo prov/usuario)
        usadas_altas = set()
        usadas_bajas = set()

        for baja in bajas:
            ff = baja["fecha_fin"]
            if ff is None:
                continue
            d_mas_1 = ff + timedelta(days=1)

            for i, alta in enumerate(altas):
                if i in usadas_altas:
                    continue
                # Regla que hemos definido: alta el día siguiente para otra plaza
                if alta["fecha_inicio"] == d_mas_1 and alta["idtbl_plazas"] != baja["idtbl_plazas"]:
                    variaciones.append(
                        {
                            "nombre_proveedor": baja["nombre_proveedor"],
                            "nif": baja["nif_proveedor"],
                            # plasmamos el cambio como "A01 -> A05"
                            "codigo_plazas": f"{baja['codigo_plazas']} -> {alta['codigo_plazas']}",
                            "tipo_cambio": "Cambio de plaza",
                            "fecha": ff,
                        }
                    )
                    usadas_bajas.add(baja["idtbl_historico_plazas"])
                    usadas_altas.add(i)
                    break

        # 6.5) Bajas puras (sin alta al día siguiente)
        for baja in bajas:
            if baja["idtbl_historico_plazas"] in usadas_bajas:
                continue
            variaciones.append(
                {
                    "nombre_proveedor": baja["nombre_proveedor"],
                    "nif": baja["nif_proveedor"],
                    "codigo_plazas": baja["codigo_plazas"],
                    "tipo_cambio": "BAJA",
                    "fecha": baja["fecha_fin"],
                }
            )

        # 6.6) Cambio de forma de pago:
        #      detectamos cambios de forma_pago dentro del mes para la misma plaza
        por_plaza: dict[int, list[dict]] = defaultdict(list)
        for r in registros:
            por_plaza[r["idtbl_plazas"]].append(r)

        for id_plaza, regs_plaza in por_plaza.items():
            regs_plaza.sort(key=lambda r: r["fecha_inicio"])
            forma_anterior = None

            for r in regs_plaza:
                # Preferimos forma_pago del histórico; si no existe, usamos la del usuario
                forma_actual = r.get("forma_pago") or r.get("forma_pago_usuario")
                # Si no hay forma actual, la forzamos a "" para que no rompa
                forma_actual = forma_actual or ""
                fi = r["fecha_inicio"]

                if forma_anterior is not None and forma_actual != forma_anterior:
                    # Cambio de forma de pago efectivo en fi
                    if inicio_mes <= fi <= fin_mes:
                        variaciones.append(
                            {
                                "nombre_proveedor": r["nombre_proveedor"],
                                "nif": r["nif_proveedor"],
                                "codigo_plazas": r["codigo_plazas"],
                                "tipo_cambio": "Forma de pago",
                                "fecha": fi,
                            }
                        )

                forma_anterior = forma_actual

    # 6.7) Ordenar variaciones por proveedor, fecha y plaza
    variaciones.sort(key=lambda v: (v["nombre_proveedor"], v["fecha"], v["codigo_plazas"]))

    return variaciones

# =============================================================================
# 7) ENDPOINT PRINCIPAL: GENERAR PADRÓN RÍO TORÍO
# =============================================================================
@rio_torio_padron_bp.route("/generar", methods=["GET"])
def generar_padron_rio_torio():
    """
    7.1) Endpoint para generar el padrón de Río Torío.

    - Calcula el periodo del padrón.
    - Obtiene el histórico del periodo.
    - Construye:
        · Tabla principal (padron_principal).
        · Tabla de variaciones (variaciones).

    NOTA:
      - Aquí todavía no generamos DOC/PDF.
      - Devolvemos una respuesta estructurada (por ejemplo JSON)
        para verificar que la lógica de datos es correcta.
      - Más adelante enchufamos la generación de documentos
        usando estas estructuras.
    """

    # 7.1.1) Calcular periodo
    periodo = obtener_periodo_padron()
    inicio_mes = periodo["inicio_mes"]
    fin_mes = periodo["fin_mes"]

    current_app.logger.info(
        "Generando padrón Río Torío para periodo %s - %s",
        inicio_mes,
        fin_mes,
    )

    # 7.1.2) Obtener histórico del periodo
    filas = obtener_historico_periodo(inicio_mes, fin_mes)

    # 7.1.3) Tabla principal del padrón
    padron_principal = construir_padron_principal(filas)

    # 7.1.4) Tabla de variaciones
    variaciones = construir_variaciones(filas, inicio_mes, fin_mes)

    # 7.1.5) De momento, devolvemos un JSON para validar.
    #        Cuando verifiquemos que todo cuadra, aquí enchufamos:
    #          - generación DOC (python-docx)
    #          - generación PDF (reportlab o similar)
    #          - escritura en carpeta padron con nombre:
    #            "{anio}_padron_{mes}_rio_torio.doc/pdf"

    return {
        "periodo": {
            "inicio": inicio_mes.isoformat(),
            "fin": fin_mes.isoformat(),
            "anio": periodo["anio"],
            "mes": periodo["mes_num"],
            "mes_nombre": periodo["mes_nombre"],
        },
        "padron_principal": padron_principal,
        "variaciones": variaciones,
    }