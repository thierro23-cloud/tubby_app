# =============================================================================
# 🧠 BACKEND INDUSTRIAL DE CONTENEDORES – MUNICIPIO ÁVILA
# =============================================================================
#
# tubby_app – Motor automático de procesamiento de PDFs administrativos
#
# (… cabecera original sin cambios …)
# =============================================================================

import logging
import re
from pathlib import Path
from typing import Optional
from datetime import datetime

import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from pypdf import PdfReader
from rapidfuzz import process, fuzz

from db import ejecutar_query, ejecutar_non_query

pytesseract.pytesseract.tesseract_cmd = r"C:\\Tesseract-OCR\\tesseract.exe"

logger = logging.getLogger(__name__)

MUNICIPIO_ID = 395
POPPLER_PATH = r"C:\\poppler\\Library\\bin"


# =============================================================================
# 2️⃣ EXTRACCIÓN DE DATOS DEL PDF
# =============================================================================


def extraer_numero_expediente(texto: str) -> Optional[str]:
    linea = " ".join(texto.split())
    m = re.search(r"(\d{1,4})\s*/\s*(\d{4})", linea)
    if not m:
        return None
    numero = int(m.group(1))
    anno = int(m.group(2))
    return f"{numero}/{anno}"


def extraer_csv(pdf_path: Path, texto: str) -> Optional[str]:
    try:
        reader = PdfReader(str(pdf_path))
        fields = reader.get_fields()
        if fields:
            for field in fields.values():
                firma = field.get("/V")
                if not firma:
                    continue

                valores = firma.values() if isinstance(firma, dict) else [firma]

                for valor in valores:
                    if isinstance(valor, str):
                        m = re.search(r"[A-Z0-9]{20,}", valor)
                        if m:
                            return m.group()
    except Exception:
        pass

    m = re.search(r"[A-Z0-9]{20,}", texto)
    if m:
        return m.group()

    return None


def extraer_fecha_firma(pdf_path: Path) -> Optional[str]:
    try:
        reader = PdfReader(str(pdf_path))
        fields = reader.get_fields()
        if not fields:
            return None

        for field in fields.values():
            firma = field.get("/V")
            if not firma:
                continue

            fecha_raw = firma.get("/M") if isinstance(firma, dict) else firma

            if fecha_raw:
                m = re.search(r"D:(\d{4})(\d{2})(\d{2})", fecha_raw)
                if m:
                    y, mo, d = m.groups()
                    return f"{y}-{mo}-{d}"
    except Exception:
        pass

    return None


def extraer_numero_solicitud(pdf_path: Path) -> Optional[str]:
    try:
        paginas = convert_from_path(
            str(pdf_path),
            dpi=300,
            poppler_path=POPPLER_PATH,
        )
        if not paginas:
            return None

        img = paginas[0]
        w, h = img.size
        header = img.crop((0, 0, w, int(h * 0.25)))

        config = "--psm 6 -c tessedit_char_whitelist=0123456789/ "
        texto = pytesseract.image_to_string(header, config=config)

        linea = " ".join(texto.split())
        m = re.search(r"(\d{1,4})\s*/\s*(\d{4})", linea)

        if m:
            numero = int(m.group(1))
            anno = int(m.group(2))
            return f"{numero}/{anno}"

    except Exception as e:
        logger.error(f"OCR ERROR numero_solicitud: {e!r}")

    return None


def extraer_nombre_solicitante(texto: str) -> Optional[str]:
    t = texto
    m = re.search(
        r"Nombre\s+solicitante\s*:\s*(.+)",
        t,
        flags=re.IGNORECASE,
    )
    if not m:
        return None

    linea = m.group(1).strip()
    linea = linea.splitlines()[0].strip()
    return linea or None


def extraer_nif_interesado(texto: str) -> Optional[str]:
    t = texto.upper()
    m = re.search(
        r"NIF\s+INTERESADO\s*:\s*([A-Z0-9\-\s]+)",
        t,
    )
    if not m:
        return None

    candidato = m.group(1).strip()
    patron_nif = r"(?:[0-9]{8}\s*-?\s*[A-Z]|[A-Z]\s*-?\s*[0-9]{8})"
    m2 = re.search(patron_nif, candidato)
    if not m2:
        return None

    nif = m2.group().replace("-", "").replace(" ", "")
    return nif


def extraer_telefono(texto: str) -> Optional[str]:
    t = texto.upper()
    m = re.search(
        r"M[ÓO]VIL\s*:\s*([0-9\s\-]+)",
        t,
    )
    if not m:
        return None

    candidato = m.group(1)
    numero = re.sub(r"[^0-9]", "", candidato)
    if len(numero) < 9:
        return None

    return numero[-9:]


def extraer_texto(pdf_path: Path) -> str:
    texto = ""
    with pdfplumber.open(str(pdf_path)) as pdf:
        for p in pdf.pages:
            texto += (p.extract_text() or "") + "\n"
    return texto


def es_retirada(texto: str) -> bool:
    return "retirada" in texto.lower()


def extraer_dimension_desde_texto(texto: str) -> Optional[str]:
    t = " ".join(texto.lower().split())

    if "hasta 5m3" in t:
        return "Hasta 5m3"
    if "de 5 hasta 8m3" in t or "de 5 a 8m3" in t:
        return "De 5 hasta 8m3"
    if "mas de 8m3" in t or "más de 8m3" in t:
        return "Más de 8m3"

    return None


def extraer_nif(texto: str) -> Optional[str]:
    t = texto.upper()
    patron_linea = r"NIF\s+REPRESENTADO\s*:\s*([A-Z0-9\-\s]+)"
    m = re.search(patron_linea, t)
    if not m:
        return None

    candidato = m.group(1).strip()
    patron_nif = r"(?:[0-9]{8}\s*-?\s*[A-Z]|[A-Z]\s*-?\s*[0-9]{8})"
    m2 = re.search(patron_nif, candidato)
    if not m2:
        return None

    nif = m2.group().replace("-", "").replace(" ", "")
    return nif


# =============================================================================
# 3️⃣ DIRECCIÓN Y FECHAS
# =============================================================================


def extraer_via_y_calle(texto: str) -> tuple[Optional[str], Optional[str]]:
    texto_mayus = texto.upper()

    marcador = "LUGAR DE UBICACIÓN:"
    idx = texto_mayus.find(marcador)
    if idx == -1:
        marcador_alt = "LUGAR DE UBICACION:"
        idx = texto_mayus.find(marcador_alt)
        if idx == -1:
            return None, None

    inicio_bloque = idx + len(marcador)
    bloque_crudo = texto_mayus[inicio_bloque : inicio_bloque + 200]

    bloque = bloque_crudo.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    bloque = " ".join(bloque.split())

    patron_c_barra = re.search(
        r"\bC/([A-ZÁÉÍÓÚÑ0-9\s]+)",
        bloque,
    )

    if patron_c_barra:
        tipo = "C/"
        nombre = patron_c_barra.group(1).strip()
    else:
        patron = re.search(
            r"\b("
            r"CALLE|C/|C\b|CL\b|"
            r"AVENIDA|AVDA\.?|AV\.?|"
            r"PLAZA|PZA\.?|PL\.?|"
            r"PASEO|PSO\.?|Pº|P°|"
            r"RONDA|RDA\.?|"
            r"CTRA\.?|CARRETERA|"
            r"CAMINO|CMNO\b|"
            r"TRAVESIA|TR\.?|TR\b|"
            r"PI\b|P\.I\."
            r")\s+([A-ZÁÉÍÓÚÑ0-9\s]+)",
            bloque,
        )

        if not patron:
            return None, None

        tipo = patron.group(1)
        nombre = patron.group(2).strip()

    cortadores = [
        "NUMERO_PORTAL",  # importante para cortar antes del portal
        "FECHA DE COLOCACIÓN",
        "FECHA DE COLOCACION",
        "FECHA COLOCACIÓN",
        "FECHA COLOCACION",
        "FECHA DE RETIRADA",
        "FECHA RETIRADA",
        "MUNICIPIO",
        "LOCALIDAD",
        "PROVINCIA",
        "CP",
        "CODIGO POSTAL",
        "CÓDIGO POSTAL",
        "Nº",
        "NUMERO",
        "NÚMERO",
    ]

    for stop in cortadores:
        idx_stop = nombre.find(stop)
        if idx_stop != -1:
            nombre = nombre[:idx_stop].strip()
            break

    EQUIVALENCIAS_TIPO_VIA = {
        "C": "CALLE",
        "C/": "CALLE",
        "CL": "CALLE",
        "CALLE": "CALLE",
        "AV": "AVENIDA",
        "AV.": "AVENIDA",
        "AVDA": "AVENIDA",
        "AVDA.": "AVENIDA",
        "AVENIDA": "AVENIDA",
        "PZA": "PLAZA",
        "PZA.": "PLAZA",
        "PLZA": "PLAZA",
        "PLZA.": "PLAZA",
        "PL": "PLAZA",
        "PL.": "PLAZA",
        "PLAZA": "PLAZA",
        "PASEO": "PASEO",
        "PSO": "PASEO",
        "PSO.": "PASEO",
        "Pº": "PASEO",
        "P°": "PASEO",
        "RDA": "RONDA",
        "RDA.": "RONDA",
        "RONDA": "RONDA",
        "CTRA": "CARRETERA",
        "CTRA.": "CARRETERA",
        "CARRETERA": "CARRETERA",
        "CMNO": "CAMINO",
        "CAMINO": "CAMINO",
        "TR": "TRAVESIA",
        "TR.": "TRAVESIA",
        "TRAVESIA": "TRAVESIA",
        "PI": "POLIGONO INDUSTRIAL",
        "P.I.": "POLIGONO INDUSTRIAL",
    }

    tipo_normalizado = EQUIVALENCIAS_TIPO_VIA.get(tipo, tipo)

    if not nombre:
        return None, None

    return tipo_normalizado, nombre


def extraer_numero_portal(texto: str) -> Optional[str]:
    """
    Busca 'numero_portal:' en el texto y devuelve el número (1–4 dígitos).
    Se asume que el formulario lo imprime explícitamente así.
    """
    t = texto.upper()
    m = re.search(r"NUMERO_PORTAL\s*:\s*([0-9]{1,4})", t)
    if not m:
        return None
    return m.group(1)


def extraer_fecha_colocacion(texto: str) -> Optional[str]:
    patron = re.compile(
        r"FECHA\s+DE\s+COLOCACI[ÓO]N:\s*([0-3]?\d/[0-1]?\d/\d{4})",
        re.IGNORECASE,
    )
    m = patron.search(texto)
    if not m:
        return None

    fecha_str = m.group(1)
    try:
        dt = datetime.strptime(fecha_str, "%d/%m/%Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None


def extraer_fecha_retirada(texto: str) -> Optional[str]:
    patron = re.compile(
        r"FECHA\s+DE\s+RETIRADA:\s*([0-3]?\d/[0-1]?\d/\d{4})",
        re.IGNORECASE,
    )
    m = patron.search(texto)
    if not m:
        return None

    fecha_str = m.group(1)

    try:
        dt = datetime.strptime(fecha_str, "%d/%m/%Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None


# =============================================================================
# 4️⃣ RESOLUCIÓN DE DATOS EN BD COMUNES
# =============================================================================


def obtener_proveedor(nif: Optional[str]) -> Optional[int]:
    if not nif:
        return None

    sql = "SELECT idtbl_proveedores FROM tbl_proveedores WHERE nif=%s"
    r = ejecutar_query(sql, (nif,), nombre_bd="bd_tbl_comunes")
    return r[0]["idtbl_proveedores"] if r else None


def obtener_dimension(desc: Optional[str]) -> Optional[int]:
    if not desc:
        return None

    sql = "SELECT idtbl_dimensiones FROM tbl_dimensiones WHERE descripcion=%s"
    r = ejecutar_query(sql, (desc,), nombre_bd="bd_tbl_comunes")
    return r[0]["idtbl_dimensiones"] if r else None


def normalizar_tipo_via(tipo: Optional[str]) -> Optional[str]:
    if not tipo:
        return None

    tipo = tipo.strip().upper()
    equivalencias = {
        "C": "CALLE",
        "CL": "CALLE",
        "C/": "CALLE",
        "CALLE": "CALLE",
        "AV": "AVENIDA",
        "AVDA": "AVENIDA",
        "AVENIDA": "AVENIDA",
        "PZA": "PLAZA",
        "PLAZA": "PLAZA",
        "PSO": "PASEO",
        "PASEO": "PASEO",
        "RDA": "RONDA",
        "RONDA": "RONDA",
    }
    return equivalencias.get(tipo, tipo)


def obtener_tipo_via(tipo_detectado: Optional[str]) -> Optional[int]:
    if not tipo_detectado:
        return None

    sql = """
    SELECT idtbl_tipos_de_vias, tipos_de_vias
    FROM tbl_tipos_de_vias
    """
    tipos = ejecutar_query(sql, (), nombre_bd="bd_tbl_comunes")
    if not tipos:
        return None

    nombres = [t["tipos_de_vias"].upper() for t in tipos]
    match = process.extractOne(
        tipo_detectado.upper(),
        nombres,
        scorer=fuzz.token_sort_ratio,
    )

    if match and match[1] >= 70:
        return tipos[match[2]]["idtbl_tipos_de_vias"]

    return None


def obtener_calle(nombre_calle: str, id_tipo_via: int) -> Optional[int]:
    sql = """
    SELECT idtbl_calles, calles
    FROM tbl_calles
    WHERE idtbl_municipios=%s
      AND idtbl_tipos_de_vias=%s
    """
    calles = ejecutar_query(
        sql,
        (MUNICIPIO_ID, id_tipo_via),
        nombre_bd="bd_tbl_comunes",
    )
    if not calles:
        return None

    nombres = [c["calles"].upper() for c in calles]
    match = process.extractOne(
        nombre_calle.upper(),
        nombres,
        scorer=fuzz.token_sort_ratio,
    )

    if match and match[1] >= 75:
        return calles[match[2]]["idtbl_calles"]

    return None


# =============================================================================
# 5️⃣ CONTROL DE DUPLICADOS (CSV)
# =============================================================================


def csv_existe(csv: Optional[str]) -> bool:
    if not csv:
        return False

    sql = """
    SELECT idtbl_control_contenedores
    FROM tbl_control_contenedores
    WHERE csv=%s OR csv_retirada=%s
    LIMIT 1
    """

    r = ejecutar_query(
        sql,
        (csv, csv),
        nombre_bd="control_via_publica",
    )

    return bool(r)


# =============================================================================
# 6️⃣ OPERACIONES BD (control_via_publica)
# =============================================================================


def insertar_colocacion(datos: dict) -> None:
    """
    Inserta un registro de COLOCACIÓN en tbl_control_contenedores.
    Campos cubiertos (ajusta al esquema real si difiere):
      - idtbl_proveedores
      - nombre_solicitante
      - nif
      - telefono
      - fecha_colocacion
      - fecha_firma_inicial
      - fecha_subida_instalacion (NOW)
      - idtbl_dimensiones
      - idtbl_tipos_de_vias
      - idtbl_calles
      - numero_portal
      - csv
      - numero_expediente
      - numero_colocacion (usando numero_solicitud)
      - numero_solicitud
      - anio_expediente
      - idtbl_gestor_subida
    """
    sql = """
    INSERT INTO tbl_control_contenedores
    (
        idtbl_proveedores,
        nombre_solicitante,
        nif,
        telefono,
        fecha_colocacion,
        fecha_firma_inicial,
        fecha_subida_instalacion,
        idtbl_dimensiones,
        idtbl_tipos_de_vias,
        idtbl_calles,
        numero_portal,
        csv,
        numero_expediente,
        numero_colocacion,
        numero_solicitud,
        anio_expediente,
        idtbl_gestor_subida
    )
    VALUES
    (
        %s, %s, %s, %s,
        %s, %s, NOW(),
        %s, %s, %s,
        %s, %s, %s,
        %s, %s, %s,
        %s
    )
    """

    ejecutar_non_query(
        sql,
        (
            datos.get("idtbl_proveedores"),
            datos.get("nombre_solicitante"),
            datos.get("nif"),
            datos.get("telefono"),
            datos.get("fecha_colocacion"),
            datos.get("fecha_firma_inicial"),
            datos.get("idtbl_dimensiones"),
            datos.get("idtbl_tipos_de_vias"),
            datos.get("idtbl_calles"),
            datos.get("numero_portal"),
            datos.get("csv"),
            datos.get("numero_expediente"),
            datos.get("numero_solicitud"),  # numero_colocacion
            datos.get("numero_solicitud"),
            datos.get("anio_solicitud"),
            datos.get("idtbl_gestor_subida"),
        ),
        nombre_bd="control_via_publica",
    )


def actualizar_retirada_en_control(
    id_colocacion: int,
    csv_retirada: str,
    numero_solicitud_crudo_retirada: Optional[str],
    fecha_colocacion: Optional[str],
    fecha_retirada: Optional[str],
) -> None:
    ejecutar_non_query(
        """
        UPDATE tbl_control_contenedores
        SET csv_retirada          = %s,
            n_solicitud_retirada  = %s,
            fecha_colocacion      = %s,
            fecha_retirada        = %s,
            fecha_subida_retirada = NOW()
        WHERE idtbl_control_contenedores = %s
        """,
        params=(
            csv_retirada,
            numero_solicitud_crudo_retirada,
            fecha_colocacion,
            fecha_retirada,
            id_colocacion,
        ),
        nombre_bd="control_via_publica",
    )


def encontrar_colocacion_para_retirada(
    numero_solicitud: Optional[str],
    anio_solicitud: Optional[str],
    numero_expediente: Optional[str],
) -> Optional[int]:
    if numero_solicitud and anio_solicitud:
        sql = """
        SELECT idtbl_control_contenedores
        FROM tbl_control_contenedores
        WHERE numero_solicitud = %s
          AND anio_expediente  = %s
          AND csv_retirada IS NULL
        LIMIT 1
        """
        r = ejecutar_query(
            sql,
            (numero_solicitud, anio_solicitud),
            nombre_bd="control_via_publica",
        )
        if r:
            return r[0]["idtbl_control_contenedores"]

    if numero_expediente:
        sql = """
        SELECT idtbl_control_contenedores
        FROM tbl_control_contenedores
        WHERE numero_expediente = %s
          AND csv_retirada IS NULL
        LIMIT 1
        """
        r = ejecutar_query(
            sql,
            (numero_expediente,),
            nombre_bd="control_via_publica",
        )
        if r:
            return r[0]["idtbl_control_contenedores"]

    return None


# =============================================================================
# 7️⃣ NORMALIZACIÓN Y VALIDACIÓN DE NEGOCIO
# =============================================================================


def _normalizar_solicitud_con_anio(
    valor: Optional[str],
) -> tuple[Optional[str], Optional[str]]:
    if not valor:
        return None, None

    texto = valor.strip()
    if not texto:
        return None, None

    if "/" in texto:
        num, anio = texto.split("/", 1)
        return num.strip() or None, anio.strip() or None

    if "-" in texto:
        num, anio = texto.split("-", 1)
        return num.strip() or None, anio.strip() or None

    return texto, None


def validar_datos_contenedor(
    es_retirada: bool,
    csv: Optional[str],
    numero_solicitud: Optional[str],
    numero_expediente: Optional[str],
    fecha_colocacion: Optional[str],
) -> tuple[str, Optional[str]]:
    if es_retirada:
        if not numero_expediente:
            return "pendiente_validacion", "Falta número de expediente en retirada"
        return "auto_guardado", None

    if not csv:
        return "pendiente_validacion", "Falta CSV en colocación"

    if not numero_solicitud:
        return "pendiente_validacion", "Falta número de solicitud en colocación"

    if not fecha_colocacion:
        return "pendiente_validacion", "Falta FECHA DE COLOCACIÓN en colocación"

    return "auto_guardado", None


# =============================================================================
# 8️⃣ PROCESADOR PRINCIPAL: procesar_pdf_core
# =============================================================================


def procesar_pdf_core(pdf_path, id_gestor_subida: Optional[int] = None):
    """
    Procesa un PDF de contenedores (colocación o retirada) y devuelve:
      {
        "estado": "auto_guardado" | "pendiente_validacion" | "solo_retirada",
        "motivo": str | None,
        "datos": dict_con_datos_extraidos
      }
    """
    pdf_path = Path(pdf_path)

    csv = None
    numero_solicitud = None
    numero_expediente = None
    fecha_firma = None
    fecha_colocacion = None
    fecha_retirada = None
    retirada = False
    nif = None
    idtbl_proveedores = None
    dimension_desc = None
    idtbl_dimensiones = None
    tipo_via = None
    nombre_calle = None
    id_tipo_via = None
    idtbl_calles = None
    nombre_solicitante = None
    nif_interesado = None
    telefono = None
    numero_portal = None

    numero_solicitud_crudo = None
    numero_solicitud_num = None
    anio_solicitud = None

    try:
        texto = extraer_texto(pdf_path)

        csv = extraer_csv(pdf_path, texto)

        numero_solicitud = extraer_numero_solicitud(pdf_path)

        numero_solicitud_crudo = numero_solicitud
        numero_solicitud_num, anio_solicitud = _normalizar_solicitud_con_anio(
            numero_solicitud_crudo
        )

        nombre_solicitante = extraer_nombre_solicitante(texto)
        nif_interesado = extraer_nif_interesado(texto)
        telefono = extraer_telefono(texto)

        fecha_firma = extraer_fecha_firma(pdf_path)
        fecha_colocacion = extraer_fecha_colocacion(texto)
        retirada = es_retirada(texto)
        fecha_retirada = extraer_fecha_retirada(texto) if retirada else None

        logger.info(f"Fecha firma inicial: {fecha_firma}")
        logger.info(f"Fecha colocacion: {fecha_colocacion}")
        logger.info(f"Fecha retirada: {fecha_retirada}")

        if retirada:
            numero_expediente = extraer_numero_expediente(texto)
        else:
            numero_expediente = None

        nif = extraer_nif(texto) or nif_interesado

        idtbl_proveedores = obtener_proveedor(nif)

        dimension_desc = extraer_dimension_desde_texto(texto)
        idtbl_dimensiones = obtener_dimension(dimension_desc)

        tipo_via, nombre_calle = extraer_via_y_calle(texto)
        tipo_via = normalizar_tipo_via(tipo_via)
        id_tipo_via = obtener_tipo_via(tipo_via) if tipo_via else None

        if nombre_calle and id_tipo_via:
            idtbl_calles = obtener_calle(nombre_calle, id_tipo_via)

        numero_portal = extraer_numero_portal(texto)

        datos = {
            "csv": csv,
            "numero_expediente": numero_expediente,
            "numero_solicitud_crudo": numero_solicitud_crudo,
            "numero_solicitud": numero_solicitud_num,
            "anio_solicitud": anio_solicitud,
            "fecha_firma_inicial": fecha_firma,
            "fecha_colocacion": fecha_colocacion,
            "fecha_retirada": fecha_retirada,
            "ruta_pdf": str(pdf_path),
            "idtbl_proveedores": idtbl_proveedores,
            "idtbl_dimensiones": idtbl_dimensiones,
            "idtbl_calles": idtbl_calles,
            "idtbl_tipos_de_vias": id_tipo_via,
            "es_retirada": retirada,
            "nombre_solicitante": nombre_solicitante,
            "nif": nif_interesado or nif,
            "telefono": telefono,
            "numero_portal": numero_portal,
            "idtbl_gestor_subida": id_gestor_subida,
        }

        logger.info("--------------- DATOS EXTRAIDOS ---------------")
        logger.info(f"CSV: {csv}")
        logger.info(f"Expediente: {numero_expediente}")
        logger.info(f"Solicitud (crudo): {numero_solicitud_crudo}")
        logger.info(f"Solicitud (numero): {numero_solicitud_num}")
        logger.info(f"Año solicitud: {anio_solicitud}")
        logger.info(f"Fecha firma inicial: {fecha_firma}")
        logger.info(f"Fecha colocacion: {fecha_colocacion}")
        logger.info(f"Fecha retirada: {fecha_retirada}")
        logger.info(f"Nombre solicitante: {nombre_solicitante}")
        logger.info(f"NIF interesado: {nif_interesado}")
        logger.info(f"Telefono: {telefono}")
        logger.info(f"NIF usado proveedor: {nif}")
        logger.info(f"Proveedor id: {idtbl_proveedores}")
        logger.info(f"Dimension texto: {dimension_desc}")
        logger.info(f"Dimension id: {idtbl_dimensiones}")
        logger.info(f"Tipo via detectado: {tipo_via}")
        logger.info(f"Tipo via id: {id_tipo_via}")
        logger.info(f"Nombre calle detectado: {nombre_calle}")
        logger.info(f"Calle id: {idtbl_calles}")
        logger.info(f"Numero portal detectado: {numero_portal}")
        logger.info(f"Retirada: {retirada}")
        logger.info(f"Gestor subida: {id_gestor_subida}")
        logger.info("-----------------------------------------------")

        logger.info(
            "VALIDAR >> retirada=%s csv=%r num_sol=%r num_exp=%r fecha_col=%r",
            retirada,
            csv,
            numero_solicitud_num,
            numero_expediente,
            fecha_colocacion,
        )

        estado, motivo = validar_datos_contenedor(
            es_retirada=retirada,
            csv=csv,
            numero_solicitud=numero_solicitud_num,
            numero_expediente=numero_expediente,
            fecha_colocacion=fecha_colocacion,
        )

        logger.info("VALIDAR >> resultado estado=%s motivo=%r", estado, motivo)

        if estado == "pendiente_validacion":
            return {
                "estado": estado,
                "motivo": motivo,
                "datos": datos,
            }

        if retirada:
            id_colocacion = encontrar_colocacion_para_retirada(
                numero_solicitud=numero_solicitud_num,
                anio_solicitud=anio_solicitud,
                numero_expediente=numero_expediente,
            )

            if not id_colocacion:
                logger.warning(
                    "Retirada sin colocacion asociada (num_sol=%r, anio=%r, num_exp=%r, csv=%r)",
                    numero_solicitud_num,
                    anio_solicitud,
                    numero_expediente,
                    csv,
                )
                return {
                    "estado": "solo_retirada",
                    "motivo": "Retirada sin colocación asociada (por solicitud/año ni expediente)",
                    "datos": datos,
                }

            actualizar_retirada_en_control(
                id_colocacion=id_colocacion,
                csv_retirada=csv,
                numero_solicitud_crudo_retirada=numero_solicitud_crudo,
                fecha_colocacion=fecha_colocacion,
                fecha_retirada=fecha_retirada,
            )

            return {
                "estado": "auto_guardado",
                "motivo": None,
                "datos": datos,
            }

        else:
            insertar_colocacion(datos)
            return {
                "estado": "auto_guardado",
                "motivo": None,
                "datos": datos,
            }

    except Exception as e:
        logger.error(f"[CORE-ERROR] {e!r}")

        datos_error = {
            "csv": csv,
            "numero_expediente": numero_expediente,
            "numero_solicitud_crudo": numero_solicitud_crudo,
            "numero_solicitud": numero_solicitud_num,
            "anio_solicitud": anio_solicitud,
            "fecha_firma_inicial": fecha_firma,
            "fecha_colocacion": fecha_colocacion,
            "fecha_retirada": fecha_retirada,
            "ruta_pdf": str(pdf_path),
            "idtbl_proveedores": idtbl_proveedores,
            "idtbl_dimensiones": idtbl_dimensiones,
            "idtbl_calles": idtbl_calles,
            "idtbl_tipos_de_vias": id_tipo_via,
            "es_retirada": retirada,
            "nombre_solicitante": nombre_solicitante,
            "nif": nif_interesado or nif,
            "telefono": telefono,
            "numero_portal": numero_portal,
            "idtbl_gestor_subida": id_gestor_subida,
        }

        return {
            "estado": "pendiente_validacion",
            "motivo": "Error interno procesando PDF",
            "datos": datos_error,
        }


# =============================================================================
# 9️⃣ WRAPPER PARA WATCHER (ASYNC)
# =============================================================================

import concurrent.futures

executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)


def procesar_pdf_async(
    app, pdf_path, destino_db=None, id_gestor_subida: Optional[int] = None
):
    """
    Wrapper asíncrono legacy para procesar un PDF de contenedores usando
    procesar_pdf_core dentro de un hilo.
    """

    def tarea():
        with app.app_context():
            return procesar_pdf_core(pdf_path, id_gestor_subida=id_gestor_subida)

    future = executor.submit(tarea)
    return future.result()
