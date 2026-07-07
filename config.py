# config.py
# ============================================================================
# ⚙️ CONFIGURACIÓN GLOBAL DE LA APLICACIÓN FLASK
# ----------------------------------------------------------------------------
# - Esta clase Config la carga app.py con:
#       from config import Config
#       app.config.from_object(Config)
# - Todo lo que cuelga de Config en MAYÚSCULAS pasa a app.config["..."].
# - Aquí definimos:
#       * SECRET_KEY  → clave de Flask (sesiones, cookies firmadas, etc.)
#       * DATABASES   → todas las conexiones a MySQL que usará db.get_connection()
# ============================================================================


class Config:
    # ========================================================================
    # SECCIÓN 1. CLAVE SECRETA DE FLASK
    # ------------------------------------------------------------------------
    # - NO es la contraseña de la base de datos.
    # - Solo se usa para firmar cookies de sesión, tokens CSRF, etc.
    # - Debe ser una cadena difícil de adivinar.
    # ========================================================================
    SECRET_KEY = "0836W@c287C_cambia_esto_por_algo_mas_largo"

    # ========================================================================
    # SECCIÓN 2. DICCIONARIO DE BASES DE DATOS (DATABASES)
    # ------------------------------------------------------------------------
    # - Clave: nombre lógico de la "casa" que usas en get_connection("nombre").
    # - Valor: diccionario con parámetros de conexión:
    #       HOST, USER, PASSWORD, DB, PORT
    # - db.get_connection(nombre_bd) hace:
    #       libro_casas = current_app.config["DATABASES"]
    #       casa = libro_casas[nombre_bd]
    #       host = casa["HOST"], etc.
    # - Por eso TODAS las claves internas deben estar en MAYÚSCULAS.
    # ========================================================================
    DATABASES = {
        # ====================================================================
        # 2.1 BD COMÚN: bd_tbl_comunes
        # --------------------------------------------------------------------
        # - Base de datos por defecto (usuarios, roles, login, etc.).
        # - Es la que usa get_connection() si no se pasa nombre_bd.
        # - auth_bp.login llama a get_connection() sin argumentos.
        # ====================================================================
        "bd_tbl_comunes": {
            "HOST": "localhost",  # 🌐 Host o IP del servidor MySQL
            "USER": "root",  # 👤 Usuario MySQL con acceso a esta BD
            "PASSWORD": "F@Fe1132",  # 🔑 Contraseña (vacía si tu MySQL lo permite)
            "DB": "bd_tbl_comunes",  # 🏠 Nombre REAL de la BD en MySQL
            "PORT": 3306,  # 🚪 Puerto MySQL (por defecto 3306)
        },
        # ====================================================================
        # 2.2 BD PRINCIPAL DE OBRAS: control_obras
        # --------------------------------------------------------------------
        # - Contiene tablas tipo:
        #     tbl_inspecciones_obras, tbl_obras, tbl_control_contenedores, etc.
        # - Módulos que deberían usarla:
        #     control_contenedores_bp, control_contenedores_informes_bp,
        #     control_contenedores_manual_bp, inspecciones_obras_bp,
        #     panel_ocupacion_via_bp.
        # ====================================================================
        "control_via_publica": {
            "HOST": "localhost",
            "USER": "root",
            "PASSWORD": "F@Fe1132",
            "DB": "control_via_publica",  # 🏠 nombre REAL en MySQL
            "PORT": 3306,
        },
        # ====================================================================
        # 2.3 ALIAS "obras" → MISMA BD FÍSICA QUE control_via_publica
        # --------------------------------------------------------------------
        # OBJETIVO:
        # - Permitir que código antiguo que usa get_connection("obras")
        #   funcione sin cambios.
        # - Internamente apunta a la MISMA base física "control_obras".
        # ====================================================================
        "control_via_publica": {
            "HOST": "localhost",
            "USER": "root",
            "PASSWORD": "F@Fe1132",
            "DB": "control_via_publica",  # 🧷 misma BD que control_obras
            "PORT": 3306,
        },
        # ====================================================================
        # 2.4 BD GIS MUNICIPAL: gis_municipal
        # --------------------------------------------------------------------
        # - Base donde puedes guardar capas GIS, geometrías, etc.
        # - Cambia "gis_municipal" si en MySQL se llama de otra forma.
        # ====================================================================
        "gis_municipal": {
            "HOST": "localhost",
            "USER": "root",
            "PASSWORD": "F@Fe1132",
            "DB": "gis_municipal",
            "PORT": 3306,
        },
        # ====================================================================
        # 2.5 BD INVENTARIO GENERAL: inventario
        # --------------------------------------------------------------------
        # - Para inventario de activos, material, etc.
        # ====================================================================
        "inventario": {
            "HOST": "localhost",
            "USER": "root",
            "PASSWORD": "F@Fe1132",
            "DB": "inventario",
            "PORT": 3306,
        },
        # ====================================================================
        # 2.6 BD MOBILIARIO URBANO: mobiliario_urbano
        # --------------------------------------------------------------------
        # - Bancos, farolas, papeleras, señales, etc.
        # ====================================================================
        "mobiliario_urbano": {
            "HOST": "localhost",
            "USER": "root",
            "PASSWORD": "F@Fe1132",
            "DB": "mobiliario_urbano",
            "PORT": 3306,
        },
        # ====================================================================
        # 2.7 BD PARKING CAMIONES: parquin_camiones
        # --------------------------------------------------------------------
        # - Plazas de parking, camiones, reservas, etc.
        # ====================================================================
        "parquin_camiones": {
            "HOST": "localhost",
            "USER": "root",
            "PASSWORD": "F@Fe1132",
            "DB": "parquin_camiones",
            "PORT": 3306,
        },
        # ====================================================================
        # 2.8 BD PATRULLA VERDE: patrulla_verde
        # --------------------------------------------------------------------
        # - Incidencias ambientales, inspecciones de zonas verdes, etc.
        # ====================================================================
        "patrulla_verde": {
            "HOST": "localhost",
            "USER": "root",
            "PASSWORD": "F@Fe1132",
            "DB": "patrulla_verde",
            "PORT": 3306,
        },
        # ====================================================================
        # 2.9 BD PERSONAL / VESTUARIO: personal_vestuario
        # --------------------------------------------------------------------
        # - Gestión de equipamiento de personal (tallas, entregas, stock, etc.).
        # ====================================================================
        "personal_vestuario": {
            "HOST": "localhost",
            "USER": "root",
            "PASSWORD": "F@Fe1132",
            "DB": "personal_vestuario",
            "PORT": 3306,
        },
        # ====================================================================
        # 2.10 BD PLANES DE EMERGENCIA: plan_de_emergencias
        # --------------------------------------------------------------------
        # - Información de planes de emergencia, simulacros, recursos, etc.
        # ====================================================================
        "plan_de_emergencias": {
            "HOST": "localhost",
            "USER": "root",
            "PASSWORD": "F@Fe1132",
            "DB": "plan_de_emergencias",
            "PORT": 3306,
        },
    }


# ============================================================================
# SECCIÓN 3. CONFIGURACIÓN DEL WATCHER DE ENDPOINTS
# ----------------------------------------------------------------------------
# - Sistema automático de sincronización de endpoints Flask → MySQL
# - Detecta cambios en archivos .py y actualiza tbl_endpoints
# - Los endpoints se guardan en la BD principal: bd_tbl_comunes
# ============================================================================


class WatcherConfig:
    """
    Configuración específica para el sistema de vigilancia de endpoints.

    Uso:
        - El watcher usa esta configuración para logging y comportamiento
        - La conexión a MySQL usa DATABASES["bd_tbl_comunes"]
    """

    # ========================================================================
    # 3.1 CONFIGURACIÓN DE LOGGING
    # ========================================================================

    # Archivo donde se guardan los logs del watcher
    LOG_FILE = "endpoints_watcher.log"

    # Formato de las entradas en el archivo de log
    # Ejemplo: 2026-05-22 19:08:15 - INFO - Mensaje del log
    LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

    # Formato de fecha en los logs
    LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    # Nivel de detalle del log
    # Opciones: DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_LEVEL = "INFO"

    # ========================================================================
    # 3.2 CONFIGURACIÓN DEL WATCHER
    # ========================================================================

    # Tiempo mínimo (segundos) entre sincronizaciones
    # Evita múltiples ejecuciones cuando se modifican varios archivos a la vez
    DEBOUNCE_SECONDS = 2

    # Vigilar subdirectorios de forma recursiva
    # True: vigila toda la estructura de carpetas
    # False: solo vigila la carpeta raíz
    WATCH_RECURSIVE = True

    # Base de datos donde se guardan los endpoints
    # Debe coincidir con una clave de DATABASES
    ENDPOINTS_DATABASE = "bd_tbl_comunes"

    # Nombre de la tabla de endpoints
    ENDPOINTS_TABLE = "tbl_endpoints"
