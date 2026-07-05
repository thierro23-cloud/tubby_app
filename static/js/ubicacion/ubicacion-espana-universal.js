/**
 * ============================================================================
 * 🇪🇸 UBICACIÓN ESPAÑA - SISTEMA UNIVERSAL v1.0
 * ============================================================================
 * Autor: Tino Hierro
 * Fecha: 2026-05-23
 * 
 * Sistema autónomo de carga dinámica de provincias, municipios y calles.
 * No requiere dependencias externas.
 * 
 * USO:
 * 1. Incluir este archivo: <script src="ubicacion-espana-universal.js"></script>
 * 2. Asegurar que existen selects con IDs: provincia, municipio, tipo_via, calle
 * 3. El sistema se inicializa automáticamente
 * 
 * PARA MODO EDICIÓN:
 * UbicacionEspana.precargar(provinciaId, municipioId, tipoViaId, calleId);
 * ============================================================================
 */

const UbicacionEspana = (function() {
  'use strict';
  
  const CONFIG = {
    endpoints: {
      municipios: '/helpers_vias/municipios',
      calles: '/helpers_vias/calles'
    },
    selectors: {
      provincia: 'provincia',
      municipio: 'municipio',
      tipoVia: 'tipo_via',
      calle: 'calle'
    },
    debug: true
  };
  
  let elements = {};
  
  function log(...args) {
    if (CONFIG.debug) console.log('[UbicacionES]', ...args);
  }
  
  function error(...args) {
    console.error('[UbicacionES ERROR]', ...args);
  }
  
  async function cargarMunicipios(provinciaId, preseleccionado = null) {
    log('📍 Cargando municipios para provincia:', provinciaId);
    
    const selectMunicipio = elements.municipio;
    if (!selectMunicipio) {
      error('Select municipio no encontrado');
      return;
    }
    
    selectMunicipio.innerHTML = '<option value="">Cargando...</option>';
    selectMunicipio.disabled = true;
    
    if (elements.calle) {
      elements.calle.innerHTML = '<option value="">-- Seleccione municipio primero --</option>';
      elements.calle.disabled = true;
    }
    
    if (!provinciaId) {
      selectMunicipio.innerHTML = '<option value="">-- Seleccione provincia primero --</option>';
      return;
    }
    
    try {
      const url = `${CONFIG.endpoints.municipios}?id_provincia=${provinciaId}`;
      log('   🌐 GET:', url);
      
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      
      const data = await res.json();
      log('   📦 Respuesta:', data);
      
      let municipios = null;
      if (data.ok && Array.isArray(data.municipios)) {
        municipios = data.municipios;
      } else if (Array.isArray(data)) {
        municipios = data;
      }
      
      if (!municipios || municipios.length === 0) {
        log('   ⚠️ Sin municipios para esta provincia');
        selectMunicipio.innerHTML = '<option value="">-- Sin municipios --</option>';
        return;
      }
      
      log(`   ✅ ${municipios.length} municipios cargados`);
      
      selectMunicipio.innerHTML = '<option value="">-- Seleccione municipio --</option>';
      
      municipios.forEach(mun => {
        const option = document.createElement('option');
        option.value = mun.idtbl_municipios;
        option.textContent = mun.municipios;
        
        if (preseleccionado && mun.idtbl_municipios == preseleccionado) {
          option.selected = true;
          log(`   🎯 Preseleccionado: ${mun.municipios}`);
        }
        
        selectMunicipio.appendChild(option);
      });
      
      selectMunicipio.disabled = false;
      
    } catch (err) {
      error('Error cargando municipios:', err);
      selectMunicipio.innerHTML = '<option value="">-- Error al cargar --</option>';
    }
  }
  
  async function cargarCalles(municipioId, tipoViaId, preseleccionado = null) {
    log('🛣️ Cargando calles para municipio:', municipioId, 'tipo:', tipoViaId);
    
    const selectCalle = elements.calle;
    if (!selectCalle) return;
    
    selectCalle.innerHTML = '<option value="">Cargando...</option>';
    selectCalle.disabled = true;
    
    if (!municipioId || !tipoViaId) {
      selectCalle.innerHTML = '<option value="">-- Seleccione municipio y tipo --</option>';
      return;
    }
    
    try {
      const url = `${CONFIG.endpoints.calles}?id_municipio=${municipioId}&id_tipo_via=${tipoViaId}`;
      log('   🌐 GET:', url);
      
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      
      const data = await res.json();
      
      let calles = null;
      if (data.ok && Array.isArray(data.calles)) {
        calles = data.calles;
      } else if (Array.isArray(data)) {
        calles = data;
      }
      
      if (!calles || calles.length === 0) {
        log('   ⚠️ Sin calles para este municipio/tipo');
        selectCalle.innerHTML = '<option value="">-- Sin calles --</option>';
        return;
      }
      
      log(`   ✅ ${calles.length} calles cargadas`);
      
      selectCalle.innerHTML = '<option value="">-- Seleccione calle --</option>';
      
      calles.forEach(c => {
        const option = document.createElement('option');
        option.value = c.idtbl_calles;
        option.textContent = c.calles;
        
        if (preseleccionado && c.idtbl_calles == preseleccionado) {
          option.selected = true;
          log(`   🎯 Preseleccionada: ${c.calles}`);
        }
        
        selectCalle.appendChild(option);
      });
      
      selectCalle.disabled = false;
      
    } catch (err) {
      error('Error cargando calles:', err);
      selectCalle.innerHTML = '<option value="">-- Error al cargar --</option>';
    }
  }
  
  function registrarEventos() {
    if (elements.provincia) {
      elements.provincia.addEventListener('change', function() {
        const provinciaId = this.value;
        log('━━━ PROVINCIA CAMBIADA:', provinciaId);
        cargarMunicipios(provinciaId);
      });
      log('✅ Listener provincia registrado');
    }
    
    if (elements.municipio && elements.tipoVia && elements.calle) {
      const cargarCallesHandler = () => {
        const municipioId = elements.municipio.value;
        const tipoViaId = elements.tipoVia.value;
        log('━━━ MUNICIPIO/TIPO CAMBIADO:', municipioId, tipoViaId);
        cargarCalles(municipioId, tipoViaId);
      };
      
      elements.municipio.addEventListener('change', cargarCallesHandler);
      elements.tipoVia.addEventListener('change', cargarCallesHandler);
      log('✅ Listeners municipio/tipo vía registrados');
    }
  }
  
  return {
    init: function() {
      log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      log('🇪🇸 UBICACIÓN ESPAÑA - INICIALIZANDO');
      log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      
      elements.provincia = document.getElementById(CONFIG.selectors.provincia);
      elements.municipio = document.getElementById(CONFIG.selectors.municipio);
      elements.tipoVia = document.getElementById(CONFIG.selectors.tipoVia);
      elements.calle = document.getElementById(CONFIG.selectors.calle);
      
      log('📋 Elementos encontrados:');
      log('   - Provincia:', elements.provincia ? '✅' : '❌');
      log('   - Municipio:', elements.municipio ? '✅' : '❌');
      log('   - Tipo vía:', elements.tipoVia ? '✅' : '❌');
      log('   - Calle:', elements.calle ? '✅' : '❌');
      
      if (!elements.provincia || !elements.municipio) {
        error('⚠️ Faltan elementos mínimos (provincia/municipio)');
        return;
      }
      
      registrarEventos();
      
      log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      log('✅ INICIALIZACIÓN COMPLETADA');
      log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    },
    
    precargar: async function(provinciaId, municipioId = null, tipoViaId = null, calleId = null) {
      log('━━━ PRECARGA MODO EDICIÓN');
      log('   Provincia:', provinciaId, '| Municipio:', municipioId);
      
      if (provinciaId) {
        await cargarMunicipios(provinciaId, municipioId);
      }
      
      if (municipioId && tipoViaId) {
        await cargarCalles(municipioId, tipoViaId, calleId);
      }
    },
    
    setDebug: function(enabled) {
      CONFIG.debug = enabled;
      log('Debug:', enabled ? 'activado' : 'desactivado');
    }
  };
})();

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => UbicacionEspana.init());
} else {
  UbicacionEspana.init();
}