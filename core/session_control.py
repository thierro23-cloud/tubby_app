# =============================================================================
# 🔐 CONTROL DE SESIONES (ANTI DOBLE LOGIN + TIMEOUT)
# =============================================================================

from datetime import datetime, timedelta
from flask import session
from core.auditoria.auditoria import registrar_salida


SESSION_TIMEOUT = 30  # minutos


def controlar_sesion():

    ahora = datetime.now()

    ultima = session.get("ultima_actividad")

    if ultima:
        ultima = datetime.strptime(ultima, "%Y-%m-%d %H:%M:%S")

        # 🔴 Timeout
        if ahora - ultima > timedelta(minutes=SESSION_TIMEOUT):
            registrar_salida("TIMEOUT")
            session.clear()
            return False

    # Actualizar actividad
    session["ultima_actividad"] = ahora.strftime("%Y-%m-%d %H:%M:%S")

    return True