# =============================================================================
# 🅿️  btn_rio_torio_plazas_bp · GESTIÓN DE PLAZAS DE CAMIONES (ZONA RÍO/TORIO)
# =============================================================================
"""
OBJETIVO GENERAL
----------------
Este blueprint se encarga de gestionar las plazas de parking para camiones,
usando la tabla `tbl_plazas` y respetando las relaciones:

- `tbl_plazas.idtbl_usuarios`        → `tbl_usuarios.idtbl_usuarios`
- `tbl_usuarios.idtbl_proveedores`   → `tbl_proveedores.idtbl_proveedores`

Además:
- Solo carga usuarios cuyo proveedor tiene parquin activo (`tbl_proveedores.parquin = 1`).
- Expone:
  - un listado de plazas,
  - un formulario de alta,
  - un formulario de edición.
- Todas las rutas están protegidas con `login_required`.

TABLAS IMPLICADAS (mínimo)
--------------------------
- parquin_camiones.tbl_plazas
    · idtbl_plazas (PK)
    · codigo_plazas
    · observaciones
    · fila
    · numero_expediente
    · idtbl_usuarios
    · fecha_inicio
    · fecha_fin
    · exp_solicitud
    · exp_solicitud_fin
    · idtbl_inventario

- parquin_camiones.tbl_usuarios
    · idtbl_usuarios (PK)
    · idtbl_proveedores (FK → tbl_proveedores)
    · numero_cuenta
    · activo_baja
    · fecha_inicio
    · fecha_baja
    · rol

- parquin_camiones.tbl_proveedores
    · idtbl_proveedores (PK)
    · Nombre_Razon_Social
    · parquin  (tinyint / boolean: 1 = tiene parquin)

- parquin_camiones.tbl_inventario (pendiente de definir)
    · idtbl_inventario (PK)
    · descripcion
"""

# =============================================================================
# 1️⃣ IMPORTS Y CONFIGURACIÓN DEL BLUEPRINT
# =============================================================================

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)
from flask_login import login_required, current_user

from db import ejecutar_query, ejecutar_non_query

# 1.1️⃣ DEFINICIÓN DEL BLUEPRINT
# ------------------------------
# - variable: btn_rio_torio_plazas_bp
# - nombre interno (endpoint): "rio_torio_plazas_bp"
# - url_prefix: todas las rutas empiezan por /parquin/rio_torio_plazas
# - template_folder: carpeta donde estarán las plantillas HTML
btn_rio_torio_plazas_bp = Blueprint(
    "rio_torio_plazas_bp",
    __name__,
    url_prefix="/parquin/rio_torio_plazas",
    template_folder="../../templates/parquin",
)


# =============================================================================
# 1.2️⃣ FUNCIÓN DE PERMISOS PARA SUPER ADMIN
# =============================================================================


def es_super_admin():
    """
    Devuelve True si el usuario actual es super admin.
    Ajusta los valores según cómo guardes el rol en tu tabla tbl_usuarios.
    """
    rol = getattr(current_user, "rol", None)
    if rol is None:
        return False
    rol_normalizado = str(rol).upper().replace(" ", "_")
    return rol_normalizado in ("SUPER_ADMIN", "SUPERADMIN", "SUPER_ADMIN_USER")


# =============================================================================
# 2️⃣ LISTADO PRINCIPAL DE PLAZAS (RÍO/TORIO)
# =============================================================================


@btn_rio_torio_plazas_bp.route("/", methods=["GET"])
@login_required
def lista_plazas_rio_torio():
    """
    2.1️⃣ LISTA DE PLAZAS

    Muestra el listado de plazas de camiones usando `tbl_plazas`, e incluye
    información del usuario y del proveedor asociado (si existen).

    NOTA:
    - De momento no filtramos por "zona" (RÍO/TORIO) porque no se ha definido
      aún una columna específica para ello (p.ej. `zona` o `tipo_plaza`).
    - Cuando exista esa columna, bastará con añadir:
          WHERE p.zona = 'RIO_TORIO'
      en el SQL.
    """

    sql = """
        SELECT
            p.idtbl_plazas,
            p.codigo_plazas,
            p.observaciones,
            p.fila,
            p.numero_expediente,
            p.idtbl_usuarios,
            p.fecha_inicio,
            p.fecha_fin,
            p.exp_solicitud,
            p.exp_solicitud_fin,
            p.idtbl_inventario,
            u.idtbl_proveedores,
            u.numero_cuenta,
            u.activo_baja,
            u.rol,
            pr.Nombre_Razon_Social AS proveedor_nombre
        FROM tbl_plazas AS p
        LEFT JOIN tbl_usuarios AS u
               ON p.idtbl_usuarios = u.idtbl_usuarios
        LEFT JOIN tbl_proveedores AS pr
               ON u.idtbl_proveedores = pr.idtbl_proveedores
        ORDER BY p.fila, p.codigo_plazas
    """

    plazas = ejecutar_query(sql, (), nombre_bd="parquin_camiones")

    return render_template(
        "rio_torio_plazas.html",
        plazas=plazas,
        usuario_actual=current_user,
        es_super_admin=es_super_admin(),
    )


# =============================================================================
# 3️⃣ ALTA DE NUEVA PLAZA
# =============================================================================


@btn_rio_torio_plazas_bp.route("/nueva", methods=["GET", "POST"])
@login_required
def nueva_plaza_rio_torio():
    """
    3.1️⃣ NUEVA PLAZA (FORMULARIO DE ALTA)

    Esta vista permite crear una nueva fila en `tbl_plazas`.

    Campos gestionados:
      - codigo_plazas
      - observaciones
      - fila
      - numero_expediente
      - idtbl_usuarios          (FK → tbl_usuarios)
      - fecha_inicio
      - fecha_fin
      - exp_solicitud
      - exp_solicitud_fin
      - idtbl_inventario        (FK → tbl_inventario, pendiente de definir)

    Seguridad:
      - login_required: solo usuariosautenticados pueden crear plazas.
      - Si quieres filtrar por rol (ej. solo ADMIN/PARQUIN/SUPER_ADMIN), puedes añadir un
        chequeo con current_user.rol al inicio.
    """

    # 3.2️⃣ POST → procesar envío de formulario
    if request.method == "POST":
        codigo_plazas = request.form.get("codigo_plazas") or None
        observaciones = request.form.get("observaciones") or None
        fila = request.form.get("fila") or None
        numero_expediente = request.form.get("numero_expediente") or None
        idtbl_usuarios = request.form.get("idtbl_usuarios") or None
        fecha_inicio = request.form.get("fecha_inicio") or None
        fecha_fin = request.form.get("fecha_fin") or None
        exp_solicitud = request.form.get("exp_solicitud") or None
        exp_solicitud_fin = request.form.get("exp_solicitud_fin") or None
        idtbl_inventario = request.form.get("idtbl_inventario") or None

        # 3.2.1️⃣ Normalizar tipos (cadenas vacías → None, ints donde toca)
        idtbl_usuarios = int(idtbl_usuarios) if idtbl_usuarios else None
        idtbl_inventario = int(idtbl_inventario) if idtbl_inventario else None

        # 3.2.2️⃣ INSERT en tbl_plazas
        sql = """
            INSERT INTO tbl_plazas (
                codigo_plazas,
                observaciones,
                fila,
                numero_expediente,
                idtbl_usuarios,
                fecha_inicio,
                fecha_fin,
                exp_solicitud,
                exp_solicitud_fin,
                idtbl_inventario
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s
            )
        """

        ejecutar_non_query(
            sql,
            (
                codigo_plazas,
                observaciones,
                fila,
                numero_expediente,
                idtbl_usuarios,
                fecha_inicio,
                fecha_fin,
                exp_solicitud,
                exp_solicitud_fin,
                idtbl_inventario,
            ),
            nombre_bd="parquin_camiones",
        )

        flash("Plaza creada correctamente", "success")
        return redirect(url_for("rio_torio_plazas_bp.lista_plazas_rio_torio"))

    # 3.3️⃣ GET → mostrar formulario vacío con combos cargados
    usuarios = _cargar_usuarios_con_parquin()
    inventario = _cargar_inventario_plazas()

    return render_template(
        "rio_torio_plaza_form.html",
        modo="nuevo",
        plaza=None,
        usuarios=usuarios,
        inventario=inventario,
        usuario_actual=current_user,
        es_super_admin=es_super_admin(),
    )


# =============================================================================
# 4️⃣ EDICIÓN DE PLAZA EXISTENTE
# =============================================================================


@btn_rio_torio_plazas_bp.route("/editar/<int:id_plaza>", methods=["GET", "POST"])
@login_required
def editar_plaza_rio_torio(id_plaza: int):
    """
    4.1️⃣ EDITAR PLAZA (FORMULARIO DE EDICIÓN)

    Permite modificar una plaza ya existente en `tbl_plazas`:

    - Si la plaza no existe, redirige al listado con mensaje de error.
    - Si existe, permite cambiar todos los campos gestionados en el alta.
    """

    # 4.2️⃣ POST → guardar cambios
    if request.method == "POST":
        codigo_plazas = request.form.get("codigo_plazas") or None
        observaciones = request.form.get("observaciones") or None
        fila = request.form.get("fila") or None
        numero_expediente = request.form.get("numero_expediente") or None
        idtbl_usuarios = request.form.get("idtbl_usuarios") or None
        fecha_inicio = request.form.get("fecha_inicio") or None
        fecha_fin = request.form.get("fecha_fin") or None
        exp_solicitud = request.form.get("exp_solicitud") or None
        exp_solicitud_fin = request.form.get("exp_solicitud_fin") or None
        idtbl_inventario = request.form.get("idtbl_inventario") or None

        idtbl_usuarios = int(idtbl_usuarios) if idtbl_usuarios else None
        idtbl_inventario = int(idtbl_inventario) if idtbl_inventario else None

        sql = """
            UPDATE tbl_plazas
            SET
                codigo_plazas     = %s,
                observaciones     = %s,
                fila              = %s,
                numero_expediente = %s,
                idtbl_usuarios    = %s,
                fecha_inicio      = %s,
                fecha_fin         = %s,
                exp_solicitud     = %s,
                exp_solicitud_fin = %s,
                idtbl_inventario  = %s
            WHERE idtbl_plazas = %s
        """

        ejecutar_non_query(
            sql,
            (
                codigo_plazas,
                observaciones,
                fila,
                numero_expediente,
                idtbl_usuarios,
                fecha_inicio,
                fecha_fin,
                exp_solicitud,
                exp_solicitud_fin,
                idtbl_inventario,
                id_plaza,
            ),
            nombre_bd="parquin_camiones",
        )

        flash("Plaza actualizada correctamente", "success")
        return redirect(url_for("rio_torio_plazas_bp.lista_plazas_rio_torio"))

    # 4.3️⃣ GET → cargar datos actuales de la plaza + combos
    plaza = _cargar_plaza(id_plaza)
    if not plaza:
        flash("Plaza no encontrada", "danger")
        return redirect(url_for("rio_torio_plazas_bp.lista_plazas_rio_torio"))

    usuarios = _cargar_usuarios_con_parquin()
    inventario = _cargar_inventario_plazas()

    return render_template(
        "rio_torio_plaza_form.html",
        modo="editar",
        plaza=plaza,
        usuarios=usuarios,
        inventario=inventario,
        usuario_actual=current_user,
        es_super_admin=es_super_admin(),
    )


# =============================================================================
# 5️⃣ HELPERS DE DATOS (USUARIOS, INVENTARIO, PLAZA)
# =============================================================================


def _cargar_usuarios_con_parquin():
    """
    5.1️⃣ CARGAR USUARIOS CON PARQUIN ACTIVO

    Devuelve una lista de usuarios (`tbl_usuarios`) cuyos proveedores
    (`tbl_proveedores`) tienen parquin activo.

    Criterios aplicados:
      - tbl_proveedores.parquin = 1
      - tbl_usuarios.activo_baja = 1

    Campos devueltos (mínimo):
      - u.idtbl_usuarios
      - u.idtbl_proveedores
      - u.numero_cuenta
      - u.activo_baja
      - u.fecha_inicio
      - u.fecha_baja
      - u.rol
      - proveedor_nombre (Nombre_Razon_Social)
    """

    sql = """
        SELECT
            u.idtbl_usuarios,
            u.idtbl_proveedores,
            u.numero_cuenta,
            u.activo_baja,
            u.fecha_inicio,
            u.fecha_baja,
            u.rol,
            p.Nombre_Razon_Social AS proveedor_nombre
        FROM tbl_usuarios AS u
        INNER JOIN tbl_proveedores AS p
                ON u.idtbl_proveedores = p.idtbl_proveedores
        WHERE p.parquin = 1
          AND u.activo_baja = 1
        ORDER BY p.Nombre_Razon_Social, u.numero_cuenta
    """

    return ejecutar_query(sql, (), nombre_bd="parquin_camiones")


def _cargar_inventario_plazas():
    """
    5.2️⃣ CARGAR INVENTARIO PARA PLAZAS

    Devuelve la lista de elementos de inventario disponibles para asociar
    a una plaza (barreras, enchufes, etc.).

    NOTA:
    - Esta función asume la existencia de una tabla `tbl_inventario` con:
        · idtbl_inventario
        · descripcion
      Si la tabla aún no existe, se captura la excepción y se devuelve lista vacía.
    """

    try:
        sql = """
            SELECT
                idtbl_inventario,
                descripcion
            FROM tbl_inventario
            ORDER BY descripcion
        """
        return ejecutar_query(sql, (), nombre_bd="parquin_camiones")
    except Exception:
        # Si todavía no existe la tabla, devolvemos lista vacía.
        return []


def _cargar_plaza(id_plaza: int):
    """
    5.3️⃣ CARGAR UNA PLAZA CON SUS RELACIONES

    Carga una fila de `tbl_plazas` por `idtbl_plazas` e incluye:

      - datos de la propia plaza,
      - datos del usuario (si existe),
      - datos del proveedor asociado (si existe).

    Devuelve:
      - dict con todas las columnas mencionadas en el SELECT,
      - o None si no se encuentra la plaza.
    """

    sql = """
        SELECT
            p.idtbl_plazas,
            p.codigo_plazas,
            p.observaciones,
            p.fila,
            p.numero_expediente,
            p.idtbl_usuarios,
            p.fecha_inicio,
            p.fecha_fin,
            p.exp_solicitud,
            p.exp_solicitud_fin,
            p.idtbl_inventario,
            u.idtbl_proveedores,
            u.numero_cuenta,
            u.activo_baja,
            u.rol,
            pr.Nombre_Razon_Social AS proveedor_nombre
        FROM tbl_plazas AS p
        LEFT JOIN tbl_usuarios AS u
               ON p.idtbl_usuarios = u.idtbl_usuarios
        LEFT JOIN tbl_proveedores AS pr
               ON u.idtbl_proveedores = pr.idtbl_proveedores
        WHERE p.idtbl_plazas = %s
        LIMIT 1
    """

    filas = ejecutar_query(sql, (id_plaza,), nombre_bd="parquin_camiones")
    return filas[0] if filas else None
