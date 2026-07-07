# =============================================================================
# 📁 ARCHIVO: agenda_core/relaciones_contenedores_bp.py
# =============================================================================
# API para gestionar relaciones colocación↔retirada de CONTENEDORES.
#
# Responsabilidades:
#   - Listar relaciones existentes (para panel).
#   - Crear nueva relación:
#       · Insertar en tbl_relacion_colocacion_retirada.
#       · Registrar quién hace la vinculación (idtbl_usuario).
#       · Cerrar el evento de agenda de la colocación correspondiente.
# =============================================================================

from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from datetime import datetime

from db import ejecutar_query, ejecutar_non_query
from agenda_core.backend_agenda import cerrar_evento_contenedor_por_id

relaciones_contenedores_bp = Blueprint(
    "relaciones_contenedores",
    __name__,
    url_prefix="/api/relaciones/contenedores",
)

# =============================================================================
# 1️⃣ LISTAR RELACIONES PARA PANEL
# =============================================================================


@relaciones_contenedores_bp.route("/", methods=["GET"])
@login_required
def listar_relaciones_contenedores():
    """
    Devuelve las relaciones colocación–retirada de contenedores.

    Respuesta (JSON): lista de objetos con:
      - idtbl_relacion
      - idtbl_contenedor_colocacion
      - idtbl_contenedor_retirada
      - fecha_vinculacion
      - idtbl_usuario
      - usuario_nombre (si existe en tabla de usuarios)
    """
    try:
        filas = ejecutar_query(
            """
            SELECT
                r.idtbl_relacion,
                r.idtbl_contenedor_colocacion,
                r.idtbl_contenedor_retirada,
                r.fecha_vinculacion,
                r.idtbl_usuario,
                u.nombre AS usuario_nombre
            FROM tbl_relacion_colocacion_retirada r
            LEFT JOIN tbl_usuarios u
                   ON r.idtbl_usuario = u.idtbl_usuarios
            ORDER BY r.fecha_vinculacion DESC
            """,
            (),
            nombre_bd="control_via_publica",
        )

        return jsonify(filas), 200

    except Exception as e:
        current_app.logger.error(
            f"[RELACIONES_CONTENEDORES] Error listando relaciones: {e!r}",
            exc_info=True,
        )
        return jsonify({"error": str(e)}), 500


# =============================================================================
# 2️⃣ CREAR RELACIÓN (COLOCACIÓN↔RETIRADA) + CERRAR AGENDA
# =============================================================================


@relaciones_contenedores_bp.route("/", methods=["POST"])
@login_required
def crear_relacion_contenedor():
    """
    Crea una relación colocación–retirada para un contenedor y
    cierra el evento de agenda asociado a la colocación.

    Espera JSON:
      {
        "id_colocacion": 123,          # idtbl_contenedor (colocación)
        "id_retirada": 456,            # idtbl_contenedor (retirada)
        "fecha_retirada": "2026-06-07" # opcional si ya está en la BD
      }
    """
    data = request.get_json(silent=True) or {}

    id_colocacion = data.get("id_colocacion")
    id_retirada = data.get("id_retirada")
    fecha_retirada_str = data.get("fecha_retirada")

    if not id_colocacion or not id_retirada:
        return jsonify({"error": "id_colocacion e id_retirada son obligatorios"}), 400

    # Fecha de retirada: si llega, intentar parsearla; si no, intentar leer de BD
    fecha_retirada = None
    if fecha_retirada_str:
        try:
            fecha_retirada = datetime.strptime(fecha_retirada_str, "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "fecha_retirada debe ser YYYY-MM-DD"}), 400
    else:
        try:
            fila_ret = ejecutar_query(
                """
                SELECT fecha_retirada
                FROM tbl_control_contenedores
                WHERE idtbl_contenedor = %s
                """,
                (id_retirada,),
                nombre_bd="control_via_publica",
            )
            if fila_ret and fila_ret[0].get("fecha_retirada"):
                fecha_retirada = fila_ret[0]["fecha_retirada"]
        except Exception as e:
            current_app.logger.warning(
                f"[RELACIONES_CONTENEDORES] No se pudo obtener fecha_retirada de BD: {e!r}"
            )

    try:
        # 2.1 Insertar relación
        ejecutar_non_query(
            """
            INSERT INTO tbl_relacion_colocacion_retirada (
                idtbl_contenedor_colocacion,
                idtbl_contenedor_retirada,
                fecha_vinculacion,
                idtbl_usuario
            ) VALUES (%s, %s, NOW(), %s)
            """,
            (id_colocacion, id_retirada, current_user.id),
            nombre_bd="control_via_publica",
        )

        # 2.2 Cerrar evento de agenda de la colocación
        cerrar_evento_contenedor_por_id(id_colocacion, fecha_retirada)

        return jsonify({"status": "ok"}), 201

    except Exception as e:
        current_app.logger.error(
            f"[RELACIONES_CONTENEDORES] Error creando relación: {e!r}",
            exc_info=True,
        )
        return jsonify({"error": str(e)}), 500
