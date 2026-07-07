# blueprints/control_via_publica/btn_contenedores_edicion_bp.py
# =============================================================================
# 🗑️ BOTÓN CONTENEDORES_EDICION · CONTROL VÍA PÚBLICA
# =============================================================================
# Módulo lógico: control_via_publica_contenedores
#
# 🎯 OBJETIVO GLOBAL DE ESTA PANTALLA
# ----------------------------------
# Pantalla de EDICIÓN AVANZADA sobre registros ya existentes en
#   tbl_control_contenedores (BD: control_via_publica).
#
# NO CREA contenedores nuevos; solo:
#   · Permite FILTRAR por fecha_colocacion (rango desde / hasta).
#   · Permite NAVEGAR registro a registro (anterior / siguiente) dentro
#     del conjunto filtrado.
#   · Permite EDITAR campos clave del contenedor actual y GUARDAR cambios.
#   · Permite ELIMINAR el registro actual.
#   · Permite CALCULAR latitud/longitud aproximadas a partir de la calle
#     (sin número de portal) mediante API de geocodificación (Geoapify)
#     y cachear resultados por calle.
#
# 🧩 CONTEXTO DE USO
# ------------------
# - Herramienta de backoffice para correcciones manuales.
# - Accesible desde distintos paneles:
#       · Panel de gestores de vía pública.
#       · Panel de policía / inspección.
#       · Otros listados / dashboards que necesiten editar contenedores.
# - Cada panel que abre esta pantalla debe indicar una url_origen para
#   que el botón "Volver" lleve a la vista correcta sin acoplar esta
#   pantalla a un origen concreto.
#
# 🔄 FLUJO TÉCNICO
# ----------------
# 1) La vista lee filtros y parámetros:
#       - fecha_desde, fecha_hasta
#       - posicion_actual (índice en la lista filtrada, 0-based)
#       - modo: "navegar" | "editar" | "eliminar"
#       - url_origen: ruta desde la que se llegó (opcional)
#
# 2) Construye la consulta base (SQL_BASE) con filtros de fechas
#    y JOINs para obtener nombres legibles (proveedor, calle, etc.).
#
# 3) Si no hay resultados:
#       → Renderiza la plantilla de edición sin contenedor y con mensaje.
#
# 4) Según 'modo':
#       - eliminar → borra registro actual, reconsulta, ajusta posición.
#       - navegar  → mueve posición (anterior / siguiente).
#       - editar   → actualiza campos vía SQL_UPDATE_EDICION y aplica
#                   patrón Post → Redirect → Get (PRG).
#
# 5) Ajusta la posición para que esté dentro del rango [0, total-1].
#
# 6) Selecciona el contenedor actual y renderiza la plantilla
#    templates/control_via_publica/contenedores/edicion.html.
#
# 🌐 API GEOAPIFY + CACHE
# -----------------------
# - Se usa una API interna /api/geocodificar_calle que, dada
#   (idtbl_calles, idtbl_tipos_de_vias, texto de dirección…):
#       · Intenta leer de tbl_calles_geocoding_cache.
#       · Si no hay cache, llama a Geoapify y guarda el resultado.
#   Esto evita peticiones repetidas a Geoapify para la misma calle.
#
# 🔐 SEGURIDAD
# ------------
# - Decoradores login_required y rol_required para limitar acceso
#   (super_admin, gestor_via_publica).
# - url_origen se sanea para aceptar solo rutas internas (sin esquema
#   ni dominio) y evitar redirecciones externas maliciosas.
# =============================================================================

from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    current_app,
    redirect,
    url_for,
    flash,
)
from services.helpers import login_required, rol_required
from db import ejecutar_query, ejecutar_non_query
import requests
from urllib.parse import urlparse
from datetime import date  # 🧠 para lógica de año de expediente

# =============================================================================
# 🧠 1️⃣ LÓGICA DE AÑO DE EXPEDIENTE (BACKEND)
# =============================================================================
# Esta función centraliza la regla de negocio para el año del expediente
# almacenado en tbl_control_contenedores:
#
#   - anio_expediente se guarda junto con numero_expediente y la BD
#     tiene una UNIQUE compuesta:
#         UNIQUE (anio_expediente, numero_expediente)
#     que garantiza la unicidad por año. [web:45][web:49]
#
#   - En esta pantalla de EDICIÓN AVANZADA se permite modificar el año
#     manualmente, pero la función sirve para:
#       · Normalizar el valor si viene vacío o mal formateado.
#       · Dar un valor por defecto (año actual) cuando no venga nada.
#
# NOTA:
#   - A diferencia de la pantalla de VALIDACIÓN, aquí no aplicamos la
#     “regla de enero” estricta; el objetivo de esta vista es poder
#     corregir expedientes antiguos si hace falta.
# =============================================================================


def resolver_anio_expediente_edicion(valor_anio_form: str | None) -> int | None:
    """
    Normaliza el año del expediente en edición avanzada.

    - Si valor_anio_form viene vacío → devuelve None (se podrá guardar NULL).
    - Si viene un entero válido → devuelve ese año.
    - Si viene basura → devuelve año actual como razonable por defecto.
    """
    if not valor_anio_form:
        return None

    try:
        anio = int(valor_anio_form)
        # Puedes acotar si quieres (ej. 2000–2100)
        if 2000 <= anio <= 2100:
            return anio
        # Fuera de rango, usamos año actual
        return date.today().year
    except ValueError:
        return date.today().year


# -----------------------------------------------------------------------------
# 2️⃣ CONFIGURACIÓN DEL BLUEPRINT · CONTENEDORES EDICIÓN
# -----------------------------------------------------------------------------
btn_contenedores_edicion_bp = Blueprint(
    "btn_contenedores_edicion_bp",
    __name__,
    url_prefix="/control_via_publica/contenedores/edicion",
    template_folder="templates",
)

# -----------------------------------------------------------------------------
# 3️⃣ SQL_BASE · CONSULTA DE RESULTADOS CON JOINS LEGIBLES
# -----------------------------------------------------------------------------
SQL_BASE = """
SELECT
    c.*,
    p.nombre_razon_social      AS proveedor_nombre,
    p.nif                      AS proveedor_nif,
    tv.tipos_de_vias           AS tipo_via_nombre,
    ca.calles                  AS calle_nombre,
    d.descripcion              AS dimension_nombre
FROM tbl_control_contenedores AS c
LEFT JOIN bd_tbl_comunes.tbl_proveedores   AS p  ON c.idtbl_proveedores   = p.idtbl_proveedores
LEFT JOIN bd_tbl_comunes.tbl_tipos_de_vias AS tv ON c.idtbl_tipos_de_vias = tv.idtbl_tipos_de_vias
LEFT JOIN bd_tbl_comunes.tbl_calles        AS ca ON c.idtbl_calles        = ca.idtbl_calles
LEFT JOIN bd_tbl_comunes.tbl_dimensiones   AS d  ON c.idtbl_dimensiones   = d.idtbl_dimensiones
WHERE 1=1
"""

# -----------------------------------------------------------------------------
# 4️⃣ SQL_UPDATE_EDICION · UPDATE DE CAMPOS EDITABLES (INCLUYE AÑO EXPEDIENTE)
# -----------------------------------------------------------------------------
# Se añade anio_expediente al UPDATE para mantener la unicidad
# (anio_expediente, numero_expediente) en la tabla de control. [web:45][web:49]
# -----------------------------------------------------------------------------
SQL_UPDATE_EDICION = """
UPDATE tbl_control_contenedores
SET
    idtbl_proveedores      = %s,
    nombre_solicitante     = %s,
    nif                    = %s,
    telefono               = %s,
    fecha_colocacion       = %s,
    fecha_retirada         = %s,
    fecha_firma_inicial    = %s,
    idtbl_dimensiones      = %s,
    observaciones          = %s,
    idtbl_tipos_de_vias    = %s,
    idtbl_calles           = %s,
    numero_portal          = %s,
    latitud                = %s,
    longitud               = %s,
    precision_gps          = %s,
    gps_precision_ok       = %s,
    gps_nivel_calidad      = %s,
    gps_origen             = %s,
    csv                    = %s,
    csv_retirada           = %s,
    idtbl_gestores         = %s,
    numero_solicitud       = %s,
    numero_expediente      = %s,
    anio_expediente        = %s,
    n_solicitud_retirada   = %s
WHERE idtbl_control_contenedores = %s
"""


# -----------------------------------------------------------------------------
# 5️⃣ API AUXILIAR · LISTADO DE CALLES PARA EL EDITOR
# -----------------------------------------------------------------------------
@btn_contenedores_edicion_bp.route("/api/calles")
@login_required
def api_contenedores_edicion_calles():
    tipo_via_id = request.args.get("tipo_via_id", type=int)
    if not tipo_via_id:
        return jsonify([])

    calles = ejecutar_query(
        """
        SELECT idtbl_calles, calles
        FROM tbl_calles
        WHERE idtbl_tipos_de_vias = %s
          AND idtbl_municipios = 395
        ORDER BY calles ASC
        """,
        (tipo_via_id,),
        nombre_bd="bd_tbl_comunes",
    )
    return jsonify(calles)


# -----------------------------------------------------------------------------
# 6️⃣ API GEOAPIFY · GEOCODIFICAR CALLE + CACHE
# -----------------------------------------------------------------------------
@btn_contenedores_edicion_bp.route("/api/geocodificar_calle", methods=["POST"])
@login_required
def api_geocodificar_calle():
    idtbl_calles = request.values.get("idtbl_calles", type=int)
    idtbl_tipos_de_vias = request.values.get("idtbl_tipos_de_vias", type=int)
    idtbl_municipios = request.values.get("idtbl_municipios", type=int) or 395
    tipo_via_nombre = (request.values.get("tipo_via_nombre") or "").strip()
    calle_nombre = (request.values.get("calle_nombre") or "").strip()
    municipio_nombre = (request.values.get("municipio_nombre") or "Ávila").strip()
    provincia_nombre = (request.values.get("provincia_nombre") or "").strip()
    pais_nombre = (request.values.get("pais_nombre") or "España").strip()

    if not (idtbl_calles and idtbl_tipos_de_vias and calle_nombre):
        return jsonify({"error": "Faltan datos para geocodificar"}), 400

    direccion_texto = f"{tipo_via_nombre} {calle_nombre}, {municipio_nombre}"
    if provincia_nombre:
        direccion_texto += f", {provincia_nombre}"
    if pais_nombre:
        direccion_texto += f", {pais_nombre}"

    fila_cache = ejecutar_query(
        """
        SELECT latitud, longitud, precision_nivel
        FROM tbl_calles_geocoding_cache
        WHERE idtbl_calles = %s
        """,
        (idtbl_calles,),
        nombre_bd="bd_tbl_comunes",
    )

    if fila_cache:
        lat = fila_cache[0]["latitud"]
        lon = fila_cache[0]["longitud"]
        precision = fila_cache[0]["precision_nivel"]
        return jsonify(
            {
                "latitud": lat,
                "longitud": lon,
                "fuente": "cache",
                "precision_nivel": precision,
            }
        )

    api_key = current_app.config.get("GEOAPIFY_API_KEY")
    if not api_key:
        return jsonify({"error": "No hay API key de Geoapify configurada"}), 500

    params = {
        "apiKey": api_key,
        "text": direccion_texto,
        "format": "json",
    }

    try:
        resp = requests.get(
            "https://api.geoapify.com/v1/geocode/search",
            params=params,
            timeout=5,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        return jsonify({"error": f"Error llamando a Geoapify: {exc}"}), 502

    features = data.get("features") or []
    if not features:
        return jsonify({"error": "Sin resultados de geocodificación"}), 404

    feat = features[0]
    lon, lat = feat["geometry"]["coordinates"]
    props = feat.get("properties", {})
    rank = props.get("rank") or {}
    precision_nivel = rank.get("confidence", None)

    try:
        ejecutar_non_query(
            """
            INSERT INTO tbl_calles_geocoding_cache (
                idtbl_calles,
                idtbl_tipos_de_vias,
                idtbl_municipios,
                direccion_texto,
                latitud,
                longitud,
                fuente,
                precision_nivel
            )
            VALUES (%s, %s, %s, %s, %s, %s, 'geoapify', %s)
            ON DUPLICATE KEY UPDATE
                direccion_texto = VALUES(direccion_texto),
                latitud         = VALUES(latitud),
                longitud        = VALUES(longitud),
                fuente          = VALUES(fuente),
                precision_nivel = VALUES(precision_nivel)
            """,
            (
                idtbl_calles,
                idtbl_tipos_de_vias,
                idtbl_municipios,
                direccion_texto,
                lat,
                lon,
                precision_nivel,
            ),
            nombre_bd="bd_tbl_comunes",
        )
    except Exception:
        pass

    return jsonify(
        {
            "latitud": lat,
            "longitud": lon,
            "fuente": "geoapify",
            "precision_nivel": precision_nivel,
        }
    )


# -----------------------------------------------------------------------------
# 7️⃣ VISTA PRINCIPAL · EDICIÓN AVANZADA DE CONTENEDORES
# -----------------------------------------------------------------------------
@btn_contenedores_edicion_bp.route("/", methods=["GET", "POST"])
@login_required
@rol_required("super_admin", "gestor_via_publica")
def btn_contenedores_edicion():
    # 7.1 PARÁMETROS DE ENTRADA
    posicion = request.values.get("posicion_actual", 0, type=int)
    fecha_desde = request.values.get("fecha_desde") or ""
    fecha_hasta = request.values.get("fecha_hasta") or ""
    modo = request.values.get("modo") or "navegar"
    raw_url_origen = request.values.get("url_origen") or ""

    url_origen = ""
    if raw_url_origen:
        parsed = urlparse(raw_url_origen)
        if not parsed.scheme and not parsed.netloc:
            url_origen = raw_url_origen

    info = None
    error = None

    # 7.2 CONSTRUIR SQL BASE FILTRADA
    sql = SQL_BASE
    params = []

    if fecha_desde:
        sql += " AND c.fecha_colocacion >= %s"
        params.append(fecha_desde)

    if fecha_hasta:
        sql += " AND c.fecha_colocacion <= %s"
        params.append(fecha_hasta)

    filas = ejecutar_query(sql, tuple(params), nombre_bd="control_via_publica")
    total_resultados = len(filas)

    if not filas:
        return render_template(
            "control_via_publica/contenedores/edicion.html",
            contenedor=None,
            posicion=0,
            total_resultados=0,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            url_origen=url_origen,
            info=None,
            error="Sin resultados para esos filtros.",
        )

    # 7.3 ACCIONES SEGÚN MODO
    # 7.3.1 ELIMINAR
    if modo == "eliminar":
        id_contenedor = request.values.get("idtbl_control_contenedores", type=int)
        if id_contenedor:
            try:
                ejecutar_non_query(
                    "DELETE FROM tbl_control_contenedores WHERE idtbl_control_contenedores = %s",
                    (id_contenedor,),
                    nombre_bd="control_via_publica",
                )
                info = f"Contenedor {id_contenedor} eliminado correctamente."
            except Exception as exc:
                error = f"Error al eliminar el contenedor {id_contenedor}: {exc}"
        else:
            error = "No se ha recibido ID de contenedor para eliminar."

        filas = ejecutar_query(sql, tuple(params), nombre_bd="control_via_publica")
        total_resultados = len(filas)

        if total_resultados == 0:
            return render_template(
                "control_via_publica/contenedores/edicion.html",
                contenedor=None,
                posicion=0,
                total_resultados=0,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                url_origen=url_origen,
                info=info,
                error=error,
            )

        if posicion >= total_resultados:
            posicion = total_resultados - 1

    # 7.3.2 NAVEGAR
    elif modo == "navegar":
        nav = request.values.get("nav")
        if nav == "anterior":
            posicion = max(0, posicion - 1)
        elif nav == "siguiente":
            posicion = min(total_resultados - 1, posicion + 1)

    # 7.3.3 EDITAR (GUARDAR CAMBIOS)
    elif modo == "editar":
        id_contenedor = request.values.get("idtbl_control_contenedores", type=int)

        if not id_contenedor:
            flash("No se ha recibido ID de contenedor para guardar cambios.", "danger")
        else:

            def normalize_decimal_field(value):
                if value is None:
                    return None
                value = value.strip()
                if value == "":
                    return None
                try:
                    return float(value)
                except ValueError:
                    return None

            # PROVEEDOR / SOLICITANTE
            idtbl_proveedores = request.values.get("idtbl_proveedores", type=int)
            nombre_solicitante = request.values.get("nombre_solicitante") or None
            nif = request.values.get("nif") or None
            telefono = request.values.get("telefono") or None

            # FECHAS
            fecha_colocacion = request.values.get("fecha_colocacion") or None
            fecha_retirada = request.values.get("fecha_retirada") or None
            fecha_firma_inicial = request.values.get("fecha_firma_inicial") or None

            # DIMENSIÓN / OBSERVACIONES
            idtbl_dimensiones = request.values.get("idtbl_dimensiones", type=int)
            observaciones = request.values.get("observaciones") or None

            # UBICACIÓN
            idtbl_tipos_de_vias = request.values.get("idtbl_tipos_de_vias", type=int)
            idtbl_calles = request.values.get("idtbl_calles", type=int)
            numero_portal = request.values.get("numero_portal") or None

            # GPS
            latitud_raw = request.values.get("latitud")
            longitud_raw = request.values.get("longitud")
            precision_gps_raw = request.values.get("precision_gps")

            latitud = normalize_decimal_field(latitud_raw)
            longitud = normalize_decimal_field(longitud_raw)
            precision_gps = normalize_decimal_field(precision_gps_raw)

            gps_precision_ok = request.values.get("gps_precision_ok") or None
            gps_nivel_calidad = request.values.get("gps_nivel_calidad") or None
            gps_origen = request.values.get("gps_origen") or None

            # CSV / ADMIN
            csv = request.values.get("csv") or None
            csv_retirada = request.values.get("csv_retirada") or None
            idtbl_gestores = request.values.get("idtbl_gestores", type=int)
            numero_solicitud = request.values.get("numero_solicitud") or None
            numero_expediente = request.values.get("numero_expediente") or None
            n_solicitud_retirada = request.values.get("n_solicitud_retirada") or None

            # AÑO EXPEDIENTE (NUEVA LÓGICA DE EDICIÓN)
            anio_expediente_form = request.values.get("anio_expediente")
            anio_expediente = resolver_anio_expediente_edicion(anio_expediente_form)

            if gps_precision_ok in ("on", "true", "True", "1", "S"):
                gps_precision_ok = "1"
            else:
                gps_precision_ok = "0"

            try:
                ejecutar_non_query(
                    SQL_UPDATE_EDICION,
                    (
                        idtbl_proveedores,
                        nombre_solicitante,
                        nif,
                        telefono,
                        fecha_colocacion,
                        fecha_retirada,
                        fecha_firma_inicial,
                        idtbl_dimensiones,
                        observaciones,
                        idtbl_tipos_de_vias,
                        idtbl_calles,
                        numero_portal,
                        latitud,
                        longitud,
                        precision_gps,
                        gps_precision_ok,
                        gps_nivel_calidad,
                        gps_origen,
                        csv,
                        csv_retirada,
                        idtbl_gestores,
                        numero_solicitud,
                        numero_expediente,
                        anio_expediente,
                        n_solicitud_retirada,
                        id_contenedor,
                    ),
                    nombre_bd="control_via_publica",
                )
                flash(
                    f"Contenedor {id_contenedor} actualizado correctamente.", "success"
                )
            except Exception as exc:
                flash(
                    f"Error al actualizar el contenedor {id_contenedor}: {exc}",
                    "danger",
                )

        return redirect(
            url_for(
                "btn_contenedores_edicion_bp.btn_contenedores_edicion",
                posicion_actual=posicion,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                url_origen=url_origen,
                modo="navegar",
            )
        )

    # 7.4 ASEGURAR POSICIÓN VÁLIDA Y RENDERIZAR
    if posicion < 0:
        posicion = 0
    if posicion >= len(filas):
        posicion = len(filas) - 1

    contenedor = filas[posicion]

    return render_template(
        "control_via_publica/contenedores/edicion.html",
        contenedor=contenedor,
        posicion=posicion,
        total_resultados=total_resultados,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        url_origen=url_origen,
        proveedor_nombre=contenedor.get("proveedor_nombre", ""),
        proveedor_nif=contenedor.get("proveedor_nif", ""),
        tipo_via_nombre=contenedor.get("tipo_via_nombre", ""),
        calle_nombre=contenedor.get("calle_nombre", ""),
        dimension_nombre=contenedor.get("dimension_nombre", ""),
        info=info,
        error=error,
    )
