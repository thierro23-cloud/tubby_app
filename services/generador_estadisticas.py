# =============================================================================
# 📊 SERVICIO GLOBAL: GENERADOR DE ESTADÍSTICAS
# =============================================================================
#
# Este módulo centraliza todas las estadísticas del sistema.
#
# Permite generar estadísticas para:
#
#   obras
#   contenedores
#   terrazas
#   vados
#   vía pública
#
# Devuelve datos preparados para:
#
#   HTML
#   Chart.js
#   informes
#   paneles
#
# =============================================================================


# =============================================================================
# 1️⃣ IMPORTS
# =============================================================================

from db import ejecutar_query

# =============================================================================
# 2️⃣ ESTADÍSTICAS POR MES
# =============================================================================


def estadisticas_por_mes(tabla, campo_fecha):

    sql = f"""
    SELECT

        YEAR({campo_fecha}) AS anio,
        MONTH({campo_fecha}) AS mes,
        COUNT(*) AS total

    FROM {tabla}

    GROUP BY anio, mes

    ORDER BY anio DESC, mes DESC
    """

    return ejecutar_query(sql)


# =============================================================================
# 3️⃣ ESTADÍSTICAS POR AÑO
# =============================================================================


def estadisticas_por_anio(tabla, campo_fecha):

    sql = f"""
    SELECT

        YEAR({campo_fecha}) AS anio,
        COUNT(*) AS total

    FROM {tabla}

    GROUP BY anio

    ORDER BY anio DESC
    """

    return ejecutar_query(sql)


# =============================================================================
# 4️⃣ ESTADÍSTICAS POR PROVEEDOR
# =============================================================================


def estadisticas_por_proveedor(tabla, campo_proveedor):

    sql = f"""
    SELECT

        p.nombre_razon_social,
        COUNT(*) AS total

    FROM {tabla} t

    JOIN bd_tbl_comunes.tbl_proveedores p
    ON p.Idtbl_proveedores = t.{campo_proveedor}

    GROUP BY p.nombre_razon_social

    ORDER BY total DESC
    """

    return ejecutar_query(sql)


# =============================================================================
# 5️⃣ ESTADÍSTICAS POR CALLE
# =============================================================================


def estadisticas_por_calle(tabla, campo_calle):

    sql = f"""
    SELECT

        c.nombre,
        COUNT(*) AS total

    FROM {tabla} t

    JOIN tbl_calles c
    ON c.idtbl_calles = t.{campo_calle}

    GROUP BY c.nombre

    ORDER BY total DESC
    """

    return ejecutar_query(sql)


# =============================================================================
# 6️⃣ ESTADÍSTICAS POR TIPO DE VÍA
# =============================================================================


def estadisticas_por_tipo_via(tabla, campo_tipo_via):

    sql = f"""
    SELECT

        v.nombre,
        COUNT(*) AS total

    FROM {tabla} t

    JOIN tbl_tipos_de_vias v
    ON v.idtbl_tipos_de_vias = t.{campo_tipo_via}

    GROUP BY v.nombre

    ORDER BY total DESC
    """

    return ejecutar_query(sql)


# =============================================================================
# 7️⃣ ESTADÍSTICAS POR ESTADO
# =============================================================================


def estadisticas_por_estado(tabla, campo_estado):

    sql = f"""
    SELECT

        {campo_estado} AS estado,
        COUNT(*) AS total

    FROM {tabla}

    GROUP BY estado

    ORDER BY total DESC
    """

    return ejecutar_query(sql)


# =============================================================================
# 8️⃣ GENERADOR GENERAL DE ESTADÍSTICAS
# =============================================================================


def generar_estadisticas(
    tabla, campo_fecha=None, campo_proveedor=None, campo_calle=None, campo_tipo_via=None
):

    estadisticas = {}

    if campo_fecha:
        estadisticas["por_mes"] = estadisticas_por_mes(tabla, campo_fecha)
        estadisticas["por_anio"] = estadisticas_por_anio(tabla, campo_fecha)

    if campo_proveedor:
        estadisticas["por_proveedor"] = estadisticas_por_proveedor(
            tabla, campo_proveedor
        )

    if campo_calle:
        estadisticas["por_calle"] = estadisticas_por_calle(tabla, campo_calle)

    if campo_tipo_via:
        estadisticas["por_tipo_via"] = estadisticas_por_tipo_via(tabla, campo_tipo_via)

    return estadisticas
