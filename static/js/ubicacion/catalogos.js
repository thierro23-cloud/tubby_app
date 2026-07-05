/* =============================================================================
   CATALOGOS.JS - GESTIÓN DE CATÁLOGOS (PROVINCIAS, MUNICIPIOS, TIPOS DE VÍA)
   =============================================================================
   Proyecto: Ubicación España - Sistema de gestión de vías públicas
   Autor: Tino Hierro
   Fecha: 2026-05-23
   Versión: 1.0.0
   
   DESCRIPCIÓN:
   Módulo encargado de cargar y gestionar los catálogos maestros:
   - Provincias de España (tbl_provincias)
   - Municipios por provincia (tbl_municipios)
   - Tipos de vía (tbl_tipos_de_vias)
   
   DEPENDENCIAS:
   - core.js (UbicacionCore)
   
   ENDPOINTS (configurables):
   - GET /helpers_vias/provincias
   - GET /helpers_vias/municipios?id_provincia=X&q=texto
   - GET /helpers_vias/tipos_via?q=texto
   
   USO:
   await Catalogos.cargarProvincias();
   await Catalogos.cargarMunicipios(idProvincia, 'texto filtro');
   await Catalogos.cargarTiposVia();
   ============================================================================= */

const Catalogos = {
    
    // =========================================================================
    // CONFIGURACIÓN
    // =========================================================================
    
    config: {
        endpoints: {
            provincias: '/helpers_vias/provincias',
            municipios: '/helpers_vias/municipios',
            tipos_via: '/helpers_vias/tipos_via'
        },
        
        // Selectores de los elementos DOM
        selectores: {
            provincia: 'provincia',
            municipio: 'municipio',
            tipo_via: 'tipo_via'
        },

        // Cache de datos para evitar peticiones repetidas
        cache: {
            provincias: null,
            tipos_via: null,
            municipios: {} // {idProvincia: [municipios]}
        }
    },

    // =========================================================================
    // PROVINCIAS
    // =========================================================================
    
    /**
     /**
 * Carga todas las provincias de España
 * 
 * @returns {Promise<Array>} - Array de objetos provincia
 * 
 * Estructura de respuesta esperada:
 * {
 *   ok: true,
 *   provincias: [
 *     {idtbl_provincias: 1, provincias: 'Álava'},
 *     {idtbl_provincias: 5, provincias: 'Ávila'},
 *     ...
 *   ]
 * }
 * 
 * @example
 * const provincias = await Catalogos.cargarProvincias();
 * console.log(`Cargadas ${provincias.length} provincias`);
 */
async cargarProvincias() {
    try {
        // ✅ NUEVO: Verificar si ya hay provincias cargadas (desde Jinja)
        const selectProvincia = document.getElementById(this.config.selectores.provincia);
        
        if (selectProvincia && selectProvincia.options.length > 1) {
            console.log('📦 Provincias ya cargadas desde servidor (Jinja). Omitiendo carga desde API.');
            return []; // No sobrescribir
        }
        
        // Usar cache si existe
        if (this.config.cache.provincias) {
            console.log('📦 Provincias cargadas desde cache');
            this._renderizarProvincias(this.config.cache.provincias);
            return this.config.cache.provincias;
        }

        // Petición al backend
        console.log('📦 Cargando provincias desde API...');
        const data = await UbicacionCore.fetchJSON(this.config.endpoints.provincias);
        
        const provincias = data.provincias || [];
        
        // Guardar en cache
        this.config.cache.provincias = provincias;
        
        // Renderizar en select
        this._renderizarProvincias(provincias);
        
        console.log(`✅ Cargadas ${provincias.length} provincias`);
        
        return provincias;

    } catch (error) {
        UbicacionCore.mostrarError('Error al cargar las provincias');
        console.error('Error en cargarProvincias:', error);
        return [];
    }
},

    /**
     * Renderiza provincias en el select
     * @private
     */
    _renderizarProvincias(provincias) {
        const opciones = provincias.map(p => ({
            value: p.idtbl_provincias,
            text: p.provincias
        }));

        UbicacionCore.llenarSelect(
            this.config.selectores.provincia,
            opciones
        );
    },

    // =========================================================================
    // MUNICIPIOS
    // =========================================================================
    
    /**
     * Carga municipios de una provincia específica
     * 
     * @param {number} idProvincia - ID de la provincia
     * @param {string} texto - Filtro de texto opcional (búsqueda por nombre)
     * @returns {Promise<Array>} - Array de objetos municipio
     * 
     * Estructura de respuesta esperada:
     * {
     *   ok: true,
     *   municipios: [
     *     {idtbl_municipios: 395, municipios: 'Ávila', idtbl_provincias: 5},
     *     {idtbl_municipios: 396, municipios: 'Arévalo', idtbl_provincias: 5},
     *     ...
     *   ]
     * }
     * 
     * @example
     * const municipios = await Catalogos.cargarMunicipios(5); // Ávila
     * const filtrados = await Catalogos.cargarMunicipios(5, 'arév'); // Arévalo
     */
    async cargarMunicipios(idProvincia, texto = "") {
        const selectMunicipio = document.getElementById(this.config.selectores.municipio);
        
        // Limpiar select
        if (selectMunicipio) {
            selectMunicipio.innerHTML = "";
        }

        // Validar que haya provincia seleccionada
        if (!idProvincia) {
            console.log('ℹ️ No hay provincia seleccionada, municipios vacíos');
            return [];
        }

        try {
            // Comprobar cache (solo si no hay filtro de texto)
            const cacheKey = `${idProvincia}_${texto}`;
            if (!texto && this.config.cache.municipios[idProvincia]) {
                console.log(`📦 Municipios de provincia ${idProvincia} desde cache`);
                this._renderizarMunicipios(this.config.cache.municipios[idProvincia]);
                return this.config.cache.municipios[idProvincia];
            }

            // Construir URL con parámetros
            const url = new URL(this.config.endpoints.municipios, window.location.origin);
            url.searchParams.set('id_provincia', idProvincia);
            
            if (texto) {
                url.searchParams.set('q', texto);
            }

            // Petición al backend
            const data = await UbicacionCore.fetchJSON(url.toString());
            
            const municipios = data.municipios || [];
            
            // Guardar en cache (solo si no hay filtro)
            if (!texto) {
                this.config.cache.municipios[idProvincia] = municipios;
            }
            
            // Renderizar en select
            this._renderizarMunicipios(municipios);
            
            console.log(`✅ Cargados ${municipios.length} municipios de provincia ${idProvincia}`);
            
            return municipios;

        } catch (error) {
            UbicacionCore.mostrarError('Error al cargar los municipios');
            console.error('Error en cargarMunicipios:', error);
            return [];
        }
    },

    /**
     * Renderiza municipios en el select
     * @private
     */
    _renderizarMunicipios(municipios) {
        const opciones = municipios.map(m => ({
            value: m.idtbl_municipios,
            text: m.municipios
        }));

        UbicacionCore.llenarSelect(
            this.config.selectores.municipio,
            opciones
        );
    },

    // =========================================================================
    // TIPOS DE VÍA
    // =========================================================================
    
    /**
     * Carga todos los tipos de vía disponibles
     * 
     * @param {string} texto - Filtro de texto opcional
     * @returns {Promise<Array>} - Array de objetos tipo de vía
     * 
     * Estructura de respuesta esperada:
     * {
     *   ok: true,
     *   tipos_via: [
     *     {idtbl_tipos_de_vias: 1, tipos_de_vias: 'Calle'},
     *     {idtbl_tipos_de_vias: 2, tipos_de_vias: 'Avenida'},
     *     ...
     *   ]
     * }
     * 
     * @example
     * const tipos = await Catalogos./**
 * Carga todos los tipos de vía disponibles
 * 
 * @param {string} texto - Filtro de texto opcional
 * @returns {Promise<Array>} - Array de objetos tipo de vía
 * 
 * Estructura de respuesta esperada:
 * {
 *   ok: true,
 *   tipos_via: [
 *     {idtbl_tipos_de_vias: 1, tipos_de_vias: 'Calle'},
 *     {idtbl_tipos_de_vias: 2, tipos_de_vias: 'Avenida'},
 *     ...
 *   ]
 * }
 * 
 * @example
 * const tipos = await Catalogos.cargarTiposVia();
 * const filtrados = await Catalogos.cargarTiposVia('av'); // Avenida
 */
async cargarTiposVia(texto = "") {
    try {
        // ✅ NUEVO: Verificar si ya hay tipos cargados (desde Jinja)
        const selectTipoVia = document.getElementById(this.config.selectores.tipo_via);
        
        if (!texto && selectTipoVia && selectTipoVia.options.length > 1) {
            console.log('📦 Tipos de vía ya cargados desde servidor (Jinja). Omitiendo carga desde API.');
            return []; // No sobrescribir
        }
        
        // Usar cache si no hay filtro
        if (!texto && this.config.cache.tipos_via) {
            console.log('📦 Tipos de vía cargados desde cache');
            this._renderizarTiposVia(this.config.cache.tipos_via);
            return this.config.cache.tipos_via;
        }

        // Construir URL con parámetros
        console.log('📦 Cargando tipos de vía desde API...');
        const url = new URL(this.config.endpoints.tipos_via, window.location.origin);
        
        if (texto) {
            url.searchParams.set('q', texto);
        }

        // Petición al backend
        const data = await UbicacionCore.fetchJSON(url.toString());
        
        const tiposVia = data.tipos_via || [];
        
        // Guardar en cache (solo si no hay filtro)
        if (!texto) {
            this.config.cache.tipos_via = tiposVia;
        }
        
        // Renderizar en select
        this._renderizarTiposVia(tiposVia);
        
        console.log(`✅ Cargados ${tiposVia.length} tipos de vía`);
        
        return tiposVia;

    } catch (error) {
        UbicacionCore.mostrarError('Error al cargar los tipos de vía');
        console.error('Error en cargarTiposVia:', error);
        return [];
    }
},

    /**
     * Renderiza tipos de vía en el select
     * @private
     */
    _renderizarTiposVia(tiposVia) {
        const opciones = tiposVia.map(t => ({
            value: t.idtbl_tipos_de_vias,
            text: t.tipos_de_vias
        }));

        UbicacionCore.llenarSelect(
            this.config.selectores.tipo_via,
            opciones
        );
    },

    // =========================================================================
    // INICIALIZACIÓN
    // =========================================================================
    
    /**
     * Inicializa los catálogos al cargar la página
     * Carga provincias y tipos de vía automáticamente
     * 
     * @returns {Promise<void>}
     * 
     * @example
     * document.addEventListener('DOMContentLoaded', async () => {
     *     await Catalogos.inicializar();
     * });
     */
    async inicializar() {
        console.log('🚀 Inicializando catálogos...');

        try {
            // Cargar provincias y tipos de vía en paralelo
            await Promise.all([
                this.cargarProvincias(),
                this.cargarTiposVia()
            ]);

            // Si hay provincia seleccionada, cargar municipios
            const provSelect = document.getElementById(this.config.selectores.provincia);
            if (provSelect && provSelect.value) {
                await this.cargarMunicipios(provSelect.value);
            }

            console.log('✅ Catálogos inicializados correctamente');

        } catch (error) {
            console.error('❌ Error inicializando catálogos:', error);
        }
    },

    // =========================================================================
    // UTILIDADES
    // =========================================================================
    
    /**
     * Limpia la cache de catálogos
     */
    limpiarCache() {
        this.config.cache = {
            provincias: null,
            tipos_via: null,
            municipios: {}
        };
        console.log('🗑️ Cache de catálogos limpiada');
    },

    /**
     * Recarga todos los catálogos (forzando petición al servidor)
     */
    async recargar() {
        this.limpiarCache();
        await this.inicializar();
    }
};

// Log de inicialización
console.log('✅ Catalogos.js cargado correctamente');