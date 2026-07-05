# =============================================================================
# 🚀 SUPER ADMIN · BACKEND AUDITORÍA EN TIEMPO REAL
# =============================================================================
#
# 🎯 OBJETIVO:
# Sistema de logs profesional con streaming en tiempo real (SSE)
#
# ✔ Captura:
#    - Accesos (endpoints visitados)
#    - Errores (exceptions reales)
#    - Alertas (eventos personalizados)
#
# ✔ Emite:
#    - Eventos en tiempo real al frontend
#
# ✔ Arquitectura:
#    - Buffer en memoria (rápido)
#    - Cola de eventos
#    - Streaming continuo
#
# =============================================================================

from flask import Flask, Response, request, jsonify
import json
import time
import threading
from collections import deque
from datetime import datetime

app = Flask(__name__)

# =============================================================================
# 🧠 SECCIÓN 1 · CONFIGURACIÓN GLOBAL
# =============================================================================

# Buffer circular (máx 100 eventos por tipo)
logs = {
    "accesos": deque(maxlen=100),
    "errores": deque(maxlen=100),
    "alertas": deque(maxlen=100)
}

# Cola global para streaming
event_queue = deque()

# Lock para evitar conflictos en concurrencia
lock = threading.Lock()

# =============================================================================
# 🧾 SECCIÓN 2 · UTILIDAD PARA CREAR LOGS
# =============================================================================
def crear_log(tipo, mensaje):
    """
    📌 Crea un log estructurado y lo envía a:
    - Buffer histórico
    - Cola de streaming en tiempo real
    """

    log = {
        "tipo": tipo,
        "msg": mensaje,
        "time": datetime.now().strftime("%H:%M:%S")
    }

    with lock:
        logs[tipo].appendleft(log)
        event_queue.append(log)

# =============================================================================
# 🌐 SECCIÓN 3 · CAPTURA AUTOMÁTICA DE ACCESOS
# =============================================================================
@app.before_request
def registrar_acceso():
    """
    📌 Se ejecuta ANTES de cada request
    → Registra todos los accesos reales
    """

    # Evitamos registrar el propio stream para no saturar
    if request.path.startswith("/super_admin/auditoria_stream"):
        return

    crear_log(
        "accesos",
        f"{request.remote_addr} → {request.method} {request.path}"
    )

# =============================================================================
# ❌ SECCIÓN 4 · CAPTURA GLOBAL DE ERRORES
# =============================================================================
@app.errorhandler(Exception)
def manejar_error(e):
    """
    📌 Captura cualquier error no controlado
    """

    crear_log("errores", str(e))

    return jsonify({"error": "Error interno"}), 500

# =============================================================================
# 🔥 SECCIÓN 5 · STREAM EN TIEMPO REAL (SSE)
# =============================================================================
@app.route("/super_admin/auditoria_stream")
def auditoria_stream():
    """
    📌 Endpoint SSE:
    → Mantiene conexión abierta
    → Envía eventos en tiempo real
    """

    def stream():
        while True:

            if event_queue:
                with lock:
                    evento = event_queue.popleft()

                yield f"data: {json.dumps(evento)}\n\n"

            time.sleep(0.5)  # evita consumo excesivo CPU

    return Response(stream(), mimetype="text/event-stream")

# =============================================================================
# 🧪 SECCIÓN 6 · ENDPOINT DE PRUEBA (ALERTAS)
# =============================================================================
@app.route("/test-alerta")
def test_alerta():
    """
    📌 Simula una alerta manual
    """
    crear_log("alertas", "⚠️ Evento crítico detectado")
    return "OK"

# =============================================================================
# 🔐 SECCIÓN 7 · TOGGLE PERMISOS (INTEGRACIÓN FRONT)
# =============================================================================
@app.route("/super_admin/toggle-permiso", methods=["POST"])
def toggle_permiso():
    data = request.json

    crear_log(
        "alertas",
        f"Permiso cambiado → user:{data['user']} endpoint:{data['endpoint']}"
    )

    return jsonify({"ok": True})

# =============================================================================
# 🏁 SECCIÓN 8 · INICIO DEL SERVIDOR
# =============================================================================
if __name__ == "__main__":
    """
    📌 INICIO REAL DEL SISTEMA
    👉 Aquí arranca Flask
    👉 Empieza a escuchar peticiones
    👉 Activa auditoría automáticamente
    """

    app.run(debug=True, threaded=True)Ç