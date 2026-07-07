# obras_core/backend_obras.py
# =============================================================================
# 🏗️ BACKEND OBRAS
# =============================================================================
# Este módulo agrupa la lógica de backend relacionada con OBRAS:
#
#   1) Procesamiento de PDFs de licencias de obra:
#        - Extrae datos de un PDF (nº expediente, ref. catastral, solicitante,
#          presupuesto, tasa, etc.).
#        - NO toca la base de datos ni mueve archivos.
#
#   2) Integración con la agenda de vía pública:
#        - Crea eventos de agenda de tipo 'OBRA' en tbl_agenda_via_publica.
#        - Asocia la calle afectada en tbl_agenda_calles_afectadas.
#
# Este módulo está pensado para ser usado desde:
#   - Blueprints (Flask).
#   - Scripts CLI.
#   - Tareas async / cron.
#
# Mantén este fichero libre de código específico de Flask (request, response,
# render_template, etc.), para que sea reutilizable y testeable.
# =============================================================================

import re
from typing import Dict, Any, Optional
from datetime import datetime

import PyPDF2

from agenda_core.backend_agenda import (
    crear_evento_agenda,
    añadir_calle_a_evento,
)

# =============================================================================
# 1️⃣ PROCESAMIENTO DE PDFS DE OBRAS
# =============================================================================


def procesar_pdf_core_obras(ruta_pdf: str) -> Dict[str, Any]:
    """
    Lee un PDF de obras y devuelve un dict con:
      - estado: 'ok' o 'error'
      - motivo: texto explicativo
      - datos : dict con los campos necesarios para tbl_obras

    El dict 'datos' puede incluir, entre otros:

      - numero_expediente: str | None
      - tipo_expediente: str | None  (ej. 'DECLARACION_OBRA_MENOR')
      - ref_catastral: str | None
      - solicitante_nombre: str | None
      - presupuesto: float | None
      - tasa: float | None
      - fecha_documento_texto: str | None
      - estado_licencia: str | None  (ej. 'CONCEDIDA')
      - ruta_pdf_principal: str | None (se rellena en capas superiores)

    Este backend NO:
      - escribe en la BD,
      - mueve/renombra archivos,
      - muestra mensajes al usuario.

    Solo interpreta el PDF y extrae información.
    """
    datos: Dict[str, Any] = {}

    try:
        # 1) Leer texto completo del PDF
        full_text = ""
        with open(ruta_pdf, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                full_text += page.extract_text() or ""

        # Normalizamos saltos de línea y tabulaciones
        texto = full_text.replace("\n", " ").replace("\t", " ")

        # 2) Número de expediente (ej. "Nº EXPEDIENTE: 533/2025")
        m = re.search(r"N[ºO]\s*EXPEDIENTE:\s*([0-9\/-]+)", texto, re.IGNORECASE)
        datos["numero_expediente"] = m.group(1).strip() if m else None

        # 3) Tipo de expediente (lo inferimos por texto)
        if "DECLARACION RESPONSABLE DE OBRA MENOR" in texto.upper():
            datos["tipo_expediente"] = "DECLARACION_OBRA_MENOR"
        else:
            datos["tipo_expediente"] = None

        # 4) Ref. catastral (ej. "REF. CAT: 8314304UL5081S0116GS")
        m = re.search(r"REF\.?\s*CAT[:\s]+\s*([0-9A-Z]+)", texto, re.IGNORECASE)
        datos["ref_catastral"] = m.group(1).strip() if m else None

        # 5) Solicitante (ej. "Solicitante: M. CARMEN GARCIA SÁNCHEZ")
        m = re.search(r"Solicitante:\s*([A-ZÁÉÍÓÚÑ\s\.]+)", texto)
        datos["solicitante_nombre"] = m.group(1).strip() if m else None

        # 6) Presupuesto (ej. "Presupuesto: 1.060 €")
        m = re.search(r"Presupuesto:\s*([\d\.,]+)", texto, re.IGNORECASE)
        if m:
            bruto = m.group(1).replace(".", "").replace(",", ".")
            try:
                datos["presupuesto"] = float(bruto)
            except ValueError:
                datos["presupuesto"] = None
        else:
            datos["presupuesto"] = None

        # 7) Tasa (ej. "Tasa: 15 €")
        m = re.search(r"Tasa:\s*([\d\.,]+)", texto, re.IGNORECASE)
        if m:
            bruto = m.group(1).replace(".", "").replace(",", ".")
            try:
                datos["tasa"] = float(bruto)
            except ValueError:
                datos["tasa"] = None
        else:
            datos["tasa"] = None

        # 8) Fecha del informe (ej. "Ávila, a 13 de febrero de 2026")
        #    De momento la dejamos como texto bruto. Si necesitas,
        #    en otra capa la conviertes a 'YYYY-MM-DD'.
        m = re.search(r"[ÁA]vila,\s*a\s+(.+?20[0-9]{2})", texto, re.IGNORECASE)
        datos["fecha_documento_texto"] = m.group(1).strip() if m else None

        # 9) Estado licencia (por texto del informe)
        if "procede la concesión de la licencia solicitada" in texto.lower():
            datos["estado_licencia"] = "CONCEDIDA"
        else:
            datos["estado_licencia"] = None

        # 10) Ruta del PDF principal (se rellenará en utils_async, etc.)
        datos["ruta_pdf_principal"] = None

        return {
            "estado": "ok",
            "motivo": "PDF de obras procesado correctamente",
            "datos": datos,
        }

    except Exception as e:
        return {
            "estado": "error",
            "motivo": f"Error procesando PDF de obras: {e!r}",
            "datos": datos,
        }


# =============================================================================
# 2️⃣ INTEGRACIÓN CON LA AGENDA DE VÍA PÚBLICA
# =============================================================================
# Estas funciones se apoyan en agenda_core.backend_agenda, que encapsula
# la lógica genérica de:
#   - tbl_agenda_via_publica
#   - tbl_agenda_calles_afectadas
#
# Aquí solo adaptamos el caso concreto de OBRAS:
#   - tipo de evento: 'OBRA'
#   - origen_tabla: 'tbl_obras'
#   - origen_id: idtbl_obras
# =============================================================================


def crear_evento_para_obra(
    id_obra: int,
    id_calle: int,
    titulo: str,
    descripcion: Optional[str],
    fecha_inicio: datetime,
    fecha_fin: datetime,
) -> int:
    """
    Crea un evento de agenda asociado a una obra concreta.

    Parámetros:
      - id_obra:     ID de la obra en tbl_obras (idtbl_obras).
      - id_calle:    ID de la calle afectada (idtbl_calles).
      - titulo:      Título que se mostrará en la agenda.
      - descripcion: Descripción opcional (ej. ref. catastral).
      - fecha_inicio: Fecha/hora de inicio de las obras.
      - fecha_fin:    Fecha/hora de fin de las obras.

    Comportamiento:
      1) Crea un registro en tbl_agenda_via_publica con:
           - tipo de evento 'OBRA' (codigo en tbl_tipos_evento_via_publica).
           - origen_tabla='tbl_obras', origen_id=id_obra.
      2) Asocia la calle indicada en tbl_agenda_calles_afectadas:
           - idtbl_calles = id_calle
           - sentido = 'AMBOS'

    Devuelve:
      - idtbl_agenda (int) del evento creado.

    Requisitos previos:
      - tbl_tipos_evento_via_publica debe tener un registro con codigo='OBRA'.
      - El ID de calle debe existir en tbl_calles.
    """
    # 1) Crear el evento genérico de agenda
    id_agenda = crear_evento_agenda(
        codigo_tipo="OBRA",
        titulo=titulo,
        descripcion=descripcion,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        all_day=False,
        origen_tabla="tbl_obras",
        origen_id=id_obra,
    )

    # 2) Asignar la calle afectada
    añadir_calle_a_evento(
        id_agenda=id_agenda,
        id_calle=id_calle,
        sentido="AMBOS",
    )

    return id_agenda
