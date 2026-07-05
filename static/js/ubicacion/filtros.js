/* =============================================================================
   FILTROS.JS - BÚSQUEDA Y FILTRADO ALFABÉTICO DE CALLES
   =============================================================================
   Proyecto: Ubicación España - Sistema de gestión de vías públicas
   Autor: Tino Hierro
   Fecha: 2026-05-23
   Versión: 1.0.0
   
   DESCRIPCIÓN:
   Módulo encargado de:
   - Búsqueda de calles según contexto (provincia, municipio, tipo de vía)
   - Generación de badges alfabéticos dinámicos
   - Filtrado de calles por letra (A-Z)
   - Renderizado de tabla de resultados
   - Gestión de estado de filtros activos
   
   DEPENDENCIAS:
   - core.js (UbicacionCore)
   
   ENDPOINTS:
   - GET /helpers_vias/calles?id_municipio=X&id_tipo_via=Y&q=texto
   
   ESTRUCTURA HTML REQUERIDA:
   - #tabla-calles (table con thead y tbody)
   - #alfabetico-container (div contenedor de badges)
   - #alfabetico-badges (div donde se insertan los badges)
   - #resumen-total (span para contador de registros)
   
   USO:
   await Filtros.buscarCalles(idMunicipio, idTipoVia, 'texto');
   Filtros.filtrarPorLetra('A');
   Filtros.limpiar();
   ============================================================================= */

const Filtros = {
    
    // =========================================================================
    // ESTADO GLOBAL
    // =========================================================================
    
    /**
     * Array con todas las calles cargadas desde el backend
     * @type {Array<Object>}
     */
    todasLasCalles: [],

    /**
     * Letra actualmente filtrada (null = mostrar todas)
     * @type {string|null}
     */
    letraActiva: null,

    // =========================================================================
    // CONFIGURACIÓN
    // =========================================================================
    
    config: {
        endpoints: {
            calles: '/helpers_vias/calles'
        },
        
        // Selectores DOM
        selectores: {
            tabla: 'tabla-calles',
            tbody: '#tabla-calles tbody',
            alfabeticoContainer: 'alfabetico-container',
            alfabeticoBadges: 'alfabetico-badges',
            resumenTotal: 'resumen-total'
        },

        // Configuración de visualización
        mostrarCodigoPostal: true,
        mostrarBarrio: true,
        animarTabla: true
    },

    // =========================================================================
    // BÚSQUEDA DE CALLES
    // =========================================================================
    
    /**
     * Busca calles según los filtros especificados
     * 
     * @param {number} idMunicipio - ID del municipio (obligatorio)
     * @param {number} idTipoVia - ID del tipo de vía (obligatorio)
     * @param {string} texto - Filtro de texto opcional (búsqueda en nombre calle)
     * @returns {Promise<Array>} - Array de calles encontradas
     * 
     * Estructura de respuesta esperada:
     * {
     *   ok: true,
     *   calles: [
     *     {
     *       idtbl_calles: 1,
     *       idtbl_municipios: 395,
     *       idtbl_tipos_de_vias: 1,
     *       calles: 'Mayor',
     *       Codigopostal: '05001',
     *       Barrio: 'Centro'
     *     },
     *     ...
     *   ]
     * }
     * 
     * FLUJO:
     * 1. Validar contexto obligatorio (municipio + tipo de vía)
     * 2. Construir URL con parámetros
     * 3. Hacer petición al backend
     * 4. Guardar calles en estado global
     * 5. Generar badges alfabéticos
     * 6. Renderizar tabla completa
     * 7. Actualizar contador
     * 
     * @example
     * const calles = await Filtros.buscarCalles(395, 1); // Calles de Ávila
     * const filtradas = await Filtros.buscarCalles(395, 1, 'mayor'); // Solo "Mayor"
     */
    async buscarCalles(idMunicipio, idTipoVia, texto = "") {
        // Validar contexto obligatorio
        if (!idMunicipio || !idTipoVia) {
            UbicacionCore.mostrarError('Debes seleccionar municipio y tipo de vía antes de buscar');
            return [];
        }

        try {
            // Construir URL con parámetros
            const url = new URL(this.config.endpoints.calles, window.location.origin);
            url.searchParams.set('id_municipio', idMunicipio);
            url.searchParams.set('id_tipo_via', idTipoVia);
            
            if (texto) {
                url.searchParams.set('q', texto);
            }

            console.log(`🔍 Buscando calles: municipio=${idMunicipio}, tipo=${idTipoVia}, texto="${texto}"`);

            // Petición al backend
            const data = await UbicacionCore.fetchJSON(url.toString());
            
            // Guardar resultados en estado global
            this.todasLasCalles = data.calles || [];
            
            // Resetear filtro activo
            this.letraActiva = null;
            
            // Generar badges alfabéticos
            this.generarBadgesAlfabeticos();
            
            // Renderizar tabla completa
            this.renderizarTabla(this.todasLasCalles);
            
            // Actualizar contador
            this.actualizarContador(this.todasLasCalles.length);
            
            console.log(`✅ Encontradas ${this.todasLasCalles.length} calles`);
            
            return this.todasLasCalles;

        } catch (error) {
            UbicacionCore.mostrarError('Error al buscar calles');
            console.error('Error en buscarCalles:', error);
            return [];
        }
    },

    // =========================================================================
    // BADGES ALFABÉTICOS
    // =========================================================================
    
    /**
     * Genera badges alfabéticos basados en las calles cargadas
     * 
     * ALGORITMO:
     * 1. Agrupar calles por primera letra (normalizada, sin acentos)
     * 2. Contar cantidad de calles por letra
     * 3. Ordenar letras alfabéticamente
     * 4. Crear un badge por cada letra
     * 5. Agregar badge especial "Todas"
     * 6. Asignar event listeners para filtrado
     * 
     * EJEMPLO DE SALIDA:
     * [A:15] [B:8] [C:23] [D:12] ... [Todas:150]
     * 
     * @private
     */
    generarBadgesAlfabeticos() {
        const container = document.getElementById(this.config.selectores.alfabeticoBadges);
        const wrapper = document.getElementById(this.config.selectores.alfabeticoContainer);

        if (!container || !wrapper) {
            console.warn('⚠️ Contenedor de badges alfabéticos no encontrado');
            return;
        }

        // Limpiar badges existentes
        container.innerHTML = "";

        // Si no hay calles, ocultar container
        if (this.todasLasCalles.length === 0) {
            wrapper.style.display = 'none';
            return;
        }

        // PASO 1: Agrupar por primera letra
        const grupos = {};
        
        this.todasLasCalles.forEach(calle => {
            const nombreCalle = calle.calles || "";
            if (!nombreCalle) return;
            
            // Obtener primera letra normalizada (sin acentos, mayúscula)
            const letra = UbicacionCore.primeraLetra(nombreCalle);
            
            if (!letra) return;
            
            // Incrementar contador de la letra
            grupos[letra] = (grupos[letra] || 0) + 1;
        });

        // PASO 2: Ordenar letras alfabéticamente
        const letrasOrdenadas = Object.keys(grupos).sort();

        // PASO 3: Crear badges
        letrasOrdenadas.forEach(letra => {
            const badge = this.crearBadge(letra, grupos[letra]);
            container.appendChild(badge);
        });

        // PASO 4: Badge especial "Todas"
        const badgeTodas = this.crearBadgeTodas(this.todasLasCalles.length);
        container.appendChild(badgeTodas);

        // Mostrar container
        wrapper.style.display = 'block';
        
        console.log(`✅ Generados ${letrasOrdenadas.length} badges alfabéticos`);
    },

    /**
     * Crea un badge alfabético individual
     * 
     * @param {string} letra - Letra del badge (ej: 'A', 'B', 'C')
     * @param {number} cantidad - Cantidad de calles con esa letra
     * @returns {HTMLElement} - Elemento span.badge-letra
     * 
     * @private
     */
    crearBadge(letra, cantidad) {
        const badge = document.createElement('span');
        badge.className = 'badge-letra';
        badge.textContent = `${letra}:${cantidad}`;
        badge.dataset.letra = letra;
        badge.title = `Filtrar por letra ${letra} (${cantidad} calle${cantidad === 1 ? '' : 's'})`;
        
        // Event listener: filtrar al hacer clic
        badge.addEventListener('click', () => {
            this.filtrarPorLetra(letra);
        });
        
        return badge;
    },

    /**
     * Crea el badge especial "Todas"
     * 
     * @param {number} cantidad - Total de calles
     * @returns {HTMLElement} - Elemento span.badge-letra.todas
     * 
     * @private
     */
    crearBadgeTodas(cantidad) {
        const badge = document.createElement('span');
        badge.className = 'badge-letra todas activo'; // Activo por defecto
        badge.textContent = `Todas:${cantidad}`;
        badge.title = `Mostrar todas las calles (${cantidad})`;
        
        // Event listener: mostrar todas al hacer clic
        badge.addEventListener('click', () => {
            this.filtrarPorLetra(null);
        });
        
        return badge;
    },

    // =========================================================================
    // FILTRADO POR LETRA
    // =========================================================================
    
    /**
     * Filtra las calles por la letra seleccionada
     * 
     * @param {string|null} letra - Letra a filtrar ('A', 'B', ..., null=todas)
     * 
     * FLUJO:
     * 1. Actualizar letra activa en estado
     * 2. Actualizar clases CSS de badges (activo/inactivo)
     * 3. Filtrar array de calles
     * 4. Renderizar tabla con calles filtradas
     * 5. Actualizar contador
     * 
     * @example
     * Filtros.filtrarPorLetra('A'); // Solo calles que empiezan con A
     * Filtros.filtrarPorLetra(null); // Todas las calles
     */
    filtrarPorLetra(letra) {
        this.letraActiva = letra;

        console.log(`🔤 Filtrando por letra: ${letra || 'TODAS'}`);

        // PASO 1: Actualizar badges activos
        this.actualizarBadgesActivos(letra);

        // PASO 2: Filtrar calles
        let callesFiltradas;
        
        if (letra === null) {
            // Mostrar todas
            callesFiltradas = this.todasLasCalles;
        } else {
            // Filtrar por letra
            callesFiltradas = this.todasLasCalles.filter(calle => {
                const nombreCalle = calle.calles || "";
                const primeraLetra = UbicacionCore.primeraLetra(nombreCalle);
                return primeraLetra === letra;
            });
        }

        // PASO 3: Renderizar tabla
        this.renderizarTabla(callesFiltradas);

        // PASO 4: Actualizar contador
        this.actualizarContador(callesFiltradas.length);
        
        console.log(`✅ Mostrando ${callesFiltradas.length} calles`);
    },

    /**
     * Actualiza las clases CSS de los badges (activo/inactivo)
     * 
     * @param {string|null} letraActiva - Letra activa (null = "Todas")
     * @private
     */
    actualizarBadgesActivos(letraActiva) {
        // Quitar clase activo de todos los badges
        document.querySelectorAll('.badge-letra').forEach(badge => {
            badge.classList.remove('activo');
        });

        if (letraActiva === null) {
            // Activar badge "Todas"
            const badgeTodas = document.querySelector('.badge-letra.todas');
            if (badgeTodas) {
                badgeTodas.classList.add('activo');
            }
        } else {
            // Activar badge de la letra seleccionada
            document.querySelectorAll('.badge-letra').forEach(badge => {
                if (badge.dataset.letra === letraActiva) {
                    badge.classList.add('activo');
                }
            });
        }
    },

    // =========================================================================
    // RENDERIZADO DE TABLA
    // =========================================================================
    
    /**
     * Renderiza la tabla de calles
     * 
     * @param {Array<Object>} calles - Array de objetos calle a mostrar
     * 
     * Estructura esperada de cada calle:
     * {
     *   idtbl_calles: number,
     *   idtbl_tipos_de_vias: number,
     *   calles: string,
     *   Codigopostal?: string,
     *   Barrio?: string
     * }
     * 
     * NOTA: Los campos Codigopostal y Barrio son opcionales
     * 
     * @example
     * Filtros.renderizarTabla([
     *   {idtbl_calles: 1, calles: 'Mayor', idtbl_tipos_de_vias: 1},
     *   {idtbl_calles: 2, calles: 'Real', idtbl_tipos_de_vias: 1}
     * ]);
     */
    renderizarTabla(calles) {
        const tbody = document.querySelector(this.config.selectores.tbody);
        
        if (!tbody) {
            console.warn('⚠️ tbody de tabla no encontrado');
            return;
        }

        // Limpiar tbody
        tbody.innerHTML = "";

        // Si no hay calles, mostrar mensaje
        if (calles.length === 0) {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td colspan="5" style="text-align:center; padding:20px; color:var(--text-secondary);">
                    No se encontraron calles con los filtros seleccionados
                </td>
            `;
            tbody.appendChild(tr);
            return;
        }

        // Renderizar cada calle
        calles.forEach((calle, index) => {
            const tr = document.createElement('tr');
            
            // Aplicar animación escalonada (opcional)
            if (this.config.animarTabla) {
                tr.style.animation = `fadeIn 0.3s ease ${index * 0.02}s forwards`;
                tr.style.opacity = '0';
            }
            
            tr.innerHTML = `
                <td>${calle.idtbl_calles}</td>
                <td><span class="badge">${calle.idtbl_tipos_de_vias}</span></td>
                <td><strong>${this.escaparHTML(calle.calles)}</strong></td>
                <td>${this.config.mostrarCodigoPostal ? (calle.Codigopostal || '–') : ''}</td>
                <td>${this.config.mostrarBarrio ? (calle.Barrio || '–') : ''}</td>
            `;
            
            tbody.appendChild(tr);
        });

        console.log(`✅ Renderizadas ${calles.length} calles en tabla`);
    },

    /**
     * Escapa HTML para prevenir XSS
     * @param {string} texto - Texto a escapar
     * @returns {string} - Texto escapado
     * @private
     */
    escaparHTML(texto) {
        const div = document.createElement('div');
        div.textContent = texto;
        return div.innerHTML;
    },

    // =========================================================================
    // CONTADOR DE REGISTROS
    // =========================================================================
    
    /**
     * Actualiza el contador de registros mostrados
     * 
     * @param {number} cantidad - Número de registros
     * 
     * Formato de salida:
     * - "0 registros"
     * - "1 registro"
     * - "150 registros"
     */
    actualizarContador(cantidad) {
        const label = document.getElementById(this.config.selectores.resumenTotal);
        
        if (label) {
            label.textContent = `${cantidad} registro${cantidad === 1 ? '' : 's'}`;
        }
    },

    // =========================================================================
    // LIMPIEZA
    // =========================================================================
    
    /**
     * Limpia todos los resultados y resetea el estado
     * 
     * ACCIONES:
     * - Vacía array de calles
     * - Resetea letra activa
     * - Limpia tbody de tabla
     * - Oculta badges alfabéticos
     * - Resetea contador a 0
     * 
     * @example
     * Filtros.limpiar(); // Al cambiar de municipio/tipo de vía
     */
    limpiar() {
        // Resetear estado
        this.todasLasCalles = [];
        this.letraActiva = null;
        
        // Limpiar tabla
        const tbody = document.querySelector(this.config.selectores.tbody);
        if (tbody) {
            tbody.innerHTML = "";
        }
        
        // Ocultar badges alfabéticos
        const wrapper = document.getElementById(this.config.selectores.alfabeticoContainer);
        if (wrapper) {
            wrapper.style.display = 'none';
        }
        
        // Resetear contador
        this.actualizarContador(0);
        
        console.log('🗑️ Resultados limpiados');
    },

    // =========================================================================
    // UTILIDADES
    // =========================================================================
    
    /**
     * Obtiene las calles actualmente visibles (filtradas o todas)
     * @returns {Array<Object>} - Calles visibles
     */
    getCallesVisibles() {
        if (this.letraActiva === null) {
            return this.todasLasCalles;
        }
        
        return this.todasLasCalles.filter(calle => {
            return UbicacionCore.primeraLetra(calle.calles) === this.letraActiva;
        });
    },

    /**
     * Obtiene estadísticas de las calles cargadas
     * @returns {Object} - {total, porLetra: {A: 15, B: 8, ...}}
     */
    getEstadisticas() {
        const porLetra = {};
        
        this.todasLasCalles.forEach(calle => {
            const letra = UbicacionCore.primeraLetra(calle.calles);
            porLetra[letra] = (porLetra[letra] || 0) + 1;
        });
        
        return {
            total: this.todasLasCalles.length,
            porLetra: porLetra
        };
    }
};

// Agregar animación CSS (si no existe en el CSS global)
if (!document.querySelector('style[data-filtros-animations]')) {
    const style = document.createElement('style');
    style.setAttribute('data-filtros-animations', 'true');
    style.textContent = `
        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(5px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
    `;
    document.head.appendChild(style);
}

// Log de inicialización
console.log('✅ Filtros.js cargado correctamente');