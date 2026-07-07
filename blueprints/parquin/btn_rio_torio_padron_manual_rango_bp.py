# =============================================================================
# 📄 0️⃣ INICIO · BOTÓN INDEPENDIENTE · PADRÓN MANUAL RIO_TORIO (RANGO)
# =============================================================================
"""
Este blueprint define el botón que permite generar el padrón de Rio Torío
indicando un rango de fechas manualmente (fecha_inicio, fecha_fin).

- Ruta principal:
    /parquin/rio_torio/btn_rio_torio_padron_manual_rango
- Métodos soportados:
    GET  → muestra formulario con dos <input type="date">
    POST → valida las fechas, genera el informe y devuelve un .docx

Requisitos:
- Usuario autenticado (login_required).
- Rol con permiso: "gestor" o "super_admin" (rol_required).
"""

from __future__ import annotations

from datetime import datetime

from flask import (
    Blueprint,
    request,
    render_template,
    redirect,
    url_for,
    flash,
    current_app,
    send_file,
)

from services.helpers import login_required, rol_required

# =============================================================================
# 1️⃣ DEFINICIÓN DEL BLUEPRINT
# =============================================================================
# Variable de blueprint: btn_rio_torio_padron_manual_rango_bp
# Nombre interno (para url_for): "btn_rio_torio_padron_manual_rango_bp"
# Prefijo de URL: /parquin/rio_torio
#
# Esto hará que la ruta completa de la vista sea, por ejemplo:
#   /parquin/rio_torio/btn_rio_torio_padron_manual_rango
# y el endpoint:
#   "btn_rio_torio_padron_manual_rango_bp.btn_rio_torio_padron_manual_rango"
btn_rio_torio_padron_manual_rango_bp = Blueprint(
    "btn_rio_torio_padron_manual_rango_bp",
    __name__,
    url_prefix="/parquin/rio_torio",
)


# =============================================================================
# 2️⃣ FUNCIÓN INTERNA · GENERAR INFORME WORD POR RANGO MANUAL
# =============================================================================


def _generar_informe_word_rango(fecha_inicio, fecha_fin):
    """
    Genera el informe de padrón Rio Torío usando un rango manual.

    Parámetros:
        - fecha_inicio (date): fecha de inicio del periodo.
        - fecha_fin    (date): fecha de fin del periodo.

    Retorna:
        - Path absoluto del fichero .docx generado.

    NOTA:
        - Implementar aquí la lógica real de generación del documento,
          similar a _generar_informe_word() pero usando fecha_inicio y
          fecha_fin en lugar de calcular el mes anterior.
    """
    # TODO: Implementar lógica real de generación del documento.
    raise NotImplementedError(
        "Implementar _generar_informe_word_rango(fecha_inicio, fecha_fin)."
    )


# =============================================================================
# 3️⃣ VISTA DEL BOTÓN · PADRÓN MANUAL RIO_TORIO (RANGO)
# =============================================================================
# OJO: aquí usamos SIEMPRE la variable real del blueprint:
#       btn_rio_torio_padron_manual_rango_bp
# para evitar el NameError que te daba antes.


@btn_rio_torio_padron_manual_rango_bp.route(
    "/btn_rio_torio_padron_manual_rango",
    methods=["GET", "POST"],
)
@login_required
@rol_required("gestor", "super_admin")
def btn_rio_torio_padron_manual_rango():
    """
    BOTÓN · Generar padrón Rio Torío (rango manual).

    - GET  → muestra formulario con inputs type="date".
    - POST → valida rango, genera informe y muestra mensajes flash.
    """
    # -------------------------------------------------------------------------
    # Petición POST → procesar el formulario y generar el informe
    # -------------------------------------------------------------------------
    if request.method == "POST":
        # Leemos las fechas como cadenas
        fecha_inicio_str = request.form.get("fecha_inicio", "").strip()
        fecha_fin_str = request.form.get("fecha_fin", "").strip()

        # Intentamos parsear a objetos date
        try:
            fecha_inicio = datetime.strptime(fecha_inicio_str, "%Y-%m-%d").date()
            fecha_fin = datetime.strptime(fecha_fin_str, "%Y-%m-%d").date()
        except ValueError:
            flash(
                "Fechas inválidas. Usa el selector de fecha.",
                "danger",
            )
            # Volvemos al propio formulario de rango manual
            return redirect(
                url_for(
                    "btn_rio_torio_padron_manual_rango_bp."
                    "btn_rio_torio_padron_manual_rango"
                )
            )

        # Validamos el orden de las fechas
        if fecha_fin < fecha_inicio:
            flash(
                "La fecha fin no puede ser anterior a la fecha inicio.",
                "warning",
            )
            return redirect(
                url_for(
                    "btn_rio_torio_padron_manual_rango_bp."
                    "btn_rio_torio_padron_manual_rango"
                )
            )

        # Intentamos generar el informe
        try:
            ruta = _generar_informe_word_rango(fecha_inicio, fecha_fin)
            nombre = getattr(ruta, "name", str(ruta))

            # Mensaje de éxito
            flash(
                f"Padrón generado correctamente: {nombre}",
                "success",
            )

            # Devolver el Word generado para descarga/apertura
            return send_file(
                ruta,
                as_attachment=True,
                download_name=nombre,
                mimetype=(
                    "application/vnd.openxmlformats-officedocument."
                    "wordprocessingml.document"
                ),
            )
        except NotImplementedError as e:
            current_app.logger.error(
                f"_generar_informe_word_rango no implementado: {e}"
            )
            flash(
                "Funcionalidad de padrón manual (rango) aún no implementada.",
                "danger",
            )
        except Exception as e:
            current_app.logger.error(
                f"Error generando padrón Rio Torío manual (rango): {e}"
            )
            flash(
                "Error generando el informe de padrón (manual, rango).",
                "danger",
            )

        # Si hubo error, volvemos al propio formulario de rango manual
        return redirect(
            url_for(
                "btn_rio_torio_padron_manual_rango_bp."
                "btn_rio_torio_padron_manual_rango"
            )
        )

    # -------------------------------------------------------------------------
    # Petición GET → mostrar formulario de selección de fechas
    # -------------------------------------------------------------------------
    # Puedes reutilizar la misma plantilla que el botón manual normal
    # o una específica para rango, según lo que tengas creado.
    return render_template("parquin/rio_torio/rio_torio_padron_manual.html")
