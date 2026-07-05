/* =============================================================================
   CORE.JS - UTILIDADES BASE PARA GESTIÓN DE UBICACIONES
   =============================================================================
   Proyecto: Ubicación España - Sistema de gestión de vías públicas
   Autor: Tino Hierro
   Fecha: 2026-05-23
   Versión: 1.0.0
   
   DESCRIPCIÓN:
   Librería de funciones reutilizables para:
   - Peticiones HTTP con manejo de errores
   - Normalización de textos (sin acentos)
   - Manipulación de elementos DOM (selects)
   - Validación de formularios
   - Mensajes de usuario
   
   DEPENDENCIAS:
   - Ninguna (JavaScript vanilla)
   
   USO:
   import desde otros módulos:
   UbicacionCore.fetchJSON(url, options)
   UbicacionCore.normalizarTexto(texto)
   UbicacionCore.llenarSelect(selectId, opciones)
   ============================================================================= */

const UbicacionCore = {
    
    // =========================================================================
    // CONFIGURACIÓN
    // =========================================================================
    
    config: {
        timeout: 30000, // Timeout para peticiones (30 segundos)
        debug: true     // Modo debug (logs en consola)
    },

    // =========================================================================
    // PETICIONES HTTP
    // =========================================================================
    
    /**
     * Realiza una petición fetch con manejo de errores estandarizado
     * 
     * @param {string} url - URL del endpoint
     * @param {Object} options - Opciones de fetch (method, headers, body)
     * @returns {Promise<Object>} - Respuesta JSON parseada
     * @throws {Error} - Si la petición falla o el servidor responde con error
     * 
     * @example
     * const data = await UbicacionCore.fetchJSON('/api/provincias');
     * const result = await UbicacionCore.fetchJSON('/api/calles', {
     *     method: 'POST',
     *     body: JSON.stringify({nombre: 'Mayor'})
     * });
     */
    async fetchJSON(url, options = {}) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);

        try {
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                signal: controller.signal,
                ...options
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            
            if (this.config.debug) {
                console.log(`✅ Fetch OK: ${url}`, data);
            }

            return data;

        } catch (error) {
            clearTimeout(timeoutId);
            
            if (error.name === 'AbortError') {
                console.error('❌ Timeout en petición:', url);
                throw new Error('La petición tardó demasiado tiempo');
            }

            console.error('❌ Error en fetch:', url, error);
            throw error;
        }
    },

    // =========================================================================
    // NORMALIZACIÓN DE TEXTOS
    // =========================================================================
    
    /**
     * Normaliza un texto eliminando acentos y convirtiendo a mayúsculas
     * 
     * @param {string} texto - Texto a normalizar
     * @returns {string} - Texto normalizado (sin acentos, mayúsculas)
     * 
     * @example
     * UbicacionCore.normalizarTexto('Ávila') // → 'AVILA'
     * UbicacionCore.normalizarTexto('José María') // → 'JOSE MARIA'
     */
    normalizarTexto(texto) {
        if (!texto) return "";
        
        return texto
            .toString()
            .toUpperCase()
            .normalize("NFD")                    // Descompone caracteres (á → a + ´)
            .replace(/[\u0300-\u036f]/g, "");   // Elimina marcas diacríticas
    },

    /**
     * Obtiene la primera letra normalizada de un texto
     * 
     * @param {string} texto - Texto
     * @returns {string} - Primera letra sin acentos, en mayúscula
     * 
     * @example
     * UbicacionCore.primeraLetra('Ávila') // → 'A'
     * UbicacionCore.primeraLetra('Ñoño') // → 'Ñ'
     */
    primeraLetra(texto) {
        if (!texto) return "";
        return this.normalizarTexto(texto.charAt(0));
    },

    // =========================================================================
    // MANIPULACIÓN DE DOM
    // =========================================================================
    
    /**
     * Limpia un select y lo rellena con nuevas opciones
     * 
     * @param {string} selectId - ID del elemento select
     * @param {Array<Object>} opciones - Array de {value, text}
     * @param {string|null} placeholder - Texto de opción vacía inicial (opcional)
     * 
     * @example
     * UbicacionCore.llenarSelect('provincia', [
     *     {value: 1, text: 'Ávila'},
     *     {value: 2, text: 'Burgos'}
     * ]);
     * 
     * UbicacionCore.llenarSelect('municipio', municipios, '-- Selecciona --');
     */
    llenarSelect(selectId, opciones, placeholder = null) {
        const select = document.getElementById(selectId);
        
        if (!select) {
            console.warn(`⚠️ Select con id "${selectId}" no encontrado`);
            return;
        }

        // Limpiar opciones existentes
        select.innerHTML = "";

        // Agregar placeholder si se especifica
        if (placeholder) {
            const opt = document.createElement("option");
            opt.value = "";
            opt.textContent = placeholder;
            opt.disabled = true;
            opt.selected = true;
            select.appendChild(opt);
        }

        // Agregar opciones
        opciones.forEach(item => {
            const opt = document.createElement("option");
            opt.value = item.value;
            opt.textContent = item.text;
            
            // Soportar opciones pre-seleccionadas
            if (item.selected) {
                opt.selected = true;
            }
            
            select.appendChild(opt);
        });

        if (this.config.debug) {
            console.log(`✅ Select "${selectId}" rellenado con ${opciones.length} opciones`);
        }
    },

    /**
     * Obtiene el valor seleccionado de un select
     * 
     * @param {string} selectId - ID del select
     * @returns {string|null} - Valor seleccionado o null
     */
    getSelectValue(selectId) {
        const select = document.getElementById(selectId);
        return select ? select.value : null;
    },

    /**
     * Obtiene el texto visible de la opción seleccionada
     * 
     * @param {string} selectId - ID del select
     * @returns {string} - Texto de la opción seleccionada
     */
    getSelectText(selectId) {
        const select = document.getElementById(selectId);
        if (!select || !select.selectedIndex) return "–";
        
        return select.options[select.selectedIndex].textContent;
    },

    // =========================================================================
    // VALIDACIÓN
    // =========================================================================
    
    /**
     * Valida que todos los campos requeridos tengan valor
     * 
     * @param {Object} campos - Objeto {nombreCampo: valor}
     * @returns {boolean} - true si todos los campos tienen valor
     * 
     * @example
     * const valido = UbicacionCore.validarCamposRequeridos({
     *     'Provincia': idProvincia,
     *     'Municipio': idMunicipio,
     *     'Nombre de calle': nombreCalle
     * });
     */
    validarCamposRequeridos(campos) {
        for (const [nombre, valor] of Object.entries(campos)) {
            if (!valor || valor.toString().trim() === "") {
                this.mostrarError(`El campo "${nombre}" es obligatorio`);
                return false;
            }
        }
        return true;
    },

    /**
     * Valida que un email tenga formato correcto
     * 
     * @param {string} email - Email a validar
     * @returns {boolean} - true si es válido
     */
    validarEmail(email) {
        const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return regex.test(email);
    },

    /**
     * Valida que un código postal español sea correcto
     * 
     * @param {string} cp - Código postal
     * @returns {boolean} - true si es válido (5 dígitos)
     */
    validarCodigoPostal(cp) {
        return /^\d{5}$/.test(cp);
    },

    // =========================================================================
    // MENSAJES DE USUARIO
    // =========================================================================
    
    /**
     * Muestra un mensaje de error al usuario
     * 
     * @param {string} mensaje - Mensaje a mostrar
     * 
     * TODO: Reemplazar alert() por toast/modal personalizado
     */
    mostrarError(mensaje) {
        alert(`❌ ${mensaje}`);
        console.error('Error:', mensaje);
    },

    /**
     * Muestra un mensaje de éxito al usuario
     * 
     * @param {string} mensaje - Mensaje a mostrar
     * 
     * TODO: Reemplazar alert() por toast/modal personalizado
     */
    mostrarExito(mensaje) {
        alert(`✅ ${mensaje}`);
        console.log('Éxito:', mensaje);
    },

    /**
     * Muestra un mensaje de advertencia al usuario
     * 
     * @param {string} mensaje - Mensaje a mostrar
     */
    mostrarAdvertencia(mensaje) {
        alert(`⚠️ ${mensaje}`);
        console.warn('Advertencia:', mensaje);
    },

    /**
     * Muestra una confirmación y espera respuesta del usuario
     * 
     * @param {string} mensaje - Mensaje de confirmación
     * @returns {boolean} - true si el usuario confirmó
     */
    confirmar(mensaje) {
        return confirm(`❓ ${mensaje}`);
    },

    // =========================================================================
    // UTILIDADES VARIAS
    // =========================================================================
    
    /**
     * Espera un tiempo determinado (para debugging)
     * 
     * @param {number} ms - Milisegundos a esperar
     * @returns {Promise<void>}
     * 
     * @example
     * await UbicacionCore.sleep(1000); // Espera 1 segundo
     */
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    },

    /**
     * Genera un ID único
     * 
     * @returns {string} - ID único basado en timestamp
     */
    generarId() {
        return `id_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    },

    /**
     * Formatea una fecha a formato español
     * 
     * @param {Date|string} fecha - Fecha a formatear
     * @returns {string} - Fecha en formato dd/mm/yyyy
     */
    formatearFecha(fecha) {
        const d = new Date(fecha);
        const dia = String(d.getDate()).padStart(2, '0');
        const mes = String(d.getMonth() + 1).padStart(2, '0');
        const anio = d.getFullYear();
        return `${dia}/${mes}/${anio}`;
    },

    /**
     * Limpia un string de caracteres peligrosos para SQL/XSS
     * 
     * @param {string} texto - Texto a limpiar
     * @returns {string} - Texto limpio
     */
    sanitizarTexto(texto) {
        if (!texto) return "";
        
        return texto
            .toString()
            .trim()
            .replace(/[<>]/g, "")  // Elimina < y >
            .substring(0, 255);     // Limita longitud
    }
};

// Exportar para uso en otros módulos (si se usa bundler)
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UbicacionCore;
}

// Log de inicialización
if (UbicacionCore.config.debug) {
    console.log('✅ UbicacionCore cargado correctamente');
}