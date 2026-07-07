# ============================================================================
# 🚛 1️⃣ MÓDULO · CONTENEDORES - LISTAR PENDIENTES (ARQUITECTURA NUEVA)
# ============================================================================
# 🧠 EMPIEZA INTRODUCCIÓN GENERAL
# ----------------------------------------------------------------------------
# (1.1) DESCRIPCIÓN GENERAL
#   (1.1.1) Gestiona el flujo de VALIDACIÓN MANUAL de CONTENEDORES PENDIENTES
#           detectados automáticamente desde PDF.
#   (1.1.2) Se integra en la arquitectura:
#           - PANEL  → panel_control_via_publica_bp  (control_via_publica)
#           - MÓDULO → modulo_control_via_publica_contenedores_bp
#                      (control_via_publica_contenedores)
#           - BOTÓN  → ESTE BLUEPRINT:
#               · btn_contenedores_listar_pendientes
#                   → workflow secuencial uno a uno (pantalla partida PDF|Form).
#               · serve_pdf
#                   → visualización del PDF original (mitad izquierda).
#               · calles_por_tipo
#                   → AJAX para combos dependientes (tipo vía → calles).
#               · guardar_validacion
#                   → inserción en control + eliminación de pendientes.
#
# (1.2) ARQUITECTURA TÉCNICA
#   (1.2.1) ARCHIVO   : btn_contenedores_listar_pendientes_bp.py
#   (1.2.2) BLUEPRINT : btn_contenedores_listar_pendientes_bp
#   (1.2.3) PREFIJO   : /control_via_publica/contenedores/pendientes
#   (1.2.4) PLANTILLA : control_via_publica/contenedores/contenedores_listar_pendientes.html
#   (1.2.5) RUTAS:
#           · "/"                           → btn_contenedores_listar_pendientes
#                                            (workflow uno a uno).
#           · "/pdf/<int:id_pendiente>/<path:filename>" → serve_pdf
#                                            (visor PDF en iframe).
#           · "/calles_por_tipo/<int:id_tipo>"          → calles_por_tipo
#                                            (AJAX para combo de calles).
#           · "/guardar/<int:id>"                       → guardar_validacion
#                                            (POST de formulario pro).
#
# (1.3) OBJETIVO DE DISEÑO DE UI (pantalla partida):
#   (1.3.1) MITAD IZQUIERDA
#           - IFRAME con PDF original de la solicitud.
#           - Cabecera con nombre del fichero.
#   (1.3.2) MITAD DERECHA
#           - Formulario “limpio pro” con bloques:
#               · Proveedor / Solicitante (NIF + Teléfono en la misma fila).
#               · Datos administrativos (expediente, solicitud, colocación...).
#               · Fechas en filas ordenadas (instalación, colocación, retirada,
#                 firma, subida PDFs...).
#               · Ubicación: Tipo de vía, Calle, Lat/Long, precisión, calidad,
#                 origen.
#               · Contenedor: dimensión, gestor.
#               · CSV instalación / retirada.
#               · Observaciones.
#   (1.3.3) WORKFLOW UNO A UNO:
#           - Navegación con índice `i` (0..N-1).
#           - Guardar → insertar en control, borrar pendiente y pasar al
#             siguiente (o quedarse en posición lógica).
#
# (1.4) INTEGRACIÓN CON LISTADO POR CARPETAS (vista bandejas)
#   - Desde la vista de carpetas puedes entrar al workflow haciendo clic en:
#       · "Abrir en validador" → envía:
#             · id_pendiente : ID del registro clicado en la tabla.
#             · carpeta      : carpeta actual (para_revision, solo_retirada, ...).
#             · i=0 (placeholder, se recalcula).
#   - Este módulo:
#       · Si recibe id_pendiente + carpeta:
#           1. Calcula el índice `i` real de ese pendiente dentro de la
#              bandeja (ruta_pdf = carpeta) ordenada por fecha_creacion.
#           2. Carga exactamente ese PDF en la pantalla partida.
#       · A partir de ahí, toda la navegación Anterior/Siguiente se mantiene
#         dentro de esa carpeta.
#   - Si no se recibe carpeta ni id_pendiente:
#       · Se comporta como antes (workflow clásico sobre todos los pendientes).
# ----------------------------------------------------------------------------
# 🧠 TERMINA INTRODUCCIÓN GENERAL
# ============================================================================


# ============================================================================
# 📦 2️⃣ IMPORTS Y CONFIGURACIÓN BÁSICA DEL MÓDULO
# ============================================================================

import json
import os
from datetime import date

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
    send_from_directory,
    current_app,
    flash,
    abort,
    session,
)
from db import ejecutar_query, ejecutar_non_query
from services.helpers import login_required, rol_required  # Tus decoradores
from flask_login import current_user

# ============================================================================
# 🧠 2️⃣ BIS · LÓGICA DE AÑO DE EXPEDIENTE (BACKEND)
# ============================================================================


def resolver_anio_expediente(valor_anio_form: str | None) -> int:
    """
    Resuelve el año del expediente según la fecha actual y las reglas:

    - Fuera de enero:
        · Devuelve siempre el año actual, ignore lo que venga del formulario.
    - En enero:
        · Acepta solo dos valores desde la UI:
            · año actual
            · año anterior
        · Cualquier otro valor o error se normaliza a año actual.
    """
    hoy = date.today()
    anio_actual = hoy.year

    if hoy.month != 1:
        return anio_actual

    if valor_anio_form:
        try:
            anio = int(valor_anio_form)
            if anio in (anio_actual, anio_actual - 1):
                return anio
        except ValueError:
            pass

    return anio_actual


# ============================================================================
# 🧱 3️⃣ DEFINICIÓN DEL BLUEPRINT · CONTENEDORES PENDIENTES
# ============================================================================

btn_contenedores_listar_pendientes_bp = Blueprint(
    "btn_contenedores_listar_pendientes_bp",
    __name__,
    url_prefix="/control_via_publica/contenedores/pendientes",
)

# ============================================================================
# 🧠 4️⃣ CONSULTAS SQL · CAPA DE DATOS REUTILIZABLE
# ============================================================================

SQL_PENDIENTE = """
SELECT *
FROM tbl_contenedores_pendientes
WHERE idtbl_contenedores_pendientes = %s
"""

SQL_PROVEEDORES = """
SELECT idtbl_proveedores, nombre_razon_social, nif
FROM tbl_proveedores
WHERE coloca_contenedores = 1
ORDER BY nombre_razon_social
"""

SQL_TIPOS_VIA = """
SELECT idtbl_tipos_de_vias, tipos_de_vias
FROM bd_tbl_comunes.tbl_tipos_de_vias
ORDER BY tipos_de_vias
"""

SQL_CALLES = """
SELECT idtbl_calles, calles
FROM bd_tbl_comunes.tbl_calles
WHERE idtbl_municipios = 395
ORDER BY calles
"""

SQL_CALLES_TIPO = """
SELECT idtbl_calles, calles
FROM bd_tbl_comunes.tbl_calles
WHERE idtbl_municipios = 395
  AND idtbl_tipos_de_vias = %s
ORDER BY calles
"""

SQL_DIMENSIONES = """
SELECT idtbl_dimensiones, descripcion
FROM bd_tbl_comunes.tbl_dimensiones
ORDER BY descripcion
"""

SQL_GESTORES = """
SELECT idtbl_gestores, nombre
FROM bd_tbl_comunes.tbl_gestores
ORDER BY nombre
"""

SQL_INSERT_CONTROL = """
/* Comentario largo… (idéntico al que ya tenías) */
INSERT INTO tbl_control_contenedores (
    idtbl_proveedores,
    nombre_solicitante,
    nif,
    telefono,
    fecha_colocacion,
    fecha_retirada,
    fecha_firma_inicial,
    idtbl_dimensiones,
    observaciones,
    idtbl_tipos_de_vias,
    idtbl_calles,
    numero_portal,
    csv,
    csv_retirada,
    numero_solicitud,
    numero_expediente,
    anio_expediente,
    n_solicitud_retirada,
    latitud,
    longitud,
    precision_gps,
    gps_nivel_calidad,
    gps_origen,
    fecha_subida_instalacion,
    idtbl_gestor_subida
) VALUES (
    %(idtbl_proveedores)s,
    %(nombre_solicitante)s,
    %(nif)s,
    %(telefono)s,
    %(fecha_colocacion)s,
    %(fecha_retirada)s,
    %(fecha_firma_inicial)s,
    %(idtbl_dimensiones)s,
    %(observaciones)s,
    %(idtbl_tipos_de_vias)s,
    %(idtbl_calles)s,
    %(numero_portal)s,
    %(csv)s,
    %(csv_retirada)s,
    %(numero_solicitud)s,
    %(numero_expediente)s,
    %(anio_expediente)s,
    %(n_solicitud_retirada)s,
    %(latitud)s,
    %(longitud)s,
    %(precision_gps)s,
    %(gps_nivel_calidad)s,
    %(gps_origen)s,
    NOW(),
    %(idtbl_gestor_subida)s
)
"""

# ============================================================================
# 📄 5️⃣ SERVIR PDF ORIGINAL · VISOR MITAD IZQUIERDA
# ============================================================================


@btn_contenedores_listar_pendientes_bp.route("/pdf/<int:id_pendiente>/<path:filename>")
@login_required
@rol_required("gestor", "super_admin")
def serve_pdf(id_pendiente, filename):
    rows = ejecutar_query(
        """
        SELECT ruta_pdf, nombre_pdf
        FROM tbl_contenedores_pendientes
        WHERE idtbl_contenedores_pendientes = %s
        """,
        (id_pendiente,),
        nombre_bd="control_via_publica",
    )

    if not rows:
        current_app.logger.error(
            f"[SERVE_PDF] Pendiente {id_pendiente} no encontrado en tbl_contenedores_pendientes"
        )
        abort(404)

    pendiente = rows[0]
    subcarpeta = pendiente["ruta_pdf"] or "para_revision"
    nombre_pdf = pendiente["nombre_pdf"]

    carpeta_base = os.path.join(current_app.root_path, "contenedores")
    carpeta = os.path.join(carpeta_base, subcarpeta)

    current_app.logger.info(
        f"[SERVE_PDF] Sirviendo PDF para pendiente {id_pendiente}: {carpeta}/{nombre_pdf}"
    )

    return send_from_directory(
        carpeta,
        nombre_pdf,
        mimetype="application/pdf",
    )


# ============================================================================
# 🔁 6️⃣ LISTADO SECUENCIAL · WORKFLOW UNO A UNO (PDF | FORM)
# ============================================================================


@btn_contenedores_listar_pendientes_bp.route("/", methods=["GET"])
@login_required
@rol_required("gestor", "super_admin")
def btn_contenedores_listar_pendientes():
    """
    🔁 Navegación secuencial de contenedores pendientes (pantalla partida).
    Soporta:
    - flujo clásico (?i=N sobre todos),
    - flujo por bandejas (?carpeta=...),
    - entrada directa desde listado de carpetas (?id_pendiente=...&carpeta=...).
    """
    # (6.3.0) Carpeta lógica opcional (para_revision, solo_retirada, ...)
    carpeta = request.args.get("carpeta") or None
    filtrar_por_carpeta = bool(carpeta)

    # (6.3.0.bis) id_pendiente opcional: si viene desde el listado de carpetas, lo usamos
    id_pendiente_click = request.args.get("id_pendiente", type=int)

    # (6.3.1) Índice actual (si viene ya calculado)
    indice = request.args.get("i", type=int)

    # (6.3.1.bis) Si viene id_pendiente y NO hay índice, calculamos la posición real
    if indice is None and id_pendiente_click is not None:
        if filtrar_por_carpeta:
            row = ejecutar_query(
                """
                SELECT COUNT(*) AS pos
                FROM tbl_contenedores_pendientes
                WHERE ruta_pdf = %s
                  AND fecha_creacion < (
                      SELECT fecha_creacion
                      FROM tbl_contenedores_pendientes
                      WHERE idtbl_contenedores_pendientes = %s
                  )
                """,
                (carpeta, id_pendiente_click),
                nombre_bd="control_via_publica",
            )[0]
        else:
            row = ejecutar_query(
                """
                SELECT COUNT(*) AS pos
                FROM tbl_contenedores_pendientes
                WHERE fecha_creacion < (
                    SELECT fecha_creacion
                    FROM tbl_contenedores_pendientes
                    WHERE idtbl_contenedores_pendientes = %s
                )
                """,
                (id_pendiente_click,),
                nombre_bd="control_via_publica",
            )[0]
        indice = row["pos"]

    # (6.3.1.ter) Si no viene índice o es negativo → ir a 0
    if indice is None or indice < 0:
        return redirect(
            url_for(
                "btn_contenedores_listar_pendientes_bp.btn_contenedores_listar_pendientes",
                i=0,
                carpeta=carpeta,
            ),
            code=303,
        )

    # (6.3.2) Número total de pendientes
    if filtrar_por_carpeta:
        total_rows = ejecutar_query(
            "SELECT COUNT(*) AS total FROM tbl_contenedores_pendientes WHERE ruta_pdf = %s",
            (carpeta,),
            nombre_bd="control_via_publica",
        )[0]["total"]
    else:
        total_rows = ejecutar_query(
            "SELECT COUNT(*) AS total FROM tbl_contenedores_pendientes",
            (),
            nombre_bd="control_via_publica",
        )[0]["total"]

    # (6.3.2.bis) Si NO hay pendientes, plantilla vacía
    if total_rows == 0:
        flash("No hay contenedores pendientes de validación.", "info")
        return render_template(
            "control_via_publica/contenedores/contenedores_listar_pendientes.html",
            pendiente=None,
            datos={},
            proveedores=[],
            tipos_vias=[],
            calles=[],
            dimensiones=[],
            gestores=[],
            indice=0,
            id_pendiente=None,
            total_pendientes=0,
            anio_actual=date.today().year,
            carpeta_actual=carpeta,
            url_back_carpetas=url_for(
                "btn_contenedores_listar_carpetas_bp.btn_contenedores_listar_carpetas",
                carpeta=carpeta or "para_revision",
            ),
        )

    # (6.3.3) Corregir índice si se pasa del último
    if indice >= total_rows:
        indice = max(total_rows - 1, 0)

    # (6.3.4) Obtener el pendiente N‑ésimo ordenado por fecha_creacion
    if filtrar_por_carpeta:
        resultado = ejecutar_query(
            """
            SELECT *
            FROM tbl_contenedores_pendientes
            WHERE ruta_pdf = %s
            ORDER BY fecha_creacion ASC
            LIMIT 1 OFFSET %s
            """,
            (carpeta, indice),
            nombre_bd="control_via_publica",
        )
    else:
        resultado = ejecutar_query(
            """
            SELECT *
            FROM tbl_contenedores_pendientes
            ORDER BY fecha_creacion ASC
            LIMIT 1 OFFSET %s
            """,
            (indice,),
            nombre_bd="control_via_publica",
        )

    pendiente = resultado[0]

    # (6.3.5) Parseo del JSON con datos extraídos (si lo hay)
    datos = {}
    if pendiente.get("datos_extraidos_json"):
        try:
            datos = json.loads(pendiente["datos_extraidos_json"])
        except Exception:
            datos = {}

        # Parseo del JSON con datos extraídos (si lo hay)
    datos = {}
    if pendiente.get("datos_extraidos_json"):
        try:
            datos = json.loads(pendiente["datos_extraidos_json"])
        except Exception:
            datos = {}

    # Normalizar CSVs: en carpeta solo_retirada tratamos el CSV del PDF como retirada
    if pendiente.get("ruta_pdf") == "solo_retirada":
        csv_pdf = pendiente.get("csv")
        csv_retirada_json = datos.get("csv_retirada")

        # Si el JSON no trae csv_retirada, usamos csv como retirada
        if csv_pdf and not csv_retirada_json:
            datos["csv_retirada"] = csv_pdf

        # En retiradas puras NO queremos prellenar csv instalación, aunque venga en JSON
        datos["csv"] = ""

    # (6.3.6) Rellenar datos con claves por defecto esperadas en la plantilla
    campos_defecto = {
        "nombre_solicitante": "",
        "nif": "",
        "telefono": "",
        "numero_expediente": "",
        "numero_solicitud": "",
        "n_solicitud_retirada": "",
        "fecha_colocacion": "",
        "fecha_retirada": "",
        "fecha_firma_inicial": "",
        "fecha_subida_instalacion": "",
        "fecha_subida_retirada": "",
        "idtbl_tipos_de_vias": None,
        "idtbl_calles": None,
        "latitud": "",
        "longitud": "",
        "precision_gps": "",
        "gps_nivel_calidad": "",
        "gps_origen": "direccion_pdf",
        "idtbl_dimensiones": None,
        "idtbl_gestores": None,
        "csv": "",
        "csv_retirada": "",
        "observaciones": "",
        "idtbl_proveedores": None,
        "numero_portal": "",
    }
    for k, v in campos_defecto.items():
        datos.setdefault(k, v)

    # (6.3.7) Carga de combos auxiliares
    proveedores = ejecutar_query(SQL_PROVEEDORES, (), "bd_tbl_comunes")
    tipos_vias = ejecutar_query(SQL_TIPOS_VIA, (), "bd_tbl_comunes")
    calles = ejecutar_query(SQL_CALLES, (), "bd_tbl_comunes")
    dimensiones = ejecutar_query(SQL_DIMENSIONES, (), "bd_tbl_comunes")
    gestores = ejecutar_query(SQL_GESTORES, (), "bd_tbl_comunes")

    # (6.3.7.bis) Contexto temporal para la UI (año actual)
    hoy = date.today()
    anio_actual = hoy.year

    # (6.3.8) Renderizado de la plantilla única
    carpeta_actual = carpeta or pendiente.get("ruta_pdf")

    return render_template(
        "control_via_publica/contenedores/contenedores_listar_pendientes.html",
        pendiente=pendiente,
        datos=datos,
        proveedores=proveedores,
        tipos_vias=tipos_vias,
        calles=calles,
        dimensiones=dimensiones,
        gestores=gestores,
        indice=indice,
        id_pendiente=pendiente["idtbl_contenedores_pendientes"],
        total_pendientes=total_rows,
        anio_actual=anio_actual,
        carpeta_actual=carpeta_actual,
        url_back_carpetas=url_for(
            "btn_contenedores_listar_carpetas_bp.btn_contenedores_listar_carpetas",
            carpeta=carpeta_actual,
        ),
    )


# ============================================================================
# 🌐 7️⃣ AJAX · CALLES POR TIPO DE VÍA
# ============================================================================


@btn_contenedores_listar_pendientes_bp.route("/calles_por_tipo/<int:id_tipo>")
@login_required
@rol_required("gestor", "super_admin")
def calles_por_tipo(id_tipo):
    return jsonify(ejecutar_query(SQL_CALLES_TIPO, (id_tipo,), "bd_tbl_comunes"))


# ============================================================================
# ✅ 8️⃣ GUARDAR VALIDACIÓN · INSERCIÓN + ELIMINACIÓN + SALTO
# ============================================================================


@btn_contenedores_listar_pendientes_bp.route("/guardar/<int:id>", methods=["POST"])
@login_required
@rol_required("gestor", "super_admin")
def guardar_validacion(id):
    indice_actual = request.args.get("i", default=0, type=int)
    carpeta = request.args.get("carpeta") or None

    numero_expediente_raw = request.form.get("numero_expediente")
    numero_expediente = numero_expediente_raw.strip() if numero_expediente_raw else None
    anio_expediente_form = request.form.get("anio_expediente")
    anio_expediente = resolver_anio_expediente(anio_expediente_form)

    if numero_expediente is None:
        flash("Debes indicar un número de expediente.", "warning")
        return redirect(
            url_for(
                "btn_contenedores_listar_pendientes_bp.btn_contenedores_listar_pendientes",
                i=indice_actual,
                carpeta=carpeta,
            )
        )

    if "user_id" not in session:
        current_app.logger.error(
            "[guardar_validacion] sesión sin user_id; revisa flujo de login"
        )
        abort(401, "Debes iniciar sesión para validar contenedores")

    idtbl_gestor_subida = session["user_id"]

    datos_insert = {
        "idtbl_contenedores_pendientes": id,
        "idtbl_proveedores": request.form.get("idtbl_proveedores") or None,
        "nombre_solicitante": request.form.get("nombre_solicitante") or None,
        "nif": request.form.get("nif") or None,
        "telefono": request.form.get("telefono") or None,
        "fecha_colocacion": request.form.get("fecha_colocacion") or None,
        "fecha_retirada": request.form.get("fecha_retirada") or None,
        "fecha_firma_inicial": request.form.get("fecha_firma_inicial") or None,
        "idtbl_dimensiones": request.form.get("idtbl_dimensiones") or None,
        "observaciones": request.form.get("observaciones") or None,
        "idtbl_tipos_de_vias": request.form.get("idtbl_tipos_de_vias") or None,
        "idtbl_calles": request.form.get("idtbl_calles") or None,
        "numero_portal": request.form.get("numero_portal") or None,
        "csv": request.form.get("csv") or None,
        "csv_retirada": request.form.get("csv_retirada") or None,
        "numero_solicitud": request.form.get("numero_solicitud") or None,
        "numero_expediente": numero_expediente,
        "anio_expediente": anio_expediente,
        "n_solicitud_retirada": request.form.get("n_solicitud_retirada") or None,
        "latitud": request.form.get("latitud") or None,
        "longitud": request.form.get("longitud") or None,
        "precision_gps": request.form.get("precision_gps") or None,
        "gps_nivel_calidad": request.form.get("gps_nivel_calidad") or None,
        "gps_origen": request.form.get("gps_origen") or None,
        "idtbl_gestor_subida": idtbl_gestor_subida,
    }

    ejecutar_non_query(
        SQL_INSERT_CONTROL,
        datos_insert,
        nombre_bd="control_via_publica",
    )

    ejecutar_non_query(
        """
        DELETE FROM tbl_contenedores_pendientes
        WHERE idtbl_contenedores_pendientes = %s
        """,
        (id,),
        nombre_bd="control_via_publica",
    )

    flash("Contenedor validado y guardado en control correctamente", "success")

    siguiente_indice = indice_actual
    return redirect(
        url_for(
            "btn_contenedores_listar_pendientes_bp.btn_contenedores_listar_pendientes",
            i=siguiente_indice,
            carpeta=carpeta,
        )
    )
