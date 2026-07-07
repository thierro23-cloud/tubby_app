# =============================================================================
# 🧱 BLUEPRINT · CONTENEDORES · RETIRADAS SIN RELACIÓN CON COLOCACIÓN
# =============================================================================
#
# Realizado por: Tinito
# Fecha: 06/07/2026
#
# 🎯 OBJETIVO
#   - Gestionar las RETIRADAS que no se han podido relacionar automáticamente
#     con ninguna COLOCACIÓN.
#   - Leer los PDFs ubicados en static/solo_retirada.
#   - Extraer todos los datos posibles del PDF.
#   - Permitir revisar, corregir y completar manualmente los datos extraídos.
#   - Guardar la información en tbl_contenedores_retirada.
#
# 🧩 RELACIÓN CON OTRAS PIEZAS
#   - WATCHERS / ASYNC:
#       · Detectan PDFs de retirada que no se han podido relacionar.
#       · Depositan esos PDFs en static/solo_retirada.
#   - TABLA tbl_contenedores_retirada:
#       · Almacena los datos extraídos de cada retirada.
#       · Queda como tabla de trabajo previa al emparejado.
#   - BLUEPRINT DE EMPAREJADO:
#       · Usará después tbl_contenedores_retirada y tbl_control_contenedores.
#       · Buscará la colocación correcta.
#       · Completará la relación entre retirada y colocación.
#
# 🚦 ALCANCE
#   - NO empareja retiradas con colocaciones.
#   - NO actualiza tbl_control_contenedores.
#   - NO borra PDFs físicos.
#   - NO limpia retiradas emparejadas.
#   - SÍ:
#       · Lista PDFs pendientes de retirada.
#       · Extrae texto del PDF si hay librería disponible.
#       · Intenta detectar NIF, teléfono, expediente, solicitud, fechas, CSV,
#         calle, número de portal y coordenadas GPS.
#       · Permite completar manualmente los datos.
#       · Inserta o actualiza tbl_contenedores_retirada.
#       · Deja tiene_relacion = 0.
#       · Deja idtbl_contenedor_colocacion = NULL.
# =============================================================================

from __future__ import annotations

import json
import re
from pathlib import Path
from datetime import datetime, date
from typing import Any

from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import current_user

from services.helpers import login_required
from db import ejecutar_query


btn_contenedores_retiradas_sin_relacion_bp = Blueprint(
    "btn_contenedores_retiradas_sin_relacion_bp",
    __name__,
    url_prefix="/contenedores/retiradas_sin_relacion",
)


# =============================================================================
# 📁 CONFIGURACIÓN GENERAL
# =============================================================================

PDFS_DIR = Path("static/solo_retirada")


# =============================================================================
# 🗃️ SQL · CONSULTAS AUXILIARES
# =============================================================================

SQL_SELECT_RETIRADA_POR_PDF = """
SELECT *
FROM tbl_contenedores_retirada
WHERE nombre_pdf = %s
LIMIT 1
"""

SQL_SELECT_PROVEEDORES = """
SELECT
    idtbl_proveedores,
    nombre_razon_social
FROM bd_tbl_comunes.tbl_proveedores
ORDER BY nombre_razon_social
"""

SQL_SELECT_CALLES = """
SELECT
    idtbl_calles,
    calles
FROM bd_tbl_comunes.tbl_calles
ORDER BY calles
"""

SQL_SELECT_PROVEEDOR_POR_NIF = """
SELECT
    idtbl_proveedores,
    nombre_razon_social
FROM bd_tbl_comunes.tbl_proveedores
WHERE nif = %s
LIMIT 1
"""

SQL_SELECT_CALLE_POR_NOMBRE = """
SELECT
    idtbl_calles,
    calles
FROM bd_tbl_comunes.tbl_calles
WHERE calles LIKE %s
ORDER BY
    CASE
        WHEN calles = %s THEN 0
        WHEN calles LIKE %s THEN 1
        ELSE 2
    END,
    calles
LIMIT 1
"""


# =============================================================================
# 🗃️ SQL · INSERCIÓN EN tbl_contenedores_retirada
# =============================================================================

SQL_INSERT_RETIRADA = """
INSERT INTO tbl_contenedores_retirada (
    nombre_pdf,
    ruta_pdf,
    nif,
    idtbl_proveedores,
    nombre_solicitante,
    telefono,
    numero_expediente,
    numero_solicitud,
    fecha_colocacion,
    fecha_retirada,
    fecha_firma_inicial,
    idtbl_tipos_de_vias,
    idtbl_calles,
    numero_portal,
    csv,
    csv_retirada,
    latitud,
    longitud,
    precision_gps,
    gps_nivel_calidad,
    gps_origen,
    idtbl_dimensiones,
    idtbl_gestores,
    observaciones,
    datos_extraidos_json,
    tiene_relacion,
    idtbl_contenedor_colocacion,
    fecha_creacion,
    fecha_validacion,
    idtbl_gestores_validacion
)
VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
    %s, %s, %s, %s, %s, %s, %s, NOW(), %s, %s
)
"""


# =============================================================================
# 🗃️ SQL · ACTUALIZACIÓN EN tbl_contenedores_retirada
# =============================================================================

SQL_UPDATE_RETIRADA = """
UPDATE tbl_contenedores_retirada
SET
    nombre_pdf = %s,
    ruta_pdf = %s,
    nif = %s,
    idtbl_proveedores = %s,
    nombre_solicitante = %s,
    telefono = %s,
    numero_expediente = %s,
    numero_solicitud = %s,
    fecha_colocacion = %s,
    fecha_retirada = %s,
    fecha_firma_inicial = %s,
    idtbl_tipos_de_vias = %s,
    idtbl_calles = %s,
    numero_portal = %s,
    csv = %s,
    csv_retirada = %s,
    latitud = %s,
    longitud = %s,
    precision_gps = %s,
    gps_nivel_calidad = %s,
    gps_origen = %s,
    idtbl_dimensiones = %s,
    idtbl_gestores = %s,
    observaciones = %s,
    datos_extraidos_json = %s,
    tiene_relacion = %s,
    idtbl_contenedor_colocacion = %s,
    fecha_validacion = %s,
    idtbl_gestores_validacion = %s
WHERE idtbl_contenedores_retirada = %s
"""


# =============================================================================
# 📄 LISTADO DE PDFS PENDIENTES
# =============================================================================

def _listar_pdfs_solo_retirada() -> list[Path]:
    """
    Devuelve la lista de PDFs pendientes de retirada.

    Returns:
        list[Path]: PDFs encontrados en static/solo_retirada.
    """
    if not PDFS_DIR.exists():
        return []

    return sorted(PDFS_DIR.glob("*.pdf"))


# =============================================================================
# 👤 IDENTIFICACIÓN DEL GESTOR ACTUAL
# =============================================================================

def _obtener_id_usuario_logueado() -> int | None:
    """
    Obtiene el identificador del gestor autenticado.

    Returns:
        int | None: ID del gestor o None si no está disponible.
    """
    id_usuario = getattr(current_user, "idtbl_gestores", None)

    if id_usuario is None:
        id_usuario = session.get("idtbl_gestores")

    return id_usuario


# =============================================================================
# 🧭 CONTROL DE NAVEGACIÓN DE PDFS
# =============================================================================

def _obtener_pdf_actual() -> dict[str, Any]:
    """
    Calcula qué PDF debe mostrarse actualmente.

    Returns:
        dict: Información del PDF actual, posición y total.
    """
    pdfs = _listar_pdfs_solo_retirada()
    pdf_total = len(pdfs)

    pdf_pos = request.values.get("pdf_pos", "0")

    try:
        pdf_pos = int(pdf_pos)
    except ValueError:
        pdf_pos = 0

    pdf_nav = request.args.get("pdf_nav")

    if pdf_nav == "prev" and pdf_pos > 0:
        pdf_pos -= 1
    elif pdf_nav == "next" and pdf_pos + 1 < pdf_total:
        pdf_pos += 1

    if pdf_pos < 0:
        pdf_pos = 0

    if pdf_total > 0 and pdf_pos >= pdf_total:
        pdf_pos = pdf_total - 1

    if pdf_total > 0:
        pdf_actual = pdfs[pdf_pos]
        pdf_url = url_for("static", filename=f"solo_retirada/{pdf_actual.name}")
        ruta_relativa = f"solo_retirada/{pdf_actual.name}"
    else:
        pdf_actual = None
        pdf_url = None
        ruta_relativa = None

    return {
        "pdfs": pdfs,
        "pdf_actual": pdf_actual,
        "pdf_url": pdf_url,
        "ruta_relativa": ruta_relativa,
        "pdf_pos": pdf_pos,
        "pdf_total": pdf_total,
    }


# =============================================================================
# 🔤 NORMALIZACIÓN DE TEXTO
# =============================================================================

def _limpiar_texto(texto: str | None) -> str:
    """
    Limpia espacios duplicados y saltos innecesarios.

    Args:
        texto: Texto original.

    Returns:
        str: Texto normalizado.
    """
    if not texto:
        return ""

    texto = texto.replace("\r", "\n")
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)

    return texto.strip()


def _normalizar_valor(valor: Any) -> Any:
    """
    Convierte cadenas vacías en None.

    Args:
        valor: Valor recibido.

    Returns:
        Any: Valor normalizado.
    """
    if valor is None:
        return None

    if isinstance(valor, str):
        valor = valor.strip()
        return valor if valor else None

    return valor

# =============================================================================
# 🏷️ NORMALIZACIÓN Y RENOMBRADO DEL PDF POR CSV
# =============================================================================

def _normalizar_csv_para_nombre_archivo(csv_valor: str | None) -> str | None:
    """
    Normaliza un CSV para poder usarlo como nombre seguro de archivo.

    Args:
        csv_valor: CSV extraído del PDF.

    Returns:
        str | None: CSV limpio para nombre de archivo o None.
    """
    csv_valor = _normalizar_valor(csv_valor)

    if not csv_valor:
        return None

    csv_valor = str(csv_valor).strip().upper()

    # Dejamos solo caracteres seguros para nombres de archivo.
    csv_valor = re.sub(r"[^A-Z0-9_\-]", "", csv_valor)

    return csv_valor or None


def _renombrar_pdf_por_csv(pdf_path: Path, csv_retirada: str | None, csv: str | None) -> Path:
    """
    Renombra el PDF usando como nombre principal el CSV de retirada.

    Prioridad:
        1. csv_retirada
        2. csv
        3. nombre original si no hay CSV válido

    Si ya existe un archivo con ese nombre, no lo duplica:
        - Si el archivo existente es el mismo, devuelve la ruta actual.
        - Si existe otro PDF con ese CSV, devuelve la ruta existente.

    Args:
        pdf_path: Ruta actual del PDF.
        csv_retirada: CSV específico de retirada.
        csv: CSV general del documento.

    Returns:
        Path: Ruta final del PDF.
    """
    if not pdf_path or not pdf_path.exists():
        return pdf_path

    csv_archivo = _normalizar_csv_para_nombre_archivo(csv_retirada or csv)

    if not csv_archivo:
        return pdf_path

    nuevo_nombre = f"{csv_archivo}.pdf"
    nuevo_path = pdf_path.with_name(nuevo_nombre)

    if pdf_path.name == nuevo_nombre:
        return pdf_path

    if nuevo_path.exists():
        return nuevo_path

    try:
        pdf_path.rename(nuevo_path)
        return nuevo_path
    except OSError:
        return pdf_path

def _normalizar_fecha(valor: str | None) -> str | None:
    """
    Normaliza fechas a formato YYYY-MM-DD.

    Admite:
        - DD/MM/YYYY
        - DD-MM-YYYY
        - YYYY-MM-DD

    Args:
        valor: Fecha en texto.

    Returns:
        str | None: Fecha normalizada o None.
    """
    valor = _normalizar_valor(valor)

    if not valor:
        return None

    valor = str(valor).strip()

    formatos = ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d")

    for formato in formatos:
        try:
            return datetime.strptime(valor, formato).date().isoformat()
        except ValueError:
            continue

    return None


def _normalizar_decimal(valor: str | None) -> float | None:
    """
    Convierte un texto numérico en decimal.

    Args:
        valor: Valor en texto.

    Returns:
        float | None: Número convertido o None.
    """
    valor = _normalizar_valor(valor)

    if not valor:
        return None

    try:
        return float(str(valor).replace(",", "."))
    except ValueError:
        return None


# =============================================================================
# 📖 EXTRACCIÓN DE TEXTO DEL PDF
# =============================================================================

def _extraer_texto_pdf(pdf_path: Path) -> str:
    """
    Extrae texto de un PDF usando las librerías disponibles.

    Orden de intento:
        1. PyMuPDF / fitz
        2. pypdf
        3. PyPDF2

    Args:
        pdf_path: Ruta física del PDF.

    Returns:
        str: Texto extraído o cadena vacía si no se pudo extraer.
    """
    if not pdf_path or not pdf_path.exists():
        return ""

    texto = ""

    try:
        import fitz

        partes = []
        with fitz.open(pdf_path) as doc:
            for pagina in doc:
                partes.append(pagina.get_text("text") or "")

        texto = "\n".join(partes)
        texto = _limpiar_texto(texto)

        if texto:
            return texto
    except Exception:
        pass

    try:
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_path))
        partes = []

        for pagina in reader.pages:
            partes.append(pagina.extract_text() or "")

        texto = "\n".join(partes)
        texto = _limpiar_texto(texto)

        if texto:
            return texto
    except Exception:
        pass

    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(str(pdf_path))
        partes = []

        for pagina in reader.pages:
            partes.append(pagina.extract_text() or "")

        texto = "\n".join(partes)
        texto = _limpiar_texto(texto)

        if texto:
            return texto
    except Exception:
        pass

    return ""


# =============================================================================
# 🔎 UTILIDADES DE EXTRACCIÓN POR PATRONES
# =============================================================================

def _buscar_regex(texto: str, patrones: list[str], flags: int = re.IGNORECASE) -> str | None:
    """
    Busca el primer valor que coincida con una lista de patrones.

    Args:
        texto: Texto donde buscar.
        patrones: Lista de expresiones regulares.
        flags: Flags de búsqueda.

    Returns:
        str | None: Primer valor encontrado.
    """
    for patron in patrones:
        match = re.search(patron, texto, flags)

        if match:
            if match.lastindex:
                return _normalizar_valor(match.group(1))
            return _normalizar_valor(match.group(0))

    return None


def _buscar_fecha_por_etiqueta(texto: str, etiquetas: list[str]) -> str | None:
    """
    Busca una fecha cercana a una etiqueta concreta.

    Args:
        texto: Texto del PDF.
        etiquetas: Posibles etiquetas de fecha.

    Returns:
        str | None: Fecha normalizada.
    """
    for etiqueta in etiquetas:
        patron = (
            rf"{etiqueta}"
            r"[\s:\-]*"
            r"([0-3]?\d[\/\-][01]?\d[\/\-]\d{4}|\d{4}\-\d{2}\-\d{2})"
        )

        valor = _buscar_regex(texto, [patron])

        fecha = _normalizar_fecha(valor)
        if fecha:
            return fecha

    return None


# =============================================================================
# 🧠 EXTRACCIÓN DE DATOS ESTRUCTURADOS
# =============================================================================

def _extraer_datos_desde_texto(texto: str) -> dict[str, Any]:
    """
    Extrae todos los datos posibles desde el texto del PDF.

    Args:
        texto: Texto extraído del PDF.

    Returns:
        dict: Datos detectados.
    """
    texto_limpio = _limpiar_texto(texto)

    nif = _buscar_regex(
        texto_limpio,
        [
            r"\b([XYZ]\d{7}[A-Z])\b",
            r"\b(\d{8}[A-Z])\b",
            r"\b([A-Z]\d{7}[A-Z0-9])\b",
            r"NIF[\s:\-]*([A-Z0-9]{8,10})",
            r"CIF[\s:\-]*([A-Z0-9]{8,10})",
        ],
    )

    telefono = _buscar_regex(
        texto_limpio,
        [
            r"Tel[eé]fono[\s:\-]*([+0-9\s]{9,18})",
            r"M[oó]vil[\s:\-]*([+0-9\s]{9,18})",
            r"\b([6789]\d{8})\b",
        ],
    )

    if telefono:
        telefono = re.sub(r"\s+", "", telefono)

    numero_expediente = _buscar_regex(
        texto_limpio,
        [
            r"Expediente[\s:\-]*([A-Z0-9\/\.\-_]+)",
            r"N[úu]mero de expediente[\s:\-]*([A-Z0-9\/\.\-_]+)",
            r"Nº expediente[\s:\-]*([A-Z0-9\/\.\-_]+)",
        ],
    )

    numero_solicitud = _buscar_regex(
        texto_limpio,
        [
            r"Solicitud[\s:\-]*([A-Z0-9\/\.\-_]+)",
            r"N[úu]mero de solicitud[\s:\-]*([A-Z0-9\/\.\-_]+)",
            r"Nº solicitud[\s:\-]*([A-Z0-9\/\.\-_]+)",
        ],
    )

    csv = _buscar_regex(
        texto_limpio,
        [
            r"CSV[\s:\-]*([A-Z0-9]{12,80})",
            r"C[oó]digo seguro de verificaci[oó]n[\s:\-]*([A-Z0-9]{12,80})",
        ],
    )

    csv_retirada = _buscar_regex(
        texto_limpio,
        [
            r"CSV retirada[\s:\-]*([A-Z0-9]{12,80})",
            r"CSV de retirada[\s:\-]*([A-Z0-9]{12,80})",
        ],
    )

    nombre_solicitante = _buscar_regex(
        texto_limpio,
        [
            r"Solicitante[\s:\-]*([^\n]+)",
            r"Nombre solicitante[\s:\-]*([^\n]+)",
            r"Interesado[\s:\-]*([^\n]+)",
            r"Raz[oó]n social[\s:\-]*([^\n]+)",
        ],
    )

    fecha_colocacion = _buscar_fecha_por_etiqueta(
        texto_limpio,
        [
            r"Fecha de colocaci[oó]n",
            r"Fecha colocaci[oó]n",
            r"Colocaci[oó]n",
        ],
    )

    fecha_retirada = _buscar_fecha_por_etiqueta(
        texto_limpio,
        [
            r"Fecha de retirada",
            r"Fecha retirada",
            r"Retirada",
        ],
    )

    fecha_firma_inicial = _buscar_fecha_por_etiqueta(
        texto_limpio,
        [
            r"Fecha de firma",
            r"Fecha firma",
            r"Firmado",
        ],
    )

    calle_detectada = _buscar_regex(
        texto_limpio,
        [
            r"(?:Calle|CL|C\/|Avenida|AV|Avda\.?|Plaza|Pza\.?|Paseo|Camino|Carretera)"
            r"[\s\.\/\-]*([A-ZÁÉÍÓÚÑ0-9][^\n,]{3,80})",
            r"V[ií]a p[uú]blica[\s:\-]*([^\n,]{3,80})",
            r"Emplazamiento[\s:\-]*([^\n,]{3,80})",
            r"Direcci[oó]n[\s:\-]*([^\n,]{3,80})",
        ],
    )

    numero_portal = _buscar_regex(
        texto_limpio,
        [
            r"N[úu]mero[\s:\-]*([0-9]{1,5}[A-Z]?)",
            r"Portal[\s:\-]*([0-9]{1,5}[A-Z]?)",
            r"\b(?:nº|n°|num\.?)\s*([0-9]{1,5}[A-Z]?)\b",
        ],
    )

    latitud = _buscar_regex(
        texto_limpio,
        [
            r"Latitud[\s:\-]*([\-]?\d{1,2}[\,\.]\d+)",
            r"LAT[\s:\-]*([\-]?\d{1,2}[\,\.]\d+)",
        ],
    )

    longitud = _buscar_regex(
        texto_limpio,
        [
            r"Longitud[\s:\-]*([\-]?\d{1,3}[\,\.]\d+)",
            r"LON[\s:\-]*([\-]?\d{1,3}[\,\.]\d+)",
        ],
    )

    datos = {
        "nif": nif,
        "idtbl_proveedores": None,
        "nombre_solicitante": nombre_solicitante,
        "telefono": telefono,
        "numero_expediente": numero_expediente,
        "numero_solicitud": numero_solicitud,
        "fecha_colocacion": fecha_colocacion,
        "fecha_retirada": fecha_retirada,
        "fecha_firma_inicial": fecha_firma_inicial,
        "idtbl_tipos_de_vias": None,
        "idtbl_calles": None,
        "calle_detectada": calle_detectada,
        "numero_portal": numero_portal,
        "csv": csv,
        "csv_retirada": csv_retirada or csv,
        "latitud": _normalizar_decimal(latitud),
        "longitud": _normalizar_decimal(longitud),
        "precision_gps": None,
        "gps_nivel_calidad": None,
        "gps_origen": "PDF" if latitud or longitud else None,
        "idtbl_dimensiones": None,
        "observaciones": None,
    }

    return datos


# =============================================================================
# 🔗 CRUCE AUXILIAR CON TABLAS COMUNES
# =============================================================================

def _query_opcional(sql: str, params: tuple = ()) -> list[dict]:
    """
    Ejecuta una consulta auxiliar sin romper el flujo si falla.

    Args:
        sql: Consulta SQL.
        params: Parámetros SQL.

    Returns:
        list[dict]: Resultado o lista vacía.
    """
    try:
        resultado = ejecutar_query(
            sql,
            params,
            nombre_bd="control_via_publica",
        )
        return resultado or []
    except Exception:
        return []


def _buscar_proveedor_por_nif(nif: str | None) -> int | None:
    """
    Busca proveedor por NIF.

    Args:
        nif: NIF extraído del PDF.

    Returns:
        int | None: ID del proveedor encontrado.
    """
    if not nif:
        return None

    resultado = _query_opcional(SQL_SELECT_PROVEEDOR_POR_NIF, (nif,))

    if resultado:
        return resultado[0].get("idtbl_proveedores")

    return None


def _buscar_calle_por_nombre(nombre_calle: str | None) -> int | None:
    """
    Busca calle aproximada por nombre.

    Args:
        nombre_calle: Calle detectada en el PDF.

    Returns:
        int | None: ID de la calle encontrada.
    """
    nombre_calle = _normalizar_valor(nombre_calle)

    if not nombre_calle:
        return None

    nombre_limpio = re.sub(
        r"^(calle|cl|c\/|avenida|avda|av|plaza|pza|paseo|camino|carretera)\s+",
        "",
        str(nombre_calle).strip(),
        flags=re.IGNORECASE,
    )

    patron_general = f"%{nombre_limpio}%"
    patron_inicio = f"{nombre_limpio}%"

    resultado = _query_opcional(
        SQL_SELECT_CALLE_POR_NOMBRE,
        (
            patron_general,
            nombre_limpio,
            patron_inicio,
        ),
    )

    if resultado:
        return resultado[0].get("idtbl_calles")

    return None


def _completar_ids_auxiliares(datos: dict[str, Any]) -> dict[str, Any]:
    """
    Completa IDs auxiliares a partir de datos extraídos.

    Args:
        datos: Datos extraídos del PDF.

    Returns:
        dict: Datos enriquecidos con IDs encontrados.
    """
    if not datos.get("idtbl_proveedores"):
        datos["idtbl_proveedores"] = _buscar_proveedor_por_nif(datos.get("nif"))

    if not datos.get("idtbl_calles"):
        datos["idtbl_calles"] = _buscar_calle_por_nombre(datos.get("calle_detectada"))

    return datos


# =============================================================================
# 🧾 CONSTRUCCIÓN DE DATOS BASE DE RETIRADA
# =============================================================================

def _construir_datos_retirada_desde_pdf(pdf_path: Path) -> dict[str, Any]:
    """
    Construye el diccionario inicial de retirada a partir del PDF.

    Args:
        pdf_path: PDF actual.

    Returns:
        dict: Datos preparados para mostrar o guardar.
    """
    texto_pdf = _extraer_texto_pdf(pdf_path)
    datos_extraidos = _extraer_datos_desde_texto(texto_pdf)

    datos_extraidos = _completar_ids_auxiliares(datos_extraidos)

    datos_extraidos_json = {
        "origen": "btn_contenedores_retiradas_sin_relacion_bp",
        "nombre_pdf": pdf_path.name,
        "ruta_pdf": f"solo_retirada/{pdf_path.name}",
        "fecha_extraccion": datetime.now().isoformat(timespec="seconds"),
        "texto_extraido_disponible": bool(texto_pdf),
        "campos_extraidos": datos_extraidos,
    }

    return {
        "idtbl_contenedores_retirada": None,
        "nombre_pdf": pdf_path.name,
        "ruta_pdf": f"solo_retirada/{pdf_path.name}",
        "nif": datos_extraidos.get("nif"),
        "idtbl_proveedores": datos_extraidos.get("idtbl_proveedores"),
        "nombre_solicitante": datos_extraidos.get("nombre_solicitante"),
        "telefono": datos_extraidos.get("telefono"),
        "numero_expediente": datos_extraidos.get("numero_expediente"),
        "numero_solicitud": datos_extraidos.get("numero_solicitud"),
        "fecha_colocacion": datos_extraidos.get("fecha_colocacion"),
        "fecha_retirada": datos_extraidos.get("fecha_retirada"),
        "fecha_firma_inicial": datos_extraidos.get("fecha_firma_inicial"),
        "idtbl_tipos_de_vias": datos_extraidos.get("idtbl_tipos_de_vias"),
        "idtbl_calles": datos_extraidos.get("idtbl_calles"),
        "numero_portal": datos_extraidos.get("numero_portal"),
        "csv": datos_extraidos.get("csv"),
        "csv_retirada": datos_extraidos.get("csv_retirada"),
        "latitud": datos_extraidos.get("latitud"),
        "longitud": datos_extraidos.get("longitud"),
        "precision_gps": datos_extraidos.get("precision_gps"),
        "gps_nivel_calidad": datos_extraidos.get("gps_nivel_calidad"),
        "gps_origen": datos_extraidos.get("gps_origen"),
        "idtbl_dimensiones": datos_extraidos.get("idtbl_dimensiones"),
        "idtbl_gestores": _obtener_id_usuario_logueado(),
        "observaciones": datos_extraidos.get("observaciones"),
        "datos_extraidos_json": json.dumps(datos_extraidos_json, ensure_ascii=False),
        "tiene_relacion": 0,
        "idtbl_contenedor_colocacion": None,
        "fecha_validacion": None,
        "idtbl_gestores_validacion": None,
    }


# =============================================================================
# 📥 LECTURA DE RETIRADA EXISTENTE
# =============================================================================

def _obtener_retirada_existente(nombre_pdf: str | None) -> dict[str, Any] | None:
    """
    Busca si un PDF ya tiene registro en tbl_contenedores_retirada.

    Args:
        nombre_pdf: Nombre del PDF.

    Returns:
        dict | None: Registro existente.
    """
    if not nombre_pdf:
        return None

    resultado = ejecutar_query(
        SQL_SELECT_RETIRADA_POR_PDF,
        (nombre_pdf,),
        nombre_bd="control_via_publica",
    )

    if resultado:
        return resultado[0]

    return None


# =============================================================================
# 🧩 DATOS PARA SELECTS DE FORMULARIO
# =============================================================================

def _cargar_proveedores() -> list[dict]:
    """
    Carga proveedores para selección manual.

    Returns:
        list[dict]: Proveedores.
    """
    return _query_opcional(SQL_SELECT_PROVEEDORES, ())


def _cargar_calles() -> list[dict]:
    """
    Carga calles para selección manual.

    Returns:
        list[dict]: Calles.
    """
    return _query_opcional(SQL_SELECT_CALLES, ())


# =============================================================================
# 📝 LECTURA DEL FORMULARIO MANUAL
# =============================================================================

def _leer_datos_formulario(pdf_path: Path | None) -> dict[str, Any]:
    """
    Lee los datos enviados desde el formulario.

    Args:
        pdf_path: PDF actual.

    Returns:
        dict: Datos normalizados para insertar o actualizar.
    """
    id_gestor = _obtener_id_usuario_logueado()

    nombre_pdf = request.form.get("nombre_pdf")
    ruta_pdf = request.form.get("ruta_pdf")

    if pdf_path:
        nombre_pdf = nombre_pdf or pdf_path.name
        ruta_pdf = ruta_pdf or f"solo_retirada/{pdf_path.name}"

    datos_visibles = {
        "nif": _normalizar_valor(request.form.get("nif")),
        "idtbl_proveedores": _normalizar_valor(request.form.get("idtbl_proveedores")),
        "nombre_solicitante": _normalizar_valor(request.form.get("nombre_solicitante")),
        "telefono": _normalizar_valor(request.form.get("telefono")),
        "numero_expediente": _normalizar_valor(request.form.get("numero_expediente")),
        "numero_solicitud": _normalizar_valor(request.form.get("numero_solicitud")),
        "fecha_colocacion": _normalizar_fecha(request.form.get("fecha_colocacion")),
        "fecha_retirada": _normalizar_fecha(request.form.get("fecha_retirada")),
        "fecha_firma_inicial": _normalizar_fecha(request.form.get("fecha_firma_inicial")),
        "idtbl_tipos_de_vias": _normalizar_valor(request.form.get("idtbl_tipos_de_vias")),
        "idtbl_calles": _normalizar_valor(request.form.get("idtbl_calles")),
        "numero_portal": _normalizar_valor(request.form.get("numero_portal")),
        "csv": _normalizar_valor(request.form.get("csv")),
        "csv_retirada": _normalizar_valor(request.form.get("csv_retirada")),
        "latitud": _normalizar_decimal(request.form.get("latitud")),
        "longitud": _normalizar_decimal(request.form.get("longitud")),
        "precision_gps": _normalizar_decimal(request.form.get("precision_gps")),
        "gps_nivel_calidad": _normalizar_valor(request.form.get("gps_nivel_calidad")),
        "gps_origen": _normalizar_valor(request.form.get("gps_origen")),
        "idtbl_dimensiones": _normalizar_valor(request.form.get("idtbl_dimensiones")),
        "observaciones": _normalizar_valor(request.form.get("observaciones")),
    }

    datos_extraidos_json = {
        "origen": "formulario_manual",
        "fecha_guardado": datetime.now().isoformat(timespec="seconds"),
        "campos_guardados": datos_visibles,
    }

    return {
        "idtbl_contenedores_retirada": _normalizar_valor(
            request.form.get("idtbl_contenedores_retirada")
        ),
        "nombre_pdf": _normalizar_valor(nombre_pdf),
        "ruta_pdf": _normalizar_valor(ruta_pdf),
        "nif": datos_visibles["nif"],
        "idtbl_proveedores": datos_visibles["idtbl_proveedores"],
        "nombre_solicitante": datos_visibles["nombre_solicitante"],
        "telefono": datos_visibles["telefono"],
        "numero_expediente": datos_visibles["numero_expediente"],
        "numero_solicitud": datos_visibles["numero_solicitud"],
        "fecha_colocacion": datos_visibles["fecha_colocacion"],
        "fecha_retirada": datos_visibles["fecha_retirada"],
        "fecha_firma_inicial": datos_visibles["fecha_firma_inicial"],
        "idtbl_tipos_de_vias": datos_visibles["idtbl_tipos_de_vias"],
        "idtbl_calles": datos_visibles["idtbl_calles"],
        "numero_portal": datos_visibles["numero_portal"],
        "csv": datos_visibles["csv"],
        "csv_retirada": datos_visibles["csv_retirada"],
        "latitud": datos_visibles["latitud"],
        "longitud": datos_visibles["longitud"],
        "precision_gps": datos_visibles["precision_gps"],
        "gps_nivel_calidad": datos_visibles["gps_nivel_calidad"],
        "gps_origen": datos_visibles["gps_origen"],
        "idtbl_dimensiones": datos_visibles["idtbl_dimensiones"],
        "idtbl_gestores": id_gestor,
        "observaciones": datos_visibles["observaciones"],
        "datos_extraidos_json": json.dumps(datos_extraidos_json, ensure_ascii=False),
        "tiene_relacion": 0,
        "idtbl_contenedor_colocacion": None,
        "fecha_validacion": None,
        "idtbl_gestores_validacion": None,
    }


# =============================================================================
# 💾 PREPARACIÓN DE PARÁMETROS SQL
# =============================================================================

def _params_insert(datos: dict[str, Any]) -> tuple:
    """
    Prepara parámetros para insertar una retirada.

    Args:
        datos: Datos de retirada.

    Returns:
        tuple: Parámetros SQL.
    """
    return (
        datos.get("nombre_pdf"),
        datos.get("ruta_pdf"),
        datos.get("nif"),
        datos.get("idtbl_proveedores"),
        datos.get("nombre_solicitante"),
        datos.get("telefono"),
        datos.get("numero_expediente"),
        datos.get("numero_solicitud"),
        datos.get("fecha_colocacion"),
        datos.get("fecha_retirada"),
        datos.get("fecha_firma_inicial"),
        datos.get("idtbl_tipos_de_vias"),
        datos.get("idtbl_calles"),
        datos.get("numero_portal"),
        datos.get("csv"),
        datos.get("csv_retirada"),
        datos.get("latitud"),
        datos.get("longitud"),
        datos.get("precision_gps"),
        datos.get("gps_nivel_calidad"),
        datos.get("gps_origen"),
        datos.get("idtbl_dimensiones"),
        datos.get("idtbl_gestores"),
        datos.get("observaciones"),
        datos.get("datos_extraidos_json"),
        0,
        None,
        None,
        None,
    )


def _params_update(datos: dict[str, Any], id_retirada: int) -> tuple:
    """
    Prepara parámetros para actualizar una retirada.

    Args:
        datos: Datos de retirada.
        id_retirada: ID del registro a actualizar.

    Returns:
        tuple: Parámetros SQL.
    """
    return (
        datos.get("nombre_pdf"),
        datos.get("ruta_pdf"),
        datos.get("nif"),
        datos.get("idtbl_proveedores"),
        datos.get("nombre_solicitante"),
        datos.get("telefono"),
        datos.get("numero_expediente"),
        datos.get("numero_solicitud"),
        datos.get("fecha_colocacion"),
        datos.get("fecha_retirada"),
        datos.get("fecha_firma_inicial"),
        datos.get("idtbl_tipos_de_vias"),
        datos.get("idtbl_calles"),
        datos.get("numero_portal"),
        datos.get("csv"),
        datos.get("csv_retirada"),
        datos.get("latitud"),
        datos.get("longitud"),
        datos.get("precision_gps"),
        datos.get("gps_nivel_calidad"),
        datos.get("gps_origen"),
        datos.get("idtbl_dimensiones"),
        datos.get("idtbl_gestores"),
        datos.get("observaciones"),
        datos.get("datos_extraidos_json"),
        0,
        None,
        None,
        None,
        id_retirada,
    )


# =============================================================================
# 💾 INSERCIÓN O ACTUALIZACIÓN DE RETIRADA
# =============================================================================

def _guardar_retirada_en_tabla(datos: dict[str, Any]) -> dict[str, Any]:
    """
    Inserta o actualiza una retirada en tbl_contenedores_retirada.

    Args:
        datos: Datos normalizados.

    Returns:
        dict: Resultado del guardado.
    """
    if not datos.get("nombre_pdf"):
        raise ValueError("No se puede guardar la retirada sin nombre_pdf.")

    existente = _obtener_retirada_existente(datos.get("nombre_pdf"))

    if existente:
        id_retirada = existente["idtbl_contenedores_retirada"]

        ejecutar_query(
            SQL_UPDATE_RETIRADA,
            _params_update(datos, id_retirada),
            nombre_bd="control_via_publica",
        )

        return {
            "accion": "actualizada",
            "idtbl_contenedores_retirada": id_retirada,
        }

    ejecutar_query(
        SQL_INSERT_RETIRADA,
        _params_insert(datos),
        nombre_bd="control_via_publica",
    )

    return {
        "accion": "insertada",
        "idtbl_contenedores_retirada": None,
    }


# =============================================================================
# 🔁 REDIRECCIÓN CONSERVANDO POSICIÓN
# =============================================================================

def _redirigir_a_vista_principal(pdf_pos: int):
    """
    Redirige a la vista principal conservando la posición del PDF.

    Args:
        pdf_pos: Posición actual del PDF.

    Returns:
        Response: Redirección Flask.
    """
    return redirect(
        url_for(
            "btn_contenedores_retiradas_sin_relacion_bp."
            "btn_contenedores_retiradas_sin_relacion",
            pdf_pos=pdf_pos,
        )
    )


# =============================================================================
# 📦 CARGA AUTOMÁTICA DE UN PDF EN tbl_contenedores_retirada
# =============================================================================

def _extraer_y_guardar_pdf(pdf_path: Path) -> dict[str, Any]:
    """
    Extrae datos de un PDF y los guarda en tbl_contenedores_retirada.

    Args:
        pdf_path: PDF a procesar.

    Returns:
        dict: Resultado del guardado.
    """
    datos = _construir_datos_retirada_desde_pdf(pdf_path)
    return _guardar_retirada_en_tabla(datos)


# =============================================================================
# 🧱 VISTA PRINCIPAL · RETIRADAS SIN RELACIÓN
# =============================================================================

@btn_contenedores_retiradas_sin_relacion_bp.route("/", methods=["GET", "POST"])
@login_required
def btn_contenedores_retiradas_sin_relacion():
    """
    Gestiona la pantalla principal de retiradas sin relación.

    Flujo:
        1. Lista PDFs en static/solo_retirada.
        2. Muestra el PDF actual.
        3. Si ya existe registro en tbl_contenedores_retirada, lo carga.
        4. Si no existe, intenta preparar datos extraídos del PDF.
        5. Permite guardar manualmente en tbl_contenedores_retirada.
    """
    pdf_info = _obtener_pdf_actual()
    accion = request.form.get("accion")

    pdf_actual = pdf_info["pdf_actual"]
    pdf_pos = pdf_info["pdf_pos"]

    if request.method == "POST" and accion == "guardar":
        datos = _leer_datos_formulario(pdf_actual)

        try:
            resultado = _guardar_retirada_en_tabla(datos)
            flash(
                f"Retirada {resultado['accion']} correctamente en tbl_contenedores_retirada.",
                "success",
            )
        except Exception as exc:
            flash(
                f"No se pudo guardar la retirada: {exc}",
                "danger",
            )

        return _redirigir_a_vista_principal(pdf_pos)

    if request.method == "POST" and accion == "extraer_guardar":
        if not pdf_actual:
            flash("No hay PDF actual para extraer y guardar.", "warning")
            return _redirigir_a_vista_principal(pdf_pos)

        try:
            resultado = _extraer_y_guardar_pdf(pdf_actual)
            flash(
                f"PDF extraído y retirada {resultado['accion']} correctamente.",
                "success",
            )
        except Exception as exc:
            flash(
                f"No se pudo extraer y guardar el PDF: {exc}",
                "danger",
            )

        return _redirigir_a_vista_principal(pdf_pos)

    retirada = None

    if pdf_actual:
        retirada = _obtener_retirada_existente(pdf_actual.name)

        if not retirada:
            retirada = _construir_datos_retirada_desde_pdf(pdf_actual)

    proveedores = _cargar_proveedores()
    calles = _cargar_calles()

    return render_template(
        "control_via_publica/contenedores/contenedores_retiradas_sin_relacion.html",
        pdfs=pdf_info["pdfs"],
        pdf_url=pdf_info["pdf_url"],
        pdf_pos=pdf_info["pdf_pos"],
        pdf_total=pdf_info["pdf_total"],
        pdf_actual=pdf_info["pdf_actual"],
        retirada=retirada,
        proveedores=proveedores,
        calles=calles,
    )


# =============================================================================
# 📦 RUTA · CARGAR PDF ACTUAL EN TABLA DE RETIRADAS
# =============================================================================

@btn_contenedores_retiradas_sin_relacion_bp.route("/cargar_actual", methods=["POST"])
@login_required
def btn_contenedores_retiradas_sin_relacion_cargar_actual():
    """
    Extrae y guarda únicamente el PDF actual en tbl_contenedores_retirada.

    Esta ruta no empareja. Solo carga datos de retirada.
    """
    pdf_info = _obtener_pdf_actual()
    pdf_actual = pdf_info["pdf_actual"]

    if not pdf_actual:
        flash("No hay PDF actual para cargar.", "warning")
        return _redirigir_a_vista_principal(pdf_info["pdf_pos"])

    try:
        resultado = _extraer_y_guardar_pdf(pdf_actual)
        flash(
            f"PDF actual cargado correctamente. Retirada {resultado['accion']}.",
            "success",
        )
    except Exception as exc:
        flash(
            f"No se pudo cargar el PDF actual: {exc}",
            "danger",
        )

    return _redirigir_a_vista_principal(pdf_info["pdf_pos"])


# =============================================================================
# 📦 RUTA · CARGAR TODOS LOS PDFS EN TABLA DE RETIRADAS
# =============================================================================

@btn_contenedores_retiradas_sin_relacion_bp.route("/cargar_todos", methods=["POST"])
@login_required
def btn_contenedores_retiradas_sin_relacion_cargar_todos():
    """
    Extrae y guarda todos los PDFs de static/solo_retirada.

    Esta ruta no empareja. Solo alimenta tbl_contenedores_retirada.
    """
    pdfs = _listar_pdfs_solo_retirada()

    total = len(pdfs)
    insertadas = 0
    actualizadas = 0
    errores = 0

    for pdf_path in pdfs:
        try:
            resultado = _extraer_y_guardar_pdf(pdf_path)

            if resultado["accion"] == "insertada":
                insertadas += 1
            else:
                actualizadas += 1

        except Exception:
            errores += 1

    flash(
        "Carga de retiradas finalizada. "
        f"PDFs encontrados={total}, "
        f"insertadas={insertadas}, "
        f"actualizadas={actualizadas}, "
        f"errores={errores}.",
        "info",
    )

    return _redirigir_a_vista_principal(0)