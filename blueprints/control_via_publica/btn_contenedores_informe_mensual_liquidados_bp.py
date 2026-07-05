# =============================================================================
# 📊 CONTROL DE CONTENEDORES · INFORME MENSUAL LIQUIDADOS (BOTÓN)
# =============================================================================
# 0️⃣ INTRODUCCIÓN
# -----------------------------------------------------------------------------
# Este archivo define un BOTÓN del módulo CONTENEDORES de Control de Vía Pública:
#
#   contenedores_informe_mensual_liquidados
#
# ARQUITECTURA:
#   PANEL  → panel_control_via_publica_bp
#   MÓDULO → modulo_control_via_publica_contenedores_bp
#   BOTÓN  → contenedores_informe_mensual_liquidados (este blueprint)
#
# RUTA PÚBLICA RESULTANTE:
#   /control_via_publica/contenedores/informe_mensual_liquidados
#
# FUNCIONES DEL BOTÓN:
#   ✔ Calcula el rango del MES ANTERIOR completo.
#   ✔ Consulta los contenedores liquidados (fecha_retirada en ese rango).
#   ✔ Genera un Excel en:
#         <root_app>/contenedores/informes/AÑO/MES/AAAAmm_liquidados.xlsx
#   ✔ Lanza la descarga del fichero generado al navegador.
#
# DIFERENCIAS VS VERSIÓN ANTERIOR:
#   - Se elimina el registro dinámico via register_btn_routes().
#   - Se sustituye el blueprint 'btn_contenedores_informe_mensual_bp' por
#     un blueprint estándar:
#         contenedores_informe_mensual_liquidados_bp
#   - La vista principal pasa a llamarse:
#         contenedores_informe_mensual_liquidados
#     alineada con la convención de botones tipo "nombre_botón".
# =============================================================================

from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Tuple

import pandas as pd
from flask import (
    Blueprint,
    current_app,
    render_template,
    send_file,
)

from db import ejecutar_query
from services.helpers import rol_required
from flask_login import login_required


# =============================================================================
# 1️⃣ BLUEPRINT DEL BOTÓN · ALINEADO CON LA ARQUITECTURA
# =============================================================================
# Definimos un BLUEPRINT específico para este botón de informes:
#
#   contenedores_informe_mensual_liquidados_bp
#
# Ventajas:
#   - Mantiene la arquitectura PANEL → MÓDULO → BOTONES.
#   - Evita el uso de funciones de registro dinámico (register_btn_routes).
#   - Se registra como cualquier otro blueprint en la app.
#
# El url_prefix se alinea con el módulo CONTENEDORES:
#   /control_via_publica/contenedores
# =============================================================================

btn_contenedores_informe_mensual_liquidados_bp = Blueprint(
    "btn_contenedores_informe_mensual_liquidados_bp",
    __name__,
    url_prefix="/control_via_publica/contenedores",
)


# =============================================================================
# 2️⃣ RUTA DE INFORMES · CÁLCULO Y CREACIÓN DE CARPETAS
# =============================================================================
# Función helper para obtener la ruta donde se guardará el Excel generado,
# en función de una fecha (normalmente el inicio del mes anterior).
#
# ESTRUCTURA:
#   <root_app>/contenedores/informes/AÑO/MES/
#
# Ejemplo:
#   /tubby_app/contenedores/informes/2026/03/
# =============================================================================
def obtener_ruta_informes(fecha: date) -> str:
    """
    Devuelve la ruta donde se guardará el informe.

    Estructura generada automáticamente:

        contenedores/informes/AÑO/MES
    """
    anio = fecha.strftime("%Y")
    mes = fecha.strftime("%m")

    ruta = os.path.join(
        current_app.root_path,
        "contenedores",
        "informes",
        anio,
        mes,
    )

    # Crea carpetas si no existen
    os.makedirs(ruta, exist_ok=True)

    return ruta


# =============================================================================
# 3️⃣ FECHAS · CÁLCULO DEL RANGO DEL MES ANTERIOR
# =============================================================================
# Dada una fecha de referencia (normalmente hoy), calcula:
#
#   - fecha_corte         → primer día del mes actual
#   - inicio_mes_anterior → primer día del mes anterior
#   - fin_mes_anterior    → último día del mes anterior
#
# Ejemplo:
#   fecha_ref = 2026-04-11
#   → fecha_corte         = 2026-04-01
#   → inicio_mes_anterior = 2026-03-01
#   → fin_mes_anterior    = 2026-03-31
# =============================================================================
def calcular_rango_mes_anterior(fecha_ref: date) -> Tuple[date, date, date]:
    """
    Calcula el rango completo del mes anterior.

    Devuelve:
        - fecha_corte         → primer día del mes actual
        - inicio_mes_anterior → primer día del mes anterior
        - fin_mes_anterior    → último día del mes anterior
    """
    # Primer día del mes actual
    fecha_corte = fecha_ref.replace(day=1)

    # Último día del mes anterior
    ultimo_dia_mes_anterior = fecha_corte - timedelta(days=1)

    # Primer día del mes anterior
    inicio_mes_anterior = ultimo_dia_mes_anterior.replace(day=1)

    # Último día del mes anterior
    fin_mes_anterior = ultimo_dia_mes_anterior

    return fecha_corte, inicio_mes_anterior, fin_mes_anterior


# =============================================================================
# 4️⃣ SQL BASE · CONTENEDORES LIQUIDADOS
# =============================================================================
# Consulta todos los contenedores que han sido retirados en el rango de fechas
# indicado (fecha_retirada BETWEEN %s AND %s).
#
# Columnas devueltas (resumen):
#   - Datos de control: id, nº expediente, nº solicitud, nº colocación.
#   - Fechas: colocación, retirada, instalación.
#   - Solicitante: nombre, NIF, teléfono.
#   - Proveedor: nombre_razon_social.
#   - Cálculo: días de colocación (fecha_retirada - fecha_colocacion + 1).
# =============================================================================

SQL_LIQUIDADOS = """
SELECT
    c.idtbl_control_contenedores,
    p.nombre_razon_social,
    c.numero_expediente,
    c.numero_solicitud,
    c.numero_colocacion,
    c.fecha_colocacion,
    c.fecha_retirada,
    c.nombre_solicitante,
    c.nif,
    c.telefono,

    DATEDIFF(c.fecha_retirada, c.fecha_colocacion) + 1 AS dias_colocacion

FROM control_via_publica.tbl_control_contenedores c

LEFT JOIN bd_tbl_comunes.tbl_proveedores p
       ON c.idtbl_proveedores = p.Idtbl_proveedores

WHERE
    c.fecha_retirada BETWEEN %s AND %s
"""


# =============================================================================
# 5️⃣ BOTÓN · GENERACIÓN Y DESCARGA DEL INFORME MENSUAL
# =============================================================================
# Definimos la vista principal del BOTÓN:
#
#   contenedores_informe_mensual_liquidados
#
# RUTA PÚBLICA:
#   GET /control_via_publica/contenedores/informe_mensual_liquidados
#
# RESPONSABILIDADES:
#   1) Calcular el rango de fechas del mes anterior completo.
#   2) Consultar la base de datos para obtener los contenedores liquidados
#      en ese rango (SQL_LIQUIDADOS).
#   3) Si no hay registros:
#        - Mostrar una plantilla amigable informando de ello.
#   4) Si hay registros:
#        - Convertirlos en un DataFrame de pandas.
#        - Determinar la carpeta destino con obtener_ruta_informes().
#        - Construir el nombre del fichero: AAAAMM_liquidados.xlsx.
#        - Guardar el Excel en disco.
#        - Registrar en log la ruta generada.
#        - Enviar el fichero como descarga al navegador.
# =============================================================================

@btn_contenedores_informe_mensual_liquidados_bp.route(
    "/informe_mensual_liquidados",
    methods=["GET"],
)
@login_required
@rol_required("super_admin")
def contenedores_informe_mensual_liquidados():
    """
    5.1️⃣ BOTÓN · Genera el informe Excel de contenedores liquidados del mes
    anterior y lanza la descarga del fichero resultante.

    Forma parte del módulo control_via_publica_contenedores como un botón
    especializado de informes.
    """

    # -------------------------------------------------------------------------
    # 5.1.1) Calcular fechas del mes anterior
    # -------------------------------------------------------------------------
    hoy = date.today()

    _, inicio_mes_anterior, fin_mes_anterior = calcular_rango_mes_anterior(hoy)

    current_app.logger.info(
        "Generando informe liquidados entre %s y %s",
        inicio_mes_anterior,
        fin_mes_anterior,
    )

    # -------------------------------------------------------------------------
    # 5.1.2) Consultar base de datos
    # -------------------------------------------------------------------------
    filas = ejecutar_query(
        SQL_LIQUIDADOS,
        (inicio_mes_anterior, fin_mes_anterior),
        nombre_bd="control_via_publica",
    )

    # Si no hay registros, mostramos una plantilla con mensaje amigable
    if not filas:
        return render_template(
            "control_obras/informe_contenedores_mensaje.html",
            titulo="Sin resultados",
            mensaje=(
                "No se encontraron contenedores liquidados "
                "en el mes anterior."
            ),
        )

    # -------------------------------------------------------------------------
    # 5.1.3) Convertir resultados a DataFrame de pandas
    # -------------------------------------------------------------------------
    df = pd.DataFrame(filas)

    # -------------------------------------------------------------------------
    # 5.1.4) Calcular carpeta destino (contenedores/informes/AÑO/MES)
    # -------------------------------------------------------------------------
    carpeta = obtener_ruta_informes(inicio_mes_anterior)

    # -------------------------------------------------------------------------
    # 5.1.5) Crear nombre del archivo Excel (AAAAMM_liquidados.xlsx)
    # -------------------------------------------------------------------------
    nombre_fichero = f"{inicio_mes_anterior:%Y%m}_liquidados.xlsx"

    ruta_fichero = os.path.join(
        carpeta,
        nombre_fichero,
    )

    # -------------------------------------------------------------------------
    # 5.1.6) Generar Excel en disco
    # -------------------------------------------------------------------------
    df.to_excel(
        ruta_fichero,
        index=False,
    )

    current_app.logger.info(
        "Informe liquidados generado en: %s",
        ruta_fichero,
    )

    # -------------------------------------------------------------------------
    # 5.1.7) Enviar fichero como descarga al navegador
    # -------------------------------------------------------------------------
    return send_file(
        ruta_fichero,
        as_attachment=True,
        download_name=nombre_fichero,
    )