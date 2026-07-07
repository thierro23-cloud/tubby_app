# =====================================================
# 🔹 BLUEPRINT DE AUTENTICACIÓN – MODO MÁGICO
# =====================================================
# 📦 Este es nuestro cajoncito mágico donde guardamos rutas de login, registro
# y recuperación de contraseñas.

from flask import Blueprint, request, flash, redirect, url_for, jsonify
from db import execute
from werkzeug.security import (
    generate_password_hash,
)  # 🗝️ Para hacer magia con contraseñas

# 🗂 Creamos el cajoncito mágico llamado auth_bp
auth_bp = Blueprint("auth_bp", __name__, template_folder="templates/auth")


# =====================================================
# 🔐 RECUPERAR CONTRASEÑA – EXPLICADO PARA NIÑOS
# =====================================================
@auth_bp.route("/recuperar_password", methods=["POST"])
def recuperar_password():
    """
    👶 Explicación tipo cuento:
    1️⃣ El niño escribe su correo o número mágico en el formulario.
    2️⃣ La aplicación genera una contraseña temporal secreta.
    3️⃣ Guardamos esta contraseña en la base de datos, pero de forma mágica (hasheada)
       para que nadie pueda verla.
    4️⃣ Luego enviamos un mensaje al correo del administrador con la contraseña temporal.
       (Por ahora solo devolvemos JSON para ver que funciona)
    """

    # 🧙‍♂️ Recogemos el email o número mágico del formulario
    login_id = request.form.get("login_id")  # puede ser email o número profesional

    # 👑 Siempre enviamos la nueva contraseña al correo del admin
    admin_email = "fhierro@ayuntavila.com"

    # ✨ Creamos una contraseña temporal (luego puede ser aleatoria)
    temp_password = "Temp1234!"
    # 🔐 Convertimos la contraseña en un hechizo secreto (hash) para guardarla segura
    hashed_password = generate_password_hash(temp_password)

    # 🏰 Actualizamos la contraseña en la base de datos
    query = """
        UPDATE tbl_gestores
        SET password=%s, must_change=1
        WHERE email=%s OR numero_profesional=%s
    """
    execute("bd_tbl_comunes", query, (hashed_password, login_id, login_id))

    # 📬 Aquí podríamos enviar un correo al admin con temp_password
    # Por ahora, devolvemos un mensaje mágico en JSON para pruebas
    return jsonify(
        {
            "status": "OK",  # ✅ Todo salió bien
            "mensaje": f"Contraseña temporal enviada a {admin_email}",  # 💌 Mensaje tipo cómic
            "temp_password": temp_password,  # 🔑 Para ver que funciona en pruebas
        }
    )
