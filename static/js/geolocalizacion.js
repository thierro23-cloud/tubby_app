{# ============================================================================
   📍 COMPONENTE DE GEOLOCALIZACIÓN
   ============================================================================
   ✅ Compatible con:
      - static/js/geolocalizacion.js
      - control_obras_bp.py
   ✅ Usa la versión premium del script aunque el archivo se llame simple
   ============================================================================ #}

<div class="geo-ultra-card mt-4" data-geo-auto="false" data-geo-min-accuracy="30">
  <div class="geo-ultra-header">
    <div class="geo-ultra-header-main">
      <h5 class="geo-ultra-title">📍 Geolocalización del dispositivo</h5>
      <p class="geo-ultra-subtitle">
        Captura la ubicación actual del terminal y vincúlala al registro de obra.
      </p>
    </div>

    <div class="geo-ultra-badge-wrap">
      <span id="geo_quality_badge" class="geo-ultra-badge neutral">Sin capturar</span>
    </div>
  </div>

  <div class="geo-ultra-body">
    <div class="row g-3">

      <div class="col-12 col-md-6 col-xl-3">
        <label for="latitud" class="form-label fw-semibold">🌐 Latitud</label>
        <input
          type="text"
          class="form-control"
          id="latitud"
          name="latitud"
          value="{{ datos.latitud or '' }}"
          readonly
          placeholder="Pendiente de capturar"
        >
      </div>

      <div class="col-12 col-md-6 col-xl-3">
        <label for="longitud" class="form-label fw-semibold">🌐 Longitud</label>
        <input
          type="text"
          class="form-control"
          id="longitud"
          name="longitud"
          value="{{ datos.longitud or '' }}"
          readonly
          placeholder="Pendiente de capturar"
        >
      </div>

      <div class="col-12 col-md-6 col-xl-3">
        <label for="precision_gps" class="form-label fw-semibold">🎯 Precisión (m)</label>
        <input
          type="text"
          class="form-control"
          id="precision_gps"
          name="precision_gps"
          value="{{ datos.precision_gps or '' }}"
          readonly
          placeholder="Pendiente de capturar"
        >
      </div>

      <div class="col-12 col-md-6 col-xl-3">
        <label for="fecha_captura_gps" class="form-label fw-semibold">🕒 Fecha de captura</label>
        <input
          type="text"
          class="form-control"
          id="fecha_captura_gps"
          name="fecha_captura_gps"
          value="{{ datos.fecha_captura_gps or '' }}"
          readonly
          placeholder="Pendiente de capturar"
        >
      </div>

      <div class="col-12 col-xl-8">
        <label for="estado_gps" class="form-label fw-semibold">📡 Estado de geolocalización</label>
        <input
          type="text"
          class="form-control"
          id="estado_gps"
          readonly
          value="Pendiente de capturar ubicación"
        >
      </div>

      <div class="col-12 col-xl-4">
        <label for="calidad_gps" class="form-label fw-semibold">🛰️ Calidad GPS</label>
        <input
          type="text"
          class="form-control"
          id="calidad_gps"
          value="{{ datos.gps_nivel_calidad or '' }}"
          readonly
        >
      </div>

      <div class="col-12 col-xl-8">
        <label for="enlace_maps" class="form-label fw-semibold">🗺️ Enlace a mapa</label>
        <div class="input-group">
          <input
            type="text"
            class="form-control"
            id="enlace_maps"
            readonly
            placeholder="Se generará tras capturar la ubicación"
          >
          <a
            id="abrir_maps"
            class="btn btn-outline-primary disabled"
            href="#"
            target="_blank"
            rel="noopener noreferrer"
            aria-disabled="true"
          >
            Abrir en Maps
          </a>
        </div>
      </div>

      <div class="col-12 col-xl-4">
        <label for="gps_precision_ok_text" class="form-label fw-semibold">✅ Validación de precisión</label>
        <input
          type="text"
          class="form-control"
          id="gps_precision_ok_text"
          readonly
          value="Sin validar"
        >
      </div>

      <input type="hidden" id="gps_precision_ok" name="gps_precision_ok" value="{{ datos.gps_precision_ok or '' }}">
      <input type="hidden" id="gps_origen" name="gps_origen" value="{{ datos.gps_origen or 'navigator.geolocation' }}">
      <input type="hidden" id="gps_nivel_calidad" name="gps_nivel_calidad" value="{{ datos.gps_nivel_calidad or '' }}">

      <div class="col-12">
        <div class="geo-ultra-map-wrapper">
          <div id="geo_ultra_map_placeholder" class="geo-ultra-map-placeholder">
            <div class="geo-ultra-map-icon">🗺️</div>
            <div class="geo-ultra-map-title">Mapa pendiente de ubicación</div>
            <div class="geo-ultra-map-text">
              Cuando captures la ubicación, aquí se mostrará la localización aproximada del punto.
            </div>
          </div>

          <iframe
            id="geo_ultra_map_iframe"
            class="geo-ultra-map-frame d-none"
            loading="lazy"
            referrerpolicy="no-referrer-when-downgrade"
          ></iframe>
        </div>
      </div>
    </div>

    <div class="d-flex flex-wrap gap-2 mt-4">
      <button type="button" class="btn btn-outline-primary" onclick="obtenerUbicacionUltraPremium()">
        📍 Obtener mi ubicación
      </button>

      <button type="button" class="btn btn-outline-secondary" onclick="limpiarUbicacionUltraPremium()">
        🧹 Limpiar ubicación
      </button>

      <button type="button" class="btn btn-outline-dark" onclick="recentrarMapaUltraPremium()">
        🗺️ Recentrar mapa
      </button>
    </div>

    <div class="form-text mt-3">
      La ubicación requiere permiso del navegador. En móvil funciona mejor con HTTPS y ubicación precisa activada.
    </div>
  </div>
</div>

<style>
  .geo-ultra-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 20px;
    box-shadow: 0 14px 32px rgba(15, 23, 42, 0.08);
    overflow: hidden;
  }

  .geo-ultra-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
    padding: 1.2rem 1.25rem 0 1.25rem;
  }

  .geo-ultra-title {
    margin: 0;
    font-size: 1rem;
    font-weight: 700;
    color: #0f172a;
  }

  .geo-ultra-subtitle {
    margin: .25rem 0 0 0;
    font-size: .84rem;
    color: #64748b;
    line-height: 1.45;
  }

  .geo-ultra-body {
    padding: 1.25rem;
  }

  .geo-ultra-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 34px;
    padding: .4rem .75rem;
    border-radius: 999px;
    font-size: .76rem;
    font-weight: 700;
    white-space: nowrap;
    border: 1px solid transparent;
  }

  .geo-ultra-badge.neutral {
    background: #f1f5f9;
    color: #334155;
    border-color: #e2e8f0;
  }

  .geo-ultra-badge.excelente {
    background: #dcfce7;
    color: #166534;
    border-color: #bbf7d0;
  }

  .geo-ultra-badge.muy-buena,
  .geo-ultra-badge.buena {
    background: #dbeafe;
    color: #1d4ed8;
    border-color: #bfdbfe;
  }

  .geo-ultra-badge.aceptable {
    background: #fef3c7;
    color: #92400e;
    border-color: #fde68a;
  }

  .geo-ultra-badge.baja,
  .geo-ultra-badge.invalida {
    background: #fee2e2;
    color: #991b1b;
    border-color: #fecaca;
  }

  .geo-ultra-map-wrapper {
    border: 1px solid #e5e7eb;
    border-radius: 16px;
    overflow: hidden;
    background: #f8fafc;
  }

  .geo-ultra-map-placeholder {
    min-height: 260px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    gap: .45rem;
    padding: 1rem;
    text-align: center;
    color: #64748b;
  }

  .geo-ultra-map-icon {
    font-size: 2rem;
  }

  .geo-ultra-map-title {
    font-weight: 700;
    color: #0f172a;
  }

  .geo-ultra-map-text {
    font-size: .88rem;
    max-width: 560px;
  }

  .geo-ultra-map-frame {
    width: 100%;
    min-height: 320px;
    border: 0;
  }

  @media (max-width: 768px) {
    .geo-ultra-header {
      flex-direction: column;
      align-items: flex-start;
    }

    .geo-ultra-map-frame {
      min-height: 260px;
    }
  }
</style>