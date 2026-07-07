# views_contenedores.py (por ejemplo)

from flask import Blueprint, request, render_template, redirect, url_for, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os

from db import ejecutar_non_query
from utils_async import _ruta_pdf  # ya lo tienes en utils_async

bp_contenedores = Blueprint("contenedores", __name__)


@bp_contenedores.route("/contenedores/subir", methods=["GET", "POST"])
@login_required
def subir_contenedor():
    if request.method == "POST":
        f = request.files.get("pdf")
        if not f:
            # Aquí puedes devolver error amigable
            return render_template(
                "contenedores_subir.html",
                error="Debes seleccionar un PDF",
            )

        nombre_seguro = secure_filename(f.filename)
        if not nombre_seguro.lower().endswith(".pdf"):
            return render_template(
                "contenedores_subir.html",
                error="Solo se permiten ficheros PDF",
            )

        # 1️⃣ Guardar fichero en contenedores/entrada_pdf
        ruta_destino = _ruta_pdf("entrada_pdf", nombre_seguro)
        os.makedirs(os.path.dirname(ruta_destino), exist_ok=True)
        f.save(ruta_destino)

        # 2️⃣ Registrar quién lo ha subido
        #    Ajusta nombres de tabla/campos a tu esquema real
        ejecutar_non_query(
            """
            INSERT INTO tbl_contenedores_subidas (
                idtbl_usuarios,
                nombre_pdf,
                ruta_relativa,
                fecha_subida
            ) VALUES (%s, %s, %s, NOW())
            """,
            (
                current_user.id,  # ID del usuario logueado
                nombre_seguro,
                "entrada_pdf",
            ),
            nombre_bd="control_via_publica",
        )

        # 3️⃣ Opcional: lanzar procesado asíncrono o marcar para watcher
        # Por ahora, redirigimos al panel
        return redirect(url_for("contenedores.panel_mis_subidas"))

    # GET: mostrar formulario
    return render_template("contenedores_subir.html")
