# =============================================================================
# 🧸 helpers.py – Ayudantes para sesión, roles y permisos
# =============================================================================
# OBJETIVO:
#   - Centralizar la lógica de sesión y roles.
#   - Evitar código duplicado en todos los blueprints.
#   - Definir decoradores reutilizables para proteger vistas.
#   - Registrar en audit_log todos los accesos concedidos y denegados.
#
# REGLA DE ORO:
#   - Si rol == "super_admin" → acceso total.
#
# PUNTO DE ENTRADA / SALIDA DE LA EJECUCIÓN:
#   - Estas funciones se ejecutan cuando:
#       · Se llaman explícitamente (is_logged, get_role, etc.).
#       · Se usan como decoradores sobre vistas (login_required, rol_required...).
#   - En los decoradores:
#       · "Empiezan" al entrar en wrapper().
#       · "Terminan" cuando:
#           · devuelven un redirect (no se ejecuta la vista), o
#           · ejecutan la vista protegida (func(*args, **kwargs)).
# =============================================================================


# =============================================================================
# 1️⃣ IMPORTACIONES
# =============================================================================

from functools import wraps
import uuid
from typing import Optional

from flask import (
    session,  # Diccionario de sesión (cookie firmada)
    redirect,  # Respuesta HTTP 302 (redirección)
    url_for,  # Construye URLs a partir de endpoints
    flash,  # Mensajes temporales almacenados en sesión
    request,  # Información de la petición HTTP actual
    current_app,  # Aplicación Flask actual (para config y logger)
)

# =============================================================================
# 2️⃣ FUNCIONES GENÉRICAS DE BASE DE DATOS
# =============================================================================
# Autor: Tino Hierro
# Fecha: 2026-05-23
# Descripción: Wrappers sobre db.py para mantener compatibilidad con helpers_vias
# =============================================================================


def ejecutar_consulta(
    query: str,
    params: Optional[list] = None,
    devolver_dict: bool = False,
    database: str = "bd_tbl_comunes",
) -> list:
    """
    Ejecuta una consulta SELECT y retorna los resultados.

    Esta función es un wrapper sobre db.ejecutar_query() para mantener
    compatibilidad con el código de helpers_vias.

    Args:
        query (str): Consulta SQL a ejecutar. Usa %s como placeholders.
        params (list, opcional): Lista de parámetros para la consulta.
        devolver_dict (bool, opcional): Ignorado. db.py siempre retorna diccionarios.
        database (str, opcional): Nombre de la BD en DATABASES config.

    Returns:
        list: Lista de diccionarios {columna: valor}

    Example:
        >>> resultados = ejecutar_consulta(
        ...     "SELECT * FROM tbl_provincias WHERE idtbl_provincias = %s",
        ...     [5],
        ...     database="bd_tbl_comunes"
        ... )
    """
    from db import ejecutar_query as db_ejecutar_query

    try:
        # Convertir lista a tupla (db.py espera tuplas)
        params_tuple = tuple(params) if params else None

        # db.ejecutar_query ya devuelve diccionarios por defecto
        resultados = db_ejecutar_query(query, params_tuple, nombre_bd=database)

        return resultados or []

    except Exception as e:
        current_app.logger.error(f"❌ Error en ejecutar_consulta: {e}")
        current_app.logger.error(f"   Query: {query}")
        current_app.logger.error(f"   Params: {params}")
        return []


def insertar_generico(
    tabla: str, campos: dict, database: str = "bd_tbl_comunes"
) -> int:
    """
    Inserta un registro en una tabla y retorna el ID generado.

    Args:
        tabla (str): Nombre de la tabla donde insertar.
            Ejemplo: "tbl_calles", "tbl_municipios"
        campos (dict): Diccionario con pares {nombre_columna: valor}.
            Las columnas se escapan automáticamente con backticks.
            Ejemplo: {
                "idtbl_municipios": 395,
                "idtbl_tipos_de_vias": 1,
                "calles": "Mayor"
            }
        database (str, opcional): Nombre de la BD en DATABASES config.
            Por defecto: "bd_tbl_comunes"

    Returns:
        int: ID del registro insertado (lastrowid).
            Retorna 0 si hay error.

    Example:
        >>> nuevo_id = insertar_generico(
        ...     tabla="tbl_municipios",
        ...     campos={
        ...         "idtbl_provincias": 5,
        ...         "municipios": "Arévalo",
        ...     },
        ...     database="bd_tbl_comunes"
        ... )
    """
    from db import get_connection

    try:
        # Construir lista de columnas escapadas
        columnas = ", ".join(f"`{col}`" for col in campos.keys())

        # Construir placeholders (%s, %s, %s, ...)
        placeholders = ", ".join(["%s"] * len(campos))

        # Extraer valores en el mismo orden que las columnas
        valores = tuple(campos.values())

        # Construir query INSERT
        query = f"INSERT INTO `{tabla}` ({columnas}) VALUES ({placeholders})"

        # Usar get_connection de db.py
        conn = get_connection(database)
        cursor = conn.cursor()

        # Ejecutar INSERT
        cursor.execute(query, valores)

        # Hacer commit de la transacción
        conn.commit()

        # Obtener ID autogenerado
        nuevo_id = cursor.lastrowid

        # Cerrar cursor y conexión
        cursor.close()
        conn.close()

        return nuevo_id

    except Exception as e:
        current_app.logger.error(f"❌ Error en insertar_generico: {e}")
        current_app.logger.error(f"   Tabla: {tabla}")
        current_app.logger.error(f"   Campos: {campos}")
        return 0


def ejecutar_non_query(
    query: str, params: Optional[list] = None, database: str = "bd_tbl_comunes"
) -> int:
    """
    Ejecuta una consulta INSERT/UPDATE/DELETE sin retornar resultados.

    Esta función es un wrapper sobre db.ejecutar_non_query().

    Args:
        query (str): Consulta SQL a ejecutar (INSERT, UPDATE, DELETE)
        params (list, opcional): Lista de parámetros para la consulta
        database (str, opcional): Nombre de la BD en DATABASES config

    Returns:
        int: Número de filas afectadas (rowcount)

    Example:
        >>> filas = ejecutar_non_query(
        ...     "INSERT INTO audit_log (accion, ip) VALUES (%s, %s)",
        ...     ["login", "127.0.0.1"],
        ...     database="bd_tbl_comunes"
        ... )
    """
    from db import ejecutar_non_query as db_ejecutar_non_query

    try:
        # Convertir lista a tupla (db.py espera tuplas)
        params_tuple = tuple(params) if params else None

        # Usar la función de db.py
        filas_afectadas = db_ejecutar_non_query(query, params_tuple, nombre_bd=database)

        return filas_afectadas

    except Exception as e:
        current_app.logger.error(f"❌ Error en ejecutar_non_query: {e}")
        current_app.logger.error(f"   Query: {query}")
        current_app.logger.error(f"   Params: {params}")
        return 0


# =============================================================================
# 3️⃣ UTILIDADES BÁSICAS DE SESIÓN Y ROL
# =============================================================================


def is_logged() -> bool:
    """
    Devuelve True si hay un usuario autenticado.

    Regla:
      - Se considera "logueado" si existe session["user_id"].
    """
    return "user_id" in session


def get_role() -> Optional[str]:
    """
    Devuelve el rol actual guardado en sesión.

    Si no existe la clave "rol", devuelve None.
    """
    return session.get("rol")


def is_super_admin() -> bool:
    """
    Devuelve True si el rol actual es exactamente "super_admin".
    """
    return get_role() == "super_admin"


# =============================================================================
# 4️⃣ UTILIDADES INTERNAS PARA AUDITORÍA (audit_log)
# =============================================================================
# Estas funciones NO se usan directamente en blueprints; las consumen
# los decoradores de más abajo para registrar accesos en audit_log.
# =============================================================================


def _get_request_id() -> str:
    """
    Devuelve un identificador de petición persistido en sesión.

    - Si ya existe session["request_id"], lo reutiliza.
    - Si no existe, genera un UUID4, lo guarda en sesión y lo devuelve.
    """
    rid = session.get("request_id")
    if not rid:
        rid = str(uuid.uuid4())
        session["request_id"] = rid
    return rid


def _registrar_audit(accion: str, descripcion: Optional[str] = None) -> None:
    """
    Registra una acción de acceso en la tabla audit_log.

    Estructura de audit_log:
      - idtbl_audit_log      (PK, autoincrement)
      - idtbl_gestores       (FK opcional)
      - idtbl_roles          (FK opcional)
      - accion               (texto: acceso_concedido, acceso_denegado, ...)
      - modulo               (nombre del blueprint)
      - descripcion          (texto libre con el detalle)
      - ip                   (IP remota)
      - endpoint             (endpoint completo: bp.función)
      - path                 (ruta solicitada, ej: /parquin/rio_torio/accesos/)
      - user_agent           (navegador)
      - request_id           (UUID por sesión)
      - fecha                (timestamp, NOW() en BD)

    Parámetros:
      - accion:       'acceso_concedido', 'acceso_denegado', 'logout', etc.
      - descripcion:  texto opcional para explicar el motivo.
    """
    try:
        # 1) Identidades de sesión
        idtbl_gestores = session.get("idtbl_gestores") or session.get("user_id")
        idtbl_roles = (
            None  # si más adelante guardas idtbl_roles en sesión, ajústalo aquí
        )

        # 2) Datos de la petición HTTP
        modulo = request.blueprint
        ip = request.remote_addr or ""
        endpoint = request.endpoint
        path = request.path
        user_agent = request.headers.get("User-Agent", "")[
            :250
        ]  # Limitar a 250 caracteres
        request_id = _get_request_id()

        # 3) INSERT en audit_log (bd_tbl_comunes)
        sql = """
            INSERT INTO audit_log (
                idtbl_gestores,
                idtbl_roles,
                accion,
                modulo,
                descripcion,
                ip,
                endpoint,
                path,
                user_agent,
                request_id,
                fecha
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """

        datos = [
            idtbl_gestores,
            idtbl_roles,
            accion,
            modulo,
            descripcion,
            ip,
            endpoint,
            path,
            user_agent,
            request_id,
        ]

        ejecutar_non_query(sql, datos, "bd_tbl_comunes")
    except Exception:
        # Nunca romper la vista por un fallo de auditoría.
        pass


# =============================================================================
# 5️⃣ DECORADOR BÁSICO: login_required
# =============================================================================


def login_required(func):
    """
    Decorador que exige que exista una sesión activa.

    FLUJO:
      - Empieza al entrar en wrapper().
      - Si NO hay sesión:
          · registra en audit_log 'acceso_denegado'.
          · muestra un flash.
          · redirige a auth_bp.login.
          · NO ejecuta la vista protegida.
      - Si hay sesión:
          · registra en audit_log 'acceso_concedido'.
          · ejecuta la función original (vista).
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        # 1) Verificar si hay usuario logueado
        if not is_logged():
            _registrar_audit("acceso_denegado", "Login requerido (sin sesión)")
            flash("👶 Primero tienes que hacer login.", "warning")
            return redirect(url_for("auth_bp.login"))

        # 2) Hay sesión → registrar acceso y ejecutar vista original
        _registrar_audit("acceso_concedido", "Acceso con sesión (login_required)")
        return func(*args, **kwargs)

    return wrapper


# =============================================================================
# 6️⃣ DECORADOR ESPECÍFICO: super_admin_required
# =============================================================================


def super_admin_required(func):
    """
    Decorador que exige:
      1) usuario logueado
      2) rol exactamente "super_admin"

    FLUJO:
      - Si no hay login → audit_log: acceso_denegado + redirect a login.
      - Si hay login pero rol != super_admin → acceso_denegado + redirect.
      - Si es super_admin → acceso_concedido y ejecuta la vista original.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        # 1) Exigir login
        if not is_logged():
            _registrar_audit(
                "acceso_denegado", "Login requerido (super_admin_required)"
            )
            flash("👶 Primero haz login", "warning")
            return redirect(url_for("auth_bp.login"))

        # 2) Exigir rol super_admin
        if not is_super_admin():
            _registrar_audit("acceso_denegado", "Rol distinto de super_admin")
            flash("🚫 Solo super_admin puede entrar aquí", "danger")
            return redirect(url_for("auth_bp.login"))

        # 3) Todo OK → registrar acceso y ejecutar vista
        _registrar_audit(
            "acceso_concedido", "Acceso como super_admin (super_admin_required)"
        )
        return func(*args, **kwargs)

    return wrapper


# =============================================================================
# 7️⃣ DECORADOR GENÉRICO: rol_required
# =============================================================================


def rol_required(*roles):
    """
    Decorador genérico que recibe una lista variable de roles permitidos.

    Ejemplo de uso:
        @rol_required("gestor", "policia")
        def vista():
            ...

    REGLA DE ORO:
      - Si el rol actual es "super_admin", se permite el acceso siempre,
        sin comprobar nada más.

    AUDITORÍA:
      - En todos los casos registra en audit_log:
          · acceso_denegado cuando no hay sesión o el rol no está permitido.
          · acceso_concedido cuando el rol es válido (incluido super_admin).
    """

    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            # 1) Exigir login
            if not is_logged():
                _registrar_audit("acceso_denegado", "Login requerido en rol_required")
                flash("👶 Primero login", "warning")
                return redirect(url_for("auth_bp.login"))

            # 2) Obtener rol actual desde sesión
            rol_actual = get_role()

            # 3) super_admin → acceso directo
            if rol_actual == "super_admin":
                _registrar_audit(
                    "acceso_concedido", "Acceso como super_admin (rol_required)"
                )
                return func(*args, **kwargs)

            # 4) Comprobar si el rol actual está en la lista permitida
            if rol_actual not in roles:
                roles_str = ", ".join(roles)
                _registrar_audit(
                    "acceso_denegado",
                    f"Rol '{rol_actual}' no permitido. Requiere [{roles_str}]",
                )
                flash(f"🚫 Solo [{roles_str}] pueden entrar aquí", "danger")
                return redirect(url_for("auth_bp.login"))

            # 5) Rol permitido → registrar acceso y ejecutar vista original
            _registrar_audit(
                "acceso_concedido",
                f"Acceso con rol '{rol_actual}' (rol_required)",
            )
            return func(*args, **kwargs)

        return wrapper

    # Devuelve el decorador configurado con los roles
    return decorator


# =============================================================================
# 8️⃣ DECORADOR ESPECÍFICO: watcher_web_required
# =============================================================================


def watcher_web_required(func):
    """
    Decorador específico para rutas del "watcher web".

    Permite acceso únicamente a:
      - super_admin (por la regla de oro de rol_required)
      - gestor
      - policia

    Implementado reutilizando rol_required:
      - Internamente se comporta como @rol_required("gestor", "policia").
      - La auditoría se hace en rol_required (acceso_concedido / denegado).
    """
    # rol_required("gestor", "policia") devuelve un decorador,
    # que aplicamos inmediatamente sobre func.
    return rol_required("gestor", "policia")(func)


# =============================================================================
# 9️⃣ DECORADOR OPCIONAL: blueprint_required
# =============================================================================


def blueprint_required(*blueprint_names):
    """
    Restringe acceso según el blueprint que atiende la petición.

    Uso:
        @blueprint_required("gestores_bp", "panel_gestores_bp")
        def alguna_vista():
            ...

    FLUJO:
      - Lee request.blueprint.
      - Si no está en blueprint_names:
          · registra acceso_denegado en audit_log.
          · flash + redirect a login.
      - Si está permitido:
          · registra acceso_concedido en audit_log.
          · ejecuta la vista.
    """

    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            # request.blueprint -> nombre del blueprint actual (str o None)
            current_bp = request.blueprint

            if current_bp not in blueprint_names:
                _registrar_audit(
                    "acceso_denegado",
                    f"Blueprint '{current_bp}' no permitido para esta vista",
                )
                flash("🚫 Esta vista no pertenece a este módulo.", "danger")
                return redirect(url_for("auth_bp.login"))

            _registrar_audit(
                "acceso_concedido",
                f"Acceso desde blueprint '{current_bp}' (blueprint_required)",
            )
            return func(*args, **kwargs)

        return wrapper

    return decorator


# =============================================================================
# 🔟 PERMISOS POR TABLA: tiene_permiso
# =============================================================================


def tiene_permiso(tabla: str, rol: str) -> bool:
    """
    Comprueba si un rol tiene permiso sobre una tabla concreta.

    Parámetros:
      - tabla: nombre de la tabla (ej: 'tbl_usuarios')
      - rol: rol actual (gestor, policia, usuario, ...)

    Reglas:
      - super_admin → acceso total siempre.
      - Si no hay rol → False.
      - Si existe un registro en permisos_tablas(tabla, rol) con permitido=1,
        devuelve True; en otro caso, False.
    """

    # 1) Regla de oro: super_admin accede siempre
    if rol == "super_admin":
        return True

    # 2) Sin rol → sin permiso
    if not rol:
        return False

    # 3) Consultar permisos en la tabla permisos_tablas
    filas = ejecutar_consulta(
        """
        SELECT permitido
        FROM permisos_tablas
        WHERE tabla = %s AND rol = %s
        """,
        [tabla, rol],
        devolver_dict=True,
        database="bd_tbl_comunes",
    )

    return bool(filas and filas[0].get("permitido"))


# =============================================================================
# 1️⃣1️⃣ DECORADOR: permiso_tabla_required
# =============================================================================


def permiso_tabla_required(func):
    """
    Decorador para proteger rutas dinámicas tipo /admin/<tabla>.

    FLUJO:
      - Empieza en wrapper().
      - Exige login.
      - Obtiene el rol actual.
      - Obtiene la tabla desde kwargs["tabla"].
      - Llama a tiene_permiso(tabla, rol):
          · Si False:
              · registra acceso_denegado en audit_log.
              · flash + redirect a login.
          · Si True:
              · registra acceso_concedido en audit_log.
              · ejecuta la vista original.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        # 1) Exigir login
        if not is_logged():
            _registrar_audit(
                "acceso_denegado", "Login requerido (permiso_tabla_required)"
            )
            flash("👶 Primero login", "warning")
            return redirect(url_for("auth_bp.login"))

        # 2) Obtener rol actual
        rol_actual = get_role()

        # 3) Obtener nombre de tabla desde los parámetros de la URL
        tabla = kwargs.get("tabla")

        # 4) Validar permiso sobre esa tabla
        if not tiene_permiso(tabla, rol_actual):
            _registrar_audit(
                "acceso_denegado",
                f"Sin permiso a tabla '{tabla}' con rol '{rol_actual}'",
            )
            flash(f"🚫 No tienes acceso a {tabla}", "danger")
            return redirect(url_for("auth_bp.login"))

        # 5) Todo OK → registrar acceso y ejecutar vista
        _registrar_audit(
            "acceso_concedido",
            f"Acceso a tabla '{tabla}' con rol '{rol_actual}'",
        )
        return func(*args, **kwargs)

    return wrapper
