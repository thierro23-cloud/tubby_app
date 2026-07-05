# ============================================================
# BLUEPRINT: Resolver calles desde Excel con búsqueda fuzzy
# Archivo:  blueprints/comunes/btn_ubicacion_resolver_bp.py
# Ruta base:  /comunes/calles
# Endpoint:   /comunes/calles/resolver_texto
#
# Flujo:
#   - Subes un Excel con una columna CALLE (CALLE/Calle/calle).
#   - Para cada fila, se busca la mejor coincidencia en tbl_calles
#     del municipio 395, usando:
#        * normalización (acentos, mayúsculas, tipo de vía en el texto)
#        * fuzzy matching (Levenshtein / rapidfuzz)
#        * umbral de similitud 0.75
#   - Devuelve texto copiable:
#        CALLE;idtbl_calles;idtbl_tipos_de_vias;score
# ============================================================

from flask import Blueprint, render_template, request, jsonify
from db import ejecutar_query
from services.helpers import login_required, rol_required
import pandas as pd
import unicodedata

# ------------------------------------------------------------
# 1. Intento de importar motores de fuzzy matching
# ------------------------------------------------------------

try:
    # Opción recomendada: rapidfuzz (rápido y moderno)
    from rapidfuzz import fuzz
    USE_RAPIDFUZZ = True
except ImportError:
    try:
        # Alternativa: python-Levenshtein
        from Levenshtein import ratio as levenshtein_ratio
        USE_RAPIDFUZZ = False
    except ImportError:
        # Último recurso: sin fuzzy real, solo igualdad exacta
        USE_RAPIDFUZZ = None

# ------------------------------------------------------------
# 2. Blueprint (NOMBRE ÚNICO: btn_ubicacion_resolver_bp)
# ------------------------------------------------------------

btn_ubicacion_resolver_bp = Blueprint(
    "btn_ubicacion_resolver_bp",
    __name__,
    url_prefix="/comunes/calles",
)

# ------------------------------------------------------------
# 3. Tipos de vía conocidos para normalizar el texto (no la BD)
# ------------------------------------------------------------

TIPOS_VIA_CONOCIDOS = [
    "CALLE", "CL", "C/", "C.",
    "AVENIDA", "AVDA", "AVD", "AV.", "AV",
    "CARRETERA", "CTRA", "CRTA", "CTRA.",
    "PLAZA", "PL", "PZA",
    "RONDA", "PASEO", "PSO",
    "TRAVESIA", "TRV",
    "CAMINO", "CMNO", "CAM.",
    "GLORIETA", "GTA",
    # añade aquí todos los que uses en tu base
]

# ------------------------------------------------------------
# 4. Funciones de normalización de texto
# ------------------------------------------------------------

def quitar_acentos(texto):
    """
    Quita acentos/diacríticos de un texto.
    Ejemplo: FERNÁNDEZ -> FERNANDEZ
    """
    if not texto:
        return ""
    texto = str(texto)
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def normalizar_calle(texto):
    """
    Normaliza un nombre de calle para comparación:

      - Quita acentos.
      - Convierte a mayúsculas.
      - Sustituye separadores (coma, punto, guión, punto y coma) por espacios.
      - Colapsa espacios múltiples.
      - Elimina tipos de vía conocidos al inicio (CALLE, AVDA, CTRA, etc.).

    Devuelve:
      Cadena 'limpia' para usar en fuzzy matching.
    """
    if not texto:
        return ""

    # 1) Quitar acentos
    t = quitar_acentos(texto)

    # 2) Mayúsculas
    t = t.upper()

    # 3) Sustituir separadores por espacio
    for ch in [",", ";", ".", "-"]:
        t = t.replace(ch, " ")

    # 4) Colapsar espacios
    t = " ".join(t.split())

    # 5) Separar en palabras
    partes = t.split()
    if not partes:
        return ""

    # 6) Si la primera palabra es un tipo de vía, la quitamos
    if partes[0] in TIPOS_VIA_CONOCIDOS:
        partes = partes[1:]

    return " ".join(partes)


# ------------------------------------------------------------
# 5. Búsqueda fuzzy en BD (incluye idtbl_tipos_de_vias)
# ------------------------------------------------------------

def buscar_ubicacion_por_nombre(nombre_calle, id_municipio=395, umbral_similitud=0.75):
    """
    Busca la mejor coincidencia de 'nombre_calle' en tbl_calles
    para un municipio concreto usando coincidencia borrosa.

    Pasos:
      1. Normalizar el texto de entrada (acentos, tipo de vía en el texto, espacios).
      2. Obtener candidatos en BD del municipio usando LIKE con la primera
         palabra normalizada.
      3. Normalizar cada candidato.
      4. Calcular la similitud fuzzy entre entrada y candidato.
      5. Devolver la fila con mayor similitud si >= umbral_similitud.

    Parámetros:
      nombre_calle (str): texto de la calle recibido del Excel.
      id_municipio (int): ID de municipio (por defecto 395).
      umbral_similitud (float): similitud mínima [0,1] para aceptar.

    Retorna:
      dict con la fila elegida (incluye idtbl_calles, calles,
      idtbl_tipos_de_vias, __score__) o None si no hay match suficiente.
    """
    nombre_original = (nombre_calle or "").strip()
    if not nombre_original:
        return None

    # Normalizamos el texto de entrada
    nombre_norm = normalizar_calle(nombre_original)
    if not nombre_norm:
        return None

    # Primera palabra normalizada para acotar búsqueda con LIKE
    primera_palabra = nombre_norm.split()[0]

    # Traemos candidatos del municipio donde 'calles' contenga esa palabra
    sql = """
        SELECT idtbl_calles, calles, idtbl_tipos_de_vias
        FROM tbl_calles
        WHERE idtbl_municipios = %s
          AND UPPER(calles) LIKE %s
    """
    params = (
        id_municipio,
        f"%{primera_palabra}%",
    )
    candidatos = ejecutar_query(sql, params=params, nombre_bd="bd_tbl_comunes")

    if not candidatos:
        return None

    mejor_fila = None
    mejor_score = 0.0

    for fila in candidatos:
        nombre_bd = fila["calles"]
        nombre_bd_norm = normalizar_calle(nombre_bd)

        if not nombre_bd_norm:
            continue

        # Calculamos similitud según el motor disponible
        if USE_RAPIDFUZZ is True:
            # rapidfuzz.fuzz.ratio devuelve 0-100, lo escalamos a 0-1
            score = fuzz.ratio(nombre_norm, nombre_bd_norm) / 100.0
        elif USE_RAPIDFUZZ is False:
            # python-Levenshtein.ratio devuelve 0-1 directamente
            score = levenshtein_ratio(nombre_norm, nombre_bd_norm)
        else:
            # Fallback sin libs externas: coincidencia exacta
            score = 1.0 if nombre_norm == nombre_bd_norm else 0.0

        if score > mejor_score:
            mejor_score = score
            mejor_fila = fila

    # Comprobamos si el mejor score supera el umbral
    if mejor_fila and mejor_score >= umbral_similitud:
        mejor_fila["__score__"] = mejor_score
        return mejor_fila

    return None


# ------------------------------------------------------------
# 6. Vista principal: subir Excel y devolver texto
# ------------------------------------------------------------

@btn_ubicacion_resolver_bp.route("/resolver_texto", methods=["GET", "POST"])
@login_required
@rol_required("su")
def btn_ubicacion_resolver_texto():
    """
    Vista para resolver un listado de calles desde un Excel.

    GET:
      - Muestra la plantilla 'comunes/calles/resolver_calles_texto.html'
        con un formulario para subir un archivo Excel/CSV.

    POST:
      - Recibe un archivo desde el campo 'archivo'.
      - Lo lee con pandas.read_excel().
      - Localiza una columna llamada CALLE (CALLE/Calle/calle).
      - Para cada fila:
          * Toma el valor de la columna CALLE.
          * Busca en tbl_calles del municipio 395 usando fuzzy matching.
          * Si encuentra un match con score >= 0.75:
              - Usa ese idtbl_calles e idtbl_tipos_de_vias.
          * Si no, deja id y score en blanco.
      - Construye un texto con el formato:
            CALLE;idtbl_calles;idtbl_tipos_de_vias;score
        donde 'score' es la similitud (0-1) con 2 decimales.
      - Renderiza de nuevo la plantilla con 'resultado_texto' para copiar/pegar.
    """
    # 6.1. GET: solo formulario
    if request.method == "GET":
        return render_template("comunes/calles/resolver_calles_texto.html")

    # 6.2. POST: procesar archivo
    archivo = request.files.get("archivo")
    if not archivo:
        return jsonify({"ok": False, "msg": "No has enviado ningún archivo"}), 400

    # Intentamos leer como Excel (xls, xlsx...)
    try:
        df = pd.read_excel(archivo)
    except Exception as e:
        return jsonify({"ok": False, "msg": f"No se ha podido leer el Excel: {e}"}), 400

    # 6.3. Detectar columna CALLE en el Excel
    posibles_nombres = ["CALLE", "Calle", "calle"]
    nombre_columna_calle = None
    for col in df.columns:
        if str(col) in posibles_nombres:
            nombre_columna_calle = col
            break

    if not nombre_columna_calle:
        return jsonify({
            "ok": False,
            "msg": "No se ha encontrado ninguna columna llamada CALLE (CALLE/Calle/calle) en el Excel",
        }), 400

    # 6.4. Preparar cabecera de salida
    lineas_salida = ["CALLE;idtbl_calles;idtbl_tipos_de_vias;score"]

    # 6.5. Recorrer filas del Excel y resolver cada calle
    for _, fila in df.iterrows():
        nombre_calle = str(fila.get(nombre_columna_calle, "")).strip()
        if not nombre_calle:
            continue

        id_calle = ""
        id_tipo_via = ""
        score = ""

        match = buscar_ubicacion_por_nombre(
            nombre_calle,
            id_municipio=395,
            umbral_similitud=0.75,
        )
        if match:
            id_calle = str(match["idtbl_calles"])
            id_tipo_via = str(match.get("idtbl_tipos_de_vias", "") or "")
            score_valor = match.get("__score__", 0)
            score = f"{score_valor:.2f}"

        # Añadimos la línea con todos los datos
        lineas_salida.append(f"{nombre_calle};{id_calle};{id_tipo_via};{score}")

    # 6.6. Unir todas las líneas en un bloque de texto
    texto = "\n".join(lineas_salida)

    # 6.7. Renderizar plantilla con el resultado
    return render_template(
        "comunes/calles/resolver_calles_texto.html",
        resultado_texto=texto,
    )