# =============================================================================
# 🛡️ AUTH BLUEPRINT · SISTEMA DE AUTENTICACIÓN PROFESIONAL
# =============================================================================
# 🎯 OBJETIVO:
#   Controlar todo el sistema de login/logout, manejo de sesiones y redirección
#   según el rol del usuario. Incluye:
#     - Login profesional con bcrypt
#     - Registro de intentos de login (éxito / fallo) en tbl_auditoria_intentos
#     - Logout con auditoría de IP y hora
#     - Redirección segura según rol
#     - Debug de endpoints
#     - Recuperación de contraseña simulada
# =============================================================================

# =============================================================================
# 1️⃣ IMPORTACIONES
# =============================================================================
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    current_app,
)
from db import get_connection        # 🔌 Conexión a base de datos
import bcrypt                        # 🔐 Seguridad de contraseñas

# =============================================================================
# 2️⃣ DEFINICIÓN DEL BLUEPRINT
# =============================================================================
auth_bp = Blueprint(
    "auth_bp",        # 🏷️ Nombre interno del blueprint
    __name__,
    url_prefix=""     # 🚪 Sin prefijo, login directo en /login
)

# =============================================================================
# 3️⃣ FUNCIÓN AUXILIAR · REGISTRAR INTENTOS DE LOGIN
# =============================================================================
def registrar_intento_login(idtbl_gestores, exito):
    """
    📝 Registra un intento de login en tbl_auditoria_intentos.

    Parámetros:
      - idtbl_gestores: id del gestor que intenta acceder (o None si aún
        no se conoce, por ejemplo cuando el usuario no existe).
      - exito: 1 si el login ha sido correcto, 0 si ha fallado.

    Campos que se guardan:
      - idtbl_gestores
      - endpoint      → request.endpoint (normalmente 'auth_bp.login')
      - metodo        → request.method (POST)
      - ip            → request.remote_addr
      - fecha         → NOW() en la BD
      - user_agent    → cabecera User-Agent
      - exito         → 1 / 0
    """
    conn = get_connection()
    if conn is None:
        # No rompemos el flujo de login por un fallo de auditoría.
        return

    try:
        cursor = conn.cursor()
        sql = """
            INSERT INTO tbl_auditoria_intentos (
                idtbl_gestores,
                endpoint,
                metodo,
                ip,
                fecha,
                user_agent,
                exito
            )
            VALUES (%s, %s, %s, %s, NOW(), %s, %s)
        """
        datos = [
            idtbl_gestores,
            request.endpoint,
            request.method,
            request.remote_addr or "",
            request.headers.get("User-Agent", ""),
            exito,
        ]
        cursor.execute(sql, datos)
        conn.commit()
    except Exception as e:
        current_app.logger.error("❌ Error auditando intento de login: %s", e)
    finally:
        cursor.close()
        conn.close()

# =============================================================================
# 4️⃣ RUTA /login · CONTROLADOR PRINCIPAL DE LOGIN
# =============================================================================
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    🎯 Controlador principal de login.

    FLUJO RESUMIDO:
      - GET:
          · Muestra el formulario de login.
      - POST:
          · Valida que vengan usuario y contraseña.
          · Busca el usuario en tbl_login (+ rol y estado activo).
          · Verifica contraseña con bcrypt.
          · Si algo falla → registra intento exito=0 y muestra error.
          · Si todo va bien:
              · Limpia y crea sesión segura.
              · Registra intento exito=1.
              · Redirige al panel correspondiente según rol.
    """
    preview_user = None
    error = None

    # 💡 Si quisieras reactivar el “auto-redirect” cuando ya hay sesión,
    # lo harías aquí, comprobando session["rol"] y llamando a _redirigir_por_rol.

    # -------------------------------------------------
    # 4.1️⃣ VALIDACIÓN DE FORMULARIO POST
    # -------------------------------------------------
    if request.method == "POST":
        identificador = request.form.get("login", "").strip()
        password_plana = request.form.get("password", "").strip()

        # 4.1.1️⃣ Campos obligatorios
        if not identificador or not password_plana:
            registrar_intento_login(None, 0)
            flash("Debes introducir usuario y contraseña.", "warning")
            return render_template("auth/login.html")

        # -------------------------------------------------
        # 4.2️⃣ CONEXIÓN A BASE DE DATOS
        # -------------------------------------------------
        conn = get_connection()
        if conn is None:
            registrar_intento_login(None, 0)
            error = "❌ Error de conexión con la base de datos."
            return render_template("auth/login.html", error=error)

        cursor = conn.cursor(dictionary=True)

        try:
            # -------------------------------------------------
            # 4.3️⃣ CONSULTA SQL · BÚSQUEDA DE LOGIN
            # -------------------------------------------------
            query = """
                SELECT
                    l.idtbl_login,
                    l.idtbl_gestores,
                    l.identificador,
                    l.email,
                    l.password_hash,
                    r.nombre AS rol_nombre,
                    g.activo AS gestor_activo
                FROM tbl_login l
                LEFT JOIN tbl_roles r ON l.idtbl_roles = r.idtbl_roles
                LEFT JOIN tbl_gestores g ON l.idtbl_gestores = g.idtbl_gestores
                WHERE l.identificador = %s
                LIMIT 1
            """
            cursor.execute(query, (identificador,))
            user = cursor.fetchone()

            # -------------------------------------------------
            # 4.4️⃣ VALIDACIÓN DE USUARIO
            # -------------------------------------------------
            if not user:
                registrar_intento_login(None, 0)
                error = "❌ Usuario no encontrado."
                return render_template("auth/login.html", error=error)

            if not user.get("gestor_activo"):
                registrar_intento_login(user.get("idtbl_gestores"), 0)
                error = "❌ Usuario desactivado."
                return render_template("auth/login.html", error=error)

            # -------------------------------------------------
            # 4.5️⃣ VERIFICACIÓN DE PASSWORD (BCRYPT)
            # -------------------------------------------------
            hash_bd = user.get("password_hash") or ""
            try:
                password_ok = bcrypt.checkpw(
                    password_plana.encode(),
                    hash_bd.encode(),
                )
            except Exception as e:
                current_app.logger.error("❌ bcrypt error: %s", e)
                password_ok = False

            if not password_ok:
                registrar_intento_login(user.get("idtbl_gestores"), 0)
                error = "❌ Contraseña incorrecta."
                return render_template("auth/login.html", error=error)

            # -------------------------------------------------
            # 4.6️⃣ CREACIÓN DE SESIÓN SEGURA
            # -------------------------------------------------
            session.clear()
            session["user_id"] = user.get("idtbl_login")
            session["idtbl_gestores"] = user.get("idtbl_gestores")
            session["rol"] = user.get("rol_nombre")

            current_app.logger.info(
                "✅ Login correcto: %s (%s)",
                identificador,
                user.get("rol_nombre"),
            )

            # 📌 Login OK → registramos intento exitoso
            registrar_intento_login(user.get("idtbl_gestores"), 1)

            # -------------------------------------------------
            # 4.7️⃣ REDIRECCIÓN POR ROL
            # -------------------------------------------------
            return _redirigir_por_rol(user.get("rol_nombre"))

        finally:
            cursor.close()
            conn.close()

    # -------------------------------------------------
    # 4.8️⃣ GET → Mostrar formulario
    # -------------------------------------------------
    return render_template("auth/login.html", preview_user=preview_user, error=error)

# =============================================================================
# 5️⃣ FUNCIÓN AUXILIAR: REDIRECCIÓN POR ROL
# =============================================================================
def _redirigir_por_rol(rol: str):
    """
    🔀 Redirige al panel correspondiente según el rol del usuario.

    ENDPOINTS POR ROL:
      - super_admin → super_admin_bp.super_admin
      - gestores    → panel_gestores_bp.panel_gestores
      - policias    → panel_policias_bp.panel_policias
      - vigilantes  → panel_vigilantes_bp.panel_vigilantes
      - usuarios    → panel_usuarios_bp.panel_usuarios
    """
    if rol == "super_admin":
        return redirect(url_for("super_admin_bp.super_admin"))

    if rol == "gestores":
        return redirect(url_for("panel_gestores_bp.panel_gestores"))

    if rol == "policias":
        return redirect(url_for("panel_policias_bp.panel_policias"))

    if rol == "vigilantes":
        return redirect(url_for("panel_vigilantes_bp.panel_vigilantes"))

    if rol == "usuarios":
        return redirect(url_for("panel_usuarios_bp.panel_usuarios"))

    flash(f"Rol no reconocido: {rol}", "danger")
    return redirect(url_for("auth_bp.login"))

# =============================================================================
# 6️⃣ LOGOUT
# =============================================================================
@auth_bp.route("/logout")
def logout():
    """
    🚪 Cierra sesión y registra auditoría de salida en tbl_auditorias_accesos.

    FLUJO:
      - Recupera idtbl_gestores desde la sesión.
      - Actualiza la última fila de tbl_auditorias_accesos para ese gestor
        con hora_salida y ip_salida.
      - Limpia la sesión y vuelve a /login.
    """
    id_gestor = session.get("idtbl_gestores")
    ip_cliente = request.environ.get("HTTP_X_FORWARDED_FOR", request.remote_addr)

    if id_gestor:
        conn = get_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute(
                    """
                    UPDATE tbl_auditorias_accesos
                    SET hora_salida = CURTIME(), ip_salida = %s
                    WHERE idtbl_gestores = %s
                    ORDER BY idtbl_auditorias DESC
                    LIMIT 1
                    """,
                    (ip_cliente, id_gestor),
                )
                conn.commit()
            finally:
                cursor.close()
                conn.close()

    session.clear()
    flash("Sesión cerrada correctamente.", "info")
    current_app.logger.info("👋 Logout completado desde IP %s", ip_cliente)
    return redirect(url_for("auth_bp.login"))

# =============================================================================
# 7️⃣ DEBUG ENDPOINTS
# =============================================================================
@auth_bp.route("/debug_endpoints")
def debug_endpoints():
    """
    🔍 Muestra todos los endpoints cargados en Flask.
    """
    items = [f"{rule.endpoint} → {rule}" for rule in current_app.url_map.iter_rules()]
    html = "<h2>🔍 Endpoints:</h2><ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"
    return html

# =============================================================================
# 8️⃣ RECUPERAR CONTRASEÑA
# =============================================================================
@auth_bp.route("/forgot_password", methods=["POST"])
def forgot_password():
    """
    📧 Simulación de recuperación de contraseña.
    """
    email = request.form.get("email_forgot", "").strip()
    current_app.logger.info("🔐 Recuperación solicitada para: %s", email)
    flash("Si el correo existe, recibirás instrucciones.", "info")
    return redirect(url_for("auth_bp.login"))


print(">>> Cargando auth_bp.py")