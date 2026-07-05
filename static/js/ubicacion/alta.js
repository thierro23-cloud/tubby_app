/* =============================================================================
   ALTA.JS - FORMULARIOS DE ALTA (CALLES, MUNICIPIOS, TIPOS DE VÍA)
   =============================================================================
   Proyecto: Ubicación España - Sistema de gestión de vías públicas
   Autor: Tino Hierro
   Fecha: 2026-05-23
   Versión: 1.0.0
   
   DESCRIPCIÓN:
   Módulo encargado de gestionar los formularios de alta de:
   - Calles (vinculadas a provincia, municipio y tipo de vía)
   - Municipios (vinculados a provincia)
   - Tipos de vía (catálogo independiente)
   
   DEPENDENCIAS:
   - core.js (UbicacionCore)
   
   ENDPOINTS:
   - POST /helpers_vias/crear_calle
   - POST /helpers_vias/crear_municipio
   - POST /helpers_vias/crear_tipo_via
   
   ESTRUCTURA DE PAYLOADS:
   
   Calle:
   {
     idtbl_provincias: number,
     idtbl_municipios: number,
     idtbl_tipos_de_vias: number,
     calles: string,
     Codigopostal?: string,
     Barrio?: string
   }
   
   Municipio:
   {
     idtbl_provincias: number,
     municipios: string,
     codigo_postal?: string
   }
   
   Tipo de vía:
   {
     tipos_de_vias: string
   }
   
   USO:
   await Alta.crearCalle({...});
   await Alta.crearMunicipio({...});
   await Alta.crearTipoVia({...});
   ============================================================================= */

const Alta = {
    
    // =========================================================================
    // CONFIGURACIÓN
    // =========================================================================
    
    config: {
        endpoints: {
            crear_calle: '/helpers_vias/crear_calle',
            crear_municipio: '/helpers_vias/crear_municipio',
            crear_tipo_via: '/helpers_vias/crear_tipo_via'
        },

        // Validaciones
        validaciones: {
            longitudMaximaCalle: 255,
            longitudMaximaMunicipio: 100,
            longitudMaximaTipoVia: 50,
            codigoPostalRegex: /^\d{5}$/
        }
    },

    // =========================================================================
    // ALTA DE CALLE
    // =========================================================================
    
    /**
     * Crea una nueva calle en la base de datos
     * 
     * @param {Object} datos - Datos de la calle
     * @param {number} datos.idtbl_provincias - ID de la provincia (obligatorio)
     * @param {number} datos.idtbl_municipios - ID del municipio (obligatorio)
     * @param {number} datos.idtbl_tipos_de_vias - ID del tipo de vía (obligatorio)
     * @param {string} datos.calles - Nombre de la calle (obligatorio)
     * @param {string} [datos.Codigopostal] - Código postal (opcional, 5 dígitos)
     * @param {string} [datos.Barrio] - Barrio/zona (opcional)
     * 
     * @returns {Promise<Object>} - Respuesta del servidor {ok: boolean, error?: string, id?: number}
     * 
     * VALIDACIONES:
     * - Provincia, municipio y tipo de vía obligatorios
     * - Nombre de calle obligatorio (max 255 caracteres)
     * - Código postal opcional (debe ser 5 dígitos si se proporciona)
     * - Barrio opcional (max 100 caracteres)
     * 
     * FLUJO:
     * 1. Validar campos obligatorios
     * 2. Validar formato de código postal (si existe)
     * 3. Sanitizar texto
     * 4. Enviar petición POST al backend
     * 5. Mostrar mensaje de éxito/error
     * 6. Retornar respuesta
     * 
     * @example
     * const resultado = await Alta.crearCalle({
     *     idtbl_provincias: 5,
     *     idtbl_municipios: 395,
     *     idtbl_tipos_de_vias: 1,
     *     calles: 'Mayor',
     *     Codigopostal: '05001',
     *     Barrio: 'Centro'
     * });
     * 
     * if (resultado.ok) {
     *     console.log(`Calle creada con ID: ${resultado.id}`);
     * }
     */
    async crearCalle(datos) {
        console.log('📝 Intentando crear calle:', datos);

        // VALIDACIÓN 1: Campos obligatorios
        if (!UbicacionCore.validarCamposRequeridos({
            'Provincia': datos.idtbl_provincias,
            'Municipio': datos.idtbl_municipios,
            'Tipo de vía': datos.idtbl_tipos_de_vias,
            'Nombre de calle': datos.calles
        })) {
            return { ok: false, error: 'Faltan campos obligatorios' };
        }

        // VALIDACIÓN 2: Longitud del nombre
        if (datos.calles.length > this.config.validaciones.longitudMaximaCalle) {
            UbicacionCore.mostrarError(`El nombre de la calle no puede superar ${this.config.validaciones.longitudMaximaCalle} caracteres`);
            return { ok: false, error: 'Nombre demasiado largo' };
        }

        // VALIDACIÓN 3: Código postal (opcional)
        if (datos.Codigopostal && !this.config.validaciones.codigoPostalRegex.test(datos.Codigopostal)) {
            UbicacionCore.mostrarError('El código postal debe tener 5 dígitos');
            return { ok: false, error: 'Código postal inválido' };
        }

        // SANITIZACIÓN: Limpiar textos
        const payload = {
            idtbl_provincias: parseInt(datos.idtbl_provincias),
            idtbl_municipios: parseInt(datos.idtbl_municipios),
            idtbl_tipos_de_vias: parseInt(datos.idtbl_tipos_de_vias),
            calles: UbicacionCore.sanitizarTexto(datos.calles),
            Codigopostal: datos.Codigopostal ? datos.Codigopostal.trim() : null,
            Barrio: datos.Barrio ? UbicacionCore.sanitizarTexto(datos.Barrio) : null
        };

        try {
            // Petición POST al backend
            const response = await UbicacionCore.fetchJSON(
                this.config.endpoints.crear_calle,
                {
                    method: 'POST',
                    body: JSON.stringify(payload)
                }
            );

            // Procesar respuesta
            if (response.ok) {
                UbicacionCore.mostrarExito('Calle creada correctamente');
                console.log('✅ Calle creada:', response);
            } else {
                UbicacionCore.mostrarError(response.error || 'Error al crear la calle');
                console.error('❌ Error del servidor:', response);
            }

            return response;

        } catch (error) {
            UbicacionCore.mostrarError('Error técnico al crear la calle');
            console.error('❌ Error en crearCalle:', error);
            return { ok: false, error: error.message };
        }
    },

    // =========================================================================
    // ALTA DE MUNICIPIO
    // =========================================================================
    
    /**
     * Crea un nuevo municipio en la base de datos
     * 
     * @param {Object} datos - Datos del municipio
     * @param {number} datos.idtbl_provincias - ID de la provincia (obligatorio)
     * @param {string} datos.municipios - Nombre del municipio (obligatorio)
     * @param {string} [datos.codigo_postal] - Código postal (opcional)
     * 
     * @returns {Promise<Object>} - Respuesta del servidor {ok: boolean, error?: string, id?: number}
     * 
     * VALIDACIONES:
     * - Provincia obligatoria
     * - Nombre de municipio obligatorio (max 100 caracteres)
     * - Código postal opcional (5 dígitos si se proporciona)
     * 
     * @example
     * const resultado = await Alta.crearMunicipio({
     *     idtbl_provincias: 5,
     *     municipios: 'Arévalo',
     *     codigo_postal: '05200'
     * });
     */
    async crearMunicipio(datos) {
        console.log('📝 Intentando crear municipio:', datos);

        // VALIDACIÓN: Campos obligatorios
        if (!UbicacionCore.validarCamposRequeridos({
            'Provincia': datos.idtbl_provincias,
            'Nombre del municipio': datos.municipios
        })) {
            return { ok: false, error: 'Faltan campos obligatorios' };
        }

        // VALIDACIÓN: Longitud
        if (datos.municipios.length > this.config.validaciones.longitudMaximaMunicipio) {
            UbicacionCore.mostrarError(`El nombre del municipio no puede superar ${this.config.validaciones.longitudMaximaMunicipio} caracteres`);
            return { ok: false, error: 'Nombre demasiado largo' };
        }

        // VALIDACIÓN: Código postal
        if (datos.codigo_postal && !this.config.validaciones.codigoPostalRegex.test(datos.codigo_postal)) {
            UbicacionCore.mostrarError('El código postal debe tener 5 dígitos');
            return { ok: false, error: 'Código postal inválido' };
        }

        // SANITIZACIÓN
        const payload = {
            idtbl_provincias: parseInt(datos.idtbl_provincias),
            municipios: UbicacionCore.sanitizarTexto(datos.municipios),
            codigo_postal: datos.codigo_postal ? datos.codigo_postal.trim() : null
        };

        try {
            const response = await UbicacionCore.fetchJSON(
                this.config.endpoints.crear_municipio,
                {
                    method: 'POST',
                    body: JSON.stringify(payload)
                }
            );

            if (response.ok) {
                UbicacionCore.mostrarExito('Municipio creado correctamente');
                console.log('✅ Municipio creado:', response);
            } else {
                UbicacionCore.mostrarError(response.error || 'Error al crear el municipio');
                console.error('❌ Error del servidor:', response);
            }

            return response;

        } catch (error) {
            UbicacionCore.mostrarError('Error técnico al crear el municipio');
            console.error('❌ Error en crearMunicipio:', error);
            return { ok: false, error: error.message };
        }
    },

    // =========================================================================
    // ALTA DE TIPO DE VÍA
    // =========================================================================
    
    /**
     * Crea un nuevo tipo de vía en la base de datos
     * 
     * @param {Object} datos - Datos del tipo de vía
     * @param {string} datos.tipos_de_vias - Nombre del tipo (obligatorio)
     * 
     * @returns {Promise<Object>} - Respuesta del servidor {ok: boolean, error?: string, id?: number}
     * 
     * VALIDACIONES:
     * - Nombre obligatorio (max 50 caracteres)
     * 
     * EJEMPLOS DE TIPOS DE VÍA:
     * - Calle, Avenida, Plaza, Paseo, Pasaje, Glorieta, Travesía, etc.
     * 
     * @example
     * const resultado = await Alta.crearTipoVia({
     *     tipos_de_vias: 'Pasaje'
     * });
     */
    async crearTipoVia(datos) {
        console.log('📝 Intentando crear tipo de vía:', datos);

        // VALIDACIÓN: Campo obligatorio
        if (!UbicacionCore.validarCamposRequeridos({
            'Nombre del tipo de vía': datos.tipos_de_vias
        })) {
            return { ok: false, error: 'Falta el nombre del tipo de vía' };
        }

        // VALIDACIÓN: Longitud
        if (datos.tipos_de_vias.length > this.config.validaciones.longitudMaximaTipoVia) {
            UbicacionCore.mostrarError(`El nombre del tipo de vía no puede superar ${this.config.validaciones.longitudMaximaTipoVia} caracteres`);
            return { ok: false, error: 'Nombre demasiado largo' };
        }

        // SANITIZACIÓN
        const payload = {
            tipos_de_vias: UbicacionCore.sanitizarTexto(datos.tipos_de_vias)
        };

        try {
            const response = await UbicacionCore.fetchJSON(
                this.config.endpoints.crear_tipo_via,
                {
                    method: 'POST',
                    body: JSON.stringify(payload)
                }
            );

            if (response.ok) {
                UbicacionCore.mostrarExito('Tipo de vía creado correctamente');
                console.log('✅ Tipo de vía creado:', response);
            } else {
                UbicacionCore.mostrarError(response.error || 'Error al crear el tipo de vía');
                console.error('❌ Error del servidor:', response);
            }

            return response;

        } catch (error) {
            UbicacionCore.mostrarError('Error técnico al crear el tipo de vía');
            console.error('❌ Error en crearTipoVia:', error);
            return { ok: false, error: error.message };
        }
    },

    // =========================================================================
    // UTILIDADES
    // =========================================================================
    
    /**
     * Limpia un formulario de alta
     * 
     * @param {Array<string>} camposIds - Array de IDs de campos a limpiar
     * 
     * @example
     * Alta.limpiarFormulario(['nombre_calle', 'cp', 'barrio']);
     */
    limpiarFormulario(camposIds) {
        camposIds.forEach(id => {
            const campo = document.getElementById(id);
            if (campo) {
                campo.value = '';
            }
        });
        
        console.log('🗑️ Formulario limpiado');
    },

    /**
     * Valida un formulario completo antes de enviarlo
     * 
     * @param {string} formId - ID del formulario
     * @returns {boolean} - true si es válido
     */
    validarFormulario(formId) {
        const form = document.getElementById(formId);
        if (!form) return false;

        // Usar validación nativa del navegador
        return form.checkValidity();
    }
};

// Log de inicialización
console.log('✅ Alta.js cargado correctamente');