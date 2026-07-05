#============================================================================
# 📂 1️⃣ MÓDULO · CONTENEDORES - LISTAR POR CARPETAS
#============================================================================
# (1.1) OBJETIVO
# - Vista tipo “encabezado de carpetas” para revisar de un vistazo
#   qué hay en cada carpeta lógica:
#     · para_revision
#     · pendientes_validacion
#     · solo_retirada
#     · papelera (opcional, solo lectura).
# - Desde aquí puedes:
#     · cambiar de carpeta con un <select>.
#     · ver una tabla de pendientes (id, csv, estado, motivo, fechas).
#     · saltar al workflow uno-a-uno
#       (btn_contenedores_listar_pendientes_bp.btn_contenedores_listar_pendientes)
#       directamente sobre un id concreto.
#
# (1.2) ARQUITECTURA
# - ARCHIVO   : btn_contenedores_listar_carpetas_bp.py
# - BLUEPRINT : btn_contenedores_listar_carpetas_bp
# - PREFIJO   : /control_via_publica/contenedores/carpetas
# - PLANTILLA : control_via_publica/contenedores/contenedores_listar_carpetas.html
# - RUTAS:
#   · "/" → btn_contenedores_listar_carpetas  (GET) listado filtrado por carpeta.
#
# (1.3) DOS VÍAS DE ENTRADA AL WORKFLOW
# - VÍA A (clásica, ya existente, NO se toca):
#     · /control_via_publica/contenedores/pendientes/?i=0
#     · Blueprint: btn_contenedores_listar_pendientes_bp
#     · Vista    : btn_contenedores_listar_pendientes
#     · Plantilla: contenedores_listar_pendientes.html
#
# - VÍA B (nueva, este módulo):
#     · /control_via_publica/contenedores/carpetas/?carpeta=para_revision
#     · Desde aquí:
#         · seleccionas carpeta en un <select>.
#         · ves la tabla de pendientes de esa carpeta.
#         · puedes entrar al mismo workflow uno-a-uno con un enlace.
#
# - Si por cualquier motivo la VÍA B falla (por ejemplo error SQL en este
#   módulo), la VÍA A sigue funcionando porque es un blueprint distinto
#   que no se modifica.
#
# (1.4) LÓGICA ESPECÍFICA DE CSV / CSV_RETIRADA EN EL LISTADO
# - En la tabla de carpetas queremos distinguir claramente:
#     · CSV instalación  → columna "CSV".
#     · CSV retirada     → columna "CSV retirada".
# - Regla adicional para carpeta "solo_retirada":
#     · Si en BD llegan csv y csv_retirada con el mismo valor, significa que
#       en la práctica solo tenemos CSV de retirada.
#     · En ese caso el backend fuerza csv_instalacion = None para que la
#       columna "CSV" aparezca vacía y solo se muestre el CSV de retirada
#       en la tabla, evitando duplicidad visual.
#============================================================================


#============================================================================
# 2️⃣ IMPORTS
#============================================================================
import json
from datetime import date

from flask import (
    Blueprint,
    render_template,
    request,
    url_for,
    current_app,
)
from db import ejecutar_query
from services.helpers import login_required, rol_required


#============================================================================
# 3️⃣ DEFINICIÓN DEL BLUEPRINT
#============================================================================

btn_contenedores_listar_carpetas_bp = Blueprint(
    "btn_contenedores_listar_carpetas_bp",
    __name__,
    url_prefix="/control_via_publica/contenedores/carpetas",
)


#============================================================================
# 4️⃣ CONSTANTES / CONFIG
#============================================================================

# Carpetas lógicas que vamos a exponer en el selector
CARPETAS_PERMITIDAS = [
    "colocacion",
    "entrada_pdf",
    "para_revision",
    "pendientes_validacion",
    "solo_retirada",
    "papelera",
]


#============================================================================
# 5️⃣ HELPERS
#============================================================================

def _resolver_carpeta_desde_request() -> str:
    """
    Lee ?carpeta=... de la querystring y devuelve una carpeta válida.
    Si no viene o no es válida, usa 'para_revision' por defecto.
    """
    carpeta = request.args.get("carpeta", "").strip()
    if carpeta not in CARPETAS_PERMITIDAS:
        return "para_revision"
    return carpeta


#============================================================================
# 6️⃣ RUTA PRINCIPAL · LISTAR PENDIENTES POR CARPETA
#============================================================================

@btn_contenedores_listar_carpetas_bp.route("/", methods=["GET"])
@login_required
@rol_required("gestor", "super_admin")
def btn_contenedores_listar_carpetas():
    """
    📂 Listado de pendientes agrupados por carpeta (ruta_pdf).

    - Muestra un <select> de carpeta lógica.
    - Lista los registros de tbl_contenedores_pendientes con esa ruta_pdf.
    - Normaliza los CSV de instalación/retirada para que en la carpeta
      solo_retirada no se dupliquen en la tabla.
    - Permite saltar al workflow uno-a-uno de un id concreto.
    """
    # (6.1) Resolver carpeta desde la querystring (con validación)
    carpeta = _resolver_carpeta_desde_request()

    # (6.2) Consultar pendientes de esa carpeta
    try:
        pendientes = ejecutar_query(
            """
            SELECT
                idtbl_contenedores_pendientes       AS id,
                nombre_pdf,
                ruta_pdf,
                csv,
                csv_retirada,
                estado,
                motivo,
                fecha_creacion,
                datos_extraidos_json
            FROM tbl_contenedores_pendientes
            WHERE ruta_pdf = %s
            ORDER BY fecha_creacion ASC
            """,
            (carpeta,),
            nombre_bd="control_via_publica",
        )
    except Exception as e:
        current_app.logger.error(
            "[LISTAR_CARPETAS] Error consultando pendientes para carpeta %s: %r",
            carpeta,
            e,
        )
        pendientes = []

    # (6.3) Transformar resultados en lista de filas para la plantilla
    filas = []
    for row in pendientes:
        datos = {}
        if row.get("datos_extraidos_json"):
            try:
                datos = json.loads(row["datos_extraidos_json"])
            except Exception:
                datos = {}

        # (6.3.1) Normalización de CSVs para la tabla
        csv_instalacion = row.get("csv")
        csv_retirada = row.get("csv_retirada")

        # Regla: en solo_retirada, si csv y csv_retirada son iguales,
        # consideramos que NO hay CSV de instalación y lo dejamos vacío.
        if carpeta == "solo_retirada" and csv_retirada and csv_instalacion == csv_retirada:
            csv_instalacion = None

        filas.append(
            {
                "id": row["id"],
                "nombre_pdf": row["nombre_pdf"],
                "ruta_pdf": row["ruta_pdf"],
                "csv": csv_instalacion,
                "csv_retirada": csv_retirada,
                "estado": row.get("estado"),
                "motivo": row.get("motivo"),
                "fecha_creacion": row.get("fecha_creacion"),
                "numero_expediente": datos.get("numero_expediente"),
                "numero_solicitud": datos.get("numero_solicitud"),
                "nombre_solicitante": datos.get("nombre_solicitante"),
            }
        )

    # (6.4) Contexto temporal
    hoy = date.today()
    anio_actual = hoy.year

    # (6.5) Log de control
    current_app.logger.info(
        "[LISTAR_CARPETAS] Carpeta=%s, num_pendientes=%s",
        carpeta,
        len(filas),
    )

    # (6.6) Render de la plantilla de bandejas
    return render_template(
        "control_via_publica/contenedores/contenedores_listar_carpetas.html",
        carpeta=carpeta,
        carpetas_permitidas=CARPETAS_PERMITIDAS,
        filas=filas,
        anio_actual=anio_actual,
        url_workflow_pendientes=url_for(
            "btn_contenedores_listar_pendientes_bp.btn_contenedores_listar_pendientes"
        ),
    )