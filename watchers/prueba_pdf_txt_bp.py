# =============================================================================
# 📄 prueba_pdf_txt_bp.py
# =============================================================================
# BACKEND DE PRUEBA PARA EXTRACCIÓN MASIVA DE TEXTO DE PDFs
# =============================================================================
# 🎯 OBJETIVOS:
#   1️⃣ Recorrer una carpeta con PDFs.
#   2️⃣ Extraer el máximo texto posible de cada PDF:
#        - Primero texto "nativo" (seleccionable) con PyMuPDF.
#        - Si una página no tiene casi texto, se convierte a imagen
#          y se le aplica OCR con Tesseract.
#   3️⃣ Generar un archivo .txt en la MISMA carpeta:
#        - Separador de campos: ';'
#        - Nombre: "<AÑO>_prueba_extraccion_<número_consecutivo>.txt"
#          Ejemplo: 2026_prueba_extraccion_001.txt
#
# 🧪 USO PRINCIPAL:
#   - Herramienta de pruebas para comprobar la calidad de extracción
#     (texto nativo + OCR) antes de integrar la lógica en watchers
#     o en flujos de negocio reales.
#
# 🏭 PASO A SERVIDOR:
#   - El módulo no depende de Flask ni de rutas específicas del proyecto.
#   - Funciona igual en local y en servidor si la carpeta de PDFs existe.
#   - Al integrarlo en la app, se puede:
#       · Llamar a procesar_carpeta_pdfs(...) desde un blueprint.
#       · O reutilizar extraer_texto_con_ocr(...) dentro de la lógica
#         de negocio (por ejemplo, procesar_pdf_contenedor).
# =============================================================================

from __future__ import annotations

import io
import os
import datetime
from pathlib import Path
from typing import Dict, Any, List

import fitz              # PyMuPDF
from PIL import Image
import pytesseract       # OCR Tesseract
# PyMuPDF y pytesseract se usan para extraer texto y aplicar OCR.[web:144][web:149]


# =============================================================================
# 1️⃣ EXTRACCIÓN DE TEXTO CON PyMuPDF + OCR
# =============================================================================
# 1.1) extraer_texto_con_ocr(pdf_path, idioma_ocr) (COMIENZA)
# -----------------------------------------------------------------------------
# Esta función:
#   - Abre un PDF con PyMuPDF.
#   - Recorre todas las páginas.
#   - Para cada página:
#       · Intenta extraer texto nativo: page.get_text("text").
#       · Si el texto es escaso, renderiza la página a imagen (dpi=300)
#         y aplica OCR con Tesseract en el idioma indicado (por defecto "spa").
#   - Devuelve:
#       · "paginas": lista de diccionarios con:
#             { "n": índice de página, "texto": ..., "via": "text"|"ocr" }
#       · "texto_completo": concatenación de todo el texto con saltos dobles.
#
# UMBRALES:
#   - UMBRAL_VACIA_NATIVO:
#       · Si el texto nativo tiene menos caracteres que este umbral, se
#         intenta OCR.
#   - UMBRAL_VACIA_FINAL:
#       · Si incluso tras OCR la longitud es inferior a este valor, la
#         página se descarta (se considera "vacía").
# -----------------------------------------------------------------------------
def extraer_texto_con_ocr(pdf_path: str | Path,
                          idioma_ocr: str = "spa") -> Dict[str, Any]:
    pdf_path = Path(pdf_path)
    doc = fitz.open(pdf_path)

    paginas: List[Dict[str, Any]] = []
    texto_full: List[str] = []

    # Umbrales de decisión
    UMBRAL_VACIA_NATIVO = 30
    UMBRAL_VACIA_FINAL = 10

    for i in range(len(doc)):
        page = doc.load_page(i)

        # 1) Intentar texto nativo
        texto = page.get_text("text") or ""
        texto = texto.strip()

        if len(texto) >= UMBRAL_VACIA_NATIVO:
            paginas.append({"n": i, "texto": texto, "via": "text"})
            texto_full.append(texto)
            continue

        # 2) Si texto nativo escaso, renderizar página a imagen y aplicar OCR
        pix = page.get_pixmap(dpi=300)
        img_bytes = pix.tobytes("png")
        imagen = Image.open(io.BytesIO(img_bytes))

        ocr_texto = pytesseract.image_to_string(imagen, lang=idioma_ocr)
        ocr_texto = (ocr_texto or "").strip()

        if len(ocr_texto) < UMBRAL_VACIA_FINAL:
            # Ni texto nativo ni OCR aportan suficiente contenido → se ignora
            continue

        paginas.append({"n": i, "texto": ocr_texto, "via": "ocr"})
        texto_full.append(ocr_texto)

    doc.close()

    return {
        "paginas": paginas,
        "texto_completo": "\n\n".join(texto_full),
    }
# 1.1) extraer_texto_con_ocr(pdf_path, idioma_ocr) (TERMINA)
# -----------------------------------------------------------------------------


# =============================================================================
# 2️⃣ GENERADOR DE NOMBRE DE ARCHIVO DE SALIDA
# =============================================================================
# 2.1) siguiente_nombre_salida(carpeta) (COMIENZA)
# -----------------------------------------------------------------------------
# Genera el siguiente nombre disponible del tipo:
#
#   "<AÑO>_prueba_extraccion_<número_consecutivo>.txt"
#
# Ejemplo:
#   - Si estamos en 2026 y ya existen:
#       · 2026_prueba_extraccion_001.txt
#       · 2026_prueba_extraccion_002.txt
#     el siguiente será:
#       · 2026_prueba_extraccion_003.txt
#
# LÓGICA:
#   - Busca todos los .txt con ese patrón en la carpeta.
#   - Extrae el número final y calcula el máximo.
#   - Devuelve el siguiente número +1 con relleno de 3 dígitos.
# -----------------------------------------------------------------------------
def siguiente_nombre_salida(carpeta: Path) -> Path:
    year = datetime.datetime.now().year
    patron = f"{year}_prueba_extraccion_"

    existentes = list(carpeta.glob(f"{year}_prueba_extraccion_*.txt"))

    max_n = 0
    for f in existentes:
        try:
            base = f.stem
            sufijo = base.replace(patron, "")
            n = int(sufijo)
            if n > max_n:
                max_n = n
        except ValueError:
            # Ignorar archivos que no sigan exactamente el patrón esperado
            continue

    siguiente = max_n + 1
    nombre = f"{year}_prueba_extraccion_{siguiente:03d}.txt"
    return carpeta / nombre
# 2.1) siguiente_nombre_salida(carpeta) (TERMINA)
# -----------------------------------------------------------------------------


# =============================================================================
# 3️⃣ PROCESAR CARPETA DE PDFs Y GENERAR TXT
# =============================================================================
# 3.1) procesar_carpeta_pdfs(carpeta_pdfs) (COMIENZA)
# -----------------------------------------------------------------------------
# Esta función:
#   - Recibe una ruta de carpeta (string o Path) donde hay PDFs.
#   - Crea la carpeta si no existe.
#   - Calcula el siguiente nombre de archivo TXT de salida.
#   - Recorre todos los PDFs de la carpeta (ordenados por nombre).
#   - Para cada PDF:
#       · Extrae texto completo con extraer_texto_con_ocr().
#       · Limpia saltos de línea (\n, \r) y espacios múltiples.
#       · Calcula el número de caracteres.
#       · Genera una línea:
#             "<nombre_pdf>;<ruta_absoluta>;<n_chars>;<texto_normalizado>"
#   - Escribe todas las líneas en el TXT de salida, una por línea.
#   - Devuelve la ruta del TXT generado.
#
# NOTA:
#   - Es una utilidad de pruebas; en producción, podrías reutilizar
#     extraer_texto_con_ocr(...) dentro de tu lógica de negocio para
#     alimentar tablas de BD o procesos de validación.
# -----------------------------------------------------------------------------
def procesar_carpeta_pdfs(carpeta_pdfs: str | Path) -> Path:
    carpeta = Path(carpeta_pdfs)
    carpeta.mkdir(parents=True, exist_ok=True)

    # Determinar nombre de archivo de salida
    salida = siguiente_nombre_salida(carpeta)
    lineas: List[str] = []

    # Recorrer PDFs ordenados por nombre
    for pdf in sorted(carpeta.glob("*.pdf")):
        resultado = extraer_texto_con_ocr(pdf)
        texto = resultado["texto_completo"]

        # Normalizar saltos de línea y espacios
        texto = texto.replace("\n", " ").replace("\r", " ")
        texto = " ".join(texto.split())

        n_chars = len(texto)
        linea = f"{pdf.name};{pdf.resolve()};{n_chars};{texto}"
        lineas.append(linea)

    # Escribir el TXT en la misma carpeta
    with salida.open("w", encoding="utf-8", newline="\n") as f:
        for linea in lineas:
            f.write(linea + "\n")

    return salida
# 3.1) procesar_carpeta_pdfs(carpeta_pdfs) (TERMINA)
# -----------------------------------------------------------------------------


# =============================================================================
# 4️⃣ EJECUCIÓN DIRECTA · MODO SCRIPT
# =============================================================================
# 4.1) Punto de entrada para pruebas locales (COMIENZA)
# -----------------------------------------------------------------------------
# Si ejecutas este archivo directamente:
#
#   python prueba_pdf_txt_bp.py
#
# hará lo siguiente:
#   - Usará la carpeta:
#         C:/Users/<usuario>/Desktop/tubby_app/watchers/pruebas_pdf
#   - Procesará todos los PDFs que haya allí.
#   - Generará un TXT con el nombre:
#         <AÑO>_prueba_extraccion_XXX.txt
#     en esa misma carpeta.
#
# En servidor:
#   - Puedes adaptar la ruta de carpeta_pdfs a la ubicación de pruebas
#     que uses allí, o llamar a procesar_carpeta_pdfs desde un blueprint.
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    usuario = os.getlogin()
    carpeta_pdfs = Path(
        f"C:/Users/{usuario}/Desktop/tubby_app/watchers/pruebas_pdf"
    )
    ruta_txt = procesar_carpeta_pdfs(carpeta_pdfs)
    print(f"TXT generado: {ruta_txt}")
# 4.1) Punto de entrada para pruebas locales (TERMINA)
# -----------------------------------------------------------------------------


# =============================================================================
# 5️⃣ FIN · prueba_pdf_txt_bp.py
# =============================================================================