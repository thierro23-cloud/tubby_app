# blueprints/comunes/btn_ubicacion_calles_bp.py
# =============================================================================
# 🧭 BOTÓN UBICACIÓN · CALLES DE ESPAÑA
# =============================================================================
# RESPONSABILIDADES:
#   - Mostrar un panel para mantener calles (catálogo nacional) que luego
#     usarán proveedores, usuarios, etc.
#   - Usar los helpers JSON:
#       · helpers_vias_bp.api_provincias
#       · helpers_vias_bp.api_municipios
#       · helpers_vias_bp.api_tipos_via
#       · helpers_vias_bp.api_calles
#       · helpers_vias_bp.crear_calle
#   - Permitir altas de calles SIEMPRE ligadas a provincia, municipio y tipo de vía.
#   - Recordar desde qué panel se ha abierto (super_admin, gestores, etc.)
#     para poder volver con un botón “Volver” sin usar el atrás del navegador.
# =============================================================================

from flask import Blueprint, render_template, request, url_for
from services.helpers import login_required, rol_required

btn_ubicacion_calles_bp = Blueprint(
    "btn_ubicacion_calles_bp",
    __name__,
    url_prefix="/ubicacion/calles",
)


@btn_ubicacion_calles_bp.route("/", methods=["GET"])
@login_required
@rol_required("gestor", "super_admin", "policia")
def btn_ubicacion_calles():
    """
    🧭 PANEL DE MANTENIMIENTO DE CALLES.

    - Visible desde paneles que desees (super_admin, gestores, policías...).
    - No mete lógica de BD propia: delega en helpers_vias_bp para
      catálogos y altas de calles vía JSON.
    - Recibe un parámetro GET opcional 'origen' para saber a qué panel
      devolver al usuario con el botón “Volver”.
    """

    # Origen puede venir como nombre de endpoint o alias simple
    origen = request.args.get("origen", "").strip() or None

    # Mapeo sencillo de alias → endpoint real
    # Ajusta estos nombres a tus endpoints de panel reales
    mapa_origen = {
        "super_admin": "super_admin_bp.super_admin",
        "panel_gestores": "panel_gestores_bp.panel_gestores",
        "panel_policias": "panel_policias_bp.panel_policias",
    }

    # Si nos pasan directamente el endpoint completo, lo usamos tal cual.
    # Si nos pasan alias (“super_admin”), lo traducimos con mapa_origen.
    endpoint_destino = None
    if origen:
        if origen in mapa_origen:
            endpoint_destino = mapa_origen[origen]
        else:
            # Asumimos que han pasado un endpoint válido
            endpoint_destino = origen

    # Construimos la URL de vuelta si tenemos endpoint
    url_volver = url_for(endpoint_destino) if endpoint_destino else None

    return render_template(
        "comunes/ubicacion_calles.html",
        url_volver=url_volver,
        origen=origen,
    )