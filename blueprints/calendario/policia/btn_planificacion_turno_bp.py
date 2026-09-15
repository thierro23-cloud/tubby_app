from __future__ import annotations

from datetime import date
from io import BytesIO

from flask import Blueprint, flash, jsonify, redirect, render_template, request, send_file, url_for
from openpyxl import Workbook

from db import ejecutar_non_query, ejecutar_query
from services.helpers import rol_required
from services.super_admin_metadata import super_admin_accion

btn_planificacion_turno_bp = Blueprint(
    "btn_planificacion_turno_bp",
    __name__,
    url_prefix="/calendario/policia/planificacion-turnos",
)


def _to_int(v):
    try:
        return int(v) if v not in (None, "") else None
    except Exception:
        return None


def _catalogos():
    servicios = ejecutar_query(
        "SELECT idtbl_servicios, servicios FROM tbl_servicios ORDER BY servicios"
    ) or []
    unidades = ejecutar_query(
        "SELECT idtbl_unidades_organizativas, nombre FROM tbl_unidades_organizativas ORDER BY nombre"
    ) or []
    tipos = ejecutar_query(
        "SELECT idtbl_tipos_unidades_organizativas, codigo, nombre FROM tbl_tipos_unidades_organizativas ORDER BY nombre"
    ) or []
    servicios_turno = []
    return servicios, unidades, tipos, servicios_turno


def _servicios_turno_filtrados(idtbl_servicios: int | None, idtbl_unidades: int | None, idtbl_tipos: int | None):
    if not idtbl_servicios or not idtbl_unidades or not idtbl_tipos:
        return []

    rows = ejecutar_query(
        """
        SELECT
            st.idtbl_servicios_turnos AS id,
            CONCAT_WS(
                ' - ',
                CONCAT('Turno ', st.idtbl_servicios_turnos),
                s.servicios,
                u.nombre,
                t.nombre
            ) AS texto
        FROM tbl_servicios_turnos st
        LEFT JOIN tbl_servicios s
               ON s.idtbl_servicios = st.idtbl_servicios
        LEFT JOIN tbl_unidades_organizativas u
               ON u.idtbl_unidades_organizativas = st.idtbl_unidades_organizativas
        LEFT JOIN tbl_tipos_unidades_organizativas t
               ON t.idtbl_tipos_unidades_organizativas = st.idtbl_tipos_unidades_organizativas
        WHERE st.idtbl_servicios = %s
          AND st.idtbl_unidades_organizativas = %s
          AND st.idtbl_tipos_unidades_organizativas = %s
        ORDER BY st.idtbl_servicios_turnos DESC
        """,
        (idtbl_servicios, idtbl_unidades, idtbl_tipos),
    ) or []

    return [{"id": r.get("id"), "texto": r.get("texto") or str(r.get("id"))} for r in rows if r.get("id")]


def _listado(anio: int):
    return ejecutar_query(
        """
        SELECT
            p.idtbl_planificacion_turnos,
            p.fecha,
            p.idtbl_servicio_turno,
            p.idtbl_unidades_organizativas,
            p.cantidad_requerida,
            p.es_fecha_especial,
            p.motivo,
            p.comentarios,
            p.activo,
            s.servicios AS servicio_nombre,
            u.nombre AS unidad_nombre,
            t.nombre AS tipo_unidad_nombre
        FROM tbl_planificacion_turnos p
        LEFT JOIN tbl_servicios s ON s.idtbl_servicios = p.idtbl_servicios
        LEFT JOIN tbl_unidades_organizativas u ON u.idtbl_unidades_organizativas = p.idtbl_unidades_organizativas
        LEFT JOIN tbl_tipos_unidades_organizativas t ON t.idtbl_tipos_unidades_organizativas = p.idtbl_tipos_unidades_organizativas
        WHERE YEAR(p.fecha) = %s
        ORDER BY p.fecha DESC, p.idtbl_planificacion_turnos DESC
        """,
        (anio,),
    ) or []


@btn_planificacion_turno_bp.route("/", methods=["GET", "POST"], endpoint="planificacion_turnos")
@rol_required("super_admin")
@super_admin_accion(nombre="Planificacion de turno", modulo="modulo_calendario_policia_bp")
def planificacion_turnos():
    anio = _to_int(request.args.get("anio")) or date.today().year

    if request.method == "POST":
        fecha = request.form.get("fecha")
        idtbl_servicios = _to_int(request.form.get("idtbl_servicios"))
        idtbl_unidades = _to_int(request.form.get("idtbl_unidades_organizativas"))
        idtbl_tipos = _to_int(request.form.get("idtbl_tipos_unidades_organizativas"))
        idtbl_servicio_turno = _to_int(request.form.get("idtbl_servicio_turno"))
        cantidad = _to_int(request.form.get("cantidad_requerida")) or 1

        if not fecha or not idtbl_servicios or not idtbl_unidades or not idtbl_tipos:
            flash("Faltan campos obligatorios.", "error")
            return redirect(url_for("btn_planificacion_turno_bp.planificacion_turnos", anio=anio))

        ejecutar_non_query(
            """
            INSERT INTO tbl_planificacion_turnos
            (fecha, idtbl_servicios, idtbl_unidades_organizativas, idtbl_tipos_unidades_organizativas, idtbl_servicio_turno, cantidad_requerida, activo, created_at, updated_at)
            VALUES (%s,%s,%s,%s,%s,%s,1,NOW(),NOW())
            """,
            (fecha, idtbl_servicios, idtbl_unidades, idtbl_tipos, idtbl_servicio_turno, cantidad),
        )
        flash("Planificacion creada correctamente.", "success")
        return redirect(url_for("btn_planificacion_turno_bp.planificacion_turnos", anio=anio))

    planificaciones = _listado(anio)
    servicios, unidades_organizativas, tipos_unidades_organizativas, servicios_turno = _catalogos()

    return render_template(
        "calendario/policia/planificacion_turno.html",
        anio=anio,
        planificaciones=planificaciones,
        servicios=servicios,
        unidades_organizativas=unidades_organizativas,
        tipos_unidades_organizativas=tipos_unidades_organizativas,
        servicios_turno=servicios_turno,
    )


@btn_planificacion_turno_bp.route("/servicios-turno", methods=["GET"], endpoint="servicios_turno")
@rol_required("super_admin")
@super_admin_accion(nombre="Planificacion de turno", modulo="modulo_calendario_policia_bp")
def servicios_turno():
    idtbl_servicios = _to_int(request.args.get("idtbl_servicios"))
    idtbl_unidades = _to_int(request.args.get("idtbl_unidades_organizativas"))
    idtbl_tipos = _to_int(request.args.get("idtbl_tipos_unidades_organizativas"))

    return jsonify(_servicios_turno_filtrados(idtbl_servicios, idtbl_unidades, idtbl_tipos))


@btn_planificacion_turno_bp.route("/generar-excel", methods=["GET"], endpoint="generar_excel")
@rol_required("super_admin", "gestores")
def generar_excel():
    anio = _to_int(request.args.get("anio")) or date.today().year
    rows = _listado(anio)

    wb = Workbook()
    ws = wb.active
    ws.title = "planificaciones"

    ws.append(["id", "fecha", "servicio", "unidad_organizativa", "tipo_unidad", "id_servicio_turno", "cantidad", "especial", "motivo", "comentarios", "estado"])
    for r in rows:
        ws.append([
            r.get("idtbl_planificacion_turnos"),
            r.get("fecha").strftime("%Y-%m-%d") if r.get("fecha") else "",
            r.get("servicio_nombre") or "",
            r.get("unidad_nombre") or "",
            r.get("tipo_unidad_nombre") or "",
            r.get("idtbl_servicio_turno") or "",
            r.get("cantidad_requerida") or 0,
            "si" if r.get("es_fecha_especial") else "no",
            r.get("motivo") or "",
            r.get("comentarios") or "",
            "activa" if r.get("activo") else "inactiva",
        ])

    out = BytesIO()
    wb.save(out)
    out.seek(0)

    return send_file(
        out,
        as_attachment=True,
        download_name=f"planificacion_policia_{anio}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


bp = btn_planificacion_turno_bp
blueprint = btn_planificacion_turno_bp
