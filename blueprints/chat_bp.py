"""
Blueprint de chat asistido por LLM para super_admin.

Este módulo expone:

    - Vista HTML:
        GET  /super_admin/chat_llm

    - API AJAX:
        POST /super_admin/api/chat_llm

Ambas rutas están:
    - Protegidas por login (Flask-Login).
    - Restringidas a usuarios con rol 'super_admin' (según session["rol"]).
    - Integradas con un modelo local servido por Ollama (gemma3:4b, por defecto).

Uso principal:
    - Asistir al super_admin en la redacción y revisión de textos
      jurídico‑administrativos para el ayuntamiento.

Requisitos de configuración en app.py:

    app.config["LLM_BACKEND"] = "ollama"
    app.config["LLM_MODEL"] = "gemma3:4b"
    # app.config["LLM_API_BASE"] = "http://localhost:11434"  # opcional
    # app.config["LLM_TIMEOUT"] = 30  # opcional, en segundos

Documentación API Ollama:
    - https://docs.ollama.com/api [web:104][web:106]
"""

from __future__ import annotations

from typing import Dict, Any

from flask import Blueprint, render_template, request, session, current_app, jsonify
import requests
import json


# =============================================================================
# 1️⃣ DEFINICIÓN DEL BLUEPRINT
# =============================================================================

chat_bp = Blueprint(
    "chat_bp",
    __name__,
    url_prefix="/super_admin",
)


# =============================================================================
# 2️⃣ HELPERS INTERNOS · PERMISOS Y LLAMADA A OLLAMA
# =============================================================================

def _es_super_admin() -> bool:
    """
    Helper de autorización rápida para este módulo.

    Devuelve:
        True  -> si el usuario actual tiene rol 'super_admin' en session.
        False -> en cualquier otro caso (no logueado / otro rol / sin clave).
    """
    return session.get("rol") == "super_admin"


def _llamar_ollama(prompt: str) -> str:
    """
    Llama al modelo local configurado en Ollama y devuelve la respuesta en texto plano.

    Esta función:

        - Lee de current_app.config:
            · LLM_BACKEND: debe ser "ollama".
            · LLM_MODEL  : nombre del modelo (p.ej. "gemma3:4b").
            · LLM_API_BASE: URL base de Ollama (opcional, por defecto http://localhost:11434).
            · LLM_TIMEOUT : timeout de la petición en segundos (opcional, por defecto 30).

        - Realiza una petición POST a /api/generate de Ollama.
        - Extrae el campo "response" o "output" del JSON devuelto.
        - Lanza excepciones en caso de error. El caller las captura.

    Parámetros:
        prompt (str): Prompt completo a enviar al modelo (instrucciones + mensaje).

    Devuelve:
        str: Texto de la respuesta generada por el modelo (puede ser cadena vacía).

    Referencia API:
        https://docs.ollama.com/api [web:104][web:106][web:111]
    """
    backend = current_app.config.get("LLM_BACKEND", "ollama")
    if backend != "ollama":
        raise RuntimeError(f"LLM_BACKEND={backend!r} no es compatible con _llamar_ollama")

    model = current_app.config.get("LLM_MODEL")
    if not model:
        raise RuntimeError("LLM_MODEL no está configurado en app.config")

    api_base = current_app.config.get("LLM_API_BASE", "http://localhost:11434")
    timeout = current_app.config.get("LLM_TIMEOUT", 30)

    url = f"{api_base.rstrip('/')}/api/generate"
    current_app.logger.debug(
        "[CHAT_LLM_SUPER_ADMIN] Llamando a Ollama: url=%s, model=%s, timeout=%s",
        url,
        model,
        timeout,
    )

    resp = requests.post(
        url,
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
        },
        timeout=timeout,
    )
    resp.raise_for_status()

    data_resp: Dict[str, Any] = resp.json()
    reply = (data_resp.get("response") or data_resp.get("output") or "").strip()

    current_app.logger.debug(
        "[CHAT_LLM_SUPER_ADMIN] Respuesta de Ollama recibida (longitud=%d caracteres)",
        len(reply),
    )

    return reply


# =============================================================================
# 3️⃣ VISTA HTML DEL CHAT
# =============================================================================

@chat_bp.route("/chat_llm", methods=["GET"])

def chat_llm_view():
    """
    Vista HTML del chat de asistencia jurídico‑administrativa para super_admin.

    Comportamiento:
        - Requiere usuario autenticado (login_required).
        - Verifica que session["rol"] == "super_admin".
        - Renderiza la plantilla super_admin/chat_llm.html.

    Respuestas:
        200 -> HTML del chat.
        403 -> si el usuario no es super_admin.
    """
    if not _es_super_admin():
        current_app.logger.warning(
            "[CHAT_LLM_SUPER_ADMIN] Acceso denegado a /chat_llm para rol=%r",
            session.get("rol"),
        )
        return "⛔ Acceso restringido a super_admin", 403

    return render_template("super_admin/chat_llm.html")


# =============================================================================
# 4️⃣ API AJAX · CHAT JURÍDICO‑ADMINISTRATIVO
# =============================================================================

@chat_bp.route("/api/chat_llm", methods=["POST"])

def api_chat_llm():
    """
    Endpoint AJAX para el chatbot jurídico‑administrativo.

    Uso típico desde JavaScript (fetch):
        POST /super_admin/api/chat_llm
        Content-Type: application/json
        Body: {"message": "texto o petición a redactar/mejorar"}

    Entrada JSON:
        - message (str): Texto de la consulta del usuario.
                         Puede ser una petición ("redáctame...") o un borrador
                         para mejorar.

    Salida JSON:
        - reply (str)  : Respuesta generada por el modelo local.
        - error (str)  : En caso de error, descripción amigable.

    Reglas de seguridad:
        - Requiere login (login_required).
        - Solo rol super_admin (session["rol"] == "super_admin").

    Códigos de estado:
        200 -> OK, se devuelve {"reply": "..."}.
        400 -> Petición mal formada (mensaje vacío, etc.).
        403 -> Acceso prohibido (no super_admin).
        500 -> Error interno (problemas al llamar al modelo).
    """
    # 1️⃣ Verificar rol super_admin
    if not _es_super_admin():
        current_app.logger.warning(
            "[CHAT_LLM_SUPER_ADMIN] Acceso API denegado a /api/chat_llm para rol=%r",
            session.get("rol"),
        )
        return jsonify({"error": "Acceso restringido a super_admin"}), 403

    # 2️⃣ Leer y validar el payload de entrada
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()

    if not message:
        return jsonify({"error": "Mensaje vacío"}), 400

    # (Opcional) Control de longitud máxima para evitar prompts excesivos
    max_chars = current_app.config.get("CHAT_LLM_MAX_INPUT_CHARS", 4000)
    if len(message) > max_chars:
        return jsonify(
            {
                "error": f"El mensaje es demasiado largo (máx. {max_chars} caracteres).",
            }
        ), 400

    current_app.logger.info(
        "[CHAT_LLM_SUPER_ADMIN] Petición de chat recibida (longitud=%d caracteres)",
        len(message),
    )

    # 3️⃣ Construir prompt orientado a textos jurídico‑administrativos
    system_prompt = (
        "Eres un asistente especializado en redacción de textos jurídico‑administrativos "
        "para un ayuntamiento de España. Redacta borradores claros, formales y "
        "jurídicamente prudentes, pero recuerda que el usuario es quien tomará "
        "las decisiones finales. No inventes hechos ni datos personales.\n"
        "Si el usuario pide algo que no sea estrictamente jurídico‑administrativo, "
        "adáptate, pero mantén un tono profesional y administrativo.\n"
    )

    user_prompt = (
        "Redacta o mejora el siguiente texto jurídico‑administrativo, usando estilo de "
        "administración local española, con referencias generales pero sin citar artículos "
        "concretos salvo que sea realmente necesario:\n\n"
        f"{message}\n"
    )

    prompt_completo = system_prompt + "\n" + user_prompt

    # 4️⃣ Llamar a Ollama y devolver la respuesta
    try:
        reply = _llamar_ollama(prompt_completo)

        if not reply:
            # Caso raro pero posible: el modelo responde vacío
            current_app.logger.warning(
                "[CHAT_LLM_SUPER_ADMIN] Respuesta vacía de Ollama para prompt de longitud=%d",
                len(prompt_completo),
            )
            return jsonify(
                {"error": "El modelo no ha devuelto respuesta. Inténtalo de nuevo."}
            ), 500

        return jsonify({"reply": reply})

    except requests.Timeout:
        current_app.logger.error(
            "[CHAT_LLM_SUPER_ADMIN] Timeout al llamar a Ollama",
            exc_info=True,
        )
        return jsonify({"error": "Timeout al comunicarse con el modelo local."}), 500

    except requests.RequestException as e:
        current_app.logger.error(
            f"[CHAT_LLM_SUPER_ADMIN] Error de red al llamar a Ollama: {e!r}",
            exc_info=True,
        )
        return jsonify({"error": "Error de comunicación con el modelo local."}), 500

    except Exception as e:
        current_app.logger.error(
            f"[CHAT_LLM_SUPER_ADMIN] Error inesperado llamando a Ollama: {e!r}",
            exc_info=True,
        )
        return jsonify({"error": "Error interno al generar respuesta."}), 500