# blueprints/usuarios/usuarios_bp.py
# =====================================================
# 🚗 PANEL USUARIOS BLUEPRINT
# =====================================================
# - /usuarios/panel_usuarios → panel principal de usuarios finales
#   Permisos:
#     • Ver solo SUS plazas de aparcamiento.
#     • Ver un plano del parquin con solo sus plazas resaltadas.
#   Sin posibilidad de ver otras plazas ni modificar nada.
# =====================================================

from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    url_for,
    flash,
)

usuarios_bp = Blueprint(
    "usuarios_bp",  # 🔑 url_for('usuarios_bp.panel_usuarios')
    __name__,
    url_prefix="/usuarios",  # 🌐 todas las rutas cuelgan de /usuarios
)


# =====================================================
# 🔐 HELPER: SOLO ROL "usuarios"
# =====================================================
def _requiere_usuario():
    """
    🔒 Permite acceso solo a usuarios con rol 'usuarios'.
    """
    if not session.get("user_id"):
        flash("Primero tienes que hacer login.", "danger")
        return redirect(url_for("auth_bp.login"))

    if session.get("rol") != "usuarios":
        flash("Acceso solo para usuarios del parquin.", "danger")
        return redirect(url_for("auth_bp.login"))

    return None


# =====================================================
# 🚗 PANEL PRINCIPAL DE USUARIOS
# =====================================================
@usuarios_bp.route("/panel", methods=["GET"])
def panel_usuarios():
    """
    🚗 Panel principal del rol USUARIOS.
    - Muestra:
      • Resumen de sus plazas (texto/tablas).
      • Acceso al plano filtrado a sus plazas.
    - De momento solo renderizamos el panel estático.
    """
    redir = _requiere_usuario()
    if redir:
        return redir

    # 🔜 Más adelante aquí puedes cargar las plazas reales del usuario
    # desde la BD en función de session["user_id"] o su id de empresa.
    return render_template("usuarios/panel_usuarios.html")
