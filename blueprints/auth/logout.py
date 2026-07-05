# =====================================================
# 🚪 LOGOUT SIMPLE · REGISTRO EN AUDITORÍA
# =====================================================

@auth_bp.route("/logout")
def logout():
    """
    🚪 Cierra sesión del usuario y registra la salida en auditoría.

    Qué hace:
      1. Obtiene el id del gestor y la IP del cliente desde la sesión / request.
      2. Marca la hora de salida en la última fila de auditoría de ese gestor.
      3. Limpia la sesión.
      4. Muestra un mensaje de confirmación y vuelve al login.
    """
    from db import get_connection
    from flask import request

    id_gestor = session.get("idtbl_gestores")

    # 🛰 IP del cliente (directa o detrás de proxy)
    ip_cliente = request.environ.get("HTTP_X_FORWARDED_FOR", request.remote_addr)

    if id_gestor:
        conn = get_connection()
        if conn:
            cursor = conn.cursor(dictionary=True)
            try:
                # ⏱️ Marca la hora de salida en la última auditoría de este gestor
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

    # 🧽 Limpiar sesión y volver a login
    session.clear()
    flash("Sesión cerrada correctamente", "success")
    current_app.logger.info("👋 Logout completado desde IP %s", ip_cliente)
    return redirect(url_for("auth_bp.login"))
