# =============================================================================
# 🔐 PANEL PERMISOS · SUPER ADMIN (POR BD, TABLA Y ROL)
# =============================================================================
# ✅ Propósito:
#    Panel para que el super admin gestione permisos por:
#       - Base de datos (schema)
#       - Tabla
#       - Rol (gestor / policia / usuario)
#
# ✅ Flujo:
#    1. GET  /panel-permisos
#         - Muestra un formulario dentro del super admin:
#             a) select de BD (todas menos las de sistema)
#             b) al elegir BD → select de tablas de esa BD
#             c) al elegir tabla → checkboxes de roles para esa BD+tabla
#    2. POST /panel-permisos
#         - Guarda los permisos para la BD+tabla seleccionadas
#
# ✅ Características:
#    - Totalmente automático: si añades una BD nueva, aparece sola.
#    - No dependes de listas fijas de bases/tabla en el código.
#    - Diseño pensado para incluirse en el panel super admin.
# =============================================================================

from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import ejecutar_query, ejecutar_non_query
from services.helpers import super_admin_required

panel_permisos_bp = Blueprint(
    "panel_permisos_bp",   # 📌 Nombre interno del blueprint
    __name__,
    url_prefix="/panel-permisos"   # 🌐 Prefijo de URL propio del panel
)


# =============================================================================
# 🧰 1️⃣ HELPERS DE DATOS (BD / TABLAS / PERMISOS)
# =============================================================================

def obtener_bases_datos():
    """
    🔎 Devuelve las bases de datos "de trabajo" del servidor.

    1. Ejecuta SHOW DATABASES en MySQL.
    2. Filtra las BDs de sistema: information_schema, mysql, performance_schema, sys.
    3. Devuelve la lista de nombres de BD que el super admin puede gestionar.

    ➕ Ventaja: si mañana creas 'patrulla_verde', aparecerá sola sin tocar código.
    """
    rows = ejecutar_query("SHOW DATABASES")  # Cada fila tiene clave 'Database'
    todas = [r["Database"] for r in rows]

    excluir = {"information_schema", "mysql", "performance_schema", "sys"}
    bases = [bd for bd in todas if bd not in excluir]

    return bases


def obtener_tablas_de_bd(nombre_bd):
    """
    🔎 Devuelve todas las tablas base (no vistas) de una BD concreta.

    1. Lee information_schema.tables de MySQL.
    2. Filtra por:
         - table_schema = nombre de la BD seleccionada
         - table_type   = 'BASE TABLE' (solo tablas normales)
    3. Ordena alfabéticamente por nombre de tabla.

    ➕ Se usa para alimentar el <select> de tablas tras elegir BD.
    """
    if not nombre_bd:
        return []

    rows = ejecutar_query("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = %s
          AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """, (nombre_bd,))

    return [r["table_name"] for r in rows]


def obtener_permisos_bd_tabla(nombre_bd, tabla):
    """
    🔎 Devuelve los permisos actuales para una combinación BD + tabla.

    Tabla de trabajo propuesta (ajústala a la tuya):
      permisos_tablas (bd VARCHAR, tabla VARCHAR, rol VARCHAR, permitido TINYINT)

    1. Consulta por bd + tabla.
    2. Construye un dict {rol: True/False} para 'gestor', 'policia', 'usuario'.

    Si no hay registros todavía, devuelve dict vacío.
    """
    if not nombre_bd or not tabla:
        return {}

    rows = ejecutar_query("""
        SELECT rol, permitido
        FROM bd_tbl_comunes.permisos_tablas
        WHERE bd = %s
          AND tabla = %s
    """, (nombre_bd, tabla))

    permisos = {r["rol"]: bool(r["permitido"]) for r in rows}
    return permisos


def guardar_permisos_bd_tabla(nombre_bd, tabla, permisos_dict):
    """
    💾 Guarda los permisos de una BD + tabla concreta.

    Input:
      - nombre_bd:   'bd_tbl_comunes', etc.
      - tabla:       bd_tbl_comunes.tbl_permisos_tablas.
      - permisos_dict: dict con claves 'gestor'/'policia'/'usuario' y valores True/False.

    Estrategia:
      1. Borrado previo de registros de esa combinación BD+tabla.
      2. Inserción de filas por cada rol con permitido = 0/1.

    ➕ No toca permisos de otras tablas ni de otras BDs.
    """
    if not nombre_bd or not tabla:
        return

    # 1️⃣ Borrar permisos previos solo de esa BD+tabla
    ejecutar_non_query("""
        DELETE FROM bd_tbl_comunes.tbl_permisos_tablas
        WHERE bd = %s
          AND tabla = %s
    """, (nombre_bd, tabla))

    # 2️⃣ Insertar permisos actualizados
    for rol, permitido in permisos_dict.items():
        ejecutar_non_query("""
            INSERT INTO db_tbl_comunes.tbl_permisos_tablas (bd, tabla, rol, permitido)
            VALUES (%s, %s, %s, %s)
        """, (nombre_bd, tabla, rol, 1 if permitido else 0))



# =============================================================================
# 🌐 2️⃣ PANEL PRINCIPAL (PANTALLA PERMISOS)
# =============================================================================

@panel_permisos_bp.route("/", methods=["GET", "POST"])
@super_admin_required
def panel_permisos():
    """
    Vista principal del panel de permisos.

    🔁 Comportamiento mixto GET/POST:
      - GET inicial:
          * Carga lista de BDs (select BD)
          * Si hay bd y tabla en querystring, muestra tabla + permisos.
      - POST:
          * Puede venir de:
              a) cambio de BD (solo recarga tablas)
              b) cambio de tabla (solo recarga permisos)
              c) clic en "Guardar" (persistir permisos)
    """
    # 1️⃣ Parámetros de entrada (BD y tabla seleccionadas)
    #    - Permite tanto GET (?bd=...&tabla=...) como POST (form).
    bd = request.values.get("bd")      # BD seleccionada
    tabla = request.values.get("tabla")  # Tabla seleccionada

    # 2️⃣ Lista de BDs para el desplegable (automático)
    bases_datos = obtener_bases_datos()

    # 3️⃣ Lista de tablas de la BD elegida
    tablas = obtener_tablas_de_bd(bd) if bd else []

    # 4️⃣ Roles disponibles (de momento fijos)
    roles = ["gestor", "policia", "usuario"]

    # 5️⃣ Permisos actuales para esa BD + tabla
    permisos = obtener_permisos_bd_tabla(bd, tabla) if (bd and tabla) else {}

    # 6️⃣ Si viene un POST con botón de guardar, procesamos permisos
    <input type="hidden" name="accion" value="guardar">
        # Construir dict de permisos a partir de checkboxes
        nuevos_permisos = {
            "gestor": bool(request.form.get("perm[gestor]")),
            "policia": bool(request.form.get("perm[policia]")),
            "vigilantes": bool(request.form.get("perm[vigilantes]")),
            "usuario": bool(request.form.get("perm[usuario]")),
        }

        guardar_permisos_bd_tabla(bd, tabla, nuevos_permisos)
        flash("✅ Permisos actualizados correctamente", "success")

        # Refrescamos permisos desde BD para reflejar lo guardado
        permisos = obtener_permisos_bd_tabla(bd, tabla)

    # 7️⃣ Render: esta plantilla puedes usarla como página propia
    #     o como include dentro de tu panel super_admin.
    return render_template(
        "permisos/panel_permisos.html",
        bases_datos=bases_datos,   # Lista de BDs disponibles
        bd_seleccionada=bd,        # BD actual (o None)
        tablas=tablas,             # Tablas de esa BD
        tabla_seleccionada=tabla,  # Tabla actual (o None)
        roles=roles,               # Roles fijos
        permisos=permisos          # Permisos de esa BD+tabla {rol: True/False}
    )
