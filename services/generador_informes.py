# =============================================================================
# 📊 SERVICIO GLOBAL: GENERADOR DE INFORMES
# =============================================================================
#
# Este módulo permite generar informes en múltiples formatos
# a partir de una consulta SQL.
#
# FORMATOS SOPORTADOS
#
#   HTML   → para mostrar en el sistema
#   PDF    → reportlab
#   XLSX   → Excel
#   CSV
#   JSON
#
# OBJETIVO
#
# Evitar repetir código en todos los módulos del sistema:
#
#   contenedores
#   obras
#   vados
#   terrazas
#   vía pública
#
# =============================================================================


# =============================================================================
# 1️⃣ IMPORTS
# =============================================================================

import csv
import json
import io

from db import ejecutar_query


# =============================================================================
# 2️⃣ GENERAR DATOS
# =============================================================================

def obtener_datos(sql, parametros=(), bd="control_via_publica"):

    return ejecutar_query(sql, parametros, nombre_bd=bd)


# =============================================================================
# 3️⃣ EXPORTAR JSON
# =============================================================================

def exportar_json(datos):

    return json.dumps(datos, indent=4, ensure_ascii=False)


# =============================================================================
# 4️⃣ EXPORTAR CSV
# =============================================================================

def exportar_csv(datos):

    output = io.StringIO()

    if not datos:
        return ""

    writer = csv.DictWriter(output, fieldnames=datos[0].keys())

    writer.writeheader()

    writer.writerows(datos)

    return output.getvalue()


# =============================================================================
# 5️⃣ EXPORTAR EXCEL
# =============================================================================

def exportar_excel(datos):

    from openpyxl import Workbook

    wb = Workbook()

    ws = wb.active

    if not datos:
        return wb

    columnas = list(datos[0].keys())

    ws.append(columnas)

    for fila in datos:
        ws.append(list(fila.values()))

    return wb


# =============================================================================
# 6️⃣ EXPORTAR PDF
# =============================================================================

def exportar_pdf(datos, titulo="Informe"):

    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()

    pdf = canvas.Canvas(buffer, pagesize=A4)

    y = 800

    pdf.setFont("Helvetica", 10)

    pdf.drawString(40, 820, titulo)

    if datos:

        columnas = list(datos[0].keys())

        pdf.drawString(40, y, " | ".join(columnas))

        y -= 20

        for fila in datos:

            linea = " | ".join([str(v) for v in fila.values()])

            pdf.drawString(40, y, linea)

            y -= 20

            if y < 50:

                pdf.showPage()

                y = 800

    pdf.save()

    buffer.seek(0)

    return buffer


# =============================================================================
# 7️⃣ GENERADOR PRINCIPAL
# =============================================================================

def generar_informe(sql, parametros=(), formato="html", titulo="Informe"):

    datos = obtener_datos(sql, parametros)

    if formato == "json":
        return exportar_json(datos)

    if formato == "csv":
        return exportar_csv(datos)

    if formato == "excel":
        return exportar_excel(datos)

    if formato == "pdf":
        return exportar_pdf(datos, titulo)

    return datos