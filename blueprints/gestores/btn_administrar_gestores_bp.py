# coding: utf-8
from __future__ import annotations
from flask import (
    Blueprint,
    render_template,
    request,
    flash,
    redirect,
    url_for,
    session,
    abort,
)
from services.helpers import login_required, rol_required
from db import ejecutar_query, ejecutar_non_query
from blueprints.helpers.helpers_vias import cargar_provincias, cargar_tipos_via

btn_administrar_gestores_bp = Blueprint(
    "btn_administrar_gestores_bp", __name__, url_prefix="/gestores"
)


@btn_administrar_gestores_bp.route("/btn_administrar_gestores", methods=["GET", "POST"])
@login_required
@rol_required("super_admin")
def btn_administrar_gestores():
    if session.get("rol") != "super_admin":
        abort(403)

    if request.method == "POST":
        accion = request.form.get("accion")

        if accion == "nuevo_gestor":
            nombre = (request.form.get("nombre") or "").strip()
            apellido1 = (request.form.get("apellido1") or "").strip()
            apellido2 = (request.form.get("apellido2") or "").strip()
            email = (request.form.get("email") or "").strip()
            password = (request.form.get("password") or "").strip()
            dni = (request.form.get("DNI") or "").strip()
            telefono = (request.form.get("telefono") or "").strip()
            extension = (request.form.get("extension") or "").strip()
            numero_profesional = (request.form.get("numero_profesional") or "").strip()
            idtbl_provincias = request.form.get("idtbl_provincias") or None
            idtbl_municipios = request.form.get("idtbl_municipios") or None
            idtbl_tipos_de_vias = request.form.get("idtbl_tipos_de_vias") or None
            idtbl_calles = request.form.get("idtbl_calles") or None
            idtbl_roles = request.form.get("idtbl_roles")
            activo = 1 if request.form.get("activo") else 0
            must_change = 1 if request.form.get("must_change") else 0

            if not nombre or not email:
                flash("Nombre y email obligatorios", "error")
            elif not password:
                flash("Contrasena obligatoria", "error")
            else:
                ejecutar_non_query(
                    "INSERT INTO bd_tbl_comunes.tbl_gestores (nombre, apellido1, apellido2, email, password, DNI, telefono, extension, numero_profesional, idtbl_provincias, idtbl_municipios, idtbl_tipos_de_vias, idtbl_calles, idtbl_roles, activo, must_change, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())",
                    (
                        nombre,
                        apellido1,
                        apellido2,
                        email,
                        password,
                        dni,
                        telefono,
                        extension,
                        numero_profesional,
                        idtbl_provincias,
                        idtbl_municipios,
                        idtbl_tipos_de_vias,
                        idtbl_calles,
                        idtbl_roles,
                        activo,
                        must_change,
                    ),
                    "bd_tbl_comunes",
                )
                flash("Gestor creado", "success")

        elif accion == "editar_gestor":
            idtbl_gestores = request.form.get("idtbl_gestores")
            if idtbl_gestores:
                session["gestor_en_edicion"] = idtbl_gestores

        elif accion == "guardar_edicion":
            idtbl_gestores = request.form.get("idtbl_gestores")
            nombre = (request.form.get("nombre") or "").strip()
            apellido1 = (request.form.get("apellido1") or "").strip()
            apellido2 = (request.form.get("apellido2") or "").strip()
            email = (request.form.get("email") or "").strip()
            password = (request.form.get("password") or "").strip()
            dni = (request.form.get("DNI") or "").strip()
            telefono = (request.form.get("telefono") or "").strip()
            extension = (request.form.get("extension") or "").strip()
            numero_profesional = (request.form.get("numero_profesional") or "").strip()
            idtbl_provincias = request.form.get("idtbl_provincias") or None
            idtbl_municipios = request.form.get("idtbl_municipios") or None
            idtbl_tipos_de_vias = request.form.get("idtbl_tipos_de_vias") or None
            idtbl_calles = request.form.get("idtbl_calles") or None
            idtbl_roles = request.form.get("idtbl_roles")
            activo = 1 if request.form.get("activo") else 0
            must_change = 1 if request.form.get("must_change") else 0

            if password:
                ejecutar_non_query(
                    "UPDATE bd_tbl_comunes.tbl_gestores SET nombre=%s, apellido1=%s, apellido2=%s, email=%s, password=%s, DNI=%s, telefono=%s, extension=%s, numero_profesional=%s, idtbl_provincias=%s, idtbl_municipios=%s, idtbl_tipos_de_vias=%s, idtbl_calles=%s, idtbl_roles=%s, activo=%s, must_change=%s WHERE idtbl_gestores=%s",
                    (
                        nombre,
                        apellido1,
                        apellido2,
                        email,
                        password,
                        dni,
                        telefono,
                        extension,
                        numero_profesional,
                        idtbl_provincias,
                        idtbl_municipios,
                        idtbl_tipos_de_vias,
                        idtbl_calles,
                        idtbl_roles,
                        activo,
                        must_change,
                        idtbl_gestores,
                    ),
                    "bd_tbl_comunes",
                )
            else:
                ejecutar_non_query(
                    "UPDATE bd_tbl_comunes.tbl_gestores SET nombre=%s, apellido1=%s, apellido2=%s, email=%s, DNI=%s, telefono=%s, extension=%s, numero_profesional=%s, idtbl_provincias=%s, idtbl_municipios=%s, idtbl_tipos_de_vias=%s, idtbl_calles=%s, idtbl_roles=%s, activo=%s, must_change=%s WHERE idtbl_gestores=%s",
                    (
                        nombre,
                        apellido1,
                        apellido2,
                        email,
                        dni,
                        telefono,
                        extension,
                        numero_profesional,
                        idtbl_provincias,
                        idtbl_municipios,
                        idtbl_tipos_de_vias,
                        idtbl_calles,
                        idtbl_roles,
                        activo,
                        must_change,
                        idtbl_gestores,
                    ),
                    "bd_tbl_comunes",
                )
            flash("Actualizado", "success")
            session.pop("gestor_en_edicion", None)

        elif accion == "toggle_activo":
            idtbl_gestores = request.form.get("idtbl_gestores")
            estado_actual = request.form.get("estado_actual")
            nuevo_estado = "0" if estado_actual == "1" else "1"
            ejecutar_non_query(
                "UPDATE bd_tbl_comunes.tbl_gestores SET activo=%s WHERE idtbl_gestores=%s",
                (nuevo_estado, idtbl_gestores),
                "bd_tbl_comunes",
            )

        return redirect(url_for("btn_administrar_gestores_bp.btn_administrar_gestores"))

    gestores = ejecutar_query(
        "SELECT g.idtbl_gestores, g.nombre, g.apellido1, g.apellido2, g.email, g.password, g.created_at, g.idtbl_tipos_de_vias, g.idtbl_calles, g.idtbl_provincias, g.idtbl_municipios, g.DNI, g.telefono, g.extension, g.activo, g.idtbl_roles, g.numero_profesional, g.must_change, r.nombre AS nombre_rol FROM bd_tbl_comunes.tbl_gestores AS g LEFT JOIN bd_tbl_comunes.tbl_roles AS r ON g.idtbl_roles=r.idtbl_roles ORDER BY g.apellido1, g.apellido2, g.nombre",
        (),
        "bd_tbl_comunes",
    )

    roles = ejecutar_query(
        "SELECT idtbl_roles AS id, nombre AS nombre_rol FROM bd_tbl_comunes.tbl_roles ORDER BY nombre",
        (),
        "bd_tbl_comunes",
    )

    provincias = cargar_provincias()
    municipios = []
    tipos_via = cargar_tipos_via(texto="")
    calles = []
    gestor_edicion = None
    id_en_edicion = session.get("gestor_en_edicion")

    if id_en_edicion:
        filas = ejecutar_query(
            "SELECT idtbl_gestores, nombre, apellido1, apellido2, email, password, created_at, idtbl_tipos_de_vias, idtbl_calles, idtbl_provincias, idtbl_municipios, DNI, telefono, extension, activo, idtbl_roles, numero_profesional, must_change FROM bd_tbl_comunes.tbl_gestores WHERE idtbl_gestores=%s",
            (id_en_edicion,),
            "bd_tbl_comunes",
        )
        if filas:
            gestor_edicion = filas[0]
        else:
            session.pop("gestor_en_edicion", None)

    return render_template(
        "gestores/btn_administrar_gestores.html",
        gestores=gestores,
        roles=roles,
        gestor_edicion=gestor_edicion,
        provincias=provincias,
        municipios=municipios,
        tipos_via=tipos_via,
        calles=calles,
    )
