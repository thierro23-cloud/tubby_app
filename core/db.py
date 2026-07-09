# =============================================================================
# MODULO DB - CONEXION A BASES DE DATOS MySQL
# =============================================================================
# DESCRIPCION GENERAL
# -------------------
# Este modulo se encarga de:
# 1) Abrir conexiones con MySQL a la base indicada.
# 2) Ejecutar consultas de lectura y escritura.
# 3) Garantizar cierre de cursores y conexiones.
#
# IMPORTANTE:
# - Las bases de datos deben existir previamente.
# - El esquema (tablas) debe gestionarse mediante migraciones, no desde aqui.
# - get_connection() solo conecta o falla con un error claro.
# =============================================================================

from typing import Any, Dict, List, Optional
import mysql.connector
from flask import current_app


# =============================================================================
# SECCION 1: CONEXION A LA BASE DE DATOS
# =============================================================================
def get_connection(
    nombre_bd: str = "bd_tbl_comunes",
) -> mysql.connector.MySQLConnection:
    """
    Abre una conexion a la base de datos indicada.

    Lee la configuracion desde current_app.config["DATABASES"].
    Falla con un RuntimeError claro si:
    - No hay contexto de aplicacion Flask activo.
    - La clave "DATABASES" no esta definida en la configuracion.
    - La base solicitada no esta en el diccionario DATABASES.
    - MySQL rechaza la conexion (credenciales, host, BD inexistente, etc.).

    No crea bases de datos ni tablas. Solo conecta o falla.
    """

    # 1) Leer config Flask -- no hay credenciales de fallback embebidas
    try:
        libro_casas = current_app.config.get("DATABASES")
    except RuntimeError:
        raise RuntimeError(
            "No hay contexto de aplicacion Flask disponible. "
            "Asegurate de llamar a get_connection() dentro de una request o app_context."
        )

    if not libro_casas:
        raise RuntimeError(
            "La configuracion 'DATABASES' no esta definida en la aplicacion Flask. "
            "Revisa config.py y las variables de entorno DB_HOST, DB_USER, DB_PASSWORD, DB_PORT."
        )

    casa = libro_casas.get(nombre_bd)
    if not casa:
        disponibles = ", ".join(sorted(libro_casas.keys()))
        raise RuntimeError(
            f"No encuentro la base '{nombre_bd}'. Bases disponibles: {disponibles}"
        )

    host = casa["HOST"]
    user = casa["USER"]
    pw = casa["PASSWORD"]
    database = casa["DB"]
    port = casa.get("PORT", 3306)

    # 2) Conectar -- si la BD no existe o las credenciales son incorrectas, se lanza Error
    conn = mysql.connector.connect(
        host=host, user=user, password=pw, database=database, port=port
    )
    return conn


# =============================================================================
# SECCION 2: EJECUTAR CONSULTAS (LECTURA)
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
# SECCION 3: EJECUTAR CONSULTAS (MODIFICACION)
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
