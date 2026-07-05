from __future__ import annotations

from functools import wraps

from flask import Blueprint, abort, current_app, jsonify, render_template, request
from services.helpers import login_required, rol_required
from blueprints.helpers.helpers_vias import (
    cargar_calles,
    cargar_municipios,
    cargar_provincias,
    cargar_tipos_via,
    insertar_calle,
    insertar_municipio,
    insertar_tipo_via,
)

helpers_vias_bp = Blueprint("helpers_vias_bp", __name__, url_prefix="/helpers_vias")


def roles_required(*roles_permitidos):
    def wrapper(view_func):
        @login_required
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            rol_usuario = getattr(current_user, "rol", None)
            if rol_usuario not in roles_permitidos:
                abort(403)
            return view_func(*args, **kwargs)
        return wrapped_view
    return wrapper


@helpers_vias_bp.get("/provincias")
def api_provincias():
    q = request.args.get("q", "", type=str).strip()
    try:
        provincias = cargar_provincias()
        if q:
            provincias = [p for p in provincias if q.lower() in str(p.get("provincias", "")).lower()]
        return jsonify({"ok": True, "provincias": provincias})
    except Exception as exc:
        current_app.logger.exception("Error al cargar provincias")
        return jsonify({"ok": False, "error": str(exc)}), 500


@helpers_vias_bp.get("/municipios")
def api_municipios():
    id_provincia = request.args.get("id_provincia", type=int)
    q = request.args.get("q", "", type=str).strip()
    if not id_provincia:
        return jsonify({"ok": False, "error": "Falta id_provincia"}), 400
    try:
        municipios = cargar_municipios(id_provincia=id_provincia, texto=q)
        return jsonify({"ok": True, "municipios": municipios})
    except Exception as exc:
        current_app.logger.exception("Error al cargar municipios")
        return jsonify({"ok": False, "error": str(exc)}), 500


@helpers_vias_bp.get("/tipos_via")
def api_tipos_via():
    q = request.args.get("q", "", type=str).strip()
    try:
        tipos = cargar_tipos_via(texto=q)
        return jsonify({"ok": True, "tipos_via": tipos})
    except Exception as exc:
        current_app.logger.exception("Error al cargar tipos de vía")
        return jsonify({"ok": False, "error": str(exc)}), 500


@helpers_vias_bp.get("/calles")
def api_calles():
    id_municipio = request.args.get("id_municipio", type=int)
    id_tipo_via = request.args.get("id_tipo_via", type=int)
    q = request.args.get("q", "", type=str).strip()
    if not id_municipio or not id_tipo_via:
        return jsonify({"ok": False, "error": "Faltan id_municipio o id_tipo_via"}), 400
    try:
        calles = cargar_calles(id_municipio=id_municipio, id_tipo_via=id_tipo_via, texto=q)
        return jsonify({"ok": True, "calles": calles})
    except Exception as exc:
        current_app.logger.exception("Error al cargar calles")
        return jsonify({"ok": False, "error": str(exc)}), 500


@helpers_vias_bp.post("/crear_municipio")
@login_required
@rol_required("gestor", "super_admin")
def crear_municipio():
    data = request.get_json(silent=True) or request.form
    try:
        id_provincia = int(data.get("idtbl_provincias", 0))
    except (TypeError, ValueError):
        id_provincia = 0
    nombre_mun = (data.get("municipios") or "").strip()
    codigo_postal = (data.get("codigo_postal") or "").strip() or None
    if not id_provincia or not nombre_mun:
        return jsonify({"ok": False, "error": "Faltan idtbl_provincias o municipios"}), 400
    try:
        nuevo_id = insertar_municipio(id_provincia, nombre_mun, codigo_postal)
        return jsonify({
            "ok": True,
            "municipio": {
                "idtbl_municipios": nuevo_id,
                "idtbl_provincias": id_provincia,
                "municipios": nombre_mun,
            },
        }), 201
    except Exception as exc:
        current_app.logger.exception("Error al crear municipio")
        return jsonify({"ok": False, "error": str(exc)}), 500


@helpers_vias_bp.post("/crear_tipo_via")
@login_required
@rol_required("gestor", "super_admin")
def crear_tipo_via():
    data = request.get_json(silent=True) or request.form
    nombre_tipo = (data.get("tipos_de_vias") or "").strip()
    if not nombre_tipo:
        return jsonify({"ok": False, "error": "Falta tipos_de_vias"}), 400
    try:
        nuevo_id = insertar_tipo_via(nombre_tipo)
        return jsonify({
            "ok": True,
            "tipo_via": {
                "idtbl_tipos_de_vias": nuevo_id,
                "tipos_de_vias": nombre_tipo,
            },
        }), 201
    except Exception as exc:
        current_app.logger.exception("Error al crear tipo de vía")
        return jsonify({"ok": False, "error": str(exc)}), 500


@helpers_vias_bp.post("/crear_calle")
@login_required
@rol_required("gestor", "super_admin")
def crear_calle():
    data = request.get_json(silent=True) or request.form
    try:
        id_municipio = int(data.get("idtbl_municipios", 0))
    except (TypeError, ValueError):
        id_municipio = 0
    try:
        id_tipo_via = int(data.get("idtbl_tipos_de_vias", 0))
    except (TypeError, ValueError):
        id_tipo_via = 0
    nombre_calle = (data.get("calles") or "").strip()
    if not id_municipio or not id_tipo_via or not nombre_calle:
        return jsonify({"ok": False, "error": "Faltan idtbl_municipios, idtbl_tipos_de_vias o calles"}), 400
    try:
        nuevo_id = insertar_calle(id_municipio=id_municipio, id_tipo_via=id_tipo_via, nombre_calle=nombre_calle)
        return jsonify({
            "ok": True,
            "calle": {
                "idtbl_calles": nuevo_id,
                "idtbl_municipios": id_municipio,
                "idtbl_tipos_de_vias": id_tipo_via,
                "calles": nombre_calle,
            },
        }), 201
    except Exception as exc:
        current_app.logger.exception("Error al crear calle")
        return jsonify({"ok": False, "error": str(exc)}), 500


@helpers_vias_bp.get("/panel")
@login_required
@rol_required("gestor", "super_admin")
def formulario_helpers_vias():
    provincias = cargar_provincias()
    municipios = []  # ✅ VACÍO - Se cargan dinámicamente vía AJAX
    tipos_via = cargar_tipos_via(texto="")
    calles = []      # ✅ VACÍO - Se cargan dinámicamente vía AJAX
    
    return render_template(
        "helpers_vias/formulario_helpers_vias.html",
        provincias=provincias,
        municipios=municipios,
        tipos_via=tipos_via,
        calles=calles,
    )