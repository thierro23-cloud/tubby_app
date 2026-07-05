/* =============================================================================
   ESPANA.JS - MODO PROVEEDORES (DEBUGGING VERSION)
   ============================================================================= */

const EspanaApp = {
    
    estado: {
        provinciaSeleccionada: null,
        municipioSeleccionado: null,
        tipoViaSeleccionado: null
    },

    async init() {
        console.log('🇪🇸 ========================================');
        console.log('🇪🇸 MODO ESPAÑA - PROVEEDORES');
        console.log('🇪🇸 ========================================');

        try {
            const provinciaSelect = document.getElementById('provincia');
            const tipoViaSelect = document.getElementById('tipo_via');
            const municipioSelect = document.getElementById('municipio');
            const calleSelect = document.getElementById('calle');
            
            // DIAGNÓSTICO
            console.log('📋 Verificación de selects:');
            console.log('  - provincia:', !!provinciaSelect, `(${provinciaSelect?.options.length || 0} opciones)`);
            console.log('  - municipio:', !!municipioSelect, `(${municipioSelect?.options.length || 0} opciones)`);
            console.log('  - tipo_via:', !!tipoViaSelect, `(${tipoViaSelect?.options.length || 0} opciones)`);
            console.log('  - calle:', !!calleSelect, `(${calleSelect?.options.length || 0} opciones)`);
            
            const provinciasYaCargadas = provinciaSelect && provinciaSelect.options.length > 1;
            const tiposViaYaCargados = tipoViaSelect && tipoViaSelect.options.length > 1;
            
            if (provinciasYaCargadas && tiposViaYaCargados) {
                console.log('✅ Provincias y tipos de vía ya cargados desde servidor');
            } else {
                console.warn('⚠️ Catálogos no precargados. Esto puede causar problemas.');
            }

            this.configurarEventos();

            console.log('✅ Modo España inicializado');

        } catch (error) {
            console.error('❌ Error inicializando:', error);
        }
    },

    configurarEventos() {
        console.log('🔧 Configurando eventos...');

        const provinciaSelect = document.getElementById('provincia');
        const municipioSelect = document.getElementById('municipio');
        const tipoViaSelect = document.getElementById('tipo_via');
        const calleSelect = document.getElementById('calle');

        if (!provinciaSelect || !municipioSelect || !tipoViaSelect) {
            console.error('❌ Faltan selects críticos');
            return;
        }

        // EVENTO: Provincia → Municipios
        provinciaSelect.addEventListener('change', async () => {
            const idProvincia = provinciaSelect.value;
            
            this.estado.provinciaSeleccionada = idProvincia;
            this.estado.municipioSeleccionado = null;
            
            console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
            console.log(`📍 PROVINCIA SELECCIONADA: ${idProvincia}`);
            console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
            
            // Limpiar selects
            municipioSelect.innerHTML = '<option>Cargando...</option>';
            if (calleSelect) {
                calleSelect.innerHTML = '<option>Calle</option>';
            }
            
            if (!idProvincia) {
                municipioSelect.innerHTML = '<option>Mun</option>';
                console.log('ℹ️ Provincia vacía, municipios limpiados');
                return;
            }
            
            // CARGAR MUNICIPIOS CON FETCH DIRECTO
            await this.cargarMunicipios(idProvincia);
        });

        // EVENTO: Municipio → Calles
        municipioSelect.addEventListener('change', () => {
            this.estado.municipioSeleccionado = municipioSelect.value;
            console.log(`🏘️ Municipio: ${municipioSelect.value}`);
            this.cargarCalles();
        });

        // EVENTO: Tipo de vía → Calles
        tipoViaSelect.addEventListener('change', () => {
            this.estado.tipoViaSeleccionado = tipoViaSelect.value;
            console.log(`🛣️ Tipo vía: ${tipoViaSelect.value}`);
            this.cargarCalles();
        });

        console.log('✅ Eventos configurados');
    },

    /**
     * NUEVA FUNCIÓN: Carga municipios con fetch directo
     */
    async cargarMunicipios(idProvincia) {
        const municipioSelect = document.getElementById('municipio');
        
        if (!municipioSelect) {
            console.error('❌ Select municipio no encontrado');
            return;
        }

        try {
            // PROBAR DIFERENTES FORMATOS DE URL
            const urls = [
                `/helpers_vias/municipios?id_provincia=${idProvincia}`,
                `/helpers_vias/municipios?prov_id=${idProvincia}`,
                `/helpers_vias/municipios/${idProvincia}`
            ];
            
            console.log('🌐 Probando URLs:', urls);
            
            let data = null;
            let urlUsada = null;
            
            // Intentar con cada URL
            for (const url of urls) {
                console.log(`🔄 Intentando: ${url}`);
                
                try {
                    const response = await fetch(url);
                    console.log(`  📡 Status: ${response.status}`);
                    
                    if (response.ok) {
                        const json = await response.json();
                        console.log(`  📦 Respuesta:`, json);
                        
                        if (json.municipios && json.municipios.length > 0) {
                            data = json;
                            urlUsada = url;
                            console.log(`  ✅ URL válida encontrada: ${url}`);
                            break;
                        }
                    }
                } catch (e) {
                    console.log(`  ❌ Error con URL: ${e.message}`);
                }
            }
            
            if (!data || !data.municipios) {
                console.error('❌ Ninguna URL devolvió municipios válidos');
                municipioSelect.innerHTML = '<option>Error: endpoint no válido</option>';
                return;
            }
            
            const municipios = data.municipios;
            
            console.log(`✅ ${municipios.length} municipios recibidos`);
            console.log('📋 Primer municipio:', municipios[0]);
            
            // Renderizar
            if (municipios.length > 0) {
                municipioSelect.innerHTML = '<option value="">-- Selecciona --</option>' +
                    municipios.map(m => {
                        const id = m.idtbl_municipios || m.id;
                        const nombre = m.municipios || m.nombre;
                        return `<option value="${id}">${nombre}</option>`;
                    }).join('');
                
                console.log(`✅ ${municipios.length} municipios renderizados en select`);
                console.log('📊 Opciones en select:', municipioSelect.options.length);
            } else {
                municipioSelect.innerHTML = '<option>Sin municipios</option>';
                console.warn('⚠️ Array de municipios vacío');
            }
            
        } catch (error) {
            console.error('❌ Error cargando municipios:', error);
            console.error('Stack:', error.stack);
            municipioSelect.innerHTML = '<option>Error</option>';
        }
    },

    async cargarCalles() {
        const municipioSelect = document.getElementById('municipio');
        const tipoViaSelect = document.getElementById('tipo_via');
        const calleSelect = document.getElementById('calle');

        if (!calleSelect) return;

        const idMunicipio = municipioSelect?.value;
        const idTipoVia = tipoViaSelect?.value;

        calleSelect.innerHTML = '<option>Calle</option>';

        if (!idMunicipio || !idTipoVia) {
            console.log('ℹ️ Esperando municipio y tipo de vía');
            return;
        }

        try {
            console.log(`🔍 Cargando calles: mun=${idMunicipio}, tipo=${idTipoVia}`);

            const url = `/helpers_vias/calles?id_municipio=${idMunicipio}&id_tipo_via=${idTipoVia}`;
            const response = await fetch(url);
            
            console.log(`📡 Calles - Status: ${response.status}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            const calles = data.calles || [];

            console.log(`✅ ${calles.length} calles cargadas`);

            if (calles.length > 0) {
                calleSelect.innerHTML = '<option value="">-- Selecciona --</option>' +
                    calles.map(c => `<option value="${c.idtbl_calles}">${c.calles}</option>`).join('');
            } else {
                calleSelect.innerHTML = '<option>Sin calles</option>';
            }

        } catch (error) {
            console.error('❌ Error cargando calles:', error);
            calleSelect.innerHTML = '<option>Error</option>';
        }
    },

    getEstado() {
        return {
            modo: 'ESPANA_PROVEEDORES',
            provincia: this.estado.provinciaSeleccionada,
            municipio: this.estado.municipioSeleccionado,
            tipoVia: this.estado.tipoViaSeleccionado
        };
    }
};

// AUTO-INICIALIZACIÓN
document.addEventListener('DOMContentLoaded', () => {
    console.log('📌 DOMContentLoaded disparado');
    EspanaApp.init();
});

console.log('✅ Espana.js cargado (modo debug)');