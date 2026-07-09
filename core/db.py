# =============================================================================
# 📡 MÓDULO DB – RADIO MÁGICA DE CONEXIÓN MySQL
# =============================================================================
# DESCRIPCIÓN GENERAL
# -------------------
# Este módulo se encarga de:
# 1️⃣ Abrir conexiones con MySQL a la base indicada.
# 2️⃣ Ejecutar consultas de lectura y escritura.
# 3️⃣ Garantizar cierre de cursores y conexiones.
# =============================================================================

from typing import Any, Dict, List, Optional
import mysql.connector
from flask import current_app


# =============================================================================
# 🔑 SECCIÓN 1: CONEXIÓN A BASE DE DATOS
# =============================================================================
def get_connection(
    nombre_bd: str = "bd_tbl_comunes",
) -> mysql.connector.MySQLConnection:
    """
    🔑 Abre conexión a la BD.
    - No crea la base ni tablas.
    - Solo conecta o falla.
    """

    # 1️⃣ Leer config Flask
    try:
        libro_casas = current_app.config.get("DATABASES")
    except RuntimeError:
        raise RuntimeError(
            "No hay contexto de aplicacion Flask disponible. "
            "Asegurate de llamar a get_connection() dentro de una request o app_context."
        )

    if not libro_casas:
        raise RuntimeError(
            "La configuracion 'DATABASES' no esta definida en la aplicacion Flask."
        )

    casa = libro_casas.get(nombre_bd)
    if not casa:
        disponibles = ", ".join(sorted(libro_casas.keys()))
        raise RuntimeError(
            f"No encuentro la base '{nombre_bd}'. Bases disponibles: {disponibles}"
        )

    host = casa["HOST"]
    user = casa["USER"]
    password = casa["PASSWORD"]
    database = casa["DB"]
    port = casa.get("PORT", 3306)

    # 2️⃣ Intentar conexión normal
    return mysql.connector.connect(
        host=host, user=user, password=password, database=database, port=port
    )

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
