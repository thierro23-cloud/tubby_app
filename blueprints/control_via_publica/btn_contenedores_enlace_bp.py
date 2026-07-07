# ============================================================================
# 🚛 BLUEPRINT · ENLACE CONTENEDORES (COLOCACIÓN ↔ RETIRADA)
# ============================================================================
# OBJETIVO:
#   - Listar retiradas sin relación (tbl_contenedores_retirada.tiene_relacion = FALSE)
#   - Buscar colocación candidata (tbl_control_contenedores) por:
#       · Mismo idtbl_proveedores (NIF)
#       · Mismo idtbl_tipos_de_vias
#       · Mismo idtbl_calles
#       · Fecha más cercana (menor diferencia absoluta entre fecha_colocacion y fecha_retirada)
#   - Pantalla partida: PDF retirada (izq) | Formulario (centro) | PDF colocación (der)
#   - Vincular: insertar en tbl_relacion_colocacion_retirada + actualizar tiene_relacion
#
# ARQUITECTURA:
#   - ARCHIVO   : btn_contenedores_enlace_bp.py
#   - BLUEPRINT : btn_contenedores_enlace_bp
#   - PREFIJO   : /control_via_publica/contenedores/enlace
#   - PLANTILLA : control_via_publica/contenedores/contenedores_enlace.html
#
# RUTAS:
#   · "/"                               → btn_contenedores_enlace (listado retiradas sin relación)
#   · "/ver/<int:id_retirada>"          → ver_enlace (pantalla partida)
#   · "/candidata/<int:id_retirada>"    → buscar_candidata (AJAX → devuelve colocación candidata)
#   · "/vincular/<int:id_retirada>"     → vincular (POST → guarda relación)
#   · "/pdf/retirada/<int:id>/<path:filename>"   → pdf_retirada (servir PDF de solo_retirada)
#   · "/pdf/colocacion/<int:id>/<path:filename>" → pdf_colocacion (servir PDF de para_revision)
# ============================================================================

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
from services.helpers import login_required, rol_required
from flask_login import current_user
from datetime import date
import os

# ============================================================================
# 🧱 1. DEFINICIÓN DEL BLUEPRINT
# ============================================================================

btn_contenedores_enlace_bp = Blueprint(
    "btn_contenedores_enlace_bp",
    __name__,
    url_prefix="/control_via_publica/contenedores/enlace",
)

# ============================================================================
# 📄 2. SQL · CONSULTAS BASE
# ============================================================================

SQL_RETIRADAS_SIN_RELACION = """
SELECT 
    r.*,
    p.nombre_razon_social AS proveedor_nombre,
    p.nif AS proveedor_nif
FROM tbl_contenedores_retirada r
LEFT JOIN bd_tbl_comunes.tbl_proveedores p ON p.idtbl_proveedores = r.idtbl_proveedores
WHERE r.tiene_relacion = FALSE
ORDER BY r.fecha_retirada DESC, r.fecha_creacion DESC
"""

SQL_RETIRADA_POR_ID = """
SELECT 
    r.*,
    p.nombre_razon_social AS proveedor_nombre,
    p.nif AS proveedor_nif
FROM tbl_contenedores_retirada r
LEFT JOIN bd_tbl_comunes.tbl_proveedores p ON p.idtbl_proveedores = r.idtbl_proveedores
WHERE r.idtbl_contenedores_retirada = %s
"""

SQL_OBTENER_CANDIDATA_POR_ID = """
SELECT 
    c.idtbl_control_contenedores AS id_colocacion,
    c.fecha_colocacion,
    c.numero_expediente,
    c.numero_solicitud,
    c.csv,
    c.idtbl_proveedores,
    c.idtbl_tipos_de_vias,
    c.idtbl_calles,
    c.numero_portal,
    c.latitud,
    c.longitud,
    c.csv AS csv_instalacion,
    p.nombre_razon_social AS proveedor_nombre,
    p.nif AS proveedor_nif,
    tv.tipos_de_vias AS tipo_via_nombre,
    cl.calles AS calle_nombre,
    ABS(DATEDIFF(r.fecha_retirada, c.fecha_colocacion)) AS diferencia_dias
FROM tbl_control_contenedores c
LEFT JOIN bd_tbl_comunes.tbl_proveedores p ON p.idtbl_proveedores = c.idtbl_proveedores
LEFT JOIN bd_tbl_comunes.tbl_tipos_de_vias tv ON tv.idtbl_tipos_de_vias = c.idtbl_tipos_de_vias
LEFT JOIN bd_tbl_comunes.tbl_calles cl ON cl.idtbl_calles = c.idtbl_calles
INNER JOIN tbl_contenedores_retirada r ON r.idtbl_contenedores_retirada = %s
WHERE c.idtbl_proveedores = r.idtbl_proveedores
  AND c.idtbl_tipos_de_vias = r.idtbl_tipos_de_vias
  AND c.idtbl_calles = r.idtbl_calles
  AND c.fecha_retirada IS NULL
  AND c.idtbl_control_contenedores NOT IN (
      SELECT idtbl_contenedor_colocacion 
      FROM tbl_relacion_colocacion_retirada
  )
ORDER BY diferencia_dias ASC
LIMIT 1
"""

SQL_INSERT_RELACION = """
INSERT INTO tbl_relacion_colocacion_retirada (
    idtbl_contenedor_colocacion,
    idtbl_contenedor_retirada,
    fecha_vinculacion,
    idtbl_usuario
) VALUES (
    %s, %s, NOW(), %s
)
"""

SQL_UPDATE_RELAION_EN_TBL_RETIRADA = """
UPDATE tbl_contenedores_retirada
SET tiene_relacion = TRUE,
    idtbl_contenedor_colocacion = %s,
    fecha_validacion = NOW(),
    idtbl_usuario_validacion = %s
WHERE idtbl_contenedores_retirada = %s
"""
