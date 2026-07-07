# sync_endpoints.py
"""
Módulo de sincronización de endpoints Flask con MySQL.

INTEGRACIÓN CON TU PROYECTO:
    - Usa tu estructura de config.py existente
    - Se conecta a DATABASES["bd_tbl_comunes"] por defecto
    - Compatible con tu sistema de múltiples bases de datos

Funciones principales:
    - get_flask_app(): Carga la aplicación Flask del proyecto
    - extract_endpoints(app): Extrae todos los endpoints de Flask
    - sync_to_database(endpoints, logger): Sincroniza endpoints con MySQL

Uso como script independiente:
    python sync_endpoints.py

Autor: Sistema de vigilancia automática
Fecha: 2026-05-22
"""

import sys
import os
from importlib import import_module
import mysql.connector
from mysql.connector import Error
from logging import Logger, StreamHandler, basicConfig

# ============================================================
# CONFIGURACIÓN
# ============================================================

# Establecer logging (opcional, pero recomendado)
basicConfig(level=Logger.INFO)  # Configura el nivel de logging
logger = Logger(__name__, StreamHandler())  # Crea un logger

# ============================================================
# FUNCIÓN 1: CARGAR APLICACIÓN FLASK
# ============================================================


def get_flask_app():
    """
    Importa y devuelve la instancia de Flask del proyecto.

    Returns:
        Flask: Instancia de la aplicación Flask

    Raises:
        SystemExit: Si no se puede cargar la aplicación

    IMPORTANTE: Ajustar según tu estructura de proyecto
    """
    try:
        # CAMBIAR 'app' por el nombre de tu módulo principal si es diferente
        app_module = import_module("app")

        # Verificar que el módulo tiene la variable 'app'
        if not hasattr(app_module, "app"):
            raise AttributeError("El módulo no contiene la variable 'app'")

        return app_module.app

    except ImportError as e:
        print(f"✗ Error de importación: {e}")
        print("  Verifica que el módulo existe y está en el PYTHONPATH")
        sys.exit(1)

    except AttributeError as e:
        print(f"✗ Error de atributo: {e}")
        print("  Verifica que tu módulo define: app = Flask(__name__)")
        sys.exit(1)


# ============================================================
# FUNCIÓN 2: OBTENER CONFIGURACIÓN DE BASE DE DATOS
# ============================================================


def get_db_config():
    """
    Obtiene la configuración de la base de datos desde la variable de entorno.

    Returns:
        dict: Un diccionario con la configuración de la base de datos.
    """
    import os

    db_config = os.environ.get(
        "DB_CONFIG", "host=localhost dbname=mydatabase user=myuser password=mypassword"
    )
    return db_config


# ============================================================
# FUNCIÓN 3: Extraer endpoints
# ============================================================


def extract_endpoints(app):
    """
    Extrae todos los endpoints de la aplicación Flask.

    Args:
        app (Flask): La instancia de la aplicación Flask.

    Returns:
        list: Una lista de diccionarios, donde cada diccionario representa un endpoint.
    """
    endpoints = []
    for name in dir(app):
        if name.startswith("route"):
            endpoint = getattr(app, name)
            endpoints.append(
                {
                    "name": name,
                    "methods": list(endpoint.methods),
                    "rule": str(endpoint.rule),
                }
            )
    return endpoints


# ============================================================
# FUNCIÓN 4: Sincronizar endpoints con la base de datos
# ============================================================


def sync_to_database(endpoints, logger):
    """
    Sincroniza los endpoints con la base de datos.

    Args:
        endpoints (list): Una lista de diccionarios que representan los endpoints.
        logger (Logger): El logger para registrar mensajes.

    Returns:
        dict: Un diccionario con el resultado de la sincronización.
    """

    db_config = get_db_config()

    try:
        conn = mysql.connector.connect(**dict(db_config.split()))
        cursor = conn.cursor()

        # Crear la tabla si no existe
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tbl_endpoints (
                id INT AUTO_INCREMENT PRIMARY KEY,
                endpoint VARCHAR(255) NOT NULL,
                descripcion TEXT,
                activo BOOLEAN NOT NULL DEFAULT TRUE,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
            """)

        for ep in endpoints:
            try:
                cursor.execute(
                    """
                    INSERT INTO tbl_endpoints (endpoint, descripcion, activo)
                    VALUES (%s, %s, %s)
                    """,
                    (ep["name"], ep["rule"], True),
                )
            except Error as e:
                # Intentar actualizar si ya existe
                cursor.execute(
                    """
                    UPDATE tbl_endpoints
                    SET descripcion = %s, activo = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE endpoint = %s
                    """,
                    (ep["rule"], True, ep["name"]),
                )

        conn.commit()

        # Desactivar endpoints obsoletos
        cursor.execute(
            """
            UPDATE tbl_endpoints
            SET activo = FALSE, updated_at = CURRENT_TIMESTAMP
            WHERE endpoint NOT IN (%(endpoint_list)s) AND activo = TRUE
            """,
            {"endpoint_list": ",".join(ep["name"] for ep in endpoints)},
        )

        result = {
            "success": True,
            "inserted": cursor.rowcount,
            "updated": cursor.rowcount,
            "deactivated": cursor.rowcount,
        }
        logger.info(
            f"✓ Sincronización de endpoints completa.  Insertados: {result['inserted']}, Actualizados: {result['updated']}, Desactivados: {result['deactivated']}"
        )

    except Error as e:
        logger.error(f"Error de base de datos: {e}")
        result = {"success": False, "error": str(e)}
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

    return result


# ============================================================
# BLOQUE DE EJECUCIÓN INDEPENDIENTE
# ============================================================

if __name__ == "__main__":
    """
    Permite ejecutar este archivo directamente para sincronización manual.

    Uso:
        python sync_endpoints.py

    Proceso:
        1. Carga la aplicación Flask
        2. Extrae todos los endpoints
        3. Muestra los primeros 5
        4. Sincroniza con la base de datos
        5. Muestra resumen de resultados
    """

    print("=" * 70)
    print("SINCRONIZACIÓN MANUAL DE ENDPOINTS")
    print("=" * 70)

    # Paso 1: Cargar aplicación Flask
    print("\n1. Cargando aplicación Flask...")
    app = get_flask_app()
    print("   ✓ App cargada correctamente")

    # Mostrar configuración de BD que se usará
    print(f"   ✓ Base de datos: {get_db_config()}")
    print(f"   ✓ Tabla: tbl_endpoints")

    # Paso 2: Extraer endpoints
    print("\n2. Extrayendo endpoints...")
    endpoints = extract_endpoints(app)
    print(f"   ✓ Encontrados {len(endpoints)} endpoints")

    # Paso 3: Mostrar muestra de endpoints
    print("\n3. Muestra de endpoints:")
    for i, ep in enumerate(endpoints[:5], 1):
        print(f"   {i}. {ep['name']} ({ep['methods'][0]}) - {ep['rule']}")
        print(f"      Descripción: {ep['rule']}")

    if len(endpoints) > 5:
        print(f"   ... y {len(endpoints) - 5} más")

    # Paso 4: Sincronizar con base de datos
    print("\n4. Sincronizando con la base de datos...")
    result = sync_to_database(endpoints, logger)

    # Paso 5: Mostrar resultado
    print()
    if result["success"]:
        print("✓ Sincronización exitosa:")
        print(f"   • Endpoints nuevos: {result['inserted']}")
        print(f"   • Endpoints actualizados: {result['updated']}")
        print(f"   • Endpoints desactivados: {result['deactivated']}")
    else:
        print(f"✗ Error en la sincronización: {result['error']}")

    print("\n" + "=" * 70)
