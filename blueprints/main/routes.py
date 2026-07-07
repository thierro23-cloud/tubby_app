# Importamos las herramientas básicas de Flask
# - Blueprint: para agrupar rutas en un módulo
# - render_template: para mostrar plantillas HTML
# - session: para guardar datos del usuario mientras navega
# - redirect y url_for: para mover al usuario de una ruta a otra
from flask import (
    Blueprint,
    render_template,
    session,
    redirect,
    url_for,
)  # [web:15][web:25]

# Importamos login_required, que es un “candado” para rutas
# Solo deja pasar a usuarios que estén logueados
from flask_login import login_required  # [web:19][web:21]

# Creamos un blueprint llamado "main".
# Piensa en el blueprint como una “carpeta lógica” con las rutas principales de la app.
# El nombre "main" es el que luego usamos en url_for("main.algo").
main = Blueprint("main", __name__)  # [web:15][web:25][web:30]


# ---------------------------------------------------------
# 🚪 RUTA DE INICIO: "/"
# ---------------------------------------------------------
# Esta función se ejecuta cuando el usuario visita la URL raíz de este módulo: "/".
# Decide si debe mostrar la página de introducción o mandar al usuario al "home".
@main.route("/")
def intro():
    """
    Esta vista es la PUERTA DE ENTRADA de la app.

    - Mira en la sesión si el usuario ya vio la introducción.
    - Si ya la vio, lo manda directamente a la página principal (/home).
    - Si no la vio todavía, le enseña la plantilla intro.html.
    """

    # session es como una mochila de datos ligada al navegador del usuario.
    # Aquí preguntamos: ¿en la mochila hay una clave llamada "intro_visto"?
    # session.get("intro_visto") devolverá:
    #   - True (o un valor “truthy”) si ya guardamos esa clave.
    #   - None (o False) si nunca la guardamos.
    if session.get("intro_visto"):  # [web:31]
        # Si la clave existe y es verdadera, significa que el usuario ya vio la intro.
        # Entonces NO le volvemos a enseñar la intro; lo enviamos al "home".
        #
        # url_for("main.home") construye la URL de la función home()
        # dentro del blueprint "main". Esto normalmente será "/home".
        return redirect(url_for("main.home"))  # [web:25][web:26]

    # Si no tenemos intro_visto en la sesión,
    # mostramos la plantilla "intro.html".
    # Esta será tu página de bienvenida, explicación inicial, etc.
    return render_template("intro.html")  # [web:15]


# ---------------------------------------------------------
# 🏠 RUTA PRINCIPAL PROTEGIDA: "/home"
# ---------------------------------------------------------
# Esta función muestra la página principal (home, dashboard, etc.).
@main.route("/home")
@login_required
def home():
    """
    Esta vista es la PÁGINA PRINCIPAL de la app.

    - Solo pueden entrar usuarios que estén logueados.
    - Si el usuario NO está logueado, login_required lo enviará a la página de login.
    - Si está logueado, se renderiza home.html.
    """

    # El decorador @login_required (justo encima de la función)
    # es un "guardia de seguridad":
    #   - Primero comprueba si hay un usuario autenticado.
    #   - Si NO lo hay, redirige al login (según tu configuración de Flask-Login).
    #   - Si SÍ lo hay, permite que se ejecute esta función home() normalmente. [web:19][web:21]

    # Si el usuario pasó el filtro de login_required,
    # simplemente dibujamos la plantilla "home.html".
    # Aquí suele ir tu panel, menús, etc.
    return render_template("home.html")  # [web:15]
