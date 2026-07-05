import mysql.connector        # 🧩 Esta pieza nos deja hablar con la base de datos MySQL
import psycopg2               # 🧩 Esta pieza nos deja hablar con la base de datos PostgreSQL
import psycopg2.extras        # 🧩 Estas piezas extra nos dan resultados más cómodos (diccionarios)

# --- CONFIGURACIÓN ---

MYSQL_CONFIG = {              # 🧩 Aquí guardamos los datos para entrar en MySQL
    "host": "localhost",      # 🧩 El ordenador donde está MySQL (normalmente tu PC)
    "port": 3306,             # 🧩 La puerta de MySQL (suele ser 3306)
    "user": "root",      # 🧩 Tu nombre de usuario en MySQL
    "password": "f@Fe1132", # 🧩 Tu contraseña de MySQL
    "database": "control_obras",      # 🧩 El nombre de la base donde está tbl_obras
}

PG_CONFIG = {                 # 🧩 Aquí guardamos los datos para entrar en PostgreSQL
    "host": "localhost",      # 🧩 El ordenador donde está PostgreSQL
    "port": 5432,             # 🧩 La puerta de PostgreSQL (suele ser 5432)
    "user": "postgres",       # 🧩 Tu usuario de PostgreSQL
    "password": "F@Fe1132",    # 🧩 Tu contraseña de PostgreSQL
    "dbname": "gis_municipal",       # 🧩 La base donde creamos obras_gis
}

# --- CONEXIONES ---

def get_mysql_conn():               # 🧩 Esta función abre una puerta a MySQL
    return mysql.connector.connect(**MYSQL_CONFIG)  # 🧩 Usa la configuración de arriba

def get_pg_conn():                  # 🧩 Esta función abre una puerta a PostgreSQL
    return psycopg2.connect(**PG_CONFIG)            # 🧩 Usa la configuración de arriba


def sync_obras():                   # 🧩 Esta función es la que hace toda la magia de sincronizar
    # 1) Leer obras de MySQL
    my_conn = get_mysql_conn()      # 🧩 Abrimos conexión con MySQL
    pg_conn = get_pg_conn()         # 🧩 Abrimos conexión con PostgreSQL

    try:                            # 🧩 Intentamos hacer todo esto
        my_cur = my_conn.cursor(dictionary=True)  # 🧩 Creamos un cursor que devuelve filas como diccionario

        my_cur.execute("""         # 🧩 Le pedimos a MySQL todas las obras
            SELECT
                idtbl_obras,
                idtbl_gis_municipal,
                idtbl_proveedor,
                idtbl_municipios,
                idtbl_tipos_de_vias,
                idtbl_calles,
                idtbl_tipos_de_vias1,
                idtbl_calles1,
                observaciones,
                lat,
                lon
            FROM tbl_obras
        """)                        # 🧩 Aquí acaba la consulta SQL
        obras = my_cur.fetchall()   # 🧩 Guardamos todas las obras en una lista llamada obras

        pg_cur = pg_conn.cursor(    # 🧩 Creamos un cursor para PostgreSQL
            cursor_factory=psycopg2.extras.RealDictCursor  # 🧩 También devuelve diccionarios
        )

        for obra in obras:          # 🧩 Recorremos cada obra de la lista
            idtbl_obras = obra["idtbl_obras"]             # 🧩 Cogemos el id de la obra
            id_gis = obra["idtbl_gis_municipal"]          # 🧩 Cogemos el id que apunta a GIS (si existe)
            lat = obra["lat"]                             # 🧩 Cogemos la latitud
            lon = obra["lon"]                             # 🧩 Cogemos la longitud

            # Si no hay coordenadas, no podemos crear geom
            if lat is None or lon is None:   # 🧩 Si faltan lat o lon
                continue                     # 🧩 Saltamos esta obra y pasamos a la siguiente

            if id_gis is None:               # 🧩 Si la obra aún NO tiene id GIS
                # 2a) Insertar nueva obra en obras_gis
                pg_cur.execute(             # 🧩 Mandamos una orden a PostgreSQL
                    """
                    INSERT INTO obras_gis (
                        idtbl_obras,
                        idtbl_proveedor,
                        idtbl_municipios,
                        idtbl_tipos_de_vias,
                        idtbl_calles,
                        idtbl_tipos_de_vias1,
                        idtbl_calles1,
                        observaciones,
                        lat,
                        lon,
                        geom
                    )
                    VALUES (
                        %(idtbl_obras)s,
                        %(idtbl_proveedor)s,
                        %(idtbl_municipios)s,
                        %(idtbl_tipos_de_vias)s,
                        %(idtbl_calles)s,
                        %(idtbl_tipos_de_vias1)s,
                        %(idtbl_calles1)s,
                        %(observaciones)s,
                        %(lat)s,
                        %(lon)s,
                        ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)
                    )
                    RETURNING id;
                    """,                     # 🧩 Fin del SQL
                    obra,                    # 🧩 Usamos los datos de la obra para rellenar los %(...)
                )
                new_id = pg_cur.fetchone()["id"]  # 🧩 Leemos el id nuevo que creó obras_gis

                # 2b) Guardar ese id en MySQL
                my_cur.execute(                   # 🧩 Actualizamos la obra en MySQL
                    """
                    UPDATE tbl_obras
                    SET idtbl_gis_municipal = %s
                    WHERE idtbl_obras = %s
                    """,
                    (new_id, idtbl_obras),       # 🧩 Ponemos el id GIS nuevo en la fila de esa obra
                )

            else:                     # 🧩 Si la obra YA tenía id GIS (ya estaba en obras_gis)
                # 3) Actualizar obra existente en obras_gis (por si cambian lat/lon)
                pg_cur.execute(       # 🧩 Mandamos una orden de UPDATE a PostgreSQL
                    """
                    UPDATE obras_gis
                    SET
                        idtbl_proveedor = %(idtbl_proveedor)s,
                        idtbl_municipios = %(idtbl_municipios)s,
                        idtbl_tipos_de_vias = %(idtbl_tipos_de_vias)s,
                        idtbl_calles = %(idtbl_calles)s,
                        idtbl_tipos_de_vias1 = %(idtbl_tipos_de_vias1)s,
                        idtbl_calles1 = %(idtbl_calles1)s,
                        observaciones = %(observaciones)s,
                        lat = %(lat)s,
                        lon = %(lon)s,
                        geom = ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)
                    WHERE id = %s
                    """,
                    {**obra, "id": id_gis},   # 🧩 Enviamos todos los datos de la obra y el id GIS actual
                )

        # Confirmar cambios
        pg_conn.commit()              # 🧩 Guardamos todo lo que hicimos en PostgreSQL
        my_conn.commit()              # 🧩 Guardamos todo lo que hicimos en MySQL

    finally:                          # 🧩 Pase lo que pase (bien o mal), se ejecuta esto
        my_conn.close()               # 🧩 Cerramos la puerta de MySQL
        pg_conn.close()               # 🧩 Cerramos la puerta de PostgreSQL


if __name__ == "__main__":            # 🧩 Si ejecutamos este archivo directamente desde la consola
    sync_obras()                      # 🧩 Llamamos a la función que sincroniza todas las obras
    print("Sincronización obras → obras_gis completada.")  # 🧩 Mostramos un mensajito al terminar
