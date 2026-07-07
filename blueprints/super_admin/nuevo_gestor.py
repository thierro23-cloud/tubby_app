# blueprints/super_admin/nuevo_gestor_bd.py              # 🗂️ Archivo del blueprint para dar de alta gestores
# =====================================================
# ➕ NUEVO GESTOR – ALTA EN tbl_gestores               # 🧾 Módulo específico para inserción en tbl_gestores
# =====================================================

from flask import (  # 📦 Importamos funciones de Flask
    Blueprint,  # 🧱 Crear blueprints (módulos de rutas)
    render_template,  # 🎨 Renderizar plantillas HTML
    request,  # 📥 Acceder a datos de formularios (GET/POST)
    redirect,  # 🔀 Redirigir a otra ruta
    url_for,  # 🔗 Construir URLs a partir de endpoints
    flash,  # 💬 Enviar mensajes flash al usuario
    current_app,  # 📝 Acceder al logger de la aplicación
)
from db import (
    ejecutar_query,
    ejecutar_non_query,
)  # 🔌 Funciones propias para consultar/ejecutar SQL
import bcrypt  # 🔐 Librería para cifrar contraseñas con hash

# =====================================================
# 🧱 DEFINICIÓN DEL BLUEPRINT
# =====================================================
nuevo_gestor_bp = Blueprint(  # 🧱 Creamos un nuevo blueprint
    "nuevo_gestor_bp",  # 📛 Nombre interno (para url_for, logs, etc.)
    __name__,  # 🏠 Módulo actual como origen
    url_prefix="/super_admin",  # 🌐 Prefijo: todas las rutas empezarán por /super_admin
)


# =====================================================
# ➕ RUTA: NUEVO GESTOR (GET/POST)
# =====================================================
@nuevo_gestor_bp.route(
    "/nuevo_gestor", methods=["GET", "POST"]
)  # 🔗 Ruta /super_admin/nuevo_gestor
def nuevo_gestor():
    """
    ➕ Formulario de alta de gestor:
    - GET  → muestra formulario con desplegables (provincias, roles, etc.).
    - POST → recoge datos, cifra password y hace INSERT en tbl_gestores.
    """  # 📘 Docstring: explica qué hace la vista

    # -------------------------------------------------
    # 1️⃣ CARGA DE DATOS PARA DESPLEGABLES (GET y POST)
    # -------------------------------------------------
    provincias = ejecutar_query(  # 🌍 Cargamos provincias para el <select>
        "SELECT idtbl_provincias, nombre FROM tbl_provincias ORDER BY nombre"
    )

    tipos_via = ejecutar_query(  # 🛣️ Cargamos tipos de vía para otro <select>
        "SELECT idtbl_tipos_de_vias, nombre FROM tbl_tipos_de_vias ORDER BY nombre"
    )

    roles = ejecutar_query(  # 🎭 Cargamos roles desde tbl_roles
        "SELECT idtbl_roles, roles FROM tbl_roles ORDER BY roles"
    )  # 🎭 Usamos la columna 'roles' como texto del desplegable

    municipios = []  # 🏘️ Lista vacía de municipios (se puede rellenar según provincia)
    calles = []  # 🚏 Lista vacía de calles     (según municipio)

    # -------------------------------------------------
    # 2️⃣ SI ES MÉTODO POST → PROCESAR FORMULARIO
    # -------------------------------------------------
    if (
        request.method == "POST"
    ):  # 📥 Solo entra aquí si el usuario ha enviado el formulario
        # 2.1️⃣ Recoger campos del formulario
        nombre = request.form.get("nombre", "").strip()  # 👤 Nombre
        apellido1 = request.form.get("apellido1", "").strip()  # 👤 Primer apellido
        apellido2 = request.form.get("apellido2", "").strip()  # 👤 Segundo apellido
        email = request.form.get("email", "").strip()  # ✉ Correo electrónico
        password_plana = request.form.get(
            "password", ""
        ).strip()  # 🔑 Contraseña en claro (solo mientras se procesa)

        idtbl_tipos_de_vias = request.form.get(
            "idtbl_tipos_de_vias"
        )  # 🛣️ FK tipo de vía (puede ser None)
        idtbl_provincias = request.form.get("idtbl_provincias")  # 🌍 FK provincia
        idtbl_municipios = request.form.get("idtbl_municipios")  # 🏘️ FK municipio
        idtbl_calles = request.form.get("idtbl_calles")  # 🚏 FK calle

        dni = request.form.get("DNI", "").strip()  # 🪪 DNI del gestor
        telefono = request.form.get("telefono", "").strip()  # 📞 Teléfono
        extension = (
            request.form.get("extension", "").strip() or None
        )  # ☎ Extensión (None si viene vacío)

        # ✅ Campo 'activo' puede llegar como "on" (checkbox) o como "1"
        activo_raw = request.form.get("activo")  # 📥 Valor crudo del checkbox
        activo = (
            1 if activo_raw in ("on", "1") else 0
        )  # ✅ Normalizamos a 1 (activo) o 0 (inactivo)

        idtbl_roles = request.form.get(
            "idtbl_roles"
        )  # 🎭 Rol seleccionado en el desplegable
        numero_profesional = request.form.get(
            "numero_profesional", ""
        ).strip()  # 🧾 Nº profesional colegiado

        # 🔐 must_change (si debe cambiar la contraseña al primer login)
        must_change_str = request.form.get(
            "must_change", "1"
        )  # 📥 Valor como texto ("1" o "0"), por defecto "1"
        try:
            must_change = int(must_change_str)  # 🔢 Convertimos a entero
        except ValueError:
            must_change = 1  # 🔒 Si algo raro llega, forzamos que deba cambiarla

        # -------------------------------------------------
        # 3️⃣ VALIDACIÓN BÁSICA DE CAMPOS OBLIGATORIOS
        # -------------------------------------------------
        if not nombre or not email or not password_plana:  # ❗ Comprobamos mínimos
            flash(
                "Nombre, email y contraseña son obligatorios.", "danger"
            )  # 💬 Aviso al usuario
            return render_template(  # 🔁 Volvemos a mostrar el formulario
                "super_admin/nuevo_gestor.html",  # 🧩 Plantilla del formulario
                provincias=provincias,  # 🌍 Datos provincias
                tipos_via=tipos_via,  # 🛣️ Datos tipos de vía
                municipios=municipios,  # 🏘️ Municipios (por ahora vacíos)
                calles=calles,  # 🚏 Calles (por ahora vacías)
                roles=roles,  # 🎭 Lista de roles
            )

        # -------------------------------------------------
        # 4️⃣ CIFRAR LA CONTRASEÑA CON BCRYPT
        # -------------------------------------------------
        password_hash = bcrypt.hashpw(  # 🔐 Generamos hash seguro
            password_plana.encode("utf-8"),  # 🔡 Convertimos la contraseña a bytes
            bcrypt.gensalt(),  # 🧂 Salt aleatorio por usuario
        ).decode(
            "utf-8"
        )  # 🔁 Guardamos el hash como texto en la BD

        # -------------------------------------------------
        # 5️⃣ PREPARAR Y EJECUTAR EL INSERT EN tbl_gestores
        # -------------------------------------------------
        sql = """
            INSERT INTO tbl_gestores (
                nombre,
                apellido1,
                apellido2,
                email,
                password,
                idtbl_tipos_de_vias,
                idtbl_calles,
                idtbl_provincias,
                idtbl_municipios,
                DNI,
                telefono,
                extension,
                activo,
                idtbl_roles,
                numero_profesional,
                must_change
            )
            VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            )
        """  # 🧾 Sentencia SQL parametrizada para insertar un nuevo gestor

        params = (  # 📦 Tupla de parámetros en el mismo orden que el SQL
            nombre,  # 👤 nombre
            apellido1,  # 👤 primer apellido
            apellido2,  # 👤 segundo apellido
            email,  # ✉ email
            password_hash,  # 🔐 hash de la contraseña
            idtbl_tipos_de_vias,  # 🛣️ FK tipo de vía
            idtbl_calles,  # 🚏 FK calle
            idtbl_provincias,  # 🌍 FK provincia
            idtbl_municipios,  # 🏘️ FK municipio
            dni,  # 🪪 DNI
            telefono,  # 📞 teléfono
            extension,  # ☎ extensión (puede ser None)
            activo,  # ✅ 1/0 estado activo
            idtbl_roles,  # 🎭 rol seleccionado
            numero_profesional,  # 🧾 número profesional
            must_change,  # 🔐 debe cambiar contraseña en el primer login
        )

        try:
            filas = ejecutar_non_query(sql, params)  # 🚀 Ejecutamos el INSERT en la BD
            current_app.logger.info(  # 📝 Escribimos en el log de la app
                "✅ Insertado nuevo gestor: %s (%s filas)", email, filas
            )
            flash(
                "Gestor creado correctamente.", "success"
            )  # 💬 Mensaje de éxito a la interfaz
            return redirect(url_for("super_admin_bp.super_admin"))
            # 🔀 Redirigimos al panel principal de super_admin

        except Exception as e:  # ❌ Cualquier error en el INSERT
            current_app.logger.exception("❌ Error creando gestor: %s", e)
            # 📝 Log completo del error con traza
            flash(
                f"Error creando gestor: {e}", "danger"
            )  # 💬 Mostramos error al usuario
            # 👇 Continuamos para volver a pintar el formulario con los desplegables cargados

    # -------------------------------------------------
    # 6️⃣ GET INICIAL O POST CON ERROR → MOSTRAR FORMULARIO
    # -------------------------------------------------
    return render_template(
        "super_admin/nuevo_gestor.html",  # 🧩 Plantilla del formulario de alta de gestor
        provincias=provincias,  # 🌍 Provincias para el desplegable
        tipos_via=tipos_via,  # 🛣️ Tipos de vía
        municipios=municipios,  # 🏘️ Municipios (de momento lista vacía)
        calles=calles,  # 🚏 Calles (lista vacía)
        roles=roles,  # 🎭 Lista de roles (usa columna 'roles')
    )
