from core.auth.repository import get_user_by_email
from core.auth.utils import verify_password
from flask import session


def login_user(email, password):

    user = get_user_by_email(email)

    if not user:
        return False, "Usuario no existe"

    if not verify_password(password, user["password_hash"]):
        return False, "Contraseña incorrecta"

    # 🔐 Guardar sesión
    session["user_id"] = user["idtbl_login"]
    session["rol_id"] = user["idtbl_roles"]
    session["email"] = user["email"]

    return True, "Login correcto"
