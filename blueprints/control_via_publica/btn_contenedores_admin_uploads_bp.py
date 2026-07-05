# =============================================================================
# 📁 ARCHIVO: btn_contenedores_admin_uploads_bp.py
# =============================================================================
# Panel de administración para SUBIR PDFs de CONTENEDORES.
# =============================================================================

import os
import uuid

from flask import (
    Blueprint,
    request,
    jsonify,
    current_app,
    render_template,
    session,
    abort,
)
from services.helpers import login_required, rol_required

from db import ejecutar_non_query, ejecutar_query
from watchers.utils_async import procesar_pdf_entrada


# =============================================================================
# 1️⃣ DEFINICIÓN DEL BLUEPRINT
# =============================================================================

btn_contenedores_admin_uploads_bp = Blueprint(
    "btn_contenedores_admin_uploads_bp",
    __name__,
    url_prefix="/admin/contenedores",
)


# =============================================================================
# 2️⃣ FUNCIONES AUXILIARES
# =============================================================================

def _carpeta_entrada_contenedores() -> str:
    """
    Devuelve la ruta absoluta a contenedores/entrada_pdf
    dentro del root_path de la aplicación, creando la carpeta si no existe.
    """
    base = os.path.join(current_app.root_path, "contenedores")
    ruta = os.path.join(base, "entrada_pdf")
    os.makedirs(ruta, exist_ok=True)
    return ruta


def _nombre_guardado_seguro(nombre_original: str) -> str:
    """
    Genera un nombre físico seguro (UUID + extensión) para guardar el PDF.
    Si no hay extensión, se fuerza .pdf.
    """
    _, ext = os.path.splitext(nombre_original)
    if not ext:
        ext = ".pdf"
    return f"{uuid.uuid4().hex}{ext.lower()}"


def _actualizar_upload(
    id_upload: int,
    estado_proceso: str,
    detalle_error: str | None = None,
) -> None:
    """
    Actualiza estado_proceso, detalle_error y fecha_procesado
    de un registro en tbl_contenedores_uploads.
    """
    ejecutar_non_query(
        """
        UPDATE tbl_contenedores_uploads
        SET estado_proceso = %s,
            detalle_error = %s,
            fecha_procesado = NOW()
        WHERE idtbl_contenedores_uploads = %s
        """,
        (
            estado_proceso,
            detalle_error,
            id_upload,
        ),
        nombre_bd="control_via_publica",
    )


# =============================================================================
# 3️⃣ GET /admin/contenedores/uploads · FORMULARIO
# =============================================================================

@btn_contenedores_admin_uploads_bp.route("/uploads", methods=["GET"])
@login_required
@rol_required("gestor", "super_admin", "policia")  # ajusta roles si hace falta
def btn_contenedores_formulario_subida():
    """
    Muestra el formulario HTML para subir PDFs de contenedores.
    """
    return render_template("admin_contenedores_uploads.html")


# =============================================================================
# 4️⃣ POST /admin/contenedores/uploads · SUBIDA Y PROCESO
# =============================================================================

@btn_contenedores_admin_uploads_bp.route("/uploads", methods=["POST"])
@login_required
@rol_required("gestor", "super_admin", "policia")
def subir_pdf_contenedores():
    """
    Recibe uno o varios PDFs, los guarda en entrada_pdf,
    registra la subida en tbl_contenedores_uploads
    y lanza su procesamiento con procesar_pdf_entrada.
    """

    # Id del gestor logueado según tu sistema de auth (ver auth_bp.login)
    idtbl_gestor = session.get("idtbl_gestores")
    if not idtbl_gestor:
        # No debería ocurrir si login_required funciona, pero por seguridad:
        return jsonify({"error": "Sesión inválida o usuario no identificado"}), 403

    # Soportar tanto 'file' (un solo archivo) como 'files' (múltiples)
    if "files" not in request.files and "file" not in request.files:
        return jsonify({"error": "No se ha enviado ningún archivo"}), 400

    if "files" in request.files:
        archivos = request.files.getlist("files")
    else:
        archivos = [request.files["file"]]

    if not archivos:
        return jsonify({"error": "No se ha enviado ningún archivo"}), 400

    ruta_entrada = _carpeta_entrada_contenedores()
    resultados = []

    for fichero in archivos:
        nombre_original = fichero.filename or ""

        if not nombre_original:
            resultados.append(
                {"nombre_original": None, "error": "Archivo sin nombre"}
            )
            continue

        # Solo permitir PDFs
        if not nombre_original.lower().endswith(".pdf"):
            resultados.append(
                {
                    "nombre_original": nombre_original,
                    "error": "Solo se permiten archivos PDF",
                }
            )
            continue

        # Nombre físico seguro y ruta absoluta
        nombre_guardado = _nombre_guardado_seguro(nombre_original)
        ruta_abs = os.path.join(ruta_entrada, nombre_guardado)

        try:
            # 1) Guardar fichero en disco
            fichero.save(ruta_abs)

            # 2) Ruta relativa respecto a root_path (para almacenar en BD)
            ruta_relativa = os.path.relpath(
                ruta_abs,
                current_app.root_path,
            )

            # 3) Insertar registro de subida (estado PENDIENTE)
            ejecutar_non_query(
                """
                INSERT INTO tbl_contenedores_uploads (
                    nombre_original,
                    nombre_guardado,
                    ruta_relativa,
                    idtbl_gestor,
                    estado_proceso,
                    fecha_subida
                ) VALUES (%s, %s, %s, %s, 'PENDIENTE', NOW())
                """,
                (
                    nombre_original,
                    nombre_guardado,
                    ruta_relativa,
                    idtbl_gestor,
                ),
                nombre_bd="control_via_publica",
            )

            # 4) Obtener idtbl_contenedores_uploads recién insertado
            fila_id = ejecutar_query(
                "SELECT LAST_INSERT_ID() AS id",
                (),
                nombre_bd="control_via_publica",
            )[0]
            id_upload = fila_id["id"]

            # 5) Procesar el PDF con tu flujo actual
            try:
                resultado_proceso = procesar_pdf_entrada(nombre_guardado)
                estado_proceso = "OK"
                detalle_error = None
            except Exception as e:
                current_app.logger.error(
                    f"[UPLOAD_CONTENEDORES] Error procesando PDF {nombre_guardado}: {e!r}",
                    exc_info=True,
                )
                resultado_proceso = None
                estado_proceso = "ERROR"
                detalle_error = str(e)

            # 6) Actualizar estado del upload
            _actualizar_upload(
                id_upload=id_upload,
                estado_proceso=estado_proceso,
                detalle_error=detalle_error,
            )

            # 7) Añadir al resultado de la llamada
            resultados.append(
                {
                    "id_upload": id_upload,
                    "nombre_original": nombre_original,
                    "nombre_guardado": nombre_guardado,
                    "estado_proceso": estado_proceso,
                    "resultado_proceso": resultado_proceso,
                }
            )

        except Exception as e:
            current_app.logger.error(
                f"[UPLOAD_CONTENEDORES] Error guardando archivo {nombre_original}: {e!r}",
                exc_info=True,
            )
            resultados.append(
                {
                    "nombre_original": nombre_original,
                    "error": f"Error guardando archivo: {str(e)}",
                }
            )

    return jsonify({"resultados": resultados}), 200