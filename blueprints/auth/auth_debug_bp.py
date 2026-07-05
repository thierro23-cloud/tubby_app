from flask import Blueprint, render_template, request
from db import get_connection
import bcrypt

# =============================================================================
# 🐛 BLUEPRINT DEBUG LOGIN · PROBAR COMBINACIONES IDENTIFICADOR + HASH
# =============================================================================
# ¿Para qué sirve este módulo?
# -----------------------------------------------------------------------------
# Este blueprint NO es para usuarios finales, es una herramienta de DEBUG
# para ti como desarrollador / admin técnico.
#
# Objetivo:
#   - Ver rápidamente qué identificadores y password_hash existen en tbl_login.
#   - Probar combinaciones concretas (identificador + password_hash) y ver
#     exactamente qué fila de tbl_login + rol devuelve la BD.
#
# Cuándo usarlo:
#   - Cuando no sabes qué hash tiene un usuario y quieres verlo sin entrar por
#     consola SQL.
#   - Cuando dudas de si un login falla por el identificador, por el hash o
#     por el rol asociado.
#   - Cuando quieres inspeccionar una fila real de tbl_login uniendo tbl_roles.
#
# Flujo de la pantalla:
#   1. Muestra dos combos:
#        - Lista de todos los identificadores distintos de tbl_login.
#        - Lista de todos los password_hash distintos de tbl_login.
#   2. Tú eliges un identificador y un hash y pulsas Enviar.
#   3. El backend busca EXACTAMENTE esa combinación en la BD:
#        WHERE l.identificador = X AND l.password_hash = Y
#      y hace LEFT JOIN con tbl_roles para traerse info del rol.
#   4. Si existe, te enseña todos los campos de esa fila en la plantilla
#      login_debug_combo.html. Si no, muestra un mensaje de error claro.
#
# Importante:
#   - No se usa en producción abierta al público: expone hashes y estructura
#     interna de login. Es una herramienta de laboratorio interno.
# =============================================================================

debug_login_bp = Blueprint("debug_login_bp", __name__, url_prefix="/debug")


@debug_login_bp.route("/login_combo", methods=["GET", "POST"])
def login_combo():
    """
    🔎 Pantalla de depuración para login: seleccionar IDENTIFICADOR + HASH.

    Qué hace paso a paso:
      1. Conecta a la BD y lee:
           - Todos los identificadores únicos de tbl_login.
           - Todos los password_hash únicos de tbl_login.
         Esos datos se envían a la plantilla para rellenar dos <select>.

      2. Si la petición es GET:
           - Solo renderiza el formulario con las listas de identificadores
             y hashes disponibles.

      3. Si la petición es POST:
           - Lee del formulario qué identificador y qué hash has seleccionado.
           - Si falta alguno, devuelve un error.
           - Si están los dos, lanza una consulta SQL que busca EXACTAMENTE
             esa combinación en tbl_login, uniendo además con tbl_roles para
             tener el nombre del rol.
           - Si no hay resultados, muestra un mensaje indicando que no existe
             esa fila.
           - Si hay resultado, lo guarda en "resultado" para que la plantilla
             lo pinte (verás todos los campos de esa fila en pantalla).

    En resumen:
      Esta vista te permite, sin abrir un cliente SQL, inspeccionar y verificar
      el contenido real de tbl_login para una pareja identificador + hash,
      y ver qué rol tiene asignado.
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # 1️⃣ Todos los identificadores disponibles en tbl_login (para el combo)
    cursor.execute(
        """
        SELECT DISTINCT identificador
        FROM tbl_login
        WHERE identificador IS NOT NULL
        ORDER BY identificador
        """
    )
    identificadores = [r["identificador"] for r in cursor.fetchall()]

    # 2️⃣ Todos los password_hash distintos (para el combo de hashes)
    cursor.execute(
        """
        SELECT DISTINCT password_hash
        FROM tbl_login
        WHERE password_hash IS NOT NULL
        """
    )
    passwords = [r["password_hash"] for r in cursor.fetchall()]

    resultado = None
    error = None

    # 3️⃣ Procesar el formulario cuando envías una combinación
    if request.method == "POST":
        ident_sel = request.form.get("identificador_sel", "").strip()
        pass_sel = request.form.get("password_sel", "").strip()

        if not ident_sel or not pass_sel:
            # Falta alguno de los dos campos
            error = "Debes elegir identificador y password_hash."
        else:
            # Buscamos esa combinación EXACTA en tbl_login + rol
            cursor.execute(
                """
                SELECT
                    l.idtbl_login,
                    l.idtbl_gestores,
                    l.identificador,
                    l.email,
                    l.password_hash,
                    l.idtbl_roles       AS login_idtbl_roles,
                    r.idtbl_roles       AS rol_idtbl_roles,
                    r.nombre            AS rol_nombre
                FROM tbl_login l
                LEFT JOIN tbl_roles r ON l.idtbl_roles = r.idtbl_roles
                WHERE l.identificador = %s
                  AND l.password_hash = %s
                """,
                (ident_sel, pass_sel),
            )
            row = cursor.fetchone()
            if not row:
                # No existe esa combinación exacta en la BD
                error = (
                    "No existe ninguna fila en tbl_login con ese "
                    "identificador y ese password_hash."
                )
            else:
                # Tenemos una fila real: la mandamos a la plantilla
                resultado = row

    cursor.close()
    conn.close()

    # 4️⃣ Render: formulario + listas + posible resultado o error
    return render_template(
        "auth/login_debug_combo.html",
        identificadores=identificadores,
        passwords=passwords,
        resultado=resultado,
        error=error,
    )
