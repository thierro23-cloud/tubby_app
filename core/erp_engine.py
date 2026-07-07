# =============================================================================
# 🧠 CORE.ERP_ENGINE · MOTOR DE CONSTRUCCIÓN DINÁMICA DE UI
# =============================================================================
#
# 🎯 PROPÓSITO GENERAL:
# ────────────────────────────────────────────────────────────────────────────
# Este módulo actúa como capa de abstracción entre el registro declarativo
# de paneles (core.registry) y las vistas del sistema, proporcionando
# metadatos estructurados para construir interfaces dinámicas.
#
# ⚠️ RESPONSABILIDAD CRÍTICA:
# Este módulo NO valida seguridad ni permisos. Su única función es
# proporcionar datos estructurados (metadatos de UI). La validación
# de seguridad SIEMPRE debe hacerse en:
#   1. core.middleware (before_request global)
#   2. core.permisos (tiene_permiso + endpoint_activo)
#
# 🏗️ ARQUITECTURA:
# ────────────────────────────────────────────────────────────────────────────
#
#   ┌─────────────────────────────────────────────────────────────────┐
#   │  CORE.REGISTRY (Fuente de datos)                                │
#   │  • Define paneles, tarjetas, módulos                            │
#   │  • Estructura declarativa con iconos, títulos, endpoints        │
#   └──────────────────────┬──────────────────────────────────────────┘
#                          │
#                          ▼
#   ┌─────────────────────────────────────────────────────────────────┐
#   │  CORE.ERP_ENGINE (Este archivo - Transformador)                 │
#   │  • Extrae metadatos de registry                                 │
#   │  • Aplica lógica de negocio básica (agrupación, ordenamiento)   │
#   │  • NO valida permisos (solo estructura datos)                   │
#   └──────────────────────┬──────────────────────────────────────────┘
#                          │
#                          ▼
#   ┌─────────────────────────────────────────────────────────────────┐
#   │  VISTAS (Consumidores)                                          │
#   │  • Llaman a funciones de este módulo                            │
#   │  • DEBEN validar permisos con tiene_permiso()                   │
#   │  • Renderizan UI con datos filtrados                            │
#   └─────────────────────────────────────────────────────────────────┘
#
# 🔥 REGLAS DE ORO:
# ────────────────────────────────────────────────────────────────────────────
# 1. Este módulo NUNCA decide qué puede ver un usuario
# 2. Este módulo SOLO estructura información visual
# 3. La seguridad es responsabilidad del consumidor
# 4. Separación clara: UI metadata ≠ Security validation
#
# 🎯 CASOS DE USO VÁLIDOS:
# ────────────────────────────────────────────────────────────────────────────
# ✔ Construir menús de navegación (con validación posterior)
# ✔ Generar dashboards dinámicos (con filtrado por permisos)
# ✔ Proporcionar metadatos para componentes frontend (iconos, colores)
# ✔ Organizar secciones del sistema de forma declarativa
#
# ❌ CASOS DE USO INVÁLIDOS:
# ────────────────────────────────────────────────────────────────────────────
# ✘ Usar este módulo para decidir accesos (sin validar permisos después)
# ✘ Confiar en campos "roles" del registry para seguridad real
# ✘ Saltarse tiene_permiso() asumiendo que esto ya valida
#
# 📊 EJEMPLO DE FLUJO CORRECTO:
# ────────────────────────────────────────────────────────────────────────────
#
#   # En tu vista del dashboard:
#   from core.erp_engine import obtener_metadatos_tarjetas
#   from core.permisos import tiene_permiso
#
#   @super_admin_bp.route("/dashboard")
#   def dashboard():
#       # 1. Obtener TODOS los metadatos (sin filtrar)
#       todas_las_tarjetas = obtener_metadatos_tarjetas()
#
#       # 2. Filtrar por permisos REALES de BD
#       tarjetas_visibles = [
#           t for t in todas_las_tarjetas
#           if tiene_permiso(t["endpoint"], session["rol_id"])
#       ]
#
#       # 3. Renderizar solo las permitidas
#       return render_template("dashboard.html", tarjetas=tarjetas_visibles)
#
# =============================================================================


# =============================================================================
# 1️⃣ IMPORTS · DEPENDENCIAS DEL MÓDULO
# =============================================================================
#
# 📌 core.registry:
# ──────────────────────────────────────────────────────────────────────────
# Módulo centralizado que contiene la definición declarativa de todos
# los paneles, tarjetas y módulos del sistema.
#
# 🔹 obtener_paneles():
#    Devuelve una lista de diccionarios con la siguiente estructura:
#
#    [
#        {
#            "nombre": "Panel de Gestión",
#            "descripcion": "Descripción del panel",
#            "modulos": [
#                {
#                    "nombre": "Contenedores",
#                    "endpoint": "contenedores_bp.listar",
#                    "icono": "fa-trash"
#                },
#                ...
#            ],
#            "tarjetas": [
#                {
#                    "titulo": "Gestión de Contenedores",
#                    "descripcion": "Administrar contenedores del municipio",
#                    "endpoint": "contenedores_bp.listar",
#                    "icono": "fa-trash",
#                    "color": "blue",
#                    "prioridad": 1
#                },
#                ...
#            ]
#        },
#        ...
#    ]
#
# 👉 IMPORTANTE:
#    El campo "roles" que pueda existir en tarjetas es LEGACY.
#    NO debe usarse para validación de seguridad.
#    Solo sirve como hint visual o documentación.
#
# =============================================================================

from core.registry import obtener_paneles

# =============================================================================
# 2️⃣ EXTRACCIÓN DE MÓDULOS · LISTA UNIFICADA DEL SISTEMA
# =============================================================================
#
# 🎯 OBJETIVO:
# ──────────────────────────────────────────────────────────────────────────
# Extraer TODOS los módulos registrados en el sistema, independientemente
# del panel al que pertenezcan, y devolverlos en una lista plana unificada.
#
# 📌 ¿QUÉ ES UN MÓDULO?
# ──────────────────────────────────────────────────────────────────────────
# Un módulo representa una funcionalidad completa del sistema:
#   - Contenedores
#   - Parkings
#   - Proveedores
#   - Usuarios
#   - Reportes
#
# Cada módulo tiene:
#   • nombre: identificador legible
#   • endpoint: ruta interna de Flask (ej: "contenedores_bp.listar")
#   • icono: clase CSS para representación visual
#   • metadata adicional (color, descripción, etc.)
#
# 🔄 FLUJO DE EJECUCIÓN:
# ──────────────────────────────────────────────────────────────────────────
# 1. Obtiene la estructura completa de paneles desde core.registry
# 2. Itera sobre cada panel definido
# 3. Extrae la lista de módulos de cada panel
# 4. Agrega esos módulos a una lista acumulativa
# 5. Devuelve la lista completa sin duplicados implícitos
#
# 💡 CASOS DE USO:
# ──────────────────────────────────────────────────────────────────────────
# ✔ Construir menús de navegación globales
# ✔ Inicializar sistemas de búsqueda o autocompletado
# ✔ Generar mapas de sitio dinámicos
# ✔ Documentación automática del sistema
# ✔ Análisis de cobertura de módulos
#
# ⚠️ IMPORTANTE - VALIDACIÓN DE SEGURIDAD:
# ──────────────────────────────────────────────────────────────────────────
# Esta función NO filtra por permisos.
# Si usas el resultado para mostrar UI, DEBES validar después:
#
#   modulos = obtener_modulos_activos()
#   modulos_permitidos = [
#       m for m in modulos
#       if tiene_permiso(m["endpoint"], session["rol_id"])
#   ]
#
# 🔧 MANEJO DE ERRORES:
# ──────────────────────────────────────────────────────────────────────────
# Se usa .get("modulos", []) para evitar KeyError si un panel no define
# la clave "modulos". Esto hace el sistema robusto ante cambios en registry.
#
# =============================================================================


def obtener_modulos_activos():
    """
    📦 Devuelve todos los módulos registrados en el sistema.

    Esta función NO valida permisos. Solo proporciona metadatos estructurados.
    El consumidor DEBE filtrar por tiene_permiso() antes de mostrar UI.

    :return: lista de diccionarios con metadata de módulos
    :rtype: list[dict]

    Estructura de retorno:
    [
        {
            "nombre": "Contenedores",
            "endpoint": "contenedores_bp.listar",
            "icono": "fa-trash",
            ...
        },
        ...
    ]

    Ejemplo de uso seguro:
        modulos = obtener_modulos_activos()
        modulos_visibles = [
            m for m in modulos
            if tiene_permiso(m["endpoint"], session["rol_id"])
        ]
    """

    # ---------------------------------------------------------
    # 📥 OBTENER ESTRUCTURA COMPLETA DE PANELES
    # ---------------------------------------------------------
    # obtener_paneles() devuelve la definición declarativa completa
    # desde core.registry. Puede incluir múltiples paneles organizados
    # por categorías funcionales (Gestión, Administración, Reportes, etc.)
    paneles = obtener_paneles()

    # ---------------------------------------------------------
    # 📦 INICIALIZAR LISTA ACUMULATIVA
    # ---------------------------------------------------------
    # Esta lista almacenará TODOS los módulos de TODOS los paneles
    # en una estructura plana para fácil consumo
    modulos = []

    # ---------------------------------------------------------
    # 🔄 RECORRIDO DE PANELES Y EXTRACCIÓN
    # ---------------------------------------------------------
    # Iteramos sobre cada panel definido en el registry.
    # Cada panel puede contener 0 o más módulos en su clave "modulos".
    for panel in paneles:

        # -----------------------------------------------------
        # 🔍 EXTRACCIÓN SEGURA CON .get()
        # -----------------------------------------------------
        # Usamos .get("modulos", []) en lugar de ["modulos"] para:
        #   1. Evitar KeyError si un panel no tiene módulos
        #   2. Devolver lista vacía como fallback
        #   3. Hacer el código robusto ante cambios en registry
        #
        # .extend() agrega todos los elementos de la lista a la vez,
        # en lugar de .append() que agregaría la lista como un solo elemento
        modulos.extend(panel.get("modulos", []))

    # ---------------------------------------------------------
    # 📤 RETORNO DE LISTA UNIFICADA
    # ---------------------------------------------------------
    # Devolvemos la lista completa sin filtros ni validaciones.
    # La responsabilidad de seguridad es del consumidor.
    return modulos


# =============================================================================
# 3️⃣ EXTRACCIÓN DE TARJETAS · METADATOS PARA DASHBOARDS
# =============================================================================
#
# 🎯 OBJETIVO:
# ──────────────────────────────────────────────────────────────────────────
# Proporcionar una lista unificada de todas las tarjetas definidas en
# el sistema, sin aplicar filtros de seguridad (solo estructura de datos).
#
# 📌 ¿QUÉ ES UNA TARJETA?
# ──────────────────────────────────────────────────────────────────────────
# Una tarjeta es un componente visual del dashboard que representa:
#   • Una funcionalidad del sistema
#   • Un acceso rápido a un módulo
#   • Un resumen de información importante
#
# Estructura típica:
# {
#     "titulo": "Gestión de Contenedores",
#     "descripcion": "Administrar contenedores del municipio",
#     "endpoint": "contenedores_bp.listar",
#     "icono": "fa-trash",
#     "color": "blue",
#     "prioridad": 1,
#     "metricas": {
#         "total": "dashboard_bp.total_contenedores",
#         "pendientes": "dashboard_bp.contenedores_pendientes"
#     }
# }
#
# 🔄 FLUJO DE EJECUCIÓN:
# ──────────────────────────────────────────────────────────────────────────
# 1. Obtiene estructura completa de paneles desde registry
# 2. Itera sobre cada panel
# 3. Extrae tarjetas de cada panel
# 4. Acumula en lista unificada
# 5. Devuelve lista completa
#
# 💡 CASOS DE USO:
# ──────────────────────────────────────────────────────────────────────────
# ✔ Construir dashboards dinámicos por rol
# ✔ Generar páginas de inicio personalizadas
# ✔ Crear widgets configurables
# ✔ Sistemas de favoritos o accesos rápidos
#
# ⚠️ SEGURIDAD - VALIDACIÓN OBLIGATORIA:
# ──────────────────────────────────────────────────────────────────────────
# Esta función devuelve TODAS las tarjetas sin filtrar.
# El consumidor DEBE aplicar tiene_permiso() antes de renderizar:
#
#   tarjetas = obtener_metadatos_tarjetas()
#   tarjetas_seguras = [
#       t for t in tarjetas
#       if tiene_permiso(t["endpoint"], session["rol_id"])
#   ]
#
# 🎨 METADATOS DISPONIBLES:
# ──────────────────────────────────────────────────────────────────────────
# • titulo: texto visible en la tarjeta
# • descripcion: texto explicativo
# • endpoint: ruta interna para navegación
# • icono: clase CSS (FontAwesome, Material Icons, etc.)
# • color: código de color o clase CSS
# • prioridad: orden de visualización (menor = más prioritario)
# • metricas: endpoints para obtener datos numéricos
#
# =============================================================================


def obtener_metadatos_tarjetas():
    """
    🎴 Devuelve metadatos de todas las tarjetas del sistema.

    Esta función NO valida permisos ni seguridad.
    Solo proporciona información estructurada para construcción de UI.

    ⚠️ ADVERTENCIA DE SEGURIDAD:
    El consumidor DEBE validar permisos con tiene_permiso() antes de
    mostrar cualquier tarjeta al usuario.

    :return: lista de diccionarios con metadata de tarjetas
    :rtype: list[dict]

    Estructura de retorno:
    [
        {
            "titulo": "Gestión de Contenedores",
            "endpoint": "contenedores_bp.listar",
            "icono": "fa-trash",
            "color": "blue",
            ...
        },
        ...
    ]

    Ejemplo de uso seguro:
        from core.permisos import tiene_permiso

        tarjetas = obtener_metadatos_tarjetas()
        tarjetas_visibles = [
            t for t in tarjetas
            if tiene_permiso(t["endpoint"], session["rol_id"])
        ]
        return render_template("dashboard.html", tarjetas=tarjetas_visibles)
    """

    # ---------------------------------------------------------
    # 📥 OBTENER ESTRUCTURA DE PANELES
    # ---------------------------------------------------------
    # Cargamos toda la definición declarativa desde core.registry
    paneles = obtener_paneles()

    # ---------------------------------------------------------
    # 🎴 INICIALIZAR COLECCIÓN DE TARJETAS
    # ---------------------------------------------------------
    # Lista que acumulará todas las tarjetas de todos los paneles
    tarjetas = []

    # ---------------------------------------------------------
    # 🔄 RECORRIDO Y EXTRACCIÓN
    # ---------------------------------------------------------
    # Iteramos sobre cada panel para extraer sus tarjetas
    for panel in paneles:

        # -----------------------------------------------------
        # 🔍 EXTRACCIÓN SEGURA
        # -----------------------------------------------------
        # .get("tarjetas", []) evita KeyError si un panel no define tarjetas
        # .extend() agrega todos los elementos en una sola operación
        tarjetas.extend(panel.get("tarjetas", []))

    # ---------------------------------------------------------
    # 📤 RETORNO SIN FILTROS
    # ---------------------------------------------------------
    # Devolvemos la lista completa.
    # La responsabilidad de filtrado por permisos es del consumidor.
    return tarjetas


# =============================================================================
# 4️⃣ CONSTRUCCIÓN DE DASHBOARD SEGURO · FILTRADO POR PERMISOS REALES
# =============================================================================
#
# 🎯 OBJETIVO:
# ──────────────────────────────────────────────────────────────────────────
# Proporcionar una función de alto nivel que integra metadatos de tarjetas
# con validación de permisos real desde base de datos, devolviendo SOLO
# las tarjetas que el usuario puede ver según su rol.
#
# 🔐 DIFERENCIA CLAVE CON FUNCIONES ANTERIORES:
# ──────────────────────────────────────────────────────────────────────────
# • obtener_metadatos_tarjetas() → devuelve TODO, sin filtrar
# • obtener_tarjetas_dashboard() → devuelve SOLO lo permitido (seguro)
#
# 👉 ESTA ES LA FUNCIÓN QUE DEBES USAR EN VISTAS DE DASHBOARD
#
# 🏗️ ARQUITECTURA DE VALIDACIÓN:
# ──────────────────────────────────────────────────────────────────────────
#
#   ┌──────────────────────────────────────────────────────────────┐
#   │  1. obtener_metadatos_tarjetas()                             │
#   │     ↓ Todas las tarjetas del sistema                         │
#   └──────────────────────────────────────────────────────────────┘
#                          ↓
#   ┌──────────────────────────────────────────────────────────────┐
#   │  2. Para cada tarjeta:                                       │
#   │     • Extraer endpoint                                       │
#   │     • Validar con tiene_permiso(endpoint, rol_id)            │
#   │     • Validar con endpoint_activo(endpoint)                  │
#   └──────────────────────────────────────────────────────────────┘
#                          ↓
#   ┌──────────────────────────────────────────────────────────────┐
#   │  3. Solo tarjetas que pasaron AMBAS validaciones             │
#   │     ✔ Permiso en BD                                          │
#   │     ✔ Endpoint activo                                        │
#   └──────────────────────────────────────────────────────────────┘
#
# 🔄 FLUJO DE EJECUCIÓN DETALLADO:
# ──────────────────────────────────────────────────────────────────────────
# 1. Obtiene todas las tarjetas desde obtener_metadatos_tarjetas()
# 2. Inicializa lista de tarjetas validadas (vacía)
# 3. Para cada tarjeta:
#    a. Extrae el endpoint
#    b. Si no tiene endpoint → la ignora (no es navegable)
#    c. Consulta tabla de permisos: tiene_permiso(endpoint, rol_id)
#    d. Consulta tabla de configuración: endpoint_activo(endpoint)
#    e. Si AMBAS validaciones pasan → agrega a tarjetas_visibles
# 4. Devuelve solo las tarjetas validadas
#
# 💡 CASOS DE USO:
# ──────────────────────────────────────────────────────────────────────────
# ✔ Vista principal del dashboard
# ✔ Páginas de inicio personalizadas por rol
# ✔ Widgets de acceso rápido
# ✔ Cualquier UI que muestre tarjetas interactivas
#
# 🛡️ GARANTÍAS DE SEGURIDAD:
# ──────────────────────────────────────────────────────────────────────────
# • Validación doble (permisos + estado de endpoint)
# • Consulta en tiempo real a base de datos
# • Consistente con core.middleware
# • Previene acceso a endpoints desactivados
# • Respeta configuración dinámica de permisos
#
# ⚠️ CONSIDERACIONES DE RENDIMIENTO:
# ──────────────────────────────────────────────────────────────────────────
# Esta función hace N consultas a BD (donde N = cantidad de tarjetas).
# Para optimizar en producción:
#   1. Cachear resultados durante la sesión
#   2. Pre-cargar todos los permisos del rol en una sola query
#   3. Usar Redis o similar para permisos frecuentes
#
# Ejemplo de caché simple:
#   if "tarjetas_dashboard" not in session:
#       session["tarjetas_dashboard"] = obtener_tarjetas_dashboard(rol_id)
#   return session["tarjetas_dashboard"]
#
# 🔧 DEPENDENCIAS:
# ──────────────────────────────────────────────────────────────────────────
# • core.permisos.tiene_permiso(endpoint, rol_id)
#   → Consulta tabla de permisos en BD
# • core.permisos.endpoint_activo(endpoint)
#   → Consulta tabla de configuración de endpoints
#
# =============================================================================


def obtener_tarjetas_dashboard(rol_id):
    """
    🔐 Devuelve tarjetas del dashboard validadas con permisos REALES de BD.

    Esta es la ÚNICA función que debes usar en vistas de dashboard.
    Combina metadatos de UI con validación de seguridad robusta.

    🛡️ VALIDACIONES APLICADAS:
    ──────────────────────────────────────────────────────────────────────
    1. Permiso en tabla de permisos (rol_id + endpoint)
    2. Endpoint activo en configuración del sistema

    Solo devuelve tarjetas que pasan AMBAS validaciones.

    :param rol_id: ID del rol del usuario actual (desde session["rol_id"])
    :type rol_id: int

    :return: lista de tarjetas permitidas con metadata completa
    :rtype: list[dict]

    Estructura de retorno:
    [
        {
            "titulo": "Gestión de Contenedores",
            "endpoint": "contenedores_bp.listar",
            "icono": "fa-trash",
            "color": "blue",
            ...
        },
        ...
    ]

    Ejemplo de uso en vista:
        from flask import session
        from core.erp_engine import obtener_tarjetas_dashboard

        @super_admin_bp.route("/dashboard")
        def dashboard():
            rol_id = session.get("rol_id")
            tarjetas = obtener_tarjetas_dashboard(rol_id)
            return render_template("dashboard.html", tarjetas=tarjetas)

    ⚠️ IMPORTANTE:
    No necesitas validar permisos después de llamar esta función.
    Ya devuelve solo lo que el usuario puede ver.
    """

    # ---------------------------------------------------------
    # 📥 IMPORTS LOCALES (EVITAR IMPORTS CIRCULARES)
    # ---------------------------------------------------------
    # Importamos aquí en lugar de arriba del archivo para evitar
    # dependencias circulares entre módulos.
    #
    # 📌 tiene_permiso(endpoint, rol_id):
    #    Consulta tabla de permisos en BD.
    #    Devuelve True si el rol tiene acceso al endpoint.
    #
    # 📌 endpoint_activo(endpoint):
    #    Consulta tabla de configuración.
    #    Devuelve True si el endpoint está habilitado globalmente.
    from core.permisos import tiene_permiso, endpoint_activo

    # ---------------------------------------------------------
    # 🎴 OBTENER TODAS LAS TARJETAS (SIN FILTRAR)
    # ---------------------------------------------------------
    # Llamamos a la función anterior que devuelve metadatos completos
    # sin validación de seguridad
    todas_las_tarjetas = obtener_metadatos_tarjetas()

    # ---------------------------------------------------------
    # 🔐 INICIALIZAR LISTA DE TARJETAS VALIDADAS
    # ---------------------------------------------------------
    # Solo las tarjetas que pasen validación se agregarán aquí
    tarjetas_visibles = []

    # ---------------------------------------------------------
    # 🔄 RECORRIDO Y VALIDACIÓN
    # ---------------------------------------------------------
    # Iteramos sobre cada tarjeta para aplicar filtros de seguridad
    for tarjeta in todas_las_tarjetas:

        # -----------------------------------------------------
        # 🔍 EXTRACCIÓN DEL ENDPOINT
        # -----------------------------------------------------
        # Cada tarjeta debe tener un endpoint para ser navegable.
        # Si no lo tiene, la ignoramos (puede ser decorativa)
        endpoint = tarjeta.get("endpoint")

        # -----------------------------------------------------
        # ⚠️ VALIDACIÓN 1: ENDPOINT EXISTE
        # -----------------------------------------------------
        # Si endpoint es None o "", no podemos validar permisos
        # ni navegar, así que descartamos esta tarjeta
        if not endpoint:
            continue

        # -----------------------------------------------------
        # 🛡️ VALIDACIÓN 2: PERMISO EN BD
        # -----------------------------------------------------
        # Consulta tabla de permisos:
        #   SELECT * FROM tbl_permisos
        #   WHERE endpoint = ? AND rol_id = ? AND activo = 1
        #
        # Devuelve True si el rol tiene acceso explícito
        if not tiene_permiso(endpoint, rol_id):
            continue  # El usuario no tiene permiso → saltar tarjeta

        # -----------------------------------------------------
        # 🛡️ VALIDACIÓN 3: ENDPOINT ACTIVO
        # -----------------------------------------------------
        # Consulta tabla de configuración de endpoints:
        #   SELECT activo FROM tbl_endpoints WHERE nombre = ?
        #
        # Devuelve True si el endpoint está habilitado globalmente.
        # Esto permite desactivar módulos completos sin borrar código.
        if not endpoint_activo(endpoint):
            continue  # Endpoint desactivado → saltar tarjeta

        # -----------------------------------------------------
        # ✅ TODAS LAS VALIDACIONES PASARON
        # -----------------------------------------------------
        # Si llegamos aquí, la tarjeta:
        #   ✔ Tiene endpoint válido
        #   ✔ El rol tiene permiso en BD
        #   ✔ El endpoint está activo globalmente
        #
        # → Es seguro agregar esta tarjeta a la lista visible
        tarjetas_visibles.append(tarjeta)

    # ---------------------------------------------------------
    # 📤 RETORNO DE TARJETAS VALIDADAS
    # ---------------------------------------------------------
    # Devolvemos solo las tarjetas que pasaron TODAS las validaciones.
    # El consumidor puede usar directamente esta lista sin más checks.
    return tarjetas_visibles


# =============================================================================
# 5️⃣ UTILIDADES ADICIONALES · FUNCIONES DE SOPORTE
# =============================================================================
#
# 🎯 PROPÓSITO DE ESTA SECCIÓN:
# ──────────────────────────────────────────────────────────────────────────
# Proporcionar funciones auxiliares para casos de uso específicos que
# complementan las funciones principales del motor.
#
# 📌 PRINCIPIO DE DISEÑO:
# Estas funciones NO duplican lógica de seguridad, solo proporcionan
# transformaciones y filtros de datos para mejorar la experiencia de desarrollo.
#
# =============================================================================


def obtener_tarjetas_ordenadas(rol_id, criterio="prioridad"):
    """
    🎯 Devuelve tarjetas del dashboard ordenadas según criterio específico.

    Wrapper sobre obtener_tarjetas_dashboard() que añade ordenamiento.
    Mantiene las mismas garantías de seguridad.

    :param rol_id: ID del rol del usuario
    :type rol_id: int
    :param criterio: campo por el cual ordenar ("prioridad", "titulo", etc.)
    :type criterio: str

    :return: lista de tarjetas validadas y ordenadas
    :rtype: list[dict]

    Ejemplo de uso:
        # Ordenar por prioridad (campo numérico en registry)
        tarjetas = obtener_tarjetas_ordenadas(rol_id, "prioridad")

        # Ordenar alfabéticamente por título
        tarjetas = obtener_tarjetas_ordenadas(rol_id, "titulo")
    """

    # ---------------------------------------------------------
    # 🔐 OBTENER TARJETAS VALIDADAS
    # ---------------------------------------------------------
    # Usamos la función segura que ya valida permisos
    tarjetas = obtener_tarjetas_dashboard(rol_id)

    # ---------------------------------------------------------
    # 📊 ORDENAMIENTO
    # ---------------------------------------------------------
    # Ordenamos por el criterio especificado.
    # .get(criterio, 999) asigna valor por defecto alto si no existe el campo,
    # asegurando que tarjetas sin prioridad definida vayan al final.
    #
    # Para ordenamiento alfabético (titulo), el valor por defecto es "ZZZ"
    # para que vayan al final del listado.
    valor_defecto = 999 if criterio == "prioridad" else "ZZZ"

    tarjetas_ordenadas = sorted(tarjetas, key=lambda t: t.get(criterio, valor_defecto))

    return tarjetas_ordenadas


def obtener_tarjetas_por_categoria(rol_id):
    """
    🗂️ Devuelve tarjetas agrupadas por panel/categoría.

    Útil para construir dashboards con secciones separadas.
    Mantiene validación de permisos en cada tarjeta.

    :param rol_id: ID del rol del usuario
    :type rol_id: int

    :return: diccionario con paneles como keys y tarjetas como values
    :rtype: dict[str, list[dict]]

    Estructura de retorno:
    {
        "Panel de Gestión": [
            {"titulo": "Contenedores", ...},
            {"titulo": "Parkings", ...}
        ],
        "Panel de Administración": [
            {"titulo": "Usuarios", ...}
        ]
    }

    Ejemplo de uso en template:
        {% for panel, tarjetas in paneles.items() %}
            <h2>{{ panel }}</h2>
            <div class="tarjetas-grid">
                {% for tarjeta in tarjetas %}
                    <div class="tarjeta">{{ tarjeta.titulo }}</div>
                {% endfor %}
            </div>
        {% endfor %}
    """

    # ---------------------------------------------------------
    # 📥 IMPORTS LOCALES
    # ---------------------------------------------------------
    from core.permisos import tiene_permiso, endpoint_activo

    # ---------------------------------------------------------
    # 📊 OBTENER PANELES COMPLETOS
    # ---------------------------------------------------------
    paneles = obtener_paneles()

    # ---------------------------------------------------------
    # 🗂️ INICIALIZAR DICCIONARIO DE AGRUPACIÓN
    # ---------------------------------------------------------
    # Estructura: {"nombre_panel": [tarjeta1, tarjeta2, ...]}
    tarjetas_por_panel = {}

    # ---------------------------------------------------------
    # 🔄 RECORRIDO Y FILTRADO POR PANEL
    # ---------------------------------------------------------
    for panel in paneles:

        nombre_panel = panel.get("nombre", "Sin categoría")
        tarjetas_panel = panel.get("tarjetas", [])

        # Lista de tarjetas validadas para este panel específico
        tarjetas_validadas = []

        # -----------------------------------------------------
        # 🔐 VALIDAR CADA TARJETA DEL PANEL
        # -----------------------------------------------------
        for tarjeta in tarjetas_panel:

            endpoint = tarjeta.get("endpoint")

            # Aplicar las mismas validaciones que obtener_tarjetas_dashboard()
            if not endpoint:
                continue

            if not tiene_permiso(endpoint, rol_id):
                continue

            if not endpoint_activo(endpoint):
                continue

            # Tarjeta validada → agregar a este panel
            tarjetas_validadas.append(tarjeta)

        # -----------------------------------------------------
        # 📦 AGREGAR PANEL SOLO SI TIENE TARJETAS VISIBLES
        # -----------------------------------------------------
        # No mostramos paneles vacíos (sin tarjetas permitidas)
        if tarjetas_validadas:
            tarjetas_por_panel[nombre_panel] = tarjetas_validadas

    return tarjetas_por_panel


# =============================================================================
# 6️⃣ RESUMEN Y GUÍA DE USO
# =============================================================================
#
# 📚 FUNCIONES DISPONIBLES:
# ──────────────────────────────────────────────────────────────────────────
#
# 🔓 SIN VALIDACIÓN DE SEGURIDAD (solo metadatos):
#   • obtener_modulos_activos()
#   • obtener_metadatos_tarjetas()
#
#   ⚠️ REQUIERE validación posterior con tiene_permiso()
#
# 🔐 CON VALIDACIÓN DE SEGURIDAD (listas para usar):
#   • obtener_tarjetas_dashboard(rol_id)
#   • obtener_tarjetas_ordenadas(rol_id, criterio)
#   • obtener_tarjetas_por_categoria(rol_id)
#
#   ✅ YA validadas, seguras para renderizar directamente
#
# 🎯 RECOMENDACIÓN:
# ──────────────────────────────────────────────────────────────────────────
# Usa SIEMPRE las funciones con validación (🔐) en tus vistas de dashboard.
# Solo usa las funciones sin validación (🔓) si necesitas los datos crudos
# para procesamiento interno y aplicarás tiene_permiso() manualmente después.
#
# ✅ CORRECTO:
#   tarjetas = obtener_tarjetas_dashboard(session["rol_id"])
#   return render_template("dashboard.html", tarjetas=tarjetas)
#
# ❌ INCORRECTO (riesgo de seguridad):
#   tarjetas = obtener_metadatos_tarjetas()  # Sin validar
#   return render_template("dashboard.html", tarjetas=tarjetas)
#
# 🔄 INTEGRACIÓN CON OTROS MÓDULOS:
# ──────────────────────────────────────────────────────────────────────────
# • core.registry → Fuente de datos (definición declarativa)
# • core.permisos → Validación de acceso (tiene_permiso, endpoint_activo)
# • core.middleware → Protección de rutas (before_request)
# • blueprints → Consumidores finales (vistas del dashboard)
#
# 🚀 MEJORAS FUTURAS RECOMENDADAS:
# ──────────────────────────────────────────────────────────────────────────
# 1. Sistema de caché para permisos (Redis, Flask-Caching)
# 2. Pre-carga de permisos del rol en login (una sola query)
# 3. Invalidación de caché al modificar permisos en BD
# 4. Logging de tarjetas rechazadas para análisis de UX
# 5. A/B testing de ordenamiento de tarjetas
# 6. Personalización por usuario (favoritos, orden custom)
#
# =============================================================================
