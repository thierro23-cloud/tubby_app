# =============================================================================
# 🧠 BOTÓN OBRAS · EXTRACCIÓN AUTOMÁTICA DE CSV DESDE PDF
# =============================================================================
# 🔍 INTRODUCCIÓN GENERAL
# -----------------------------------------------------------------------------
# Este botón:
#
#   btn_obras_extract_pdf
#
# cuelga del módulo de OBRAS y se encarga de:
#
#   ✔ Gestionar una pantalla donde se listan los PDF ya procesados
#   ✔ Permitir subir nuevos PDF de obras desde el navegador
#   ✔ Extraer automáticamente el CSV (Código Seguro de Verificación) del PDF
#   ✔ Evitar duplicados por CSV en la base de datos
#   ✔ Guardar la información extraída en la tabla tbl_obras_pdf
#
# Para encontrar el CSV, combina varias estrategias:
#
#   1) Buscar en METADATOS del PDF
#   2) Buscar en el TEXTO completo del PDF
#   3) Buscar en la ZONA INFERIOR de cada página
#   4) Usar OCR (pytesseract) si es necesario
#
# El botón expone:
#
#   - Una vista principal (GET) para ver los registros procesados
#   - Un endpoint (POST) para subir PDFs y procesarlos por AJAX
#
# Convención:
#   - Módulo padre (ejemplo): modulo_obras_gestion
#   - Botón:                  btn_obras_extract_pdf
#
# En este ejemplo, definimos un blueprint propio para el botón:
#   extractor_pdf_obras_bp  → con vista principal y endpoint de subida
#   y renombramos la vista raíz como: btn_obras_extract_pdf
# =============================================================================


# =============================================================================
# 1️⃣ IMPORTACIONES · DEPENDENCIAS DEL BOTÓN
# =============================================================================
# Aquí declaramos todas las librerías externas y utilidades que usa el botón:
#   - os, re, json      → manejo de ficheros, expresiones regulares y JSON
#   - pdfplumber       → lectura estructurada de PDFs
#   - pytesseract      → OCR (reconocimiento óptico de caracteres)
#   - Flask            → Blueprint, plantillas, peticiones, respuestas JSON
#   - ejecutar_query   → acceso a base de datos
# =============================================================================

import os
import re
import json
import pdfplumber
import pytesseract

from flask import Blueprint, render_template, request, jsonify

from db import ejecutar_query

# =============================================================================
# 2️⃣ BLUEPRINT DEL BOTÓN · extractor_pdf_obras_bp
# =============================================================================
# Este blueprint agrupa:
#
#   - La vista principal del botón   → btn_obras_extract_pdf (GET "/")
#   - El endpoint de subida de PDF   → subir_pdf (POST "/subir")
#
# URL base:
#   /obras/pdf
#
# Ejemplos:
#   - Pantalla principal:
#       GET  /obras/pdf/
#   - Subida de PDF por AJAX:
#       POST /obras/pdf/subir
# =============================================================================

extractor_pdf_obras_bp = Blueprint(
    "extractor_pdf_obras_bp",
    __name__,
    url_prefix="/obras/pdf",
)


# =============================================================================
# 3️⃣ REGEX CSV · PATRÓN PARA DETECTAR EL CÓDIGO SEGURO DE VERIFICACIÓN
# =============================================================================
# REGEX_CSV:
#   - Busca patrones relacionados con CSV:
#       "CSV", "C.S.V.", "Código Seguro de Verificación", "Verificación", etc.
#   - Extrae una cadena alfanumérica de entre 10 y 40 caracteres aprox.
#   - Permite espacios y guiones dentro de ese rango.
#
# Se usa sobre:
#   - Texto del PDF
#   - Metadatos
#   - Zonas específicas
#   - Resultado de OCR
# =============================================================================

REGEX_CSV = re.compile(
    r"(?:CSV|C\\.?S\\.?V\\.?|Código\\s*Seguro\\s*de\\s*Verificación|Verificación)"
    r"[^\\n]{0,80}([A-Z0-9][A-Z0-9\\-\\s]{10,40})",
    re.IGNORECASE,
)


# =============================================================================
# 4️⃣ FUNCIONES AUXILIARES · LIMPIEZA Y VALIDACIÓN DE CSV
# =============================================================================
# 4.1) limpiar_csv(csv)
#     - Elimina espacios, guiones y saltos de línea
#     - Devuelve el CSV "compacto"
#
# 4.2) csv_valido(csv)
#     - Comprueba que la longitud está entre 12 y 40
#     - Verifica que solo contiene caracteres alfanuméricos
# =============================================================================


def limpiar_csv(csv):
    if not csv:
        return None

    csv = csv.replace(" ", "")
    csv = csv.replace("-", "")
    csv = csv.replace("\\n", "")

    return csv.strip()


def csv_valido(csv):
    if not csv:
        return False

    return 12 <= len(csv) <= 40 and csv.isalnum()


# =============================================================================
# 5️⃣ BUSCAR CSV EN TEXTO PLANO
# =============================================================================
# buscar_csv(texto):
#   - Intenta localizar un CSV dentro de un texto dado usando REGEX_CSV
#   - Si encuentra un candidato, lo limpia y devuelve
#   - Si no, devuelve None
# =============================================================================


def buscar_csv(texto):
    if not texto:
        return None

    resultado = REGEX_CSV.search(texto)

    if resultado:
        return limpiar_csv(resultado.group(1))

    return None


# =============================================================================
# 6️⃣ EXTRAER TEXTO COMPLETO DEL PDF
# =============================================================================
# extraer_texto_pdf(pdf):
#   - Recorre todas las páginas del PDF
#   - Usa pdfplumber para extraer texto de cada página
#   - Concatena el texto en un único string
# =============================================================================


def extraer_texto_pdf(pdf):
    texto = ""

    for pagina in pdf.pages:
        contenido = pagina.extract_text()

        if contenido:
            texto += contenido + "\\n"

    return texto


# =============================================================================
# 7️⃣ BUSCAR CSV EN METADATOS DEL PDF
# =============================================================================
# buscar_csv_metadatos(pdf):
#   - Inspecciona los metadatos del PDF
#   - Si algún campo es texto, intenta localizar un CSV con buscar_csv()
# =============================================================================


def buscar_csv_metadatos(pdf):
    meta = pdf.metadata

    if not meta:
        return None

    for valor in meta.values():
        if isinstance(valor, str):
            csv = buscar_csv(valor)

            if csv:
                return csv

    return None


# =============================================================================
# 8️⃣ BUSCAR CSV EN LA ZONA INFERIOR DE LAS PÁGINAS
# =============================================================================
# buscar_csv_zona_inferior(pdf):
#   - Para cada página:
#       - Calcula un rectángulo en la zona inferior
#       - Extrae el texto de esa región
#       - Busca un CSV en ese texto
#
#   - Si lo encuentra, lo devuelve; si no, None
# =============================================================================


def buscar_csv_zona_inferior(pdf):
    for pagina in pdf.pages:
        ancho = pagina.width
        alto = pagina.height

        zona = (
            ancho * 0.20,
            alto * 0.80,
            ancho * 0.75,
            alto * 0.95,
        )

        region = pagina.crop(zona)

        texto = region.extract_text()

        csv = buscar_csv(texto)

        if csv:
            return csv

    return None


# =============================================================================
# 9️⃣ OCR · BÚSQUEDA DE CSV CON RECONOCIMIENTO ÓPTICO
# =============================================================================
# buscar_csv_ocr(pdf):
#   - Convierte cada página del PDF en imagen
#   - Aplica OCR con pytesseract
#   - Busca un CSV en el texto reconocido
# =============================================================================


def buscar_csv_ocr(pdf):
    for pagina in pdf.pages:
        imagen = pagina.to_image(resolution=300)

        img = imagen.original

        texto = pytesseract.image_to_string(img)

        csv = buscar_csv(texto)

        if csv:
            return csv

    return None


# =============================================================================
# 🔟 FUNCIÓN PRINCIPAL DE EXTRACCIÓN · procesar_pdf(ruta_pdf)
# =============================================================================
# Esta función coordina todas las estrategias:
#
#   1) Metadatos
#   2) Texto completo
#   3) Zona inferior
#   4) OCR
#
# En cuanto encuentra un CSV válido, lo devuelve.
# Si ninguna estrategia tiene éxito, devuelve None.
# =============================================================================


def procesar_pdf(ruta_pdf):
    with pdfplumber.open(ruta_pdf) as pdf:

        # 1) metadatos
        csv = buscar_csv_metadatos(pdf)

        if csv_valido(csv):
            return csv

        # 2) texto completo
        texto = extraer_texto_pdf(pdf)

        csv = buscar_csv(texto)

        if csv_valido(csv):
            return csv

        # 3) zona inferior
        csv = buscar_csv_zona_inferior(pdf)

        if csv_valido(csv):
            return csv

        # 4) OCR
        csv = buscar_csv_ocr(pdf)

        if csv_valido(csv):
            return csv

    return None


# =============================================================================
# 1️⃣1️⃣ PANTALLA PRINCIPAL DEL BOTÓN · btn_obras_extract_pdf
# =============================================================================
# GET /obras/pdf/
#
# - Muestra los últimos 100 PDF procesados desde la tabla tbl_obras_pdf
# - Sirve como UI principal para el botón "Extracción PDF Obras"
# =============================================================================


@extractor_pdf_obras_bp.route("/", methods=["GET"])
def btn_obras_extract_pdf():

    registros = ejecutar_query(
        """
        SELECT
            id,
            nombre_pdf,
            csv,
            fecha_creacion
        FROM tbl_obras_pdf
        ORDER BY id DESC
        LIMIT 100
        """,
        fetchall=True,
    )

    return render_template(
        "extractor_pdf_obras.html",
        registros=registros,
    )


# =============================================================================
# 1️⃣2️⃣ ENDPOINT DE SUBIDA · PROCESAR PDF Y EXTRAER CSV
# =============================================================================
# POST /obras/pdf/subir
#
# Flujo:
#   1) Recibe un archivo PDF desde el formulario (input name="pdf")
#   2) Lo guarda en la carpeta contenedores/entrada_pdf
#   3) Llama a procesar_pdf(ruta_pdf) para extraer el CSV
#   4) Si no hay CSV → responde con error JSON
#   5) Si el CSV ya existe en tbl_obras_pdf → responde "duplicado"
#   6) Si es nuevo:
#         - Inserta registro en tbl_obras_pdf
#         - Devuelve JSON con estado "ok" y el CSV encontrado
# =============================================================================


@extractor_pdf_obras_bp.route("/subir", methods=["POST"])
def subir_pdf():

    archivo = request.files.get("pdf")

    if not archivo:
        return jsonify(
            {
                "estado": "error",
                "mensaje": "No se recibió archivo",
            }
        )

    carpeta = "contenedores/entrada_pdf"
    os.makedirs(carpeta, exist_ok=True)

    ruta_pdf = os.path.join(carpeta, archivo.filename)

    archivo.save(ruta_pdf)

    # -------------------------------------------------------------
    # EXTRAER CSV
    # -------------------------------------------------------------
    csv = procesar_pdf(ruta_pdf)

    if not csv:
        return jsonify(
            {
                "estado": "error",
                "mensaje": "No se pudo detectar CSV",
            }
        )

    # -------------------------------------------------------------
    # EVITAR DUPLICADOS
    # -------------------------------------------------------------
    existe = ejecutar_query(
        """
        SELECT id
        FROM tbl_obras_pdf
        WHERE csv = %s
        """,
        (csv,),
        fetchone=True,
    )

    if existe:
        return jsonify(
            {
                "estado": "duplicado",
                "csv": csv,
            }
        )

    # -------------------------------------------------------------
    # GUARDAR JSON
    # -------------------------------------------------------------
    datos = {
        "csv": csv,
        "nombre_pdf": archivo.filename,
    }

    ejecutar_query(
        """
        INSERT INTO tbl_obras_pdf
        (
            nombre_pdf,
            csv,
            datos_extraidos_json,
            fecha_creacion
        )
        VALUES
        (
            %s,
            %s,
            %s,
            NOW()
        )
        """,
        (
            archivo.filename,
            csv,
            json.dumps(datos),
        ),
    )

    return jsonify(
        {
            "estado": "ok",
            "csv": csv,
        }
    )


# =============================================================================
# ✅ FIN BOTÓN OBRAS · EXTRACCIÓN AUTOMÁTICA DE CSV DESDE PDF
# =============================================================================
