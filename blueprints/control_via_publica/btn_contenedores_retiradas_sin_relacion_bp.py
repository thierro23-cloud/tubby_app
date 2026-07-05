# =============================================================================
# 🧱 BLUEPRINT · CONTENEDORES · RETIRADAS SIN RELACIÓN CON COLOCACIÓN
# =============================================================================
#
# 🎯 OBJETIVO
#   - Gestionar RETIRADAS que no se han podido relacionar automáticamente
#     con ninguna COLOCACIÓN a partir de los PDFs.
#   - Trabajar directamente sobre tbl_control_contenedores para:
#       · Listar solo contenedores SIN retirada (csv_retirada IS NULL).
#       · Filtrar por proveedor y por calle.
#       · Seleccionar manualmente el contenedor al que se le asigna la
#         retirada que vemos en el PDF.
#       · Completar manualmente los datos de RETIRADA y guardarlos.
#
# 🧩 RELACIÓN CON OTRAS PIEZAS
#   - BACKEND INDUSTRIAL (procesar_pdf_core):
#       · Marca estado="solo_retirada" cuando la retirada no se puede
#         vincular ni por número de solicitud ni por expediente.
#   - WATCHERS / ASYNC:
#       · Mueven esos PDFs a la carpeta solo_retirada.
#       · Tras completar aquí la retirada, el PDF puede ir a papelera
#         (por flujo async o acción posterior).
#
# 🚦 ALCANCE
#   - NO procesa PDFs ni hace OCR.
#   - NO mueve ficheros entre carpetas.
#   - SÍ:
#       · Consulta y actualiza tbl_control_contenedores.
#       · Renderiza una vista con:
#           · Visor de PDF de retirada (panel izquierdo).
#           · Filtros + selección de contenedor + formulario editable de
#             retirada (panel derecho).
# =============================================================================

# =============================================================================
# 1️⃣ IMPORTS Y REGISTRO DEL BLUEPRINT
# =============================================================================

from flask import Blueprint, render_template, request, redirect, url_for, flash
from pathlib import Path

from db import ejecutar_query

btn_contenedores_retiradas_sin_relacion_bp = Blueprint(
    "btn_contenedores_retiradas_sin_relacion_bp",
    __name__,
    url_prefix="/contenedores/retiradas_sin_relacion",
)


# =============================================================================
# 2️⃣ SQL BASE · PROVEEDORES, CALLES Y CONTENEDORES SIN RETIRADA
# =============================================================================
# IMPORTANTE:
#   - Todas las consultas trabajan siempre con c.csv_retirada IS NULL,
#     es decir, solo contenedores que aún NO tienen datos de retirada.
#   - Gracias a esto, el combo de proveedores de la plantilla ya viene
#     filtrado automáticamente: solo aparecen proveedores con contenedores
#     pendientes de retirada.
# =============================================================================

# 2.1) Proveedores que tienen contenedores sin retirada
SQL_PROVEEDORES_CON_SIN_RETIRADA = """
SELECT DISTINCT p.idtbl_proveedores, p.nombre_razon_social
FROM tbl_control_contenedores c
JOIN bd_tbl_comunes.tbl_proveedores p
  ON c.idtbl_proveedores = p.idtbl_proveedores
WHERE c.csv_retirada IS NULL
ORDER BY p.nombre_razon_social
"""

# 2.2) Calles de un proveedor con contenedores sin retirada
SQL_CALLES_POR_PROVEEDOR = """
SELECT DISTINCT c.idtbl_calles, ca.calles
FROM tbl_control_contenedores c
JOIN bd_tbl_comunes.tbl_calles ca
  ON c.idtbl_calles = ca.idtbl_calles
WHERE c.csv_retirada IS NULL
  AND c.idtbl_proveedores = %s
ORDER BY ca.calles
"""

# 2.3) Contenedores sin retirada según filtros proveedor/calle
SQL_CONTENEDORES_FILTRO = """
SELECT
    c.*,
    p.nombre_razon_social AS proveedor_nombre,
    ca.calles AS calle_nombre
FROM tbl_control_contenedores c
LEFT JOIN bd_tbl_comunes.tbl_proveedores p
  ON c.idtbl_proveedores = p.idtbl_proveedores
LEFT JOIN bd_tbl_comunes.tbl_calles ca
  ON c.idtbl_calles = ca.idtbl_calles
WHERE c.csv_retirada IS NULL
  AND (%s IS NULL OR c.idtbl_proveedores = %s)
  AND (%s IS NULL OR c.idtbl_calles = %s)
ORDER BY c.idtbl_control_contenedores
"""

# 2.4) UPDATE de datos de retirada para un contenedor
SQL_UPDATE_RETIRADA = """
UPDATE tbl_control_contenedores
SET
    csv_retirada = %s,
    fecha_retirada = %s,
    n_solicitud_retirada = %s,
    numero_expediente = %s,
    fecha_subida_retirada = CURDATE()
WHERE idtbl_control_contenedores = %s
"""


# =============================================================================
# 2️⃣ BIS · LISTADO DE PDFs DE RETIRADA SIN RELACIÓN
# =============================================================================
# - Esta parte NO toca BD, solo la carpeta donde los watchers han dejado
#   los PDFs marcados como "solo_retirada".
# - pdfs_dir: carpeta raíz de esos PDFs en el servidor.
# - Los nombres de archivo se ordenan alfabéticamente para tener un orden
#   determinista en las flechas Anterior / Siguiente.
# - La plantilla recibirá:
#       · pdf_urls  �?lista de URLs servibles (por ejemplo desde /static/...).
#       · pdf_pos   �?índice actual (0..n-1).
#       · pdf_url   �?URL del PDF actual o None si no hay PDFs.
# =============================================================================

# Ajusta esta ruta a donde tengas los PDFs de solo_retirada.
PDFS_DIR = Path("static/solo_retirada")


def _listar_pdfs_solo_retirada() -> list[Path]:
    """
    Devuelve la lista de PDFs de retirada 'sin relación' ordenados por nombre.
    Si la carpeta no existe, devuelve lista vacía.
    """
    if not PDFS_DIR.exists():
        return []
    return sorted(PDFS_DIR.glob("*.pdf"))


# =============================================================================
# 3️⃣ VISTA PRINCIPAL · GESTIÓN MANUAL DE RETIRADAS SIN RELACIÓN
# =============================================================================

@btn_contenedores_retiradas_sin_relacion_bp.route("/", methods=["GET", "POST"])
def btn_contenedores_retiradas_sin_relacion():
    """
    Vista tipo 'para_revision' pero trabajando en sentido inverso:

      1) Muestra, uno a uno, PDFs de retirada que no se han podido casar con
         ninguna colocación (carpeta solo_retirada).
      2) El usuario ve el PDF, identifica proveedor/calle/nº, y usa los
         filtros para localizar manualmente el contenedor colocado en
         tbl_control_contenedores (solo registros con csv_retirada IS NULL).
      3) Rellena manualmente los datos de retirada y los guarda en BD.
    """

    # -------------------------------------------------------------------------
    # 3.0) CONTROL DE NAVEGACIÓN DE PDFs (pdf_pos, pdf_nav)
    #   - pdf_pos: índice del PDF actual en la lista de PDFs pendientes.
    #   - pdf_nav: 'prev' o 'next' cuando se pulsan las flechas de PDF.
    # -------------------------------------------------------------------------
    pdfs = _listar_pdfs_solo_retirada()
    pdf_total = len(pdfs)

    # Posición actual de PDF desde querystring (GET)
    pdf_pos = request.values.get("pdf_pos", "0")
    try:
        pdf_pos = int(pdf_pos)
    except ValueError:
        pdf_pos = 0

    # Navegación entre PDFs vía GET: pdf_nav = 'prev' | 'next'
    pdf_nav = request.args.get("pdf_nav")
    if pdf_nav == "prev" and pdf_pos > 0:
        pdf_pos -= 1
    elif pdf_nav == "next" and pdf_pos + 1 < pdf_total:
        pdf_pos += 1

    # Normalizar pdf_pos dentro de rango
    if pdf_pos < 0:
        pdf_pos = 0
    if pdf_total > 0 and pdf_pos >= pdf_total:
        pdf_pos = pdf_total - 1

    # Determinar URL del PDF actual (si hay)
    if pdf_total > 0:
        pdf_actual = pdfs[pdf_pos]
        # Suponemos que PDFS_DIR cuelga de /static �?armamos URL relativa:
        #   static/solo_retirada/archivo.pdf
        pdf_url = url_for("static", filename=f"solo_retirada/{pdf_actual.name}")
    else:
        pdf_url = None

    # -------------------------------------------------------------------------
    # 3.1) Filtros proveedor / calle
    #   - Se leen desde querystring o formulario (request.values).
    #   - Son opcionales; se convierten a entero o None.
    # -------------------------------------------------------------------------
    proveedor_id = request.values.get("proveedor_id") or None
    calle_id = request.values.get("calle_id") or None
    try:
        proveedor_id_int = int(proveedor_id) if proveedor_id else None
    except ValueError:
        proveedor_id_int = None
    try:
        calle_id_int = int(calle_id) if calle_id else None
    except ValueError:
        calle_id_int = None

    # -------------------------------------------------------------------------
    # 3.2) Posición en listado de contenedores (cursor pos)
    #   - Índice del contenedor seleccionado dentro de la lista filtrada.
    #   - También se pasa por querystring y en formularios ocultos.
    # -------------------------------------------------------------------------
    pos_actual = request.values.get("pos", "0")
    try:
        pos_actual = int(pos_actual)
    except ValueError:
        pos_actual = 0

    # Tipo de acción POST sobre la vista:
    #   - 'guardar' �?guardar datos de retirada en BD.
    #   - 'navegar' �?moverse entre contenedores (opcional si mantienes flechas).
    accion = request.form.get("accion")  # 'navegar', 'guardar', None

    # -------------------------------------------------------------------------
    # 3.3) Guardar datos de retirada del contenedor actual (POST, accion=guardar)
    #   - Actualiza CSV, fecha, nº solicitud y expediente en tbl_control_contenedores.
    #   - Requiere idtbl_control_contenedores en el formulario.
    # -------------------------------------------------------------------------
    if request.method == "POST" and accion == "guardar":
        id_contenedor = request.form.get("idtbl_control_contenedores")
        csv_retirada = request.form.get("csv_retirada") or None
        fecha_retirada = request.form.get("fecha_retirada") or None   # YYYY-MM-DD
        n_solicitud_retirada = request.form.get("n_solicitud_retirada") or None
        numero_expediente = request.form.get("numero_expediente") or None

        if not id_contenedor:
            flash("Falta ID del contenedor para guardar los datos.", "error")
        else:
            ejecutar_query(
                SQL_UPDATE_RETIRADA,
                (
                    csv_retirada,
                    fecha_retirada,
                    n_solicitud_retirada,
                    numero_expediente,
                    id_contenedor,
                ),
                nombre_bd="control_via_publica",
            )
            flash(
                "Datos del contenedor actualizados correctamente. "
                "El PDF asociado ya puede pasar a papelera desde el flujo async.",
                "info",
            )

        # Tras guardar: recargar misma vista manteniendo pdf_pos y filtros
        return redirect(
            url_for(
                "btn_contenedores_retiradas_sin_relacion_bp."
                "btn_contenedores_retiradas_sin_relacion",
                pdf_pos=pdf_pos,
                proveedor_id=proveedor_id_int or "",
                calle_id=calle_id_int or "",
                pos=pos_actual,
            )
        )

    # -------------------------------------------------------------------------
    # 3.4) Datos para filtros (proveedores y calles)
    #   - Proveedores: YA vienen filtrados por csv_retirada IS NULL en SQL,
    #     así el combo muestra solo proveedores con contenedores pendientes.
    #   - Calles: solo se cargan cuando hay proveedor seleccionado.
    # -------------------------------------------------------------------------
    proveedores = ejecutar_query(
        SQL_PROVEEDORES_CON_SIN_RETIRADA,
        (),
        nombre_bd="control_via_publica",
    )

    calles = []
    if proveedor_id_int:
        calles = ejecutar_query(
            SQL_CALLES_POR_PROVEEDOR,
            (proveedor_id_int,),
            nombre_bd="control_via_publica",
        )

    # -------------------------------------------------------------------------
    # 3.5) Contenedores filtrados sin retirada
    #   - Lista de posibles contenedores candidatos a recibir la retirada
    #     de este PDF, según proveedor/calle.
    #   - El usuario elegirá en la plantilla cuál se considera "activo"
    #     mediante el índice pos_actual.
    # -------------------------------------------------------------------------
    contenedores = ejecutar_query(
        SQL_CONTENEDORES_FILTRO,
        (
            proveedor_id_int,
            proveedor_id_int,
            calle_id_int,
            calle_id_int,
        ),
        nombre_bd="control_via_publica",
    )

    total = len(contenedores)
    if total == 0:
        contenedor = None
        pos_actual = 0
    else:
        if pos_actual < 0:
            pos_actual = 0
        if pos_actual >= total:
            pos_actual = total - 1
        contenedor = contenedores[pos_actual]

    # -------------------------------------------------------------------------
    # 3.6) Navegación anterior / siguiente entre contenedores (OPCIONAL)
    #   - Si quieres mantener flechas internas además del selector de lista,
    #     puedes seguir usando 'accion = navegar' como antes.
    # -------------------------------------------------------------------------
    if request.method == "POST" and accion == "navegar":
        direccion = request.form.get("direccion")  # 'anterior' o 'siguiente'
        if direccion == "anterior" and pos_actual > 0:
            pos_actual -= 1
        elif direccion == "siguiente" and pos_actual + 1 < total:
            pos_actual += 1

        return redirect(
            url_for(
                "btn_contenedores_retiradas_sin_relacion_bp."
                "btn_contenedores_retiradas_sin_relacion",
                pdf_pos=pdf_pos,
                proveedor_id=proveedor_id_int or "",
                calle_id=calle_id_int or "",
                pos=pos_actual,
            )
        )

    # -------------------------------------------------------------------------
    # 3.7) Render de plantilla
    #   - Proveedores: solo con contenedores sin retirada.
    #   - Calles: dependientes del proveedor.
    #   - contenedores: lista filtrada, de la que uno es el "activo" (pos).
    #   - pdf_url, pdf_pos, pdf_total: control del visor de PDF de retirada.
    # -------------------------------------------------------------------------
    return render_template(
        "control_via_publica/contenedores/contenedores_retiradas_sin_relacion.html",
        proveedores=proveedores,
        calles=calles,
        contenedores=contenedores,
        contenedor=contenedor,
        pos=pos_actual,
        total=total,
        proveedor_id=proveedor_id_int,
        calle_id=calle_id_int,
        pdf_url=pdf_url,
        pdf_pos=pdf_pos,
        pdf_total=pdf_total,
    )