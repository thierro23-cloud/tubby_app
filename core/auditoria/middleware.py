# =============================================================================
# 🧠 CORE.MIDDLEWARE · MOTOR GLOBAL DE SEGURIDAD Y CONTROL
# =============================================================================
#
# 🎯 PROPÓSITO:
# Middleware global que intercepta TODAS las peticiones.
#
# ✔ Seguridad centralizada
# ✔ Auditoría automática
# ✔ Control de endpoints
# ✔ Control de permisos
# ✔ Manejo de errores global
#
# 🔥 ESTE ARCHIVO ES CRÍTICO
# 👉 TODO pasa por aquí antes de llegar a cualquier endpoint
#
# =============================================================================


# =============================================================================
# 1️⃣ IMPORTS
# =============================================================================

# 📌 request: Objeto global de Flask que contiene información de la petición HTTP actual
#    - request.endpoint: nombre interno del endpoint (ej: "auth_bp.login", "super_admin_bp.dashboard")
#    - request.path: ruta URL de la petición (ej: "/api/usuarios", "/login")
#    - request.method: método HTTP (GET, POST, PUT, DELETE, etc.)
#
# 📌 session: Almacenamiento persistente del lado del servidor para datos del usuario actual
#    - session["user_id"]: ID del usuario autenticado
#    - session["rol_id"]: ID del rol del usuario (determina permisos)
#    - Flask firma y encripta las sesiones automáticamente con SECRET_KEY
#
# 📌 redirect: Redirige al navegador a otra URL (código HTTP 302)
# 📌 url_for: Genera URLs dinámicamente a partir del nombre del endpoint
#    - Ejemplo: url_for("auth_bp.login") → "/login"
#    - Ventaja: si cambias la ruta física, no se rompen los enlaces
#
# 📌 flash: Almacena mensajes temporales en sesión para mostrar en la siguiente página
#    - flash("Mensaje", "categoría") → aparece en el template con get_flashed_messages()
#
# 📌 jsonify: Convierte diccionarios Python a JSON con headers correctos para APIs REST
from flask import request, session, redirect, url_for, flash, jsonify

# 📌 endpoint_activo: Verifica si un endpoint está habilitado en base de datos
#    - Permite desactivar módulos completos sin borrar código
#    - Ej: desactivar temporalmente el módulo de "contenedores" sin tocar rutas
#
# 📌 tiene_permiso: Verifica si un rol tiene acceso a un endpoint específico
#    - Consulta tabla de permisos: endpoint_id + rol_id → permitido/denegado
#    - Centraliza la lógica de autorización en un solo lugar
from core.permisos import endpoint_activo, tiene_permiso

# 📌 registrar_evento: Guarda eventos de auditoría en base de datos
#    - Registra quién, cuándo, qué hizo y desde dónde
#    - Útil para seguridad, compliance y debugging
from core.audit import registrar_evento


# =============================================================================
# 2️⃣ CONFIGURACIÓN INTERNA
# =============================================================================

# 🔓 ENDPOINTS PÚBLICOS (no requieren login)
# ────────────────────────────────────────────────────────────────────────────
# Estos endpoints son accesibles sin autenticación.
# Flask genera nombres de endpoint con formato "blueprint.función"
#
# 📌 "auth_bp.login": Página de inicio de sesión
#    - Si pidieras login aquí, tendrías un bucle infinito
#
# 📌 "auth_bp.logout": Cierre de sesión
#    - Debe ser público porque destruye la sesión activa
#
# 📌 "static": Endpoint especial de Flask para archivos estáticos
#    - Sirve CSS, JS, imágenes, fuentes, etc.
#    - Ruta física por defecto: /static/
#    - Si lo protegieras, la página de login no cargaría estilos
#
# ⚠️ IMPORTANTE: No añadas endpoints de negocio aquí
#    Solo rutas de autenticación y recursos públicos del sistema
ENDPOINTS_PUBLICOS = {
    "auth_bp.login",
    "auth_bp.logout",
    "static"
}


# =============================================================================
# 3️⃣ MIDDLEWARE PRINCIPAL (BEFORE_REQUEST)
# =============================================================================

def seguridad_global():
    """
    🔐 Middleware global de seguridad.
    Se ejecuta ANTES de cada request.
    
    📌 FLUJO DE EJECUCIÓN:
    ────────────────────────────────────────────────────────────────────────
    1. Flask recibe una petición HTTP (GET /dashboard, POST /api/usuarios, etc.)
    2. ANTES de ejecutar la vista correspondiente, Flask llama a esta función
    3. Esta función decide si permitir o bloquear la petición
    4. Si devuelve None → la petición continúa hacia la vista
    5. Si devuelve una respuesta (redirect, JSON, HTML) → la petición se corta aquí
    
    📌 ARQUITECTURA:
    ────────────────────────────────────────────────────────────────────────
    Este middleware se registra en app.py con:
        app.before_request(seguridad_global)
    
    Flask ejecuta TODOS los before_request en orden de registro,
    y el primero que devuelva algo diferente de None detiene la cadena.
    
    📌 VENTAJAS:
    ────────────────────────────────────────────────────────────────────────
    ✔ Control centralizado: no repites validaciones en cada vista
    ✔ Seguridad por defecto: nuevas rutas quedan protegidas automáticamente
    ✔ Auditoría completa: registras TODOS los accesos y denegaciones
    ✔ Separación de responsabilidades: las vistas solo manejan lógica de negocio
    """

    # ─────────────────────────────────────────────────────────────────────────
    # 🔍 OBTENER ENDPOINT DE LA PETICIÓN ACTUAL
    # ─────────────────────────────────────────────────────────────────────────
    # request.endpoint es el identificador interno de Flask para la vista.
    # Formato: "nombre_blueprint.nombre_funcion"
    #
    # Ejemplos:
    #   - Ruta: /login → endpoint: "auth_bp.login"
    #   - Ruta: /api/usuarios → endpoint: "api_bp.listar_usuarios"
    #   - Ruta: /dashboard → endpoint: "super_admin_bp.dashboard"
    #
    # ⚠️ DIFERENCIA CLAVE:
    #   - request.endpoint → nombre lógico (invariable, usado internamente)
    #   - request.path → ruta física (puede cambiar, se muestra en navegador)
    #
    # 👉 Usamos endpoint porque:
    #   1. Es estable: aunque cambies la ruta, el endpoint permanece igual
    #   2. Es único: cada vista tiene un endpoint diferente
    #   3. Es lo que usa Flask internamente para url_for() y permisos
    endpoint = request.endpoint

    # ---------------------------------------------------------
    # 🛑 IGNORAR REQUESTS SIN ENDPOINT
    # ---------------------------------------------------------
    # Algunas peticiones especiales no tienen endpoint definido:
    #   - Peticiones internas de Flask
    #   - Errores de routing antes de resolver la vista
    #   - Peticiones malformadas o inválidas
    #
    # Si endpoint es None, salimos sin hacer nada.
    # Flask manejará estos casos con sus propios mecanismos.
    if not endpoint:
        return

    # ---------------------------------------------------------
    # 🌐 IGNORAR ARCHIVOS ESTÁTICOS
    # ---------------------------------------------------------
    # Flask sirve archivos estáticos (CSS, JS, imágenes) con endpoint "static".
    # 
    # Ejemplo:
    #   - URL: /static/css/main.css → endpoint: "static"
    #   - URL: /static/js/app.js → endpoint: "static"
    #
    # 👉 POR QUÉ IGNORARLOS:
    #   1. No son funcionalidad de negocio
    #   2. La página de login necesita cargar estilos ANTES de autenticar
    #   3. No tienen datos sensibles (son públicos por diseño)
    #   4. Validarlos ralentizaría innecesariamente la aplicación
    #
    # ⚠️ NOTA: Esto cubre tanto la comprobación explícita como la que
    #    viene más abajo en ENDPOINTS_PUBLICOS. Es redundante pero seguro.
    if endpoint.startswith("static"):
        return

    # ---------------------------------------------------------
    # 🔓 ENDPOINTS PÚBLICOS
    # ---------------------------------------------------------
    # Estos endpoints están definidos en ENDPOINTS_PUBLICOS y no requieren
    # autenticación ni validación de permisos.
    #
    # 👉 CASOS DE USO:
    #   - auth_bp.login: Formulario de inicio de sesión
    #   - auth_bp.logout: Cerrar sesión activa
    #   - static: Archivos públicos (ya cubierto arriba, pero por si acaso)
    #
    # Si el endpoint actual está en este set, permitimos el acceso directo
    # sin más validaciones.
    if endpoint in ENDPOINTS_PUBLICOS:
        return

    # ---------------------------------------------------------
    # 👤 VALIDAR LOGIN
    # ---------------------------------------------------------
    # A partir de aquí, TODOS los endpoints requieren autenticación.
    # 
    # 📌 CÓMO FUNCIONA:
    #   - Cuando el usuario hace login exitoso, guardas session["user_id"]
    #   - Flask mantiene esta sesión con cookies firmadas
    #   - Si user_id no existe en session → usuario no autenticado
    #
    # 👉 RESPUESTA SEGÚN TIPO DE CLIENTE:
    #
    # 🌐 Para navegadores web (rutas HTML):
    #   - Registramos el intento en auditoría
    #   - Mostramos mensaje flash informativo
    #   - Redirigimos al login
    #   - El usuario ve una página de inicio de sesión
    #
    # 🔌 Para clientes API (rutas /api/*):
    #   - No podemos redirigir (la API no tiene navegador)
    #   - Devolvemos JSON con error y código HTTP 401 Unauthorized
    #   - El cliente frontend maneja el error (ej: mostrar modal de login)
    #
    # ⚠️ SEGURIDAD: Este bloque evita acceso no autorizado a datos y funciones
    if "user_id" not in session:
        # Registrar en auditoría para detección de intentos sospechosos
        registrar_evento("no_autenticado", endpoint)

        # Respuesta para APIs REST
        if request.path.startswith("/api"):
            return jsonify({"error": "No autenticado"}), 401

        # Respuesta para navegadores
        flash("Debes iniciar sesión", "warning")
        return redirect(url_for("auth_bp.login"))

    # ---------------------------------------------------------
    # 🔐 VALIDAR ENDPOINT ACTIVO
    # ---------------------------------------------------------
    # Permite activar/desactivar módulos completos desde base de datos
    # sin modificar código ni reiniciar la aplicación.
    #
    # 📌 CASO DE USO:
    #   - Deshabilitar temporalmente el módulo de "contenedores" por mantenimiento
    #   - Activar progresivamente nuevos módulos en producción
    #   - Ocultar funcionalidades en modo demo o pruebas
    #
    # 👉 CÓMO FUNCIONA:
    #   - La función endpoint_activo(endpoint) consulta tabla de configuración
    #   - Devuelve True si el endpoint está habilitado, False si no
    #   - Puedes controlarlo desde un panel de administración
    #
    # 🛡️ RESPUESTA:
    #   - Registro en auditoría (importante para rastrear intentos)
    #   - JSON 403 Forbidden para APIs
    #   - Mensaje HTTP simple para web
    #
    # ⚠️ NOTA: 403 es correcto aquí (no 404) porque el usuario está autenticado,
    #    pero el recurso está explícitamente prohibido por configuración
    if not endpoint_activo(endpoint):
        registrar_evento("endpoint_desactivado", endpoint)

        if request.path.startswith("/api"):
            return jsonify({"error": "Endpoint desactivado"}), 403

        return "⛔ Endpoint desactivado", 403

    # ---------------------------------------------------------
    # 🔐 VALIDAR PERMISOS
    # ---------------------------------------------------------
    # Sistema de autorización basado en roles (RBAC - Role-Based Access Control)
    #
    # 📌 ARQUITECTURA DE PERMISOS:
    #   1. Cada usuario tiene un rol (Admin, Operador, Consulta, etc.)
    #   2. Cada endpoint tiene permisos asociados
    #   3. Tabla de permisos define: rol X puede acceder a endpoint Y
    #
    # 👉 CÓMO FUNCIONA:
    #   - Al hacer login, guardas session["rol_id"]
    #   - tiene_permiso(endpoint, rol_id) consulta tabla de permisos
    #   - Devuelve True/False según configuración en BD
    #
    # 🎯 VENTAJAS:
    #   ✔ Control granular: defines acceso por cada vista
    #   ✔ Centralizado: cambias permisos en BD sin tocar código
    #   ✔ Auditable: todos los accesos quedan registrados
    #   ✔ Escalable: añadir nuevos roles no requiere cambios de lógica
    #
    # 🛡️ RESPUESTA EN CASO DE DENEGACIÓN:
    #   - Registro en auditoría con contexto (rol_id, endpoint)
    #   - JSON 403 para API
    #   - Flash message + redirect para web
    #
    # 👉 POR QUÉ REDIRIGIR AL DASHBOARD:
    #   - El usuario ya está autenticado (pasó la validación anterior)
    #   - Tiene acceso a ALGUNA parte del sistema
    #   - El dashboard es un punto de partida seguro donde puede navegar
    #   - Evita confusión (redirigir a login sería engañoso)
    #
    # ⚠️ MEJORA POSIBLE:
    #   Podrías crear una página "acceso_denegado.html" más informativa
    #   en lugar de redirigir al dashboard
    rol_id = session.get("rol_id")

    if not tiene_permiso(endpoint, rol_id):
        registrar_evento(
            accion="acceso_denegado",
            modulo=endpoint,
            descripcion=f"rol_id={rol_id}"
        )

        if request.path.startswith("/api"):
            return jsonify({"error": "Forbidden"}), 403

        flash("No tienes permisos", "danger")
        return redirect(url_for("super_admin_bp.dashboard"))

    # ---------------------------------------------------------
    # 🟢 ACCESO OK (OPCIONAL AUDIT)
    # ---------------------------------------------------------
    # Si llegamos aquí, el usuario:
    #   ✔ Está autenticado (tiene user_id en session)
    #   ✔ El endpoint está activo en configuración
    #   ✔ Su rol tiene permiso para acceder
    #
    # 👉 REGISTRO DE AUDITORÍA:
    #   - Guardar "acceso_permitido" es útil para:
    #     · Análisis de uso de la aplicación
    #     · Detección de patrones anómalos
    #     · Cumplimiento normativo (trazabilidad completa)
    #     · Debugging y soporte técnico
    #
    # ⚠️ CONSIDERACIÓN DE RENDIMIENTO:
    #   - Si tienes MUCHO tráfico, podrías:
    #     1. Registrar solo accesos denegados (más críticos)
    #     2. Usar un buffer en memoria y guardar en lotes
    #     3. Enviar a un sistema de logs externo (Elasticsearch, etc.)
    #
    # 🔄 CONTINUACIÓN DEL FLUJO:
    #   - Esta función devuelve None implícitamente
    #   - Flask interpreta None como "todo ok, continuar"
    #   - La petición sigue hacia la vista correspondiente
    registrar_evento("acceso_permitido", endpoint)


# =============================================================================
# 4️⃣ MIDDLEWARE DE ERRORES (GLOBAL)
# =============================================================================

def registrar_errores(app):
    """
    🔥 Captura TODOS los errores automáticamente
    
    📌 PROPÓSITO:
    ────────────────────────────────────────────────────────────────────────
    Flask lanza excepciones HTTP cuando algo falla:
      - 404 Not Found: ruta no existe
      - 500 Internal Server Error: error en código Python
      - 403 Forbidden: acceso denegado (aunque nosotros lo manejamos arriba)
    
    Sin estos handlers, Flask muestra páginas de error por defecto,
    que son inconsistentes, poco profesionales y rompen la experiencia.
    
    📌 VENTAJAS DE HANDLERS PERSONALIZADOS:
    ────────────────────────────────────────────────────────────────────────
    ✔ Consistencia: misma estructura de respuesta en toda la app
    ✔ Seguridad: no expones stack traces en producción
    ✔ Auditoría: registras TODOS los errores para análisis
    ✔ UX: respuestas claras tanto para web como para API
    
    📌 CÓMO SE REGISTRA:
    ────────────────────────────────────────────────────────────────────────
    En app.py llamas:
        registrar_errores(app)
    
    Esto asocia cada handler con su código HTTP correspondiente.
    
    📌 PARÁMETRO 'app':
    ────────────────────────────────────────────────────────────────────────
    Es la instancia principal de Flask.
    Necesitas pasarla porque los decoradores @app.errorhandler
    se registran en la aplicación, no en un blueprint.
    """

    # ─────────────────────────────────────────────────────────────────────────
    # 🔍 ERROR 404 - NOT FOUND
    # ─────────────────────────────────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        """
        🚫 Página o endpoint no encontrado
        
        📌 CUÁNDO SE DISPARA:
        ──────────────────────────────────────────────────────────────────
        - El usuario escribe una URL que no existe
        - Hay un typo en url_for() o en un enlace
        - Se eliminó una ruta pero quedan enlaces antiguos
        - Peticiones a recursos borrados o movidos
        
        👉 EJEMPLOS:
          - GET /dasboard (typo) → 404
          - GET /api/clientes/999999 (ID no existe) → depende de tu lógica,
            podrías manejar esto en la vista con 404 también
        
        🛡️ RESPUESTA:
        ──────────────────────────────────────────────────────────────────
        - Registro en auditoría con request.path para ver qué se buscó
        - JSON para API (máquinas)
        - Texto simple para web (idealmente plantilla HTML profesional)
        
        ⚠️ MEJORA RECOMENDADA:
          Devolver render_template("errores/404.html") con diseño
          consistente, sugerencias de navegación, y buscador interno
        
        📌 PARÁMETRO 'e':
        ──────────────────────────────────────────────────────────────────
        Es la excepción HTTP que Flask lanza internamente.
        Contiene metadata del error, pero normalmente no la usamos
        en la respuesta al usuario (por seguridad).
        """
        registrar_evento("error_404", request.path)

        # Respuesta para clientes API (apps móviles, SPAs, servicios)
        if request.path.startswith("/api"):
            return jsonify({"error": "Not Found"}), 404

        # Respuesta para navegadores
        # 👉 MEJORA: return render_template("404.html"), 404
        return "Página no encontrada", 404

    # ─────────────────────────────────────────────────────────────────────────
    # 💥 ERROR 500 - INTERNAL SERVER ERROR
    # ─────────────────────────────────────────────────────────────────────────
    @app.errorhandler(500)
    def server_error(e):
        """
        💥 Error interno del servidor
        
        📌 CUÁNDO SE DISPARA:
        ──────────────────────────────────────────────────────────────────
        - Excepción no capturada en código Python
        - Error de base de datos (tabla no existe, constraint violado)
        - División por cero, KeyError, AttributeError, etc.
        - Fallo en conexión a servicios externos
        - Error en templates Jinja2
        
        👉 EJEMPLOS:
          - division_result = 10 / 0 → ZeroDivisionError → 500
          - user = User.query.get(None) → puede lanzar error → 500
          - Template usa variable inexistente → 500
        
        🛡️ RESPUESTA:
        ──────────────────────────────────────────────────────────────────
        - Registro en auditoría (CRÍTICO para debugging)
        - JSON genérico para API (sin detalles técnicos)
        - Mensaje genérico para web
        
        ⚠️ SEGURIDAD:
          NUNCA devuelvas el stack trace completo en producción.
          Eso expone:
            - Estructura de directorios del servidor
            - Nombres de variables y lógica interna
            - Versiones de librerías
            - Rutas de base de datos
        
        👉 BUENAS PRÁCTICAS:
          1. Registra el error completo en logs del servidor
          2. Envía notificación a equipo técnico (email, Slack, Sentry)
          3. Devuelve mensaje genérico al usuario
          4. En desarrollo, Flask.debug=True muestra el debugger interactivo
        
        ⚠️ MEJORA RECOMENDADA:
          - Usar logging.exception() para guardar stack trace completo
          - Integrar Sentry o similar para tracking de errores
          - Devolver render_template("500.html") profesional
        
        📌 PARÁMETRO 'e':
        ──────────────────────────────────────────────────────────────────
        Es la excepción Python original (ZeroDivisionError, etc.).
        Puedes extraer información con:
          - str(e): mensaje de error
          - type(e).__name__: tipo de excepción
          - traceback.format_exc(): stack trace completo
        
        Pero recuerda: solo úsalo en logs, nunca en respuesta al usuario.
        """
        registrar_evento("error_500", request.path)

        # Respuesta para clientes API
        if request.path.startswith("/api"):
            return jsonify({"error": "Internal Server Error"}), 500

        # Respuesta para navegadores
        # 👉 MEJORA: return render_template("500.html"), 500
        # 👉 MEJORA: logging.exception("Error 500 en %s", request.path)
        return "Error interno del servidor", 500