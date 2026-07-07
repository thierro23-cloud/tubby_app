# =============================================================================
# 🚛 RIO_TORIO · CAMIONES · ACCESOS
# =============================================================================
# 🔥 BTN REAL DEL SISTEMA (RIO_TORIO)
#   panel_parquin
#       ↓
#   modulo_parquin_rio_torio
#       ↓
#   btn_rio_torio_accesos   ← ESTE ARCHIVO
# =============================================================================

from __future__ import annotations

from datetime import datetime
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
    current_app,
)

from db import ejecutar_query, ejecutar_non_query

# =============================================================================
# 🏗️ 1️⃣ BLUEPRINT (BTN RIO_TORIO)
# =============================================================================
#
# Crea el blueprint de accesos para RIO_TORIO:
# - endpoint: "btn_rio_torio_accesos_bp"
# - prefijo de URL: /parquin/rio_torio/accesos
# - plantillas: las coge del template_folder global (templates/)
#
btn_rio_torio_accesos_bp = Blueprint(
    "btn_rio_torio_accesos_bp",
    __name__,
    url_prefix="/parquin/rio_torio/accesos",
)


# =============================================================================
# 🔐 2️⃣ SEGURIDAD
# =============================================================================


def _requiere_login():
    """
    Comprueba si hay un user_id en sesión.
    Si no lo hay, redirige a la vista de login del blueprint auth_bp.

    Devuelve:
      - None si el usuario está autenticado.
      - Response de redirect(...) si NO lo está (hay que retornar eso en la vista).
    """
    if not session.get("user_id"):
        flash("Debes iniciar sesión", "danger")
        return redirect(url_for("auth_bp.login"))
    return None


# =============================================================================
# 🧠 3️⃣ LÓGICA DE NEGOCIO
# =============================================================================


def rt_buscar_camiones_por_matricula_parcial(matricula: str, limite: int = 10):
    """
    Busca camiones activos cuya matrícula termine con los últimos 4 caracteres
    de `matricula` (búsqueda parcial).

    Devuelve lista de resultados (idtbl_camiones, matriculas, idtbl_usuarios).
    Si `matricula` está vacía, devuelve lista vacía.
    """
    if not matricula:
        return []

    # Últimos 4 caracteres como patrón
    patron = f"%{matricula[-4:]}"

    return ejecutar_query(
        """
        SELECT idtbl_camiones, matriculas, idtbl_usuarios
        FROM tbl_camiones
        WHERE activo = 1
          AND matriculas LIKE %s
        LIMIT %s
        """,
        (patron, limite),
        nombre_bd="parquin_camiones",
    )


def rt_registrar_entrada(id_camion: int):
    """
    Registra una entrada de camión en tbl_accesos.

    Inserta:
      - idtbl_camion
      - hora_entrada = ahora (datetime.now())

    Devuelve el momento de entrada (datetime).
    """
    ahora = datetime.now()

    ejecutar_non_query(
        "INSERT INTO tbl_accesos (idtbl_camion, hora_entrada) VALUES (%s, %s)",
        (id_camion, ahora),
        nombre_bd="parquin_camiones",
    )

    return ahora


def rt_registrar_salida(id_camion: int):
    """
    Registra salida de camión actualizando la entrada abierta (sin horas_salida).

    Actualiza:
      - horas_salida = ahora
    Filtra por idtbl_camion y NULL en horas_salida, ordena por entrada más reciente.

    Devuelve el momento de salida (datetime).
    """
    ahora = datetime.now()

    ejecutar_non_query(
        """
        UPDATE tbl_accesos
        SET horas_salida = %s
        WHERE idtbl_camion = %s AND horas_salida IS NULL
        ORDER BY hora_entrada DESC
        LIMIT 1
        """,
        (ahora, id_camion),
        nombre_bd="parquin_camiones",
    )

    return ahora


# =============================================================================
# 🎥 4️⃣ API LPR (CÁMARA)
# =============================================================================


@btn_rio_torio_accesos_bp.route("/api/lpr", methods=["POST"])
def btn_rio_torio_accesos_api_lpr():
    """
    Endpoint API para procesar lectura de matrícula desde cámara LPR.

    Espera:
        POST /parquin/rio_torio/accesos/api/lpr
        JSON: {"matricula": "ABC1234"}

    Devuelve:
        - 400 si no hay matricula.
        - JSON con: { "matricula", "coincidencias": [...] }.
    """
    data = request.get_json(silent=True) or {}
    matricula = (data.get("matricula") or "").upper()

    if not matricula:
        return jsonify({"error": "matricula requerida"}), 400

    camiones = rt_buscar_camiones_por_matricula_parcial(matricula)

    return jsonify(
        {
            "matricula": matricula,
            "coincidencias": camiones,
        }
    )


# =============================================================================
# 🚚 5️⃣ ENTRADA MANUAL
# =============================================================================


@btn_rio_torio_accesos_bp.route("/entrada", methods=["GET", "POST"])
def btn_rio_torio_accesos_entrada():
    """
    Vista de entrada manual de camiones.

    Rutas posibles:
      - GET  /parquin/rio_torio/accesos/entrada
          → Muestra formulario de lectura (cámara/teclado).
      - POST /parquin/rio_torio/accesos/entrada
          → Recibe matrícula, valida y muestra pantalla de confirmación de entrada.

    Requiere login; si no hay sesión, redirige a auth_bp.login.
    """
    redir = _requiere_login()
    if redir:
        return redir

    if request.method == "POST":
        matricula = request.form.get("matricula_leida", "").upper()

        coincidencias = rt_buscar_camiones_por_matricula_parcial(matricula)

        if not coincidencias:
            flash("No encontrado", "warning")
            return redirect(
                url_for("btn_rio_torio_accesos_bp.btn_rio_torio_accesos_entrada")
            )

        return render_template(
            "parquin/rio_torio/rio_torio_accesos_confirmar_entrada.html",
            coincidencias=coincidencias,
        )

    return render_template("parquin/rio_torio/rio_torio_accesos_lectura_camara.html")


# =============================================================================
# 📊 6️⃣ PANEL ACCESOS (PRINCIPAL)
# =============================================================================


@btn_rio_torio_accesos_bp.route("/", methods=["GET"])
def btn_rio_torio_accesos():
    """
    Vista principal del panel de accesos RIO_TORIO.

    Ruta:
      - GET  /parquin/rio_torio/accesos/

    Hace:
      - Requiere login.
      - Muestra lista de accesos (entrada/salida) con matrículas.
      - Pasa `now` = datetime.now() al template para mostrar fecha actual.

    Usa:
      - current_app.logger para debug de sesión.
      - ejecutar_query(...) para cargar tabla de accesos.
    """
    current_app.logger.info("DEBUG ACCESOS session = %s", dict(session))

    redir = _requiere_login()
    if redir:
        return redir

    accesos = ejecutar_query(
        """
        SELECT a.idtbl_accesos,
               c.matriculas,
               a.hora_entrada,
               a.horas_salida
        FROM tbl_accesos a
        LEFT JOIN tbl_camiones c ON c.idtbl_camiones = a.idtbl_camion
        ORDER BY a.hora_entrada DESC
        """,
        nombre_bd="parquin_camiones",
    )

    return render_template(
        "parquin/rio_torio/rio_torio_accesos.html",
        accesos=accesos,
        now=datetime.now(),
    )
