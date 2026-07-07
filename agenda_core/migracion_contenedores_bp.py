# =============================================================================
# 📁 ARCHIVO: agenda_core/migracion_contenedores_bp.py
# =============================================================================

from flask import Blueprint, jsonify, current_app
from db import ejecutar_query, ejecutar_non_query
from datetime import datetime, timedelta

migracion_bp = Blueprint("migracion", __name__, url_prefix="/api/migracion")


@migracion_bp.route("/verificar-agenda", methods=["GET"])
def verificar_agenda():
    """
    Comprueba el estado actual de la agenda para eventos de contenedores,
    usando tbl_agenda_via_publica.
    """
    try:
        eventos = ejecutar_query(
            """
            SELECT 
                COUNT(*) AS total,
                MIN(fecha_inicio) AS primera_fecha,
                MAX(fecha_inicio) AS ultima_fecha
            FROM tbl_agenda_via_publica
            WHERE origen_tabla = 'tbl_control_contenedores'
            """,
            (),
            nombre_bd="control_via_publica",
        )[0]

        return (
            jsonify(
                {
                    "total_eventos": eventos["total"],
                    "primera_fecha": (
                        str(eventos["primera_fecha"])
                        if eventos["primera_fecha"]
                        else None
                    ),
                    "ultima_fecha": (
                        str(eventos["ultima_fecha"])
                        if eventos["ultima_fecha"]
                        else None
                    ),
                }
            ),
            200,
        )

    except Exception as e:
        current_app.logger.error(f"Error verificar_agenda: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@migracion_bp.route("/contenedores-a-agenda", methods=["POST"])
def migrar_contenedores_a_agenda():
    """
    Migra los registros de tbl_control_contenedores a tbl_agenda_via_publica
    y tbl_agenda_calles_afectadas, evitando duplicados por origen_tabla+origen_id.
    """
    try:
        # 1) Obtener tipo de evento CONTENEDORES
        tipo_evento = ejecutar_query(
            """
            SELECT idtbl_tipos_evento 
            FROM tbl_tipos_evento_via_publica 
            WHERE codigo = 'CONTENEDORES'
            LIMIT 1
            """,
            (),
            nombre_bd="control_via_publica",
        )

        if not tipo_evento:
            return jsonify({"error": "No existe el tipo de evento CONTENEDORES"}), 400

        idtbl_tipos_evento = tipo_evento[0]["idtbl_tipos_evento"]

        # 2) Obtener contenedores a migrar
        contenedores = ejecutar_query(
            """
            SELECT 
                idtbl_contenedor,
                csv,
                fecha_colocacion,
                lugar_ubicacion,
                tamano_contenedor,
                idtbl_calles
            FROM tbl_control_contenedores
            WHERE fecha_colocacion IS NOT NULL
            ORDER BY fecha_colocacion
            """,
            (),
            nombre_bd="control_via_publica",
        )

        total_ok = 0
        total_error = 0
        errores = []

        for cont in contenedores:
            try:
                idtbl_contenedor = cont["idtbl_contenedor"]
                csv = cont["csv"]
                fecha_colocacion = cont["fecha_colocacion"]
                lugar_ubicacion = cont["lugar_ubicacion"] or "Sin ubicación"
                tamano = cont["tamano_contenedor"] or ""
                idtbl_calles = cont["idtbl_calles"]

                # 2.1) Calcular fechas de evento
                if isinstance(fecha_colocacion, str):
                    fecha_inicio = datetime.strptime(fecha_colocacion, "%d/%m/%Y")
                else:
                    fecha_inicio = fecha_colocacion

                # Ejemplo: 90 días de duración
                fecha_fin = fecha_inicio + timedelta(days=90)

                # 2.2) Construir título y descripción
                titulo = f"Contenedor {csv}"
                if tamano:
                    titulo += f" - {tamano}"

                descripcion = f"Colocación de contenedor en {lugar_ubicacion}"

                # 3) Evitar duplicados: comprobar si ya existe evento para este contenedor
                existe = ejecutar_query(
                    """
                    SELECT idtbl_agenda
                    FROM tbl_agenda_via_publica
                    WHERE origen_tabla = 'tbl_control_contenedores'
                      AND origen_id = %s
                    LIMIT 1
                    """,
                    (idtbl_contenedor,),
                    nombre_bd="control_via_publica",
                )

                if existe:
                    # Ya hay evento para este contenedor → omitir
                    continue

                # 4) Insertar evento en tbl_agenda_via_publica
                ejecutar_non_query(
                    """
                    INSERT INTO tbl_agenda_via_publica (
                        idtbl_tipos_evento,
                        titulo,
                        descripcion,
                        fecha_inicio,
                        fecha_fin,
                        all_day,
                        origen_tabla,
                        origen_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        idtbl_tipos_evento,
                        titulo,
                        descripcion,
                        fecha_inicio,
                        fecha_fin,
                        1,  # all_day = 1
                        "tbl_control_contenedores",
                        idtbl_contenedor,
                    ),
                    nombre_bd="control_via_publica",
                )

                evento = ejecutar_query(
                    "SELECT LAST_INSERT_ID() AS id", (), nombre_bd="control_via_publica"
                )[0]

                idtbl_agenda = evento["id"]

                # 5) Asociar calle afectada (si hay)
                if idtbl_calles:
                    ejecutar_non_query(
                        """
                        INSERT INTO tbl_agenda_calles_afectadas (
                            idtbl_agenda,
                            idtbl_calles,
                            sentido,
                            observaciones
                        ) VALUES (%s, %s, %s, %s)
                        """,
                        (
                            idtbl_agenda,
                            idtbl_calles,
                            "AMBOS",
                            lugar_ubicacion,
                        ),
                        nombre_bd="control_via_publica",
                    )

                total_ok += 1

            except Exception as e:
                total_error += 1
                errores.append(f"CSV {csv}: {str(e)}")
                current_app.logger.error(
                    f"Error migrando CSV {csv}: {e}", exc_info=True
                )

        return (
            jsonify(
                {
                    "status": "completado",
                    "total_contenedores": len(contenedores),
                    "migrados": total_ok,
                    "errores": total_error,
                    "detalle_errores": errores,
                }
            ),
            200,
        )

    except Exception as e:
        current_app.logger.error(
            f"Error migrar_contenedores_a_agenda: {e}", exc_info=True
        )
        return jsonify({"error": str(e)}), 500
