/* =============================================================================
   AVILA.JS - CONFIGURACIÓN ESPECÍFICA PARA CALLES DE ÁVILA
   =============================================================================
   Proyecto: Ubicación España - Sistema de gestión de vías públicas
   Autor: Tino Hierro
   Fecha: 2026-05-23
   Versión: 1.0.0
   
   DESCRIPCIÓN:
   Configuración específica para la gestión de calles de Ávila capital.
   
   CARACTERÍSTICAS ESPECÍFICAS:
   - Provincia FIJA: Ávila (idtbl_provincias = 5)
   - Municipio FIJO: Ávila (idtbl_municipios = 395)
   - Solo requiere selección de tipo de vía
   - Interfaz simplificada (oculta selects de provincia y municipio)
   - Búsqueda optimizada (sin filtros de provincia/municipio)
   - Precarga automática de calles al inicio
   
   DEPENDENCIAS:
   - core.js (UbicacionCore)
   - catalogos.js (Catalogos)
   - filtros.js (Filtros)
   - alta.js (Alta)
   
   ESTRUCTURA HTML REQUERIDA:
   - #provincia (select - se ocultará)
   - #municipio (select - se ocultará)
   - #tipo_via (select)
   - #texto_calle (input)
   - #btn-buscar (button)
   - #btn-limpiar (button)
   - #btn-alta-calle (button)
   - #nombre_calle, #cp, #barrio (inputs del formulario de alta)
   - #resumen-contexto (span para mostrar contexto)
   - #contexto-alta (div para mostrar contexto en formulario de alta)
   
   USO:
   <script src="js/ubicacion/core.js"></script>
   <script src="js/ubicacion/catalogos.js"></script>
   <script src="js/ubicacion/filtros.js"></script>
   <script src="js/ubicacion/alta.js"></script>
   <script src="js/ubicacion/avila.js"></script>
   ============================================================================= */

const AvilaApp = {
    
    // =========================================================================
    // CONFIGURACIÓN FIJA DE ÁVILA
    // =========================================================================
    
    /**
     * ID de la provincia de Ávila en tbl_provincias
     * @constant {number}
     */
    PROVINCIA_AVILA: 5,

    /**
     * ID del municipio de Ávila en tbl_municipios
     * @constant {number}
     */
    MUNICIPIO_AVILA: 395,

    /**
     * Nombre completo de la provincia (para mostrar)
     * @constant {string}
     */
    NOMBRE_PROVINCIA: 'Ávila',

    /**
     * Nombre completo del municipio (para mostrar)
     * @constant {string}
     */
    NOMBRE_MUNICIPIO: 'Ávila',

    // =========================================================================
    // INICIALIZACIÓN
    // =========================================================================
    
    /**
     * Inicializa la aplicación en modo Ávila
     * 
     * FLUJO DE INICIALIZACIÓN:
     * 1. Log de inicio
     * 2. Cargar solo tipos de vía (provincia y municipio son fijos)
     * 3. Ocultar selects innecesarios (provincia, municipio)
     * 4. Mostrar indicador de contexto fijo
     * 5. Configurar event listeners
     * 6. Precargar calles (si hay tipo de vía seleccionado)
     * 
     * @returns {Promise<void>}
     * 
     * @example
     * document.addEventListener('DOMContentLoaded', () => {
     *     AvilaApp.init();
     * });
     */
    async init() {
        console.log('🏛️ ========================================');
        console.log('🏛️ INICIALIZANDO MODO ÁVILA');
        console.log('🏛️ Provincia: Ávila (ID: 5)');
        console.log('🏛️ Municipio: Ávila (ID: 395)');
        console.log('🏛️ ========================================');

        try {
            // PASO 1: Cargar solo tipos de vía
            console.log('📦 Cargando tipos de vía...');
            await Catalogos.cargarTiposVia();

            // PASO 2: Ocultar selects de provincia y municipio
            this.ocultarSelectsInnecesarios();

            // PASO 3: Configurar event listeners
            this.configurarEventos();

            // PASO 4: Actualizar contexto inicial
            this.actualizarContexto();

            // PASO 5: Precargar calles si hay tipo de vía seleccionado
            await this.precargarCalles();

            console.log('✅ Modo Ávila inicializado correctamente');

        } catch (error) {
            console.error('❌ Error inicializando modo Ávila:', error);
            UbicacionCore.mostrarError('Error al inicializar la aplicación');
        }
    },

    // =========================================================================
    // CONFIGURACIÓN DE INTERFAZ
    // =========================================================================
    
    /**
     * Oculta y deshabilita los selects de provincia y municipio
     * Muestra un indicador de contexto fijo en su lugar
     * 
     * @private
     */
    ocultarSelectsInnecesarios() {
        console.log('🔧 Ocultando selects de provincia y municipio...');

        // Buscar los .form-field que contienen los selects
        const provinciaField = document.querySelector('label[for="provincia"]')?.closest('.form-field');
        const municipioField = document.querySelector('label[for="municipio"]')?.closest('.form-field');

        // Ocultar los campos
        if (provinciaField) {
            provinciaField.style.display = 'none';
            console.log('  ✓ Campo provincia ocultado');
        }

        if (municipioField) {
            municipioField.style.display = 'none';
            console.log('  ✓ Campo municipio ocultado');
        }

        // Agregar indicador de contexto fijo
        this.mostrarIndicadorContextoFijo();
    },

    /**
     * Muestra un indicador visual de que el contexto está fijo en Ávila
     * @private
     */
    mostrarIndicadorContextoFijo() {
        const filtrosCard = document.querySelector('.card');
        
        if (!filtrosCard) {
            console.warn('⚠️ No se encontró .card para insertar indicador de contexto');
            return;
        }

        const cardHeader = filtrosCard.querySelector('.card-header');
        
        if (!cardHeader) {
            console.warn('⚠️ No se encontró .card-header');
            return;
        }

        // Crear indicador
        const indicador = document.createElement('div');
        indicador.className = 'contexto-fijo';
        indicador.innerHTML = `
            <div style="
                padding: 10px 14px;
                background: rgba(59, 130, 246, 0.12);
                border: 1px solid rgba(59, 130, 246, 0.3);
                border-radius: 8px;
                margin-bottom: 12px;
                font-size: 0.82rem;
                color: var(--text-primary);
                display: flex;
                align-items: center;
                gap: 8px;
            ">
                <span style="font-size: 1.2rem;">📍</span>
                <div>
                    <strong>Contexto fijo:</strong> ${this.NOMBRE_PROVINCIA} · ${this.NOMBRE_MUNICIPIO}
                    <div style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 2px;">
                        Solo necesitas seleccionar el tipo de vía
                    </div>
                </div>
            </div>
        `;

        // Insertar después del header
        cardHeader.after(indicador);
        console.log('  ✓ Indicador de contexto fijo agregado');
    },

    // =========================================================================
    // EVENT LISTENERS
    // =========================================================================
    
    /**
     * Configura todos los event listeners específicos de Ávila
     * 
     * EVENTOS:
     * - Click en botón buscar
     * - Click en botón limpiar
     * - Click en botón alta de calle
     * - Enter en campo de texto
     * - Change en tipo de vía (para actualizar contexto)
     * 
     * @private
     */
    configurarEventos() {
        console.log('🔧 Configurando event listeners...');

        // EVENTO: Buscar calles
        const btnBuscar = document.getElementById('btn-buscar');
        if (btnBuscar) {
            btnBuscar.addEventListener('click', () => {
                this.buscarCalles();
            });
            console.log('  ✓ Listener en btn-buscar');
        }

        // EVENTO: Limpiar filtros
        const btnLimpiar = document.getElementById('btn-limpiar');
        if (btnLimpiar) {
            btnLimpiar.addEventListener('click', () => {
                this.limpiarFiltros();
            });
            console.log('  ✓ Listener en btn-limpiar');
        }

        // EVENTO: Alta de calle
        const btnAltaCalle = document.getElementById('btn-alta-calle');
        if (btnAltaCalle) {
            btnAltaCalle.addEventListener('click', () => {
                this.altaCalle();
            });
            console.log('  ✓ Listener en btn-alta-calle');
        }

        // EVENTO: Enter en campo de texto
        const textoCalle = document.getElementById('texto_calle');
        if (textoCalle) {
            textoCalle.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    this.buscarCalles();
                }
            });
            console.log('  ✓ Listener de Enter en texto_calle');
        }

        // EVENTO: Change en tipo de vía (actualizar contexto)
        const tipoVia = document.getElementById('tipo_via');
        if (tipoVia) {
            tipoVia.addEventListener('change', () => {
                this.actualizarContexto();
                Filtros.limpiar();
            });
            console.log('  ✓ Listener en tipo_via');
        }
    },

    // =========================================================================
    // BÚSQUEDA DE CALLES
    // =========================================================================
    
    /**
     * Busca calles de Ávila con los filtros seleccionados
     * 
     * VALIDACIONES:
     * - Tipo de vía debe estar seleccionado
     * 
     * PARÁMETROS FIJOS:
     * - idMunicipio: 395 (Ávila)
     * - idTipoVia: del select
     * - texto: del input (opcional)
     * 
     * @returns {Promise<void>}
     * 
     * @example
     * await AvilaApp.buscarCalles();
     */
    async buscarCalles() {
        const idTipoVia = document.getElementById('tipo_via')?.value;
        const texto = document.getElementById('texto_calle')?.value || '';

        console.log(`🔍 Buscando calles de Ávila: tipo=${idTipoVia}, texto="${texto}"`);

        // Validar que haya tipo de vía seleccionado
        if (!idTipoVia) {
            UbicacionCore.mostrarError('Debes seleccionar un tipo de vía');
            return;
        }

        // Llamar a Filtros con parámetros fijos de Ávila
        await Filtros.buscarCalles(
            this.MUNICIPIO_AVILA,  // Municipio fijo: Ávila
            idTipoVia,
            texto
        );

        // Actualizar contexto en pantalla
        this.actualizarContexto();
    },

    /**
     * Precarga calles automáticamente si hay tipo de vía seleccionado
     * Se ejecuta al inicializar la aplicación
     * 
     * @private
     * @returns {Promise<void>}
     */
    async precargarCalles() {
        const tipoViaSelect = document.getElementById('tipo_via');
        
        if (tipoViaSelect && tipoViaSelect.value) {
            console.log('📦 Precargando calles automáticamente...');
            await this.buscarCalles();
        }
    },

    // =========================================================================
    // LIMPIEZA DE FILTROS
    // =========================================================================
    
    /**
     * Limpia los filtros de búsqueda
     * 
     * ACCIONES:
     * - Vacía el campo de texto
     * - Limpia resultados de la tabla
     * - Mantiene el tipo de vía seleccionado
     * 
     * @example
     * AvilaApp.limpiarFiltros();
     */
    limpiarFiltros() {
        console.log('🗑️ Limpiando filtros...');

        // Limpiar campo de texto
        const textoCalle = document.getElementById('texto_calle');
        if (textoCalle) {
            textoCalle.value = '';
        }

        // Limpiar resultados
        Filtros.limpiar();

        console.log('✅ Filtros limpiados');
    },

    // =========================================================================
    // ALTA DE CALLE
    // =========================================================================
    
    /**
     * Crea una nueva calle en Ávila
     * 
     * VALIDACIONES:
     * - Tipo de vía obligatorio
     * - Nombre de calle obligatorio
     * 
     * DATOS FIJOS:
     * - idtbl_provincias: 5 (Ávila)
     * - idtbl_municipios: 395 (Ávila)
     * 
     * FLUJO:
     * 1. Validar tipo de vía seleccionado
     * 2. Recoger datos del formulario
     * 3. Agregar IDs fijos de Ávila
     * 4. Llamar a Alta.crearCalle()
     * 5. Si OK: limpiar formulario y recargar listado
     * 
     * @returns {Promise<void>}
     * 
     * @example
     * await AvilaApp.altaCalle();
     */
    async altaCalle() {
        console.log('📝 Intentando crear nueva calle en Ávila...');

        // Validar que haya tipo de vía seleccionado
        const idTipoVia = document.getElementById('tipo_via')?.value;
        
        if (!idTipoVia) {
            UbicacionCore.mostrarError('Debes seleccionar un tipo de vía antes de dar de alta una calle');
            return;
        }

        // Recoger datos del formulario
        const nombreCalle = document.getElementById('nombre_calle')?.value?.trim();
        const codigoPostal = document.getElementById('cp')?.value?.trim();
        const barrio = document.getElementById('barrio')?.value?.trim();

        // Construir payload con IDs fijos de Ávila
        const datos = {
            idtbl_provincias: this.PROVINCIA_AVILA,      // FIJO: 5
            idtbl_municipios: this.MUNICIPIO_AVILA,      // FIJO: 395
            idtbl_tipos_de_vias: idTipoVia,
            calles: nombreCalle,
            Codigopostal: codigoPostal,
            Barrio: barrio
        };

        console.log('  Datos a enviar:', datos);

        // Llamar al módulo de alta
        const response = await Alta.crearCalle(datos);

        // Si fue exitoso, limpiar formulario y recargar
        if (response.ok) {
            // Limpiar formulario de alta
            this.limpiarFormularioAlta();

            // Recargar listado de calles
            await this.buscarCalles();
        }
    },

    /**
     * Limpia el formulario de alta de calles
     * @private
     */
    limpiarFormularioAlta() {
        const campos = ['nombre_calle', 'cp', 'barrio'];
        
        campos.forEach(id => {
            const campo = document.getElementById(id);
            if (campo) {
                campo.value = '';
            }
        });

        console.log('🗑️ Formulario de alta limpiado');
    },

    // =========================================================================
    // ACTUALIZACIÓN DE CONTEXTO
    // =========================================================================
    
    /**
     * Actualiza el resumen de contexto en pantalla
     * 
     * ACTUALIZA:
     * - #resumen-contexto (en panel de resultados)
     * - #contexto-alta (en panel de alta)
     * 
     * FORMATO:
     * "Ávila · Ávila · [Tipo de vía]"
     * 
     * @example
     * AvilaApp.actualizarContexto();
     * // Resultado: "Ávila · Ávila · Calle"
     */
    actualizarContexto() {
        const tipoViaSelect = document.getElementById('tipo_via');
        const tipoViaTexto = tipoViaSelect?.options[tipoViaSelect.selectedIndex]?.textContent || '–';

        const contextoTexto = `${this.NOMBRE_PROVINCIA} · ${this.NOMBRE_MUNICIPIO} · ${tipoViaTexto}`;

        // Actualizar resumen de resultados
        const resumenContexto = document.getElementById('resumen-contexto');
        if (resumenContexto) {
            resumenContexto.textContent = contextoTexto;
        }

        // Actualizar contexto de alta
        const contextoAlta = document.getElementById('contexto-alta');
        if (contextoAlta) {
            contextoAlta.textContent = contextoTexto;
        }

        console.log(`📍 Contexto actualizado: ${contextoTexto}`);
    },

    // =========================================================================
    // UTILIDADES
    // =========================================================================
    
    /**
     * Obtiene el estado actual de la aplicación
     * @returns {Object} - Estado con configuración y datos cargados
     */
    getEstado() {
        return {
            modo: 'AVILA',
            provincia: {
                id: this.PROVINCIA_AVILA,
                nombre: this.NOMBRE_PROVINCIA
            },
            municipio: {
                id: this.MUNICIPIO_AVILA,
                nombre: this.NOMBRE_MUNICIPIO
            },
            tipoViaSeleccionado: document.getElementById('tipo_via')?.value || null,
            totalCallesCargadas: Filtros.todasLasCalles.length,
            letraActiva: Filtros.letraActiva
        };
    },

    /**
     * Exporta las calles actuales a CSV
     * @returns {string} - Contenido CSV
     */
    exportarCSV() {
        const calles = Filtros.getCallesVisibles();
        
        let csv = 'ID,Tipo de vía,Calle,Código Postal,Barrio\n';
        
        calles.forEach(calle => {
            csv += `${calle.idtbl_calles},`;
            csv += `${calle.idtbl_tipos_de_vias},`;
            csv += `"${calle.calles}",`;
            csv += `${calle.Codigopostal || ''},`;
            csv += `${calle.Barrio || ''}\n`;
        });

        console.log(`📊 CSV generado con ${calles.length} calles`);
        
        return csv;
    },

    /**
     * Descarga las calles visibles como archivo CSV
     */
    descargarCSV() {
        const csv = this.exportarCSV();
        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = `calles_avila_${new Date().toISOString().split('T')[0]}.csv`;
        link.click();
        
        URL.revokeObjectURL(url);
        
        UbicacionCore.mostrarExito('CSV descargado correctamente');
    }
};

// =============================================================================
// AUTO-INICIALIZACIÓN
// =============================================================================

/**
 * Inicializa automáticamente la aplicación cuando el DOM está listo
 */
document.addEventListener('DOMContentLoaded', () => {
    AvilaApp.init();
});

// Log de carga del módulo
console.log('✅ Avila.js cargado correctamente');