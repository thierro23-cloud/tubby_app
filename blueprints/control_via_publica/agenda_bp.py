"""
blueprints/control_via_publica/agenda_bp.py

Vista principal de la agenda de vía pública.

Responsabilidades:
    1. Calcular rango de fechas según vista (día/semana/mes) y fecha de referencia.
    2. Gestionar navegación temporal (anterior/siguiente/hoy).
    3. Aplicar filtros de tipo de vía, calle y tipos de evento.
    4. Cargar eventos desde agenda_core.backend_agenda.
    5. Renderizar template con todos los datos necesarios.

Versión: 2.0.0 (Producción)
"""

from datetime import datetime, timedelta, date

from flask import Blueprint, render_template, request
from services.helpers import login_required, rol_required

from blueprints.helpers.helpers_vias import cargar_tipos_via, cargar_calles
from db import ejecutar_query

# Importar backend de agenda (comentado hasta tener la implementación completa)
# from agenda_core.backend_agenda import obtener_agenda_general

# Configuración
ID_MUNICIPIO_AVILA = 395


# =============================================================================
# 1. DEFINICIÓN DEL BLUEPRINT
# =============================================================================

agenda_bp = Blueprint(
    "agenda_bp",
    __name__,
    url_prefix="/control_via_publica/agenda",
)


# =============================================================================
# 2. FUNCIONES AUXILIARES
# =============================================================================

def calcular_rango_fechas(vista: str, fecha_ref: date) -> tuple:
    """
    Calcula el rango de fechas según la vista y fecha de referencia.
    
    Args:
        vista: "dia", "semana" o "mes"
        fecha_ref: Fecha base para el cálculo
        
    Returns:
        tuple: (fecha_desde, fecha_hasta, prev_ref, next_ref)
    """
    if vista == "dia":
        fecha_desde = datetime.combine(fecha_ref, datetime.min.time())
        fecha_hasta = datetime.combine(fecha_ref, datetime.max.time())
        prev_ref = fecha_ref - timedelta(days=1)
        next_ref = fecha_ref + timedelta(days=1)
        
    elif vista == "mes":
        primer_dia_mes = fecha_ref.replace(day=1)
        fecha_desde = datetime.combine(primer_dia_mes, datetime.min.time())
        
        # Calcular último día del mes correctamente
        if primer_dia_mes.month == 12:
            primer_dia_mes_siguiente = primer_dia_mes.replace(year=primer_dia_mes.year + 1, month=1)
        else:
            primer_dia_mes_siguiente = primer_dia_mes.replace(month=primer_dia_mes.month + 1)
        
        ultimo_dia_mes = primer_dia_mes_siguiente - timedelta(days=1)
        fecha_hasta = datetime.combine(ultimo_dia_mes, datetime.max.time())
        
        # Navegación mensual
        if primer_dia_mes.month == 1:
            prev_ref = primer_dia_mes.replace(year=primer_dia_mes.year - 1, month=12)
        else:
            prev_ref = primer_dia_mes.replace(month=primer_dia_mes.month - 1)
            
        next_ref = primer_dia_mes_siguiente
        
    else:  # semana (por defecto)
        # Calcular inicio de semana (lunes)
        dias_desde_lunes = fecha_ref.weekday()
        inicio_semana = fecha_ref - timedelta(days=dias_desde_lunes)
        fin_semana = inicio_semana + timedelta(days=6)
        
        fecha_desde = datetime.combine(inicio_semana, datetime.min.time())
        fecha_hasta = datetime.combine(fin_semana, datetime.max.time())
        
        prev_ref = inicio_semana - timedelta(days=7)
        next_ref = inicio_semana + timedelta(days=7)
    
    return fecha_desde, fecha_hasta, prev_ref, next_ref


def normalizar_calles(calles_raw: list, id_tipo_via_seleccionado: int = None) -> list:
    """
    NO hace nada, devuelve las calles tal como vienen de cargar_calles().
    
    El template agenda_principal.html espera:
        - idtbl_calles
        - calles
        - idtbl_tipos_de_vias (si existe)
    
    Args:
        calles_raw: Lista de calles desde cargar_calles()
        id_tipo_via_seleccionado: ID del tipo de vía (no usado)
        
    Returns:
        list: Misma lista sin cambios
    """
    return calles_raw

def normalizar_tipos_via(tipos_via_raw: list) -> list:
    """
    NO hace nada, devuelve los tipos tal como vienen.
    
    El template espera:
        - idtbl_tipos_de_vias
        - tipos_de_vias
    
    Args:
        tipos_via_raw: Lista desde cargar_tipos_via()
        
    Returns:
        list: Misma lista sin cambios
    """
    return tipos_via_raw# =============================================================================
# 3. RUTA PRINCIPAL
# =============================================================================

@agenda_bp.route("/")
@login_required
@rol_required("super_admin", "gestor")
def agenda_principal():
    """
    Vista principal de la agenda de vía pública.
    
    Query params:
        - vista: "dia" | "semana" | "mes" (default: "semana")
        - fecha_ref: YYYY-MM-DD (default: hoy)
        - id_tipo_via: int (filtro tipo de vía)
        - id_calle: int (filtro calle específica)
        - codigos_tipo: list[str] (tipos de evento seleccionados)
        
    Template context:
        - fecha_desde, fecha_hasta: Rango de fechas calculado
        - fecha_ref: Fecha base de navegación
        - prev_ref, next_ref: Fechas para navegación anterior/siguiente
        - filtros: Dict con todos los filtros activos
        - tipos_via: Lista de tipos de vía disponibles
        - calles: Lista de calles (filtradas por tipo si aplica)
        - tipos_evento: Lista de tipos de evento con colores
        - eventos: Lista de eventos en el rango (de agenda_core)
    """
    
    # -------------------------------------------------------------------------
    # 3.1 Procesar parámetros de entrada
    # -------------------------------------------------------------------------
    
    vista = request.args.get("vista", "semana").lower()
    if vista not in ["dia", "semana", "mes"]:
        vista = "semana"
    
    # Fecha de referencia
    fecha_ref_str = request.args.get("fecha_ref")
    if fecha_ref_str:
        try:
            fecha_ref = datetime.strptime(fecha_ref_str, "%Y-%m-%d").date()
        except ValueError:
            fecha_ref = date.today()
    else:
        fecha_ref = date.today()
    
    # Filtros
    id_tipo_via = request.args.get("id_tipo_via", type=int)
    id_calle = request.args.get("id_calle", type=int)
    codigos_tipo = request.args.getlist("codigos_tipo")
    
    # -------------------------------------------------------------------------
    # 3.2 Calcular rango de fechas
    # -------------------------------------------------------------------------
    
    fecha_desde, fecha_hasta, prev_ref, next_ref = calcular_rango_fechas(vista, fecha_ref)
    
    # -------------------------------------------------------------------------
    # 3.3 Cargar tipos de vía
    # -------------------------------------------------------------------------
    
    tipos_via_raw = cargar_tipos_via(texto="")
    tipos_via = normalizar_tipos_via(tipos_via_raw)
    
    # -------------------------------------------------------------------------
    # 3.4 Cargar calles (solo si hay tipo de vía seleccionado)
    # -------------------------------------------------------------------------
    
    if id_tipo_via:
        calles_raw = cargar_calles(
            id_municipio=ID_MUNICIPIO_AVILA,
            id_tipo_via=id_tipo_via,
            texto="",
        )
        calles = normalizar_calles(calles_raw, id_tipo_via)
    else:
        calles = []
    
    # -------------------------------------------------------------------------
    # 3.5 Cargar tipos de evento
    # -------------------------------------------------------------------------
    
    tipos_evento_raw = ejecutar_query(
        """
        SELECT
            idtbl_tipos_evento,
            codigo,
            nombre_publico,
            color_hex
        FROM tbl_tipos_evento_via_publica
        ORDER BY nombre_publico
        """,
        (),
        nombre_bd="control_via_publica",
    )
    
    tipos_evento = [
        {
            "codigo": t["codigo"],
            "nombre_publico": t["nombre_publico"] or t["codigo"],
            "color_hex": t["color_hex"] or "#64748b",
        }
        for t in tipos_evento_raw
    ]
    
    # -------------------------------------------------------------------------
    # 3.6 Cargar eventos (desde agenda_core)
    # -------------------------------------------------------------------------
    
    # TODO: Descomentar cuando agenda_core esté completamente implementado
    """
    from agenda_core.backend_agenda import obtener_agenda_general
    
    try:
        if codigos_tipo:
            eventos = obtener_agenda_general(
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                codigos_tipo=codigos_tipo
            )
        else:
            eventos = obtener_agenda_general(
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta
            )
        
        # Filtrar por calle si está seleccionada
        if id_calle:
            eventos = [e for e in eventos if e.get("idtbl_calles") == id_calle]
            
    except Exception as e:
        current_app.logger.error(f"Error cargando eventos de agenda: {e}", exc_info=True)
        eventos = []
    """
    
    # Mientras tanto, lista vacía
    eventos = []
    
    # -------------------------------------------------------------------------
    # 3.7 Preparar contexto de filtros
    # -------------------------------------------------------------------------
    
    filtros = {
        "vista": vista,
        "id_tipo_via": id_tipo_via,
        "id_calle": id_calle,
        "codigos_tipo": codigos_tipo,
    }
    
    # -------------------------------------------------------------------------
    # 3.8 Renderizar template
    # -------------------------------------------------------------------------
    
    return render_template(
        "super_admin/agenda.html",
        fecha_desde=fecha_desde.strftime("%d/%m/%Y"),
        fecha_hasta=fecha_hasta.strftime("%d/%m/%Y"),
        fecha_ref=fecha_ref.strftime("%Y-%m-%d"),
        prev_ref=prev_ref.strftime("%Y-%m-%d"),
        next_ref=next_ref.strftime("%Y-%m-%d"),
        filtros=filtros,
        tipos_via=tipos_via,
        calles=calles,
        tipos_evento=tipos_evento,
        eventos=eventos,
    )