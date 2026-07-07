#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BLUEPRINT: CONTROL DE CONTENEDORES - MAPA ORBITAL
Vista de mapa interactivo con Leaflet.js y OpenStreetMap
"""

from flask import Blueprint, render_template, jsonify, current_app
from sqlalchemy import text

# ==============================================================================
# CONFIGURACIÓN DEL BLUEPRINT
# ==============================================================================

btn_contenedores_mapa_bp = Blueprint(
    "btn_contenedores_mapa_bp",
    __name__,
    template_folder="templates/control_via_publica/contenedores",
    url_prefix="/control-obras",
)


# ==============================================================================
# FUNCIÓN HELPER PARA OBTENER DB
# ==============================================================================


def get_db():
    """Obtiene la instancia de SQLAlchemy desde la app actual"""
    return current_app.extensions["sqlalchemy"]


# ==============================================================================
# RUTA PRINCIPAL - MAPA DE CONTENEDORES HTML
# ==============================================================================


@btn_contenedores_mapa_bp.route("/contenedores/mapa")
def btn_contenedores_mapa():
    """
    Renderiza la vista principal del mapa interactivo de contenedores.
    """

    query = text("""
        SELECT 
            c.latitud,
            c.longitud,
            CASE 
                WHEN c.fecha_retirada IS NULL THEN 'instalado'
                ELSE 'retirado'
            END AS estado,
            CONCAT(c.numero_expediente, '/', c.anio_expediente) AS numero_expediente,
            CONCAT_WS(' ', 
                tv.nombre_tipo_via,
                cal.nombre_calle,
                c.numero_portal
            ) AS direccion,
            DATE_FORMAT(c.fecha_colocacion, '%d/%m/%Y') AS fecha_colocacion,
            DATE_FORMAT(c.fecha_retirada, '%d/%m/%Y') AS fecha_retirada
        FROM tbl_control_contenedores c
        LEFT JOIN tbl_tipos_de_vias tv 
            ON c.idtbl_tipos_de_vias = tv.idtbl_tipos_de_vias
        LEFT JOIN tbl_calles cal 
            ON c.idtbl_calles = cal.idtbl_calles
        WHERE c.latitud IS NOT NULL 
          AND c.longitud IS NOT NULL
        ORDER BY c.fecha_colocacion DESC
    """)

    try:
        db = get_db()
        result = db.session.execute(query)
        contenedores = [dict(row._mapping) for row in result]
    except Exception as e:
        current_app.logger.error(f"ERROR al ejecutar query de contenedores: {e}")
        contenedores = []

    return render_template("contenedores_mapa.html", contenedores=contenedores)


# ==============================================================================
# API GEOJSON - INTEGRACIÓN AJAX
# ==============================================================================


@btn_contenedores_mapa_bp.route("/api/contenedores/geojson")
def contenedores_geojson():
    """
    API endpoint que devuelve contenedores en formato GeoJSON RFC 7946.
    """

    query = text("""
        SELECT 
            c.latitud,
            c.longitud,
            CASE 
                WHEN c.fecha_retirada IS NULL THEN 'instalado'
                ELSE 'retirado'
            END AS estado,
            CONCAT(c.numero_expediente, '/', c.anio_expediente) AS numero_expediente,
            CONCAT_WS(' ', 
                tv.nombre_tipo_via,
                cal.nombre_calle,
                c.numero_portal
            ) AS direccion,
            DATE_FORMAT(c.fecha_colocacion, '%d/%m/%Y') AS fecha_colocacion,
            DATE_FORMAT(c.fecha_retirada, '%d/%m/%Y') AS fecha_retirada
        FROM tbl_control_contenedores c
        LEFT JOIN tbl_tipos_de_vias tv 
            ON c.idtbl_tipos_de_vias = tv.idtbl_tipos_de_vias
        LEFT JOIN tbl_calles cal 
            ON c.idtbl_calles = cal.idtbl_calles
        WHERE c.latitud IS NOT NULL 
          AND c.longitud IS NOT NULL
        ORDER BY c.fecha_colocacion DESC
    """)

    try:
        db = get_db()
        result = db.session.execute(query)
        contenedores = [dict(row._mapping) for row in result]

        geojson = {"type": "FeatureCollection", "features": []}

        for c in contenedores:
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [c["longitud"], c["latitud"]],
                },
                "properties": {
                    "estado": c["estado"],
                    "numero_expediente": c["numero_expediente"],
                    "direccion": c["direccion"],
                    "fecha_colocacion": c["fecha_colocacion"],
                    "fecha_retirada": c["fecha_retirada"],
                },
            }
            geojson["features"].append(feature)

        return jsonify(geojson)

    except Exception as e:
        return (
            jsonify(
                {
                    "type": "FeatureCollection",
                    "features": [],
                    "error": f"Error al generar GeoJSON: {str(e)}",
                }
            ),
            500,
        )


# ==============================================================================
# API ESTADÍSTICAS - MÉTRICAS EN TIEMPO REAL
# ==============================================================================


@btn_contenedores_mapa_bp.route("/api/contenedores/estadisticas")
def contenedores_estadisticas():
    """
    Endpoint que devuelve estadísticas agregadas de contenedores.
    """

    query = text("""
        SELECT 
            COUNT(*) AS total,
            SUM(CASE WHEN fecha_retirada IS NULL THEN 1 ELSE 0 END) AS instalados,
            SUM(CASE WHEN fecha_retirada IS NOT NULL THEN 1 ELSE 0 END) AS retirados,
            SUM(CASE WHEN gps_precision_ok = 1 THEN 1 ELSE 0 END) AS gps_validados,
            AVG(precision_gps) AS precision_promedio,
            MIN(precision_gps) AS mejor_precision,
            MAX(precision_gps) AS peor_precision
        FROM tbl_control_contenedores
        WHERE latitud IS NOT NULL 
          AND longitud IS NOT NULL
    """)

    try:
        db = get_db()
        result = db.session.execute(query).fetchone()

        total = result.total or 0
        instalados = result.instalados or 0
        retirados = result.retirados or 0

        if total > 0:
            porcentaje_instalados = round((instalados / total) * 100, 2)
            porcentaje_retirados = round((retirados / total) * 100, 2)
        else:
            porcentaje_instalados = 0.0
            porcentaje_retirados = 0.0

        estadisticas = {
            "total": total,
            "instalados": instalados,
            "retirados": retirados,
            "gps_validados": result.gps_validados or 0,
            "precision_promedio": (
                round(float(result.precision_promedio), 2)
                if result.precision_promedio
                else 0.0
            ),
            "mejor_precision": (
                round(float(result.mejor_precision), 2)
                if result.mejor_precision
                else 0.0
            ),
            "peor_precision": (
                round(float(result.peor_precision), 2) if result.peor_precision else 0.0
            ),
            "porcentaje_instalados": porcentaje_instalados,
            "porcentaje_retirados": porcentaje_retirados,
        }

        return jsonify(estadisticas)

    except Exception as e:
        return (
            jsonify({"error": str(e), "total": 0, "instalados": 0, "retirados": 0}),
            500,
        )


# ==============================================================================
# API RECIENTES - ÚLTIMAS INSTALACIONES
# ==============================================================================


@btn_contenedores_mapa_bp.route("/api/contenedores/recientes")
def contenedores_recientes():
    """
    Devuelve los 10 contenedores instalados más recientemente.
    """

    query = text("""
        SELECT 
            CONCAT(c.numero_expediente, '/', c.anio_expediente) AS numero_expediente,
            CONCAT_WS(' ', 
                tv.nombre_tipo_via,
                cal.nombre_calle,
                c.numero_portal
            ) AS direccion,
            DATE_FORMAT(c.fecha_colocacion, '%d/%m/%Y') AS fecha_colocacion,
            CASE 
                WHEN c.fecha_retirada IS NULL THEN 'instalado'
                ELSE 'retirado'
            END AS estado
        FROM tbl_control_contenedores c
        LEFT JOIN tbl_tipos_de_vias tv 
            ON c.idtbl_tipos_de_vias = tv.idtbl_tipos_de_vias
        LEFT JOIN tbl_calles cal 
            ON c.idtbl_calles = cal.idtbl_calles
        WHERE c.latitud IS NOT NULL 
          AND c.longitud IS NOT NULL
        ORDER BY c.fecha_colocacion DESC
        LIMIT 10
    """)

    try:
        db = get_db()
        result = db.session.execute(query)
        recientes = [dict(row._mapping) for row in result]
        return jsonify(recientes)

    except Exception as e:
        return jsonify({"error": str(e), "recientes": []}), 500
