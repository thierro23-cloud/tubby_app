# =============================================================================
# 📡 1️⃣ MÓDULO DB – “RADIO MÁGICA” PARA HABLAR CON LAS BASES DE DATOS
# =============================================================================
# 1.1) ESQUEMA GENERAL
# --------------------
#   1) Importaciones y tipos
#       → Herramientas para conexiones limpias.
#   2) get_connection()
#       → Abre una conexión a una “casa” (base de datos).
#   3) ejecutar_query()
#       → Hace SELECT (lee datos).
#   4) ejecutar_non_query()
#       → Hace INSERT / UPDATE / DELETE (modifica datos).
#
# 1.2) CONCEPTO CLAVE
# -------------------
#   - current_app.config["DATABASES"] es el “libro de direcciones”
#     de todas las casas de datos.
#   - Cada clave (p. ej. "bd_tbl_comunes", "parquin_camiones",
#     "control_via_publica") describe cómo conectarse a esa BD.
#   - Todas las funciones de este módulo usan SIEMPRE ese libro de
#     direcciones para ser independientes del entorno
#     (desarrollo, producción, etc.).
# =============================================================================

from typing import Any, Dict, List, Optional  # 🧩 Tipos para escribir código claro

import mysql.connector                        # 🔌 Cliente MySQL
from mysql.connector import Error             # 🚨 Tipo de error de MySQL

from flask import current_app                 # 📋 Config y logger de la app Flask


# =============================================================================
# 📗 2️⃣ SECCIÓN – LIBRO DE DIRECCIONES: current_app.config["DATABASES"]
# =============================================================================
# 2.1) NOTA IMPORTANTE
# --------------------
# En lugar de definir aquí las credenciales, este módulo SIEMPRE las lee
# desde current_app.config["DATABASES"], que deberías tener en tu create_app
# o config:
#
#   app.config["DATABASES"] = {
#       "bd_tbl_comunes": {
#           "HOST": "localhost",
#           "USER": "root",
#           "PASSWORD": "tu_password",
#           "DB": "bd_tbl_comunes",
#           "PORT": 3306,
#       },
#       "parquin_camiones": {
#           "HOST": "localhost",
#           "USER": "root",
#           "PASSWORD": "tu_password",
#           "DB": "parquin_camiones",
#           "PORT": 3306,
#       },
#       "control_via_publica": {
#           "HOST": "localhost",
#           "USER": "root",
#           "PASSWORD": "tu_password",
#           "DB": "control_via_publica",
#           "PORT": 3306,
#       },
#   }
#
# 2.2) VENTAJAS
# -------------
#   - Cambias credenciales solo en la config.
#   - El código de acceso a BD no necesita tocarse al cambiar de entorno.
# =============================================================================


# =============================================================================
# 🔑 3️⃣ SECCIÓN – FUNCIÓN get_connection(): ABRIR LA PUERTA DE UNA “CASA”
# =============================================================================
def get_connection(nombre_bd: str = "bd_tbl_comunes") -> mysql.connector.MySQLConnection:
    """
    3.0️⃣ DESCRIPCIÓN GENERAL
    ------------------------
    Abre la puerta de una casa de datos definida en current_app.config["DATABASES"].

    3.1️⃣ PARÁMETROS
    ----------------
    nombre_bd : str
        Nombre lógico de la casa en el "libro de direcciones".
        Debe ser una de las claves de current_app.config["DATABASES"], por ejemplo:
        - "bd_tbl_comunes"
        - "parquin_camiones"
        - "control_via_publica"

    3.2️⃣ COMPORTAMIENTO DOCENTE
    ----------------------------
    1) Lee el diccionario DATABASES de la configuración de Flask.
    2) Busca la entrada con clave igual a nombre_bd.
    3) Si no existe:
        - Lanza RuntimeError indicando qué casas están disponibles.
    4) Si existe:
        - Extrae HOST, USER, PASSWORD, DB, PORT.
        - Crea una conexión mysql.connector.connect(...)
        - Devuelve esa conexión para que el llamante la use.

    3.3️⃣ EJEMPLOS
    --------------
    # Casa principal (usuarios, roles, etc.)
    conn = get_connection("bd_tbl_comunes")

    # Casa del parquin de camiones
    conn = get_connection("parquin_camiones")

    # Casa de vía pública
    conn = get_connection("control_via_publica")
    """

    # 3.4️⃣ Leemos el "libro de direcciones" de todas las casas
    libro_casas: Optional[Dict[str, Dict[str, Any]]] = current_app.config.get("DATABASES")

    # 3.5️⃣ Si no hay DATABASES en la config, no podemos continuar
    if not libro_casas:
        raise RuntimeError(
            "❌ No hay 'DATABASES' definido en la configuración de Flask.\n"
            "   Debes registrar app.config['DATABASES'] en tu create_app/config "
            "con las casas de datos disponibles."
        )

    # 3.6️⃣ Buscamos la casa concreta que nos piden por nombre_bd
    casa = libro_casas.get(nombre_bd)

    # 3.7️⃣ Si no existe esa casa, explicamos qué casas SÍ existen
    if not casa:
        disponibles = ", ".join(sorted(libro_casas.keys()))
        raise RuntimeError(
            f"❌ ¡No encuentro la casa '{nombre_bd}' en el libro de DATABASES!\n"
            f"   Casas disponibles: {disponibles}"
        )

    # 3.8️⃣ Extraemos los datos de conexión de esa casa
    host = casa["HOST"]           # 🌐 Dirección IP o nombre de host (ej: localhost)
    user = casa["USER"]           # 👤 Usuario de la BD (ej: root)
    password = casa["PASSWORD"]   # 🔑 Contraseña
    database = casa["DB"]         # 🏠 Nombre de la base de datos (schema)
    port = casa.get("PORT", 3306) # 🚪 Puerto de MySQL (3306 por defecto)

    try:
        # 3.9️⃣ Intentamos abrir la conexión con MySQL
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=port,
        )

        # 3.10️⃣ Si tenemos logger de Flask, registramos que todo ha ido bien
        try:
            current_app.logger.info("✅ ¡Puerta abierta! BD=%s 🏠", database)
        except Exception:
            # Si por algún motivo no hay logger (por ejemplo en scripts sueltos),
            # simplemente ignoramos el fallo de logging.
            pass

        # 3.11️⃣ Devolvemos la conexión abierta al llamante
        return conn

    except Error as e:
        # 3.12️⃣ Si algo falla al abrir la conexión, intentar loguearlo
        try:
            current_app.logger.error("❌ ¡Puerta cerrada! BD=%s: %s 🚪", database, e)
        except Exception:
            # Como último recurso, mostramos el error por consola
            print(f"❌ Error abriendo {database}: {e}")

        # 3.13️⃣ Re-lanzamos el error para que el código de arriba pueda gestionarlo
        raise


# =============================================================================
# 🔍 4️⃣ SECCIÓN – FUNCIÓN ejecutar_query(): CONSULTAS SQL (LECTURA / ESCRITURA)
# =============================================================================
def ejecutar_query(
    sql: str,
    params: Optional[tuple] = None,
    nombre_bd: str = "bd_tbl_comunes",
) -> List[Dict[str, Any]]:
    """
    4.0️⃣ DESCRIPCIÓN GENERAL
    ------------------------
    Ejecuta una sentencia SQL sobre la BD indicada.

    - Si la sentencia es de LECTURA (SELECT, SHOW, DESCRIBE, EXPLAIN),
      devuelve una lista de dicts con las filas.
    - Si la sentencia es de ESCRITURA (INSERT, UPDATE, DELETE, REPLACE),
      hace COMMIT y devuelve una lista vacía.

    4.1️⃣ PARÁMETROS
    ----------------
    sql : str
        Sentencia SQL a ejecutar.
    params : Optional[tuple]
        Parámetros para la consulta, para usar placeholders %s de forma segura.
    nombre_bd : str
        Nombre de la casa en current_app.config["DATABASES"].

    4.2️⃣ DEVUELVE
    --------------
    List[Dict[str, Any]]
        - SELECT → lista de filas (cada fila dict {columna: valor}).
        - INSERT/UPDATE/DELETE → lista vacía.
    """

    # 4.3️⃣ Abrir conexión a la BD (puerta de la casa)
    conn = get_connection(nombre_bd)

    # 4.4️⃣ Crear cursor que devuelve filas como diccionarios
    cursor = conn.cursor(dictionary=True)

    try:
        # 4.5️⃣ Determinar tipo de sentencia: lectura vs escritura
        sql_strip = sql.lstrip().upper()
        es_lectura = sql_strip.startswith(
            ("SELECT", "SHOW", "DESCRIBE", "EXPLAIN")
        )

        # 4.6️⃣ Registrar en el log la consulta y sus parámetros (si los hay)
        #       → Esto es clave para depurar errores tipo 1054 y ver el SQL real.
        try:
            current_app.logger.info("🔍 [QUERY %s] SQL: %r", nombre_bd, sql)
            if params is not None:
                current_app.logger.info("   ↳ params: %r", params)
        except Exception:
            # Si no hay logger disponible, simplemente seguimos.
            pass

        # 4.7️⃣ Ejecutar la consulta, con o sin parámetros
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)

        # 4.8️⃣ Según el tipo de sentencia, actuar:
        if es_lectura:
            # 4.8.1️⃣ Consulta de LECTURA → recoger filas y devolverlas
            respuestas: List[Dict[str, Any]] = cursor.fetchall()
            return respuestas
        else:
            # 4.8.2️⃣ Consulta de ESCRITURA → hacer COMMIT y devolver lista vacía
            conn.commit()
            return []

    finally:
        # 4.9️⃣ Cerrar siempre cursor y conexión (éxito o error)
        cursor.close()
        conn.close()


# =============================================================================
# ✏️ 5️⃣ SECCIÓN – FUNCIÓN ejecutar_non_query(): INSERT / UPDATE / DELETE
# =============================================================================
# 5.1) OBJETIVO GLOBAL
# --------------------
# - Proporcionar un ÚNICO punto de entrada para todos los comandos SQL de
#   modificación: INSERT, UPDATE y DELETE.
# - Encapsular la lógica de:
#       · abrir conexión a la BD correcta (la "casa" nombre_bd),
#       · ejecutar la sentencia con parámetros (usando placeholders %s),
#       · hacer commit de los cambios,
#       · cerrar recursos (cursor y conexión),
#       · devolver el número de filas afectadas.
#
# - Al usar parámetros (cursor.execute(sql, params)) evitamos construir SQL
#   a mano con concatenaciones y reducimos riesgo de inyección SQL.
#
# - ESTA VERSIÓN ES CORRECTA PARA LOS DECIMAL/NULL:
#       · No transforma los parámetros a str().
#       · Si le pasas None en params, el driver lo convierte en NULL
#         en MySQL, lo que permite guardar campos DECIMAL opcionales
#         (como latitud/longitud) sin generar el error:
#            "Incorrect decimal value: 'None' for column 'latitud'".
#   Siempre que:
#       · las columnas permitan NULL,
#       · desde la vista envíes None para campos vacíos y cadenas
#         numéricas válidas para los rellenos. [web:193]
# =============================================================================
def ejecutar_non_query(
    sql: str,
    params: Optional[tuple] = None,
    nombre_bd: str = "bd_tbl_comunes",
) -> int:
    """
    5.2️⃣ DESCRIPCIÓN GENERAL
    ------------------------
    Cambia cosas en la casa: INSERT, UPDATE, DELETE.

    5.3️⃣ PARÁMETROS
    ----------------
    sql : str
        Sentencia SQL de modificación (INSERT, UPDATE o DELETE).
        Debe usar placeholders %s para cada parámetro.
    params : Optional[tuple]
        Tuple con los valores a enlazar en la sentencia SQL, en el
        mismo orden que los %s. Si no hay parámetros, puede ser None.
    nombre_bd : str
        Nombre de la casa (base de datos) tal y como está definida en
        current_app.config["DATABASES"]. Por defecto: "bd_tbl_comunes".

    5.4️⃣ DEVUELVE
    --------------
    int
        Número de filas afectadas por la operación (cursor.rowcount).

    5.5️⃣ EJEMPLOS DE USO
    ---------------------
    # 1) Insertar un usuario en la casa principal
    filas = ejecutar_non_query(
        "INSERT INTO tbl_login (usuario, password) VALUES (%s, %s)",
        ("pepe", "secreto"),
    )

    # 2) Marcar una plaza como ocupada en el parquin de camiones
    cambios = ejecutar_non_query(
        "UPDATE tbl_plazas SET estado='ocupada' WHERE idtbl_plazas=%s",
        (123,),
        nombre_bd="parquin_camiones",
    )

    # 3) Borrar un registro en control_via_publica
    borradas = ejecutar_non_query(
        "DELETE FROM tbl_incidencias WHERE id=%s",
        (42,),
        nombre_bd="control_via_publica",
    )
    """

    # 5.6️⃣ Abrimos la puerta de la casa indicada (nombre_bd)
    conn = get_connection(nombre_bd)

    # 5.7️⃣ Creamos un cursor normal (no hace falta dictionary=True)
    cursor = conn.cursor()

    try:
        # 5.8️⃣ Registramos la operación en el logger (si existe)
        #       → Muy útil para depuración: ver el SQL y params reales.
        try:
            current_app.logger.info("✏️ [NONQUERY %s] SQL: %r", nombre_bd, sql)
            if params is not None:
                current_app.logger.info("   ↳ params: %r", params)
        except Exception:
            # Si no hay logger (por ejemplo en tests), no bloqueamos nada.
            pass

        # 5.9️⃣ Ejecutamos la sentencia SQL, con o sin parámetros
        # - Si params es un tuple con valores:
        #       cursor.execute(sql, params)
        #   Deja que el driver adapte los tipos:
        #       · None      → NULL en MySQL.
        #       · str/float → se convierten según el tipo de columna.
        #
        # - Importante: NO convertir params a str() aquí, para que:
        #       None siga siendo None,
        #       y las columnas DECIMAL acepten correctamente NULL.
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)

        # 5.10️⃣ Confirmamos (commit) los cambios en la base de datos
        conn.commit()

        # 5.11️⃣ Obtenemos cuántas filas se han visto afectadas
        cambios: int = cursor.rowcount

        # 5.12️⃣ Devolvemos ese número al llamante
        return cambios

    finally:
        # 5.13️⃣ Siempre cerramos cursor y conexión aunque haya error
        cursor.close()
        conn.close()


# =============================================================================
# 🎓 6️⃣ SECCIÓN – RESUMEN DOCENTE: CÓMO USAR ESTE MÓDULO
# =============================================================================
"""
6.1️⃣ USO TÍPICO EN OTROS MÓDULOS
--------------------------------

from db import ejecutar_query, ejecutar_non_query

# 1) LEER DATOS (SELECT) DE LA CASA PRINCIPAL
usuarios = ejecutar_query("SELECT * FROM tbl_login")

# 2) LEER DATOS DEL PARQUIN
plazas = ejecutar_query(
    "SELECT * FROM tbl_plazas",
    nombre_bd="parquin_camiones",
)

# 3) MODIFICAR DATOS (UPDATE) EN CONTROL VÍA PÚBLICA
ejecutadas = ejecutar_non_query(
    "UPDATE tbl_incidencias SET estado='cerrada' WHERE id=%s",
    (99,),
    nombre_bd="control_via_publica",
)

6.2️⃣ IDEA CENTRAL
-----------------
La idea es que el resto de la aplicación NO se preocupe de host/usuario/password:
solo tiene que saber el nombre lógico de la casa ("bd_tbl_comunes", "parquin_camiones",
"control_via_publica") y este módulo se encarga de todo lo demás. 📡✨
"""