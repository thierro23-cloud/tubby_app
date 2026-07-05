# =============================================================================
# 🔘 BOTÓN · UBICACIÓN · CALLES GEOLOCALIZACIÓN
# Archivo: blueprints/comunes/btn_ubicacion_calles_geolocalizacion_bp.py
# =============================================================================
"""
Objetivo
--------
Este blueprint implementa el botón:

    btn_ubicacion_calles_geolocalizacion_bp.btn_ubicacion_calles_geolocalizacion

que se cuelga del módulo:

    modulo_comunes_ubicacion_bp (panel: panel_comunes_bp)

y sirve para:

  1. Mostrar una página donde el super_admin puede subir un CSV de calles.
     - Formato CSV: idtbl_calles, tipo_via, nombre_calle, via_mas_calle.
  2. Para cada fila del CSV:
     - Construir una dirección textual (via_mas_calle + municipio + país).
     - Llamar a la API de geocodificación de Geoapify.
     - Obtener latitud, longitud y nivel de confianza.
  3. Insertar/actualizar la tabla de cache:

        tbl_calles_geocoding_cache
        ------------------------------------------
        idtbl_calles
        idtbl_tipos_de_vias
        idtbl_municipios
        direccion_texto
        latitud
        longitud
        fuente
        precision_nivel
        fecha_ultima_actualizacion

  4. Devolver un resumen al super_admin:
     - Filas leídas.
     - Calles geocodificadas correctamente.
     - Calles sin coordenadas.
     - Filas con error.

Notas importantes
-----------------
- La función está pensada para ejecutar la geocodificación de calles
  (sin número de portal): un centro aproximado por calle.
- Para evitar problemas de codificación, se asume que el CSV viene
  de Excel/Windows y se lee como cp1252 con errors="replace".
- Las llamadas a Geoapify usan timeout y captura de errores para evitar
  colgados eternos de la petición.

Requisitos previos
------------------
- Tener creada la tabla tbl_calles_geocoding_cache en la BD
  bd_tbl_comunes (o la que corresponda).
- Definir GEOAPIFY_API_KEY con tu clave real de Geoapify.
- Ajustar get_conn_bd_tbl_comunes() a tu configuración de MySQL.
- Tener registrada la plantilla:
    templates/comunes/ubicacion_calles_geolocalizacion.html
  con el formulario que llama a este endpoint.

"""

# =============================================================================
# 1️⃣ IMPORTS
# =============================================================================

from flask import Blueprint, render_template, request
from services.helpers import login_required, rol_required

import csv
import io
import logging
from datetime import datetime
import time

import requests
import mysql.connector


# =============================================================================
# 2️⃣ CONFIGURACIÓN BÁSICA
# =============================================================================

# Logger de módulo (usa la config de logging global de tu app)
log = logging.getLogger(__name__)

# Clave de Geoapify: cámbiala por la tuya real y/o lee de config/entorno
GEOAPIFY_API_KEY = "1879e8295d4f4f5ba1e456fdebcf88b4"

# Contexto de municipio para construir la dirección textual
MUNICIPIO_NOMBRE = "Ávila"
PAIS_NOMBRE = "España"
ID_MUNICIPIO = 395  # idtbl_municipios correspondiente a Ávila

# Duración máxima de cada petición a Geoapify (segundos)
GEOAPIFY_TIMEOUT = 5

# Pausa entre peticiones para no saturar el rate limit (segundos)
GEOAPIFY_SLEEP = 0.2


def get_conn_bd_tbl_comunes():
    """
    Devuelve una conexión a la BD bd_tbl_comunes.

    Ajusta host, user, password y database a tu entorno real.
    Idealmente, si ya tienes un helper central en services/db.py,
    reutilízalo aquí para mantener un solo punto de configuración.
    """
    return mysql.connector.connect(
        host="localhost",
        port=3306,
        user="root",               # 👈 cambia esto a tu usuario real
        password="F@Fe1132",    # 👈 cambia esto a tu password real
        database="bd_tbl_comunes", # 👈 o el nombre real de la BD
    )


# =============================================================================
# 3️⃣ FUNCIÓN AUXILIAR · LLAMADA A GEOAPIFY
# =============================================================================

def geocode_geoapify(direccion: str):
    """
    Llama a la API de geocodificación directa de Geoapify para una dirección.

    Parámetros
    ----------
    direccion : str
        Cadena con la dirección completa, por ejemplo:
        "Avenida DERECHOS HUMANOS DE LOS, Ávila, España"

    Devuelve
    --------
    (latitud, longitud, confidence) o (None, None, None) en caso de error.

    Manejo de errores
    -----------------
    - Cualquier error de red, timeout o respuesta inválida se captura y
      devuelve (None, None, None).
    - Si el API no encuentra ninguna feature, también devolvemos None.
    """
    url = "https://api.geoapify.com/v1/geocode/search"
    params = {
        "apiKey": GEOAPIFY_API_KEY,
        "text": direccion,
        "format": "json",
    }

    try:
        resp = requests.get(url, params=params, timeout=GEOAPIFY_TIMEOUT)
        resp.raise_for_status()
    except requests.Timeout:
        log.warning("⏱️ [Geoapify] Timeout geocodificando: %s", direccion)
        return None, None, None
    except requests.RequestException as exc:
        log.warning("⚠️ [Geoapify] Error de red (%s) para: %s", exc, direccion)
        return None, None, None

    try:
        data = resp.json()
    except ValueError:
        log.warning("⚠️ [Geoapify] Respuesta no es JSON para: %s", direccion)
        return None, None, None

    features = data.get("features") or []
    if not features:
        # Sin resultados
        return None, None, None

    feat = features[0]
    try:
        lon, lat = feat["geometry"]["coordinates"]
    except Exception:
        log.warning("⚠️ [Geoapify] Sin coordenadas en feature para: %s", direccion)
        return None, None, None

    rank = feat.get("properties", {}).get("rank", {})
    confidence = rank.get("confidence")

    return lat, lon, confidence


# =============================================================================
# 4️⃣ BLUEPRINT DEL BOTÓN
# =============================================================================

btn_ubicacion_calles_geolocalizacion_bp = Blueprint(
    "btn_ubicacion_calles_geolocalizacion_bp",
    __name__,
    # Se cuelga bajo /comunes/ubicacion/calles_geolocalizacion/
    url_prefix="/comunes/ubicacion/calles_geolocalizacion",
)


# =============================================================================
# 5️⃣ VISTA PRINCIPAL · SUBIR CSV + GEOLOCALIZAR
# =============================================================================

@btn_ubicacion_calles_geolocalizacion_bp.route("/", methods=["GET", "POST"])
@login_required
@rol_required("super_admin")
def btn_ubicacion_calles_geolocalizacion():
    """
    Endpoint: btn_ubicacion_calles_geolocalizacion
    URL     : /comunes/ubicacion/calles_geolocalizacion/

    GET
    ---
    - Muestra la plantilla:
        templates/comunes/ubicacion_calles_geolocalizacion.html
      con un formulario para subir un CSV de calles.

    POST
    ----
    - Recibe un archivo CSV en `archivo_csv`.
    - Lee el CSV (codificación cp1252).
    - Para cada fila:
        - Construye la dirección textual.
        - Llama a Geoapify para obtener lat/long.
        - Inserta/actualiza tbl_calles_geocoding_cache.
    - Devuelve la misma plantilla con un resumen del proceso.

    Formato esperado del CSV
    ------------------------
    idtbl_calles,tipo_via,nombre_calle,via_mas_calle

    Ejemplo de fila:
    -----------------
    27,Avenida,"DERECHOS HUMANOS DE LOS","Avenida DERECHOS HUMANOS DE LOS"
    """
    error = None
    info = None
    resumen = None

    # -------------------------------------------------------------------------
    # 5.1. PETICIÓN GET → sólo mostrar el formulario
    # -------------------------------------------------------------------------
    if request.method == "GET":
        return render_template(
            "comunes/ubicacion_calles_geolocalizacion.html",
            error=error,
            info=info,
            resumen=resumen,
        )

    # -------------------------------------------------------------------------
    # 5.2. PETICIÓN POST → procesar CSV
    # -------------------------------------------------------------------------
    # En este punto, request.method == "POST"
    log.info("📥 [calles_geo] POST recibido, procesando CSV subido...")

    f = request.files.get("archivo_csv")
    if not f:
        error = "No se ha enviado ningún archivo CSV."
        return render_template(
            "comunes/ubicacion_calles_geolocalizacion.html",
            error=error,
            info=info,
            resumen=resumen,
        )

    try:
        # ---------------------------------------------------------------------
        # 5.2.1. Lectura del CSV con codificación Windows (cp1252)
        # ---------------------------------------------------------------------
        # Asumimos que el CSV viene de Excel en Windows, por lo que suele
        # estar guardado como cp1252. Usamos errors="replace" para evitar
        # que caracteres raros detengan el proceso.
        log.info("📄 [calles_geo] Abriendo CSV con cp1252...")
        stream = io.TextIOWrapper(
            f.stream,
            encoding="cp1252",
            newline="",
            errors="replace",
        )
        reader = csv.DictReader(stream)

        # ---------------------------------------------------------------------
        # 5.2.2. Conexión a la BD
        # ---------------------------------------------------------------------
        log.info("🗃 [calles_geo] Conectando a bd_tbl_comunes...")
        conn = get_conn_bd_tbl_comunes()
        cur = conn.cursor()

        # Sentencia de inserción/actualización en cache
        sql = """
        INSERT INTO tbl_calles_geocoding_cache (
            idtbl_calles,
            idtbl_tipos_de_vias,
            idtbl_municipios,
            direccion_texto,
            latitud,
            longitud,
            fuente,
            precision_nivel,
            fecha_ultima_actualizacion
        ) VALUES (
            %(idtbl_calles)s,
            %(idtbl_tipos_de_vias)s,
            %(idtbl_municipios)s,
            %(direccion_texto)s,
            %(latitud)s,
            %(longitud)s,
            %(fuente)s,
            %(precision_nivel)s,
            %(fecha_ultima_actualizacion)s
        )
        ON DUPLICATE KEY UPDATE
            idtbl_tipos_de_vias        = VALUES(idtbl_tipos_de_vias),
            idtbl_municipios           = VALUES(idtbl_municipios),
            direccion_texto            = VALUES(direccion_texto),
            latitud                    = VALUES(latitud),
            longitud                   = VALUES(longitud),
            fuente                     = VALUES(fuente),
            precision_nivel            = VALUES(precision_nivel),
            fecha_ultima_actualizacion = VALUES(fecha_ultima_actualizacion)
        """

        # Contadores para el resumen
        filas_leidas = 0
        geocodificadas_ok = 0
        sin_coordenadas = 0
        errores = 0
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                        # ---------------------------------------------------------------------
        # 5.2.3. Bucle principal: leer CSV y geocodificar
        # ---------------------------------------------------------------------
        log.info("🚀 [calles_geo] Inicio de procesado de filas del CSV...")

        PROVINCIA = "Ávila"

        # Límite de filas mientras pruebas (None para procesar todas)
        MAX_FILAS_DEBUG = 50  # pon None cuando ya esté todo afinado

        for row in reader:
            filas_leidas += 1

            # Si estás en modo debug y quieres limitar filas, activa esto:
            if MAX_FILAS_DEBUG is not None and filas_leidas > MAX_FILAS_DEBUG:
                log.info("🛑 [calles_geo] Alcanzado límite de debug: %s filas", MAX_FILAS_DEBUG)
                break

            # Log de progreso cada N filas
            if filas_leidas % 50 == 0:
                log.info("🔁 [calles_geo] Procesadas %s filas...", filas_leidas)

            # -------------------------
            # 1) idtbl_calles
            # -------------------------
            try:
                idtbl_calles = int(row["idtbl_calles"])
            except Exception:
                errores += 1
                continue

            # -------------------------
            # 2) vía y nombre
            # -------------------------
            via_mas_calle = (row.get("via_mas_calle") or "").strip()
            if not via_mas_calle:
                # No hay texto de dirección aprovechable
                sin_coordenadas += 1
                continue

            # Dirección completa: "<via_mas_calle>, Ávila, Ávila, España"
            direccion = f"{via_mas_calle}, {MUNICIPIO_NOMBRE}, {PROVINCIA}, {PAIS_NOMBRE}"

            # -------------------------
            # 3) Llamada a Geoapify
            #    (si quieres probar sin llamar al API, comenta este bloque y
            #     usa las coordenadas falsas que hay más abajo)
            # -------------------------
            lat, lon, conf = geocode_geoapify(direccion)

            if filas_leidas <= 5:
                log.info("🧪 [calles_geo] Dirección: %s", direccion)
                log.info("🧪 [calles_geo] Resultado Geoapify: lat=%s lon=%s conf=%s", lat, lon, conf)

            # Pequeña pausa para no saturar el API
            time.sleep(GEOAPIFY_SLEEP)

            if lat is None or lon is None:
                # Sin resultado de geocodificación (incluye timeouts)
                sin_coordenadas += 1
                log.info("ℹ️ [calles_geo] Sin resultados para: %s", direccion)
                continue

            # ⚠️ Si quieres probar sin Geoapify, comenta el bloque anterior
            #     y descomenta esto:
            #
            # lat, lon, conf = 40.656, -4.700, 1.0

            # -------------------------
            # 4) Insert/Update en cache
            # -------------------------
            data = {
                "idtbl_calles": idtbl_calles,
                "idtbl_tipos_de_vias": None,            # se puede rellenar después
                "idtbl_municipios": ID_MUNICIPIO,
                "direccion_texto": direccion,
                "latitud": float(lat),
                "longitud": float(lon),
                "fuente": "geoapify",
                "precision_nivel": float(conf) if conf is not None else None,
                "fecha_ultima_actualizacion": now,
            }
            cur.execute(sql, data)
            geocodificadas_ok += 1

        # ---------------------------------------------------------------------
        # 5.2.4. Commit y cierre de conexión
        # ---------------------------------------------------------------------
        conn.commit()
        cur.close()
        conn.close()

        # Mensaje final de info y resumen
        info = "Proceso de geolocalización finalizado."
        resumen = {
            "filas_leidas": filas_leidas,
            "geocodificadas_ok": geocodificadas_ok,
            "sin_coordenadas": sin_coordenadas,
            "errores": errores,
        }

        log.info(
            "✅ [calles_geo] Fin de proceso: %s filas, %s ok, %s sin coords, %s errores",
            filas_leidas,
            geocodificadas_ok,
            sin_coordenadas,
            errores,
        )

    except Exception as exc:
        # Cualquier excepción no prevista aterriza aquí
        error = f"Error al procesar el CSV o geocodificar: {exc}"
        log.exception("❌ [calles_geo] Error inesperado en geolocalización de calles")

    # -------------------------------------------------------------------------
    # 5.3. Render de la plantilla con mensajes/resumen
    # -------------------------------------------------------------------------
    return render_template(
        "comunes/ubicacion_calles_geolocalizacion.html",
        error=error,
        info=info,
        resumen=resumen,
    )