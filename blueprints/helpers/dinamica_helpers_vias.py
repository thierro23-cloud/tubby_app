# ============================================================================
# 🌐 API DINÁMICA HELPERS VIAS
# ============================================================================

@helpers_vias_bp.route('/api/municipios/<int:provincia_id>')
@login_required
def api_municipios(provincia_id):
    municipios = Municipio.query.filter_by(idtbl_provincias=provincia_id).all()

    return jsonify([
        {"id": m.id, "nombre": m.nombre}
        for m in municipios
    ])


@helpers_vias_bp.route('/api/calles/<int:municipio_id>')
@login_required
def api_calles(municipio_id):
    calles = Calle.query.filter_by(idtbl_municipios=municipio_id).all()

    return jsonify([
        {"id": c.id, "nombre": c.nombre}
        for c in calles
    ])