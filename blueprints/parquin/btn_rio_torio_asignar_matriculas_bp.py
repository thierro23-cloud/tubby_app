# btn_rio_torio_asignar_matriculas_bp.py
# =============================================================================
# MÓDULO: Asignación de matrículas de camiones para Río Torío
# PROPÓSITO: Blueprint de Flask que implementa una vista de administración
#            para asignar/reasignar matrículas a usuarios del parquin.
# AUTOR: Tino Hierro
# ÚLTIMA ACTUALIZACIÓN: 2026-06-05
# =============================================================================

from __future__ import annotations

from urllib.parse import urlparse

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    current_app,
)
from services.helpers import rol_required
from db import ejecutar_query, ejecutar_non_query

# =============================================================================
# 1️⃣ BLUEPRINT · ASIGNAR MATRÍCULAS RÍO TORÍO
# =============================================================================

# ⚠️ IMPORTANTE: El blueprint debe declararse ANTES de usarlo en decoradores @route
btn_rio_torio_asignar_matriculas_bp = Blueprint(
    "btn_rio_torio_asignar_matriculas_bp",
    __name__,
    url_prefix="/parquin/rio_torio",  # Prefijo de URL para todas las rutas de este blueprint
)

# =============================================================================
# 2️⃣ HELPERS · PARSEO, USUARIOS, DESTINO
# =============================================================================


def _parsear_matriculas_solo(texto: str) -> list[str]:
    """
    Convierte el contenido pegado por el usuario en una lista de matrículas normalizadas.

    Formato de entrada admitido:
      - Una matrícula por línea (ej: "1234ABC")
      - Varias matrículas por línea separadas por punto y coma (ej: "1234ABC; 5678DEF")

    Proceso de normalización:
      1. Elimina líneas vacías
      2. Recorta espacios en blanco alrededor de cada trozo
      3. Convierte a mayúsculas
      4. Filtra cadenas no vacías

    Parámetros:
        texto (str): Contenido pegado desde el formulario

    Retorno:
        list[str]: Lista de matrículas normalizadas en mayúsculas sin espacios

    Ejemplo:
        >>> _parsear_matriculas_solo("1234ABC\\n5678def; 9012ghi")
        ['1234ABC', '5678DEF', '9012GHI']
    """
    mats: list[str] = []

    for linea in texto.splitlines():
        linea = linea.strip()
        if not linea:
            continue

        for trozo in linea.split(";"):
            mat = trozo.strip().upper()
            if mat:
                mats.append(mat)

    return mats


def _asignar_matriculas_a_usuario(id_usuario: int, matriculas: list[str]) -> dict:
    """
    Asigna o actualiza matrículas en tbl_camiones para un usuario concreto de Río Torío.

    Estrategia de persistencia (por cada matrícula):
      1. VERIFICACIÓN 1: ¿Ya existe ese camión para este usuario?
         → Si SÍ: ACTUALIZA solo el campo 'activo = 1' (reactivar)
         →Si NO: continuar

      2. VERIFICACIÓN 2: ¿Existe la matrícula para OTRO usuario?
         → Si SÍ: REASIGNA cambiando idtbl_usuarios y activa 'activo = 1'
         → Si NO: continuar

      3. INSERCIÓN: ¿No existe en ningún usuario?
         → INSERTA nueva fila con idtbl_usuarios, matriculas, activo = 1

    Parámetros:
        id_usuario (int): ID del usuario en tbl_usuarios al que se asignan las matrículas
        matriculas (list[str]): Lista de matrículas normalizadas a procesar

    Retorno:
        dict: Resumen con claves:
            - "procesadas" (int): Total de matrículas procesadas
            - "actualizados" (int): Fila*s* modificadas (reactivadas o reasignadas)
            - "insertados" (int): Nuevas filas creadas

    Ejemplo de retorno:
        {
            "procesadas": 10,
            "actualizados": 3,
            "insertados": 7
        }

    Límites de diseño:
      - No valida formato de matrícula (asume que ya está normalizado)
      - No maneja transacciones explícitas (cada query es atómica independiente)
      - Las matrículas se almacenan tal cual en la columna 'matriculas' (sin formato fijo)
    """
    procesadas = 0
    actualizados = 0
    insertados = 0

    current_app.logger.info(
        "🚚 [_asignar_matriculas_a_usuario] Usuario %s, matrículas: %s",
        id_usuario,
        matriculas,
    )

    for matricula in matriculas:
        procesadas += 1

        # 1) ¿Ya existe ese camión para este usuario?
        existe_mismo = ejecutar_query(
            """
            SELECT idtbl_camiones
            FROM tbl_camiones
            WHERE idtbl_usuarios = %s
              AND matriculas = %s
            """,
            (id_usuario, matricula),
            nombre_bd="parquin_camiones",
        )

        if existe_mismo:
            ejecutar_non_query(
                """
                UPDATE tbl_camiones
                SET activo = 1
                WHERE idtbl_camiones = %s
                """,
                (existe_mismo[0]["idtbl_camiones"],),
                nombre_bd="parquin_camiones",
            )
            actualizados += 1
            continue

        # 2) ¿Existe la matrícula para otro usuario?
        existe_otro = ejecutar_query(
            """
            SELECT idtbl_camiones
            FROM tbl_camiones
            WHERE matriculas = %s
            LIMIT 1
            """,
            (matricula,),
            nombre_bd="parquin_camiones",
        )

        if existe_otro:
            ejecutar_non_query(
                """
                UPDATE tbl_camiones
                SET idtbl_usuarios = %s,
                    activo = 1
                WHERE idtbl_camiones = %s
                """,
                (id_usuario, existe_otro[0]["idtbl_camiones"]),
                nombre_bd="parquin_camiones",
            )
            actualizados += 1
            continue

        # 3) No existe → insertar nueva fila
        ejecutar_non_query(
            """
            INSERT INTO tbl_camiones (idtbl_usuarios, matriculas, activo)
            VALUES (%s, %s, 1)
            """,
            (id_usuario, matricula),
            nombre_bd="parquin_camiones",
        )
        insertados += 1

    current_app.logger.info(
        "✅ [_asignar_matriculas_a_usuario] Usuario %s: procesadas=%s, actualizados=%s, insertados=%s",
        id_usuario,
        procesadas,
        actualizados,
        insertados,
    )

    return {
        "procesadas": procesadas,
        "actualizados": actualizados,
        "insertados": insertados,
    }


def _obtener_usuarios_parquin() -> list[dict]:
    """
    Obtiene el listado de usuarios del parquin con datos del proveedor para el <select>.

    Consulta SQL:
      - Une tbl_usuarios (esquema parquin_camiones) con tbl_proveedores (esquema bd_tbl_comunes)
      - Filtra por usuarios que tienen proveedor asociado (INNER JOIN)
      - Ordena por nombre/razón social del proveedor

    Campos devueltos:
        - idtbl_usuarios (int): PK de tbl_usuarios
        - nombre_razon_social (str): Nombre comercial o razón social del proveedor
        - nif (str): NIF/CIF del proveedor

    Retorno:
        list[dict]: Lista de diccionarios con las columnas mencionadas

    Uso típico:
        Se pasa directamente al template para renderizar un <select> con opciones.
        Ejemplo en Jinja2:
            {% for usuario in usuarios %}
                <option value="{{ usuario.idtbl_usuarios }}">
                    {{ usuario.nombre_razon_social }} ({{ usuario.nif }})
                </option>
            {% endfor %}

    Nota:
      - El INNER JOIN implica que USERS sin proveedor NO aparecerán
      - La ordenación es case-sensitive dependiendo de la collation de MySQL
    """
    sql = """
        SELECT
            u.idtbl_usuarios,
            pr.Nombre_Razon_Social AS nombre_razon_social,
            pr.NIF                 AS nif
        FROM parquin_camiones.tbl_usuarios AS u
        INNER JOIN bd_tbl_comunes.tbl_proveedores AS pr
            ON u.idtbl_proveedores = pr.Idtbl_proveedores
        ORDER BY pr.Nombre_Razon_Social
    """
    return ejecutar_query(sql, nombre_bd="bd_tbl_comunes")


def _resolver_destino(origen: str | None) -> str:
    """
    Resuelve la URL de destino para redirigir tras procesar el formulario.

    Lógica de resolución:
      1. Si 'origen' es None o vacío → devuelve la propia vista del botón
      2. Si 'origen' es una ruta interna relativa (sin esquema ni dominio)
         → devuelve 'origen' tal cual
      3. Si 'origen' es URL absoluta (tiene http://, https://, etc.)
         → ignora 'origen' y devuelve la propia vista del botón

    Parámetros:
        origen (str | None): Valor del parámetro 'next' (GET o POST)

    Retorno:
        str: URL relativa segura para redirección

    Motivación de seguridad:
      - Previene redirecciones abiertas a dominios externos (SSRF/Phishing)
      - Solo permite redirecciones a rutas internas del mismo sitio

    Ejemplos:
        >>> _resolver_destino("/parquin/lista")
        "/parquin/lista"

        >>> _resolver_destino("https://evil.com")
        "/parquin/rio_torio/btn_rio_torio_asignar_matriculas"

        >>> _resolver_destino(None)
        "/parquin/rio_torio/btn_rio_torio_asignar_matriculas"
    """
    if origen:
        parsed = urlparse(origen)
        if not parsed.scheme and not parsed.netloc:
            return origen

    return url_for(
        "btn_rio_torio_asignar_matriculas_bp.btn_rio_torio_asignar_matriculas"
    )


# =============================================================================
# 3️⃣ VISTA PRINCIPAL · PEGAR LISTADO Y ASIGNAR
# =============================================================================


@btn_rio_torio_asignar_matriculas_bp.route(
    "/btn_rio_torio_asignar_matriculas",
    methods=["GET", "POST"],
)
@rol_required("gestor", "super_admin")
def btn_rio_torio_asignar_matriculas():
    """
    Vista de administración para asignar matrículas de camiones a un usuario de Río Torío.

    Endpoints:
        GET  /parquin/rio_torio/btn_rio_torio_asignar_matriculas
            → Muestra el formulario con el select de usuarios

        POST /parquin/rio_torio/btn_rio_torio_asignar_matriculas
            → Procesa el formulario y asigna las matrículas

    Parámetros de seguridad:
        - Decorador @rol_required("gestor", "super_admin")
          Solo usuarios con rol 'gestor' o 'super_admin' pueden acceder

    Parámetros del formulario (POST):
        - idtbl_usuarios (str): ID del usuario seleccionado (se convierte a int)
        - listado (str): Texto pegado con las matrículas
        - next (str, opcional): URL de destino para redirección posterior

    Flujo de procesamiento (POST):
        1. Validar que hay usuario seleccionado
        2. Validar que el ID es un entero válido
        3. Validar que hay texto en el listado
        4. Parsear matrículas con _parsear_matriculas_solo()
        5. Validar que se interpretaron matrículas válidas
        6. Ejecutar _asignar_matriculas_a_usuario()
        7. Mostrar flash con resumen de resultados
        8. Redirigir al destino seguro con _resolver_destino()

    Mensajes de feedback (flash):
        - "Debes seleccionar un usuario." → warning
        - "Usuario no válido." → danger
        - "No se ha recibido ningún listado de matrículas." → warning
        - "No se han podido interpretar matrículas válidas..." → danger
        - "Usuario X: procesadas Y matrículas..." → success
        - "Error asignando matrículas..." → danger

    Plantilla renderizada (GET):
        parquin/rio_torio/rio_torio_asignar_matriculas.html

    Contexto de la plantilla (GET):
        - usuarios (list[dict]): Usuarios con proveedor para el select
        - origen (str): Valor del parámetro 'next' para redirección

    Logs generados:
        - INFO: user_id, longitud del texto, origen en POST
        - INFO: matrículas parseadas
        - INFO: usuario y cantidad de usuarios cargados en GET
        - INFO: resumen final de procesadas/actualizados/insertados
        - ERROR: excepción durante la asignación
    """
    origen = request.form.get("next") or request.args.get("next", "")

    if request.method == "POST":
        usuario_id_str = request.form.get("idtbl_usuarios", "").strip()
        texto = request.form.get("listado", "").strip()

        current_app.logger.info(
            "📥 [POST asignar_matriculas] usuario_id_str=%r, texto_len=%s, origen=%r",
            usuario_id_str,
            len(texto),
            origen,
        )

        # Validación 1: Usuario seleccionado
        if not usuario_id_str:
            flash("Debes seleccionar un usuario.", "warning")
            return redirect(_resolver_destino(origen))

        # Validación 2: ID de usuario válido
        try:
            id_usuario = int(usuario_id_str)
        except ValueError:
            flash("Usuario no válido.", "danger")
            return redirect(_resolver_destino(origen))

        # Validación 3: Listado no vacío
        if not texto:
            flash("No se ha recibido ningún listado de matrículas.", "warning")
            return redirect(_resolver_destino(origen))

        # Parseo de matrículas
        mats = _parsear_matriculas_solo(texto)
        current_app.logger.info("🧾 Matrículas parseadas: %s", mats)

        # Validación 4: Matrículas válidas
        if not mats:
            flash(
                "No se han podido interpretar matrículas válidas. Revisa el formato.",
                "danger",
            )
            return redirect(_resolver_destino(origen))

        # Asignación a la base de datos
        try:
            resumen = _asignar_matriculas_a_usuario(id_usuario, mats)
            flash(
                f"Usuario {id_usuario}: procesadas {resumen['procesadas']} matrículas. "
                f"Actualizadas {resumen['actualizados']} y creadas {resumen['insertados']} nuevas.",
                "success",
            )
        except Exception as e:
            current_app.logger.error("Error asignando matrículas Rio Torío: %s", e)
            flash(
                "Error asignando matrículas. Revisa el log para más detalles.",
                "danger",
            )

        return redirect(_resolver_destino(origen))

    # GET: mostrar formulario con select de usuarios
    usuarios = _obtener_usuarios_parquin()
    current_app.logger.info(
        "🔍 [GET asignar_matriculas] origen=%r, usuarios_cargados=%s",
        origen,
        len(usuarios),
    )
    return render_template(
        "parquin/rio_torio/rio_torio_asignar_matriculas.html",
        usuarios=usuarios,
        origen=origen,
    )
