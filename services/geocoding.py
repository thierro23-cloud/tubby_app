# =============================================================================
# 🌍 SERVICIO DE GEOLOCALIZACIÓN · RESOLVER LAT/LONG PARA CALLES Y PORTALES
# =============================================================================
#  OBJETIVO GLOBAL
#  ---------------
#  Centralizar TODA la lógica relacionada con geolocalización de direcciones
#  (calle + portal) para que pueda usarse desde cualquier módulo del proyecto:
#      · Control de contenedores
#      · Obras
#      · Inventario
#      · Otros módulos futuros
#
#  Este servicio se apoya en una TABLA DE CACHÉ en la BBDD:
#
#      bd_tbl_comunes.tbl_calles_portales_geo
#
#  y en los metadatos de calles y tipos de vía:
#
#      bd_tbl_comunes.tbl_calles
#      bd_tbl_comunes.tbl_tipos_de_vias
#
#  REGLAS DE NEGOCIO PRINCIPALES
#  -----------------------------
#  1) SI HAY COORDENADAS EN EL PDF:
#       - Se consideran la fuente más fiable.
#       - Se usan directamente para el registro (contenedor, obra, etc.).
#       - Si no existe fila en tbl_calles_portales_geo para esa
#         combinación (calle + portal), se inserta con fuente = 'PDF'
#         para enriquecer la caché.
#
#  2) SI NO HAY COORDENADAS EN EL PDF:
#       2.1) Se busca primero en tbl_calles_portales_geo:
#             - Si hay fila para (calle + portal) → se usan esas coords.
#       2.2) Si NO hay fila en caché:
#             - Se construye una dirección en texto legible:
#                  "{tipo_via} {calle} {portal}, {municipio}, {pais}"
#               (portal por defecto = 1 si viene vacío).
#             - Se llama al servicio externo Geocode.xyz para obtener
#               latitud/longitud aproximadas.
#             - Si Geocode.xyz devuelve coordenadas:
#                  · Se inserta la nueva fila en tbl_calles_portales_geo
#                    con fuente = 'geocode_xyz'.
#                  · Se devuelven esas coords para el registro.
#             - Si Geocode.xyz NO devuelve resultado:
#                  · Se devuelve (None, None) y la lógica de negocio decide
#                    qué hacer (guardar sin GPS, mostrar error, etc.).
#
#  3) REUTILIZACIÓN Y ESCALABILIDAD
#       - Todos los módulos llaman a la MISMA función pública:
#
#             resolver_lat_long(...)
#
#         Esto permite:
#           · Cambiar de proveedor (de Geocode.xyz a otro) en un único punto.
#           · Ajustar la estrategia de caché sin tocar los blueprints.
#           · Asegurar que contenedores, obras e inventario comparten
#             exactamente la misma lógica de geolocalización.
#
#  4) RESPONSABILIDAD DE ESTE MÓDULO
#       - Resolver coordenadas a partir de:
#           · idtbl_calles
#           · numero_portal
#           · latitud/longitud opcionales de PDF
#       - Gestionar la tabla de caché (consultar e insertar/actualizar).
#       - Llamar al servicio externo Geocode.xyz cuando sea necesario.
#
#  5) RESPONSABILIDAD DEL CÓDIGO QUE LO LLAMA
#       - Abrir la conexión a la BBDD (MySQLConnection).
#       - Hacer COMMIT o ROLLBACK cuando proceda.
#       - Decidir qué hacer si la función devuelve (None, None).
#       - Manejar mensajes al usuario en caso de fallo de geocodificación.
#
#  USO TÍPICO EN UN BLUEPRINT
#  --------------------------
#      from services.geocoding import resolver_lat_long
#
#      latitud, longitud = resolver_lat_long(
#          conn=conn,
#          idtbl_calles=int(id_calle) if id_calle else None,
#          numero_portal=request.form.get("numero_portal"),
#          lat_pdf=request.form.get("latitud_pdf"),
#          lon_pdf=request.form.get("longitud_pdf"),
#          municipio="Avila",
#          pais="España",
#      )
#
#      # Usar latitud/longitud en el INSERT/UPDATE de contenedores, obras, etc.
#
# =============================================================================

from __future__ import annotations

# =============================================================================
# 1️⃣ IMPORTS Y CONFIGURACIÓN BÁSICA
# =============================================================================
#  - logging     → para registrar avisos y errores de geocodificación.
#  - typing      → tipos opcionales y tuplas.
#  - requests    → llamadas HTTP a Geocode.xyz.
#  - MySQL       → tipos de conexión y cursor dict para trabajar con la BBDD.
# =============================================================================

import logging
from typing import Optional, Tuple

import requests
from mysql.connector.connection import MySQLConnection
from mysql.connector.cursor import MySQLCursorDict

logger = logging.getLogger(__name__)


# =============================================================================
# 2️⃣ HELPERS PRIVADOS · ACCESO A TABLAS COMUNES
# =============================================================================
#  2.1) _get_calle_y_tipo()
#       - Dado un idtbl_calles, devuelve (tipo_via, nombre_calle).
#       - Usa bd_tbl_comunes.tbl_calles y bd_tbl_comunes.tbl_tipos_de_vias.
#
#  2.2) _buscar_en_cache()
#       - Consulta bd_tbl_comunes.tbl_calles_portales_geo para ver
#         si ya hay coordenadas para (calle + portal).
#
#  2.3) _insertar_en_cache()
#       - Inserta o actualiza una fila en tbl_calles_portales_geo con
#         las coordenadas calculadas (fuente = 'PDF' o 'geocode_xyz').
# =============================================================================


def _get_calle_y_tipo(
    conn: MySQLConnection,
    idtbl_calles: int,
) -> Optional[Tuple[str, str]]:
    """
    Devuelve (tipo_via, nombre_calle) a partir de idtbl_calles.

    - type_via  → CL, AV, PZ, etc.
    - nombre_calle → texto de la calle, sin el tipo.
    """
    sql = """
        SELECT
            tv.tipos_de_vias AS tipo_via,
            c.calles          AS nombre_calle
        FROM bd_tbl_comunes.tbl_calles AS c
        LEFT JOIN bd_tbl_comunes.tbl_tipos_de_vias AS tv
            ON tv.idtbl_tipos_de_vias = c.idtbl_tipos_de_vias
        WHERE c.idtbl_calles = %s
        LIMIT 1
    """
    cur: MySQLCursorDict = conn.cursor(dictionary=True)
    cur.execute(sql, (idtbl_calles,))
    row = cur.fetchone()
    cur.close()
    if not row:
        return None

    tipo_via = (row.get("tipo_via") or "").strip()
    nombre_calle = (row.get("nombre_calle") or "").strip()

    if not nombre_calle:
        return None

    return tipo_via, nombre_calle


def _buscar_en_cache(
    conn: MySQLConnection,
    idtbl_calles: int,
    numero_portal: Optional[int],
) -> Optional[Tuple[float, float]]:
    """
    Busca coordenadas en bd_tbl_comunes.tbl_calles_portales_geo.

    - Si numero_portal es None o vacío, se asume portal = 1.
    - Si existe fila exacta (calle + portal), devuelve (latitud, longitud).
    - Si no existe, devuelve None.
    """
    numero = numero_portal if numero_portal not in (None, "") else 1

    sql = """
        SELECT latitud, longitud
        FROM bd_tbl_comunes.tbl_calles_portales_geo
        WHERE idtbl_calles = %s
          AND numero_portal = %s
        LIMIT 1
    """
    cur: MySQLCursorDict = conn.cursor(dictionary=True)
    cur.execute(sql, (idtbl_calles, numero))
    row = cur.fetchone()
    cur.close()

    if not row:
        return None

    return float(row["latitud"]), float(row["longitud"])


def _insertar_en_cache(
    conn: MySQLConnection,
    idtbl_calles: int,
    numero_portal: Optional[int],
    latitud: float,
    longitud: float,
    fuente: str,
) -> None:
    """
    Inserta o actualiza una fila en tbl_calles_portales_geo.

    - Si ya existe fila para (calle + portal), actualiza coordenadas y fuente.
    - Si no existe, la inserta.
    - El COMMIT lo hace la lógica de negocio superior, no esta función.
    """
    numero = numero_portal if numero_portal not in (None, "") else 1

    sql = """
        INSERT INTO bd_tbl_comunes.tbl_calles_portales_geo (
            idtbl_calles,
            numero_portal,
            latitud,
            longitud,
            fuente
        )
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            latitud  = VALUES(latitud),
            longitud = VALUES(longitud),
            fuente   = VALUES(fuente),
            fecha_actualizacion = CURRENT_TIMESTAMP
    """
    cur = conn.cursor()
    cur.execute(sql, (idtbl_calles, numero, latitud, longitud, fuente))
    cur.close()


# =============================================================================
# 3️⃣ HELPER PRIVADO · LLAMADA A GEOCODE.XYZ
# =============================================================================
#  _geocode_geocode_xyz()
#  -----------------------
#  - Dada una dirección en texto (ej. "CL MAYOR 1, Avila, España") llama
#    al servicio Geocode.xyz y devuelve (latitud, longitud).
#  - Usa JSON = 1 para parsear fácilmente la respuesta.
#  - Maneja excepciones y registra errores en el logger.
#  - NO controla el ritmo de llamadas (throttling): esa responsabilidad
#    se puede añadir en la lógica que use esta función si alguna vez
#    haces grandes volúmenes de geocodificación.
# =============================================================================


def _geocode_geocode_xyz(
    direccion: str,
    region: str = "ES",
    timeout: int = 5,
) -> Optional[Tuple[float, float]]:
    """
    Llama a Geocode.xyz para geocodificar una dirección.

    Parámetros:
        - direccion: cadena con dirección completa.
        - region: código de país (por defecto 'ES').
        - timeout: tiempo máximo de espera de la petición HTTP.

    Devuelve:
        - (latitud, longitud) como floats si hay resultado.
        - None si no hay datos o hay error.
    """
    url = "https://geocode.xyz"
    params = {
        "locate": direccion,
        "region": region,
        "json": 1,
    }

    try:
        resp = requests.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()

        # Geocode.xyz suele devolver 'latt' y 'longt' en la respuesta JSON.
        latt = data.get("latt")
        longt = data.get("longt")

        if not latt or not longt:
            logger.warning("Geocode.xyz sin resultados para dirección: %s", direccion)
            return None

        return float(latt), float(longt)

    except Exception as e:
        logger.exception("Error llamando a Geocode.xyz para '%s': %s", direccion, e)
        return None


# =============================================================================
# 4️⃣ FUNCIÓN PÚBLICA · RESOLVER_LAT_LONG()
# =============================================================================
#  Esta es la FUNCIÓN ÚNICA que deben usar los blueprints del proyecto
#  cuando necesiten resolver coordenadas para un registro:
#
#      - Contenedores
#      - Obras
#      - Inventario
#      - Otros
#
#  Entradas principales:
#      - conn          → conexión MySQL (MySQLConnection).
#      - idtbl_calles  → ID de la calle (FK a bd_tbl_comunes.tbl_calles).
#      - numero_portal → número de portal (puede venir vacío o None).
#      - lat_pdf       → latitud proveniente del PDF (str/None).
#      - lon_pdf       → longitud proveniente del PDF (str/None).
#      - municipio     → nombre de municipio (por defecto "Avila").
#      - pais          → nombre de país (por defecto "España").
#
#  Salida:
#      - Tupla (latitud_final, longitud_final) como floats o (None, None).
#
#  Prioridades de resolución:
#      1) PDF (si lat/long vienen informadas desde el PDF).
#      2) Caché (tabla bd_tbl_comunes.tbl_calles_portales_geo).
#      3) Geocode.xyz (si no hay en caché).
#
#  IMPORTANTE:
#      - Esta función NO hace COMMIT ni ROLLBACK.
#        Eso lo controla la capa de negocio que la llama.
# =============================================================================


def resolver_lat_long(
    conn: MySQLConnection,
    idtbl_calles: Optional[int],
    numero_portal: Optional[str],
    lat_pdf: Optional[str],
    lon_pdf: Optional[str],
    municipio: str = "Avila",
    pais: str = "España",
) -> Tuple[Optional[float], Optional[float]]:
    """
    Resuelve latitud/longitud para una dirección (calle + portal)
    siguiendo la estrategia definida en la introducción.

    1) Intentar usar lat/long de PDF (si ambos valores son válidos).
    2) Si no hay PDF → buscar en tabla de caché.
    3) Si no hay en caché → geocodificar con Geocode.xyz y actualizar caché.
    """

    # -------------------------------------------------------------------------
    # 4.1 VALIDACIÓN BÁSICA · SIN CALLE NO SE PUEDE GEOLOCALIZAR
    # -------------------------------------------------------------------------
    if not idtbl_calles:
        return None, None

    # -------------------------------------------------------------------------
    # 4.2 INTENTAR USAR COORDENADAS DEL PDF (SI VENGAN INFORMATAS)
    # -------------------------------------------------------------------------
    lat_final: Optional[float] = None
    lon_final: Optional[float] = None

    if lat_pdf not in (None, "", "None") and lon_pdf not in (None, "", "None"):
        try:
            lat_final = float(str(lat_pdf).strip())
            lon_final = float(str(lon_pdf).strip())
        except ValueError:
            lat_final = None
            lon_final = None

        if lat_final is not None and lon_final is not None:
            # Enriquecemos la caché con fuente='PDF' para esta calle/portal
            try:
                portal_int = int(numero_portal) if numero_portal not in (None, "") else 1
            except ValueError:
                portal_int = 1

            _insertar_en_cache(
                conn=conn,
                idtbl_calles=idtbl_calles,
                numero_portal=portal_int,
                latitud=lat_final,
                longitud=lon_final,
                fuente="PDF",
            )
            return lat_final, lon_final

    # -------------------------------------------------------------------------
    # 4.3 SIN PDF → CONSULTAR TABLA DE CACHÉ (CALLes_PORTALES_GEO)
    # -------------------------------------------------------------------------
    try:
        portal_int = int(numero_portal) if numero_portal not in (None, "") else 1
    except ValueError:
        portal_int = 1

    en_cache = _buscar_en_cache(conn, idtbl_calles, portal_int)
    if en_cache:
        return en_cache

    # -------------------------------------------------------------------------
    # 4.4 NO ESTÁ EN CACHÉ → CONSTRUIR DIRECCIÓN Y LLAMAR A GEOCODE.XYZ
    # -------------------------------------------------------------------------
    calle_info = _get_calle_y_tipo(conn, idtbl_calles)
    if not calle_info:
        # No se puede construir la dirección
        return None, None

    tipo_via, nombre_calle = calle_info

    direccion = f"{tipo_via} {nombre_calle} {portal_int}, {municipio}, {pais}".strip()

    coords = _geocode_geocode_xyz(direccion)
    if not coords:
        # Geocode.xyz no ha devuelto resultado
        return None, None

    lat_final, lon_final = coords

    # -------------------------------------------------------------------------
    # 4.5 GUARDAR RESULTADO EN CACHÉ COMO FUENTE = 'geocode_xyz'
    # -------------------------------------------------------------------------
    _insertar_en_cache(
        conn=conn,
        idtbl_calles=idtbl_calles,
        numero_portal=portal_int,
        latitud=lat_final,
        longitud=lon_final,
        fuente="geocode_xyz",
    )

    return lat_final, lon_final