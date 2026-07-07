# =============================================================================
# 📡 MÓDULO DB – RADIO MÁGICA CON CREACIÓN AUTOMÁTICA DE BD Y TABLAS
# =============================================================================
# DESCRIPCIÓN GENERAL
# -------------------
# Este módulo se encarga de:
# 1️⃣ Abrir conexiones con MySQL a la base indicada.
# 2️⃣ Crear la base de datos si no existe.
# 3️⃣ Crear tablas básicas automáticamente (con idtbl_nombre_tabla como PK).
# 4️⃣ Ejecutar consultas de lectura y escritura.
# 5️⃣ Garantizar cierre de cursores y conexiones.
# =============================================================================

from typing import Any, Dict, List, Optional
import mysql.connector
from mysql.connector import Error
from flask import current_app

# 📦 BASES DE DATOS DE FALLBACK
FALLBACK_DATABASES = {
    "bd_tbl_comunes": {
        "HOST": "localhost",
        "USER": "root",
        "PASSWORD": "F@Fe1132",
        "DB": "bd_tbl_comunes",
        "PORT": 3306,
    },
    "parquin_camiones": {
        "HOST": "localhost",
        "USER": "root",
        "PASSWORD": "F@Fe1132",
        "DB": "parquin_camiones",
        "PORT": 3306,
    },
    "control_via_publica": {
        "HOST": "localhost",
        "USER": "root",
        "PASSWORD": "F@Fe1132",
        "DB": "control_via_publica",
        "PORT": 3306,
    },
    "gis_municipal": {
        "HOST": "localhost",
        "USER": "root",
        "PASSWORD": "F@Fe1132",
        "DB": "gis_municipal",
        "PORT": 3306,
    },
    "inventario": {
        "HOST": "localhost",
        "USER": "root",
        "PASSWORD": "F@Fe1132",
        "DB": "inventario",
        "PORT": 3306,
    },
    "patrulla_verde": {
        "HOST": "localhost",
        "USER": "root",
        "PASSWORD": "F@Fe1132",
        "DB": "patrulla_verde",
        "PORT": 3306,
    },
    "plan_de_emergencias": {
        "HOST": "localhost",
        "USER": "root",
        "PASSWORD": "F@Fe1132",
        "DB": "plan_de_emergencias",
        "PORT": 3306,
    },
    "personal_vestuario": {
        "HOST": "localhost",
        "USER": "root",
        "PASSWORD": "F@Fe1132",
        "DB": "personal_vestuario",
        "PORT": 3306,
    },
    "mobiliario_urbano": {
        "HOST": "localhost",
        "USER": "root",
        "PASSWORD": "F@Fe1132",
        "DB": "mobiliario_urbano",
        "PORT": 3306,
    },
}


# =============================================================================
# 🔑 SECCIÓN 1: CONEXIÓN CON CREACIÓN AUTOMÁTICA DE BD Y TABLAS
# =============================================================================
def get_connection(
    nombre_bd: str = "bd_tbl_comunes",
) -> mysql.connector.MySQLConnection:
    """
    🔑 Abre conexión a la BD.
    - Crea la base si no existe.
    - Crea tablas básicas si no existen.
    """

    # 1️⃣ Leer config Flask o fallback
    try:
        libro_casas = current_app.config.get("DATABASES")
    except RuntimeError:
        libro_casas = None

    if not libro_casas:
        libro_casas = FALLBACK_DATABASES

    casa = libro_casas.get(nombre_bd)
    if not casa:
        disponibles = ", ".join(sorted(libro_casas.keys()))
        raise RuntimeError(
            f"❌ No encuentro la base '{nombre_bd}'! Casas disponibles: {disponibles}"
        )

    host = casa["HOST"]
    user = casa["USER"]
    password = casa["PASSWORD"]
    database = casa["DB"]
    port = casa.get("PORT", 3306)

    # 2️⃣ Intentar conexión normal
    try:
        conn = mysql.connector.connect(
            host=host, user=user, password=password, database=database, port=port
        )
        # Si está todo bien, crear tablas básicas si no existen
        _crear_tablas_basicas(conn, database)
        return conn
    except Error as e:
        if e.errno == 1049:  # BD desconocida
            # Conexión temporal para crear base
            temp_conn = mysql.connector.connect(
                host=host, user=user, password=password, port=port
            )
            cursor = temp_conn.cursor()
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{database}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            )
            temp_conn.commit()
            cursor.close()
            temp_conn.close()
            # Reconectar sobre la base recién creada
            conn = mysql.connector.connect(
                host=host, user=user, password=password, database=database, port=port
            )
            _crear_tablas_basicas(conn, database)
            return conn
        else:
            raise


# =============================================================================
# 📗 SECCIÓN 2: CREACIÓN AUTOMÁTICA DE TABLAS BÁSICAS
# =============================================================================
def _crear_tablas_basicas(conn: mysql.connector.MySQLConnection, database: str):
    """
    🔧 Crea tablas básicas automáticamente si no existen.
    Premisa: el ID principal siempre es `idtbl_nombre_tabla`.
    """

    tablas_sql = {
        "tbl_login": f"""
            CREATE TABLE IF NOT EXISTS tbl_login (
                idtbl_login INT AUTO_INCREMENT PRIMARY KEY,
                usuario VARCHAR(50) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                rol VARCHAR(50) DEFAULT 'usuario',
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        "tbl_plazas": f"""
            CREATE TABLE IF NOT EXISTS tbl_plazas (
                idtbl_plazas INT AUTO_INCREMENT PRIMARY KEY,
                numero INT NOT NULL,
                estado ENUM('libre','ocupada') DEFAULT 'libre',
                fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        "tbl_incidencias": f"""
            CREATE TABLE IF NOT EXISTS tbl_incidencias (
                idtbl_incidencias INT AUTO_INCREMENT PRIMARY KEY,
                descripcion TEXT NOT NULL,
                estado ENUM('abierta','cerrada') DEFAULT 'abierta',
                fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
    }

    cursor = conn.cursor()
    for nombre, sql in tablas_sql.items():
        cursor.execute(sql)
    conn.commit()
    cursor.close()


# =============================================================================
# 📗 SECCIÓN 3: EJECUTAR CONSULTAS (LECTURA)
# =============================================================================
def ejecutar_query(
    sql: str, params: Optional[tuple] = None, nombre_bd: str = "bd_tbl_comunes"
) -> List[Dict[str, Any]]:
    conn = get_connection(nombre_bd)
    cursor = conn.cursor(dictionary=True)
    try:
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        sql_strip = sql.lstrip().upper()
        if sql_strip.startswith(("SELECT", "SHOW", "DESCRIBE", "EXPLAIN")):
            return cursor.fetchall()
        else:
            conn.commit()
            return []
    finally:
        cursor.close()
        conn.close()


# =============================================================================
# 📗 SECCIÓN 4: EJECUTAR CONSULTAS (MODIFICACIÓN)
# =============================================================================
def ejecutar_non_query(
    sql: str, params: Optional[tuple] = None, nombre_bd: str = "bd_tbl_comunes"
) -> int:
    conn = get_connection(nombre_bd)
    cursor = conn.cursor()
    try:
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        conn.commit()
        return cursor.rowcount
    finally:
        cursor.close()
        conn.close()


# =============================================================================
# 📘 SECCIÓN 5: EJEMPLOS DE USO
# =============================================================================
"""
# Leer usuarios
usuarios = ejecutar_query("SELECT * FROM tbl_login")

# Insertar nuevo usuario
ejecutar_non_query(
    "INSERT INTO tbl_login (usuario, password) VALUES (%s,%s)",
    ("pepe","123456")
)

# Marcar plaza como ocupada
ejecutar_non_query(
    "UPDATE tbl_plazas SET estado='ocupada' WHERE idtbl_plazas=%s",
    (1,),
    nombre_bd="parquin_camiones"
)

# Crear incidencia
ejecutar_non_query(
    "INSERT INTO tbl_incidencias (descripcion) VALUES (%s)",
    ("Vía obstruida por contenedor",),
    nombre_bd="control_via_publica"
)
"""
