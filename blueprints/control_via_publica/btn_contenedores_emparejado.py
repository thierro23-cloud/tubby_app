# =============================================================================
# 🧱 BLUEPRINT · CONTENEDORES · EMPAREJADO AUTOMÁTICO DE RETIRADAS
# =============================================================================
#
# Realizado por: Tinito
# Fecha: 06/07/2026
#
# 🎯 OBJETIVO
#   - Ejecutar el proceso automático de emparejado entre PDFs de RETIRADA
#     pendientes y COLOCACIONES existentes en tbl_control_contenedores.
#   - Centralizar en un blueprint independiente la acción automática de:
#       · Volcar PDFs de static/solo_retirada a tbl_contenedores_retirada.
#       · Ejecutar el motor profesional de emparejado.
#       · Limpiar retiradas ya emparejadas.
#       · Eliminar PDFs físicos correspondientes.
#
# 🧩 RELACIÓN CON OTRAS PIEZAS
#   - BLUEPRINT DE RETIRADAS SIN RELACIÓN:
#       · Muestra los PDFs pendientes y permite resolverlos manualmente.
#   - SERVICE DE EMPAREJADO:
#       · Contiene la lógica real de negocio.
#       · Evita que el blueprint dependa de watchers.utils_async.
#   - BASE DE DATOS:
#       · Usa tbl_contenedores_retirada como tabla auxiliar.
#       · Usa tbl_control_contenedores como tabla principal de control.
#
# 🚦 ALCANCE
#   - NO renderiza la pantalla manual.
#   - NO procesa PDFs ni hace OCR.
#   - NO debe contener lógica pesada de negocio.
#   - SÍ:
#       · Coordina el flujo automático completo.
#       · Lanza el motor de emparejado.
#       · Devuelve resumen mediante flash.
# =============================================================================

from pathlib import Path
from datetime import datetime

from flask import Blueprint, redirect, url_for, flash, session
from flask_login import current_user

from services.helpers import login_required
from db import ejecutar_query
from services.control_via_publica.contenedores_emparejado_service import (
    emparejar_retiradas_con_colocaciones,
)


btn_contenedores_emparejado_bp = Blueprint(
    "btn_contenedores_emparejado_bp",
    __name__,
    url_prefix="/contenedores/emparejado",
)


# =============================================================================
# 📁 CONFIGURACIÓN DE RUTAS Y CARPETAS
# =============================================================================

PDFS_DIR = Path("static/solo_retirada")


# =============================================================================
# 📄 LISTADO DE PDFS PENDIENTES DE RETIRADA
# =============================================================================

def _listar_pdfs_solo_retirada() -> list[Path]:
    """
    Devuelve la lista de PDFs pendientes de retirada ubicados en
    static/solo_retirada.

    Returns:
        list[Path]: Lista ordenada de archivos PDF encontrados.
    """
    if not PDFS_DIR.exists():
        return []

    return sorted(PDFS_DIR.glob("*.pdf"))


# =============================================================================
# 🗃️ SQL · VOLCADO Y LIMPIEZA DE RETIRADAS
# =============================================================================

SQL_INSERT_RETIRADA_DESDE_SOLO = """
INSERT INTO tbl_contenedores_retirada (
    ruta_pdf,
    nombre_pdf,
    origen,
    fecha_subida,
    estado
)
VALUES (%s, %s, %s, %s, %s)
"""

SQL_SELECT_RETIRADAS_EMPAREJADAS = """
SELECT idtbl_contenedores_retirada, ruta_pdf, nombre_pdf
FROM tbl_contenedores_retirada
WHERE estado = 'emparejada'
"""

SQL_DELETE_RETIRADA = """
DELETE FROM tbl_contenedores_retirada
WHERE idtbl_contenedores_retirada = %s
"""


# =============================================================================
# ⬆️ VOLCADO DE PDFS A TABLA AUXILIAR
# =============================================================================

def volcar_pdfs_solo_retirada_a_tabla() -> dict:
    """
    Inserta en tbl_contenedores_retirada todos los PDFs existentes en
    static/solo_retirada.

    Cada PDF se registra con:
        - origen = 'solo_retirada'
        - estado = 'solo_retirada'

    Returns:
        dict: Resumen del volcado realizado.
    """
    pdfs = _listar_pdfs_solo_retirada()
    hoy = datetime.now().date()

    insertados = 0

    for pdf_path in pdfs:
        ruta_relativa = f"solo_retirada/{pdf_path.name}"
        nombre_pdf = pdf_path.name

        ejecutar_query(
            SQL_INSERT_RETIRADA_DESDE_SOLO,
            (
                ruta_relativa,
                nombre_pdf,
                "solo_retirada",
                hoy,
                "solo_retirada",
            ),
            nombre_bd="control_via_publica",
        )

        insertados += 1

    return {
        "total_pdfs": len(pdfs),
        "insertados": insertados,
    }


# =============================================================================
# 🧹 LIMPIEZA DE RETIRADAS EMPAREJADAS
# =============================================================================

def borrar_retiradas_emparejadas_y_pdfs() -> dict:
    """
    Borra las retiradas marcadas como emparejadas y elimina sus PDFs físicos.

    Flujo:
        1. Busca filas con estado = 'emparejada'.
        2. Borra dichas filas de tbl_contenedores_retirada.
        3. Elimina el PDF físico correspondiente de static/solo_retirada.

    Returns:
        dict: Resumen de limpieza en base de datos y sistema de archivos.
    """
    retiradas = ejecutar_query(
        SQL_SELECT_RETIRADAS_EMPAREJADAS,
        (),
        nombre_bd="control_via_publica",
    )

    borrados_bd = 0
    borrados_fs = 0

    for retirada in retiradas or []:
        retirada_id = retirada["idtbl_contenedores_retirada"]
        ruta_pdf = retirada["ruta_pdf"]

        ejecutar_query(
            SQL_DELETE_RETIRADA,
            (retirada_id,),
            nombre_bd="control_via_publica",
        )
        borrados_bd += 1

        pdf_path = PDFS_DIR / Path(ruta_pdf).name

        try:
            if pdf_path.exists():
                pdf_path.unlink()
                borrados_fs += 1
        except OSError:
            pass

    return {
        "borrados_bd": borrados_bd,
        "borrados_fs": borrados_fs,
    }


# =============================================================================
# 👤 OBTENCIÓN DEL USUARIO LOGUEADO
# =============================================================================

def _obtener_id_usuario_logueado():
    """
    Obtiene el identificador del gestor actualmente autenticado.

    Primero intenta obtenerlo desde current_user y, si no está disponible,
    lo busca en session.

    Returns:
        int | None: ID del gestor logueado o None si no se encuentra.
    """
    id_usuario_logueado = getattr(current_user, "idtbl_gestores", None)

    if id_usuario_logueado is None:
        id_usuario_logueado = session.get("idtbl_gestores")

    return id_usuario_logueado


# =============================================================================
# 🔁 RUTA PRINCIPAL · EMPAREJADO AUTOMÁTICO
# =============================================================================

@btn_contenedores_emparejado_bp.route("/", methods=["GET"])
@login_required
def btn_contenedores_emparejado():
    """
    Ejecuta el proceso completo de emparejado automático.

    Pasos:
        1. Obtiene el usuario logueado.
        2. Vuelca PDFs pendientes a tbl_contenedores_retirada.
        3. Ejecuta el motor de emparejado.
        4. Borra retiradas emparejadas y PDFs físicos.
        5. Redirige a la vista manual de retiradas sin relación.
    """
    id_usuario_logueado = _obtener_id_usuario_logueado()

    if not id_usuario_logueado:
        flash(
            "No se pudo obtener el id del gestor actual; no se ejecuta el emparejado.",
            "danger",
        )
        return redirect(
            url_for(
                "btn_contenedores_retiradas_sin_relacion_bp."
                "btn_contenedores_retiradas_sin_relacion"
            )
        )

    resumen_volcado = volcar_pdfs_solo_retirada_a_tabla()

    resumen_emparejado = emparejar_retiradas_con_colocaciones(
        id_usuario_logueado
    )

    resumen_borrado = borrar_retiradas_emparejadas_y_pdfs()

    flash(
        "Emparejado automático ejecutado. "
        f"Volcado: {resumen_volcado['insertados']} de "
        f"{resumen_volcado['total_pdfs']} PDFs cargados. "
        f"Emparejado: total={resumen_emparejado.get('total_retiradas', 0)}, "
        f"emparejadas={resumen_emparejado.get('emparejadas', 0)}, "
        f"sin_match={resumen_emparejado.get('sin_match', 0)}. "
        f"Limpieza: retiradas borradas={resumen_borrado['borrados_bd']}, "
        f"PDFs eliminados={resumen_borrado['borrados_fs']}.",
        "success",
    )

    return redirect(
        url_for(
            "btn_contenedores_retiradas_sin_relacion_bp."
            "btn_contenedores_retiradas_sin_relacion"
        )
    )