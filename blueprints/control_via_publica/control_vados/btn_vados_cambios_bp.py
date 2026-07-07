from flask import Blueprint, render_template, request, jsonify, g
from services.helpers import (
    login_required,
    rol_required,
    ejecutar_consulta,
    ejecutar_non_query,
)

# =============================================================================
# 1. BLUEPRINT: BTN_VADOS_CAMBIOS_BP
# =============================================================================
# Este blueprint agrupa:
# - Un formulario único (GET) para cambiar número o titular de un vado.
#   - El usuario busca el vado por número (numero_vado), no por idtbl_vados.
# - Tres endpoints:
#     * GET  /                                         → formulario (vados_cambios.html).
#     * POST /numero                                   → cambia el número de vado y deja traza en
#                                                        tbl_vados_historico_numeros.
#     * POST /titular                                  → cambia el titular (proveedor) y deja traza en
#                                                        tbl_vados_historico_titulares.
#     * GET  /api/buscar_proveedores_por_nif           → API para autocompletar NIF.
#
# El idtbl_gestores se obtiene del usuario logueado (g.user["idtbl_gestores"]).
# =============================================================================

btn_vados_cambios_bp = Blueprint(
    "btn_vados_cambios_bp",
    __name__,
    url_prefix="/vados_cambios",
)


# =============================================================================
# 2. HELPER: OBTENER VADO POR NÚMERO DE VADO
# =============================================================================
# Esta función lee un vado de tbl_vados buscando por numero_vado (no por idtbl_vados) para:
# - Validar que existe.
# - Recuperar el idtbl_vados, el número actual y el proveedor actual,
#   necesarios para guardar el histórico antes de cambiar.
# =============================================================================


def get_vado_por_numero_vado(numero_vado: str) -> dict | None:
    """
    Busca un vado en tbl_vados por numero_vado (el número de vado).
    Devuelve un dict con los datos del vado, o None si no existe.
    """
    # Normalizamos el número (quitamos espacios, mayúsculas, etc. si es necesario)
    numero_vado_norm = (numero_vado or "").strip()

    if not numero_vado_norm:
        return None

    filas = ejecutar_consulta(
        """
        SELECT
            idtbl_vados,
            idtbl_tipos_de_vias,
            idtbl_calles,
            Puerta,
            idtbl_municipios,
            idtbl_proveedores,
            numero_vado,
            idtbl_vado_anterior,
            idtbl_propietario_anterior,
            fecha_alta,
            fecha_baja,
            fecha_cambio,
            idtbl_gestores,
            tipo_operacion,
            baja,
            superficie,
            anchura
        FROM tbl_vados
        WHERE numero_vado = %s
        """,
        params=(numero_vado_norm,),
        devolver_dict=True,
        database="control_via_publica",
    )
    # Si hay varios vados con el mismo número (no debería), devuelve el primero.
    return filas[0] if filas else None


# =============================================================================
# 3. GET / : FORMULARIO DE CAMBIOS (vados_cambios.html)
# =============================================================================
# Muestra una única plantilla donde el usuario puede:
# - Introducir un número de vado (numero_vado), no idtbl_vados.
# - Elegir si quiere cambiar número o cambiar titular.
# - Rellenar los campos necesarios (número nuevo, motivo, proveedor nuevo, etc.).
# La lógica del formulario (qué endpoint POST llamar) se implementa en el JS/HTML.
# =============================================================================


@btn_vados_cambios_bp.get("/")
@login_required
@rol_required("gestor", "super_admin")
def btn_vados_cambios_formulario() -> str:
    """
    Renderiza la plantilla vados_cambios.html.
    Esta plantilla debe contener:
      - Un campo para número de vado (numero_vado).
      - Un bloque/form para cambiar número (POST a /vados_cambios/numero).
      - Un bloque/form para cambiar titular (POST a /vados_cambios/titular).
      - Un campo para buscar proveedores por NIF que use la API
        /vados_cambios/api/buscar_proveedores_por_nif.
    """
    return render_template("control_via_publica/Control_vados/vados_cambios.html")


# =============================================================================
# 4. POST /numero: CAMBIO DE NÚMERO DE VADO
# =============================================================================
# Recibe JSON con:
#   - numero_vado_actual       (str, obligatorio)  → número de vado actual.
#   - numero_vado_nuevo        (str, obligatorio)  → número de vado nuevo.
#   - motivo_cambio            (str, obligatorio)
#   - observaciones            (str, opcional)
#
# Flujo:
#   1. Validar parámetros y que el vado exista (buscando por numero_vado_actual).
#   2. Obtener idtbl_vados del vado.
#   3. Insertar en tbl_vados_historico_numeros:
#        idtbl_vados, numero_anterior, numero_nuevo, NOW(),
#        idtbl_gestores, observaciones, motivo_cambio.
#   4. Actualizar tbl_vados.numero_vado y fecha_cambio, idtbl_gestores.
#   5. Devolver JSON con el detalle del cambio.
# =============================================================================


@btn_vados_cambios_bp.post("/numero")
@login_required
@rol_required("gestor", "super_admin")
def cambiar_numero_vado():
    """
    Cambia el número de un vado y registra el cambio en el histórico de números.
    Se busca el vado por numero_vado (número de vado), no por idtbl_vados.
    """
    # Leemos el cuerpo de la petición como JSON.
    data = request.get_json(silent=True) or {}

    numero_vado_actual = (data.get("numero_vado_actual") or "").strip()
    numero_vado_nuevo = (data.get("numero_vado_nuevo") or "").strip()
    motivo_cambio = (data.get("motivo_cambio") or "").strip()
    observaciones = (data.get("observaciones") or "").strip()

    # Validaciones básicas de entrada.
    if not numero_vado_actual:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "numero_vado_actual obligatorio",
                }
            ),
            400,
        )
    if not numero_vado_nuevo:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "numero_vado_nuevo obligatorio",
                }
            ),
            400,
        )
    if not motivo_cambio:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "motivo_cambio obligatorio",
                }
            ),
            400,
        )

    # Obtenemos el idtbl_gestores del usuario logueado.
    idtbl_gestores = getattr(g, "user", {}).get("idtbl_gestores", None)
    if not idtbl_gestores:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "No se ha podido determinar el gestor logueado",
                }
            ),
            400,
        )

    # 4.1 Buscamos el vado por número de vado actual.
    vado = get_vado_por_numero_vado(numero_vado_actual)
    if not vado:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "Vado no encontrado con ese número de vado",
                }
            ),
            404,
        )

    idtbl_vados = vado["idtbl_vados"]
    numero_anterior = vado["numero_vado"]

    # Si el número nuevo es igual al actual, no hacemos nada.
    if numero_anterior == numero_vado_nuevo:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "El número nuevo es igual al actual",
                }
            ),
            400,
        )

    try:
        # 4.2 Insertar un registro en el histórico de números.
        insertar_hist_sql = """
            INSERT INTO tbl_vados_historico_numeros (
                idtbl_vados,
                numero_anterior,
                numero_nuevo,
                fecha_cambio,
                idtbl_gestores,
                observaciones,
                motivo_cambio
            )
            VALUES (
                %s, %s, %s,
                NOW(), %s, %s, %s
            )
        """
        ejecutar_non_query(
            insertar_hist_sql,
            params=(
                idtbl_vados,
                numero_anterior,
                numero_vado_nuevo,
                idtbl_gestores,
                observaciones,
                motivo_cambio,
            ),
            database="control_via_publica",
        )

        # 4.3 Actualizar el número en la tabla principal tbl_vados.
        update_sql = """
            UPDATE tbl_vados
            SET numero_vado = %s,
                fecha_cambio = NOW(),
                idtbl_gestores = %s
            WHERE idtbl_vados = %s
        """
        ejecutar_non_query(
            update_sql,
            params=(numero_vado_nuevo, idtbl_gestores, idtbl_vados),
            database="control_via_publica",
        )

    except Exception as exc:
        # Si algo falla, devolvemos error 500 con el detalle.
        return (
            jsonify(
                {
                    "ok": False,
                    "error": f"Error al cambiar número de vado: {exc}",
                }
            ),
            500,
        )

    # Respuesta de éxito con la información del cambio.
    return (
        jsonify(
            {
                "ok": True,
                "mensaje": "Número de vado actualizado correctamente",
                "vado": {
                    "idtbl_vados": idtbl_vados,
                    "numero_anterior": numero_anterior,
                    "numero_vado_nuevo": numero_vado_nuevo,
                },
            }
        ),
        200,
    )


# =============================================================================
# 5. POST /titular: CAMBIO DE TITULAR (PROVEEDOR)
# =============================================================================
# Recibe JSON con:
#   - numero_vado                  (str, obligatorio)  → número de vado para buscarlo.
#   - idtbl_proveedor_nuevo        (int, obligatorio)
#   - observaciones                (str, opcional)
#
# Flujo:
#   1. Validar parámetros y que el vado exista (buscando por numero_vado).
#   2. Obtener idtbl_vados y idtbl_proveedores del vado.
#   3. Insertar en tbl_vados_historico_titulares:
#        idtbl_vados, idtbl_proveedor_anterior, idtbl_proveedor_nuevo,
#        NOW(), idtbl_gestores, observaciones.
#   4. Actualizar tbl_vados.idtbl_proveedores y fecha_cambio, idtbl_gestores.
#   5. Devolver JSON con el detalle del cambio.
# =============================================================================


@btn_vados_cambios_bp.post("/titular")
@login_required
@rol_required("gestor", "super_admin")
def cambiar_titular_vado():
    """
    Cambia el titular (proveedor) de un vado y registra el cambio
    en el histórico de titulares.
    Se busca el vado por numero_vado (número de vado), no por idtbl_vados.
    """
    # Leemos el cuerpo de la petición como JSON.
    data = request.get_json(silent=True) or {}

    numero_vado = (data.get("numero_vado") or "").strip()
    observaciones = (data.get("observaciones") or "").strip()

    try:
        idtbl_proveedor_nuevo = int(data.get("idtbl_proveedor_nuevo") or 0)
    except ValueError:
        idtbl_proveedor_nuevo = 0

    # Validaciones básicas de entrada.
    if not numero_vado:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "numero_vado obligatorio",
                }
            ),
            400,
        )
    if idtbl_proveedor_nuevo <= 0:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "idtbl_proveedor_nuevo inválido",
                }
            ),
            400,
        )

    # Obtenemos el idtbl_gestores del usuario logueado.
    idtbl_gestores = getattr(g, "user", {}).get("idtbl_gestores", None)
    if not idtbl_gestores:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "No se ha podido determinar el gestor logueado",
                }
            ),
            400,
        )

    # 5.1 Buscamos el vado por número de vado.
    vado = get_vado_por_numero_vado(numero_vado)
    if not vado:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "Vado no encontrado con ese número de vado",
                }
            ),
            404,
        )

    idtbl_vados = vado["idtbl_vados"]
    idtbl_proveedor_anterior = vado["idtbl_proveedores"]

    # Si el proveedor nuevo es igual al actual, no tiene sentido el cambio.
    if idtbl_proveedor_anterior == idtbl_proveedor_nuevo:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "El proveedor nuevo es igual al actual",
                }
            ),
            400,
        )

    try:
        # 5.2 Insertar un registro en el histórico de titulares.
        insertar_hist_sql = """
            INSERT INTO tbl_vados_historico_titulares (
                idtbl_vados,
                idtbl_proveedor_anterior,
                idtbl_proveedor_nuevo,
                fecha_cambio,
                idtbl_gestores,
                observaciones
            )
            VALUES (
                %s, %s, %s,
                NOW(), %s, %s
            )
        """
        ejecutar_non_query(
            insertar_hist_sql,
            params=(
                idtbl_vados,
                idtbl_proveedor_anterior,
                idtbl_proveedor_nuevo,
                idtbl_gestores,
                observaciones,
            ),
            database="control_via_publica",
        )

        # 5.3 Actualizar el titular en la tabla principal tbl_vados.
        update_sql = """
            UPDATE tbl_vados
            SET idtbl_proveedores = %s,
                fecha_cambio = NOW(),
                idtbl_gestores = %s
            WHERE idtbl_vados = %s
        """
        ejecutar_non_query(
            update_sql,
            params=(idtbl_proveedor_nuevo, idtbl_gestores, idtbl_vados),
            database="control_via_publica",
        )

    except Exception as exc:
        # Si algo falla en histórico o en la actualización, devolvemos error 500.
        return (
            jsonify(
                {
                    "ok": False,
                    "error": f"Error al cambiar titular de vado: {exc}",
                }
            ),
            500,
        )

    # Respuesta de éxito con la información del cambio.
    return (
        jsonify(
            {
                "ok": True,
                "mensaje": "Titular del vado actualizado correctamente",
                "vado": {
                    "idtbl_vados": idtbl_vados,
                    "numero_vado": numero_vado,
                    "idtbl_proveedor_anterior": idtbl_proveedor_anterior,
                    "idtbl_proveedor_nuevo": idtbl_proveedor_nuevo,
                },
            }
        ),
        200,
    )


# =============================================================================
# 6. GET /api/buscar_proveedores_por_nif: AUTOCOMPLETE DE PROVEEDORES
# =============================================================================
# Endpoint de apoyo para plantillas que quieran buscar proveedores por NIF.
#
# Parámetros (query string):
#   - q: texto a buscar en el NIF (inicio, mitad, etc.).
#
# Comportamiento:
#   - Si q está vacío, devuelve [].
#   - Si q tiene valor, busca en bd_tbl_comunes.tbl_proveedores los registros
#     cuyo NIF, normalizado (sin espacios y en mayúsculas), contenga q_norm.
#
# Respuesta:
#   JSON con lista de objetos:
#   [
#     {
#       "idtbl_proveedores": 40103,
#       "NIF": "6581160D",
#       "Nombre_Razon_Social": "OSCAR ALONSO PEREZ"
#     },
#     ...
#   ]
# =============================================================================


@btn_vados_cambios_bp.get("/api/buscar_proveedores_por_nif")
@login_required
@rol_required("gestor", "super_admin")
def api_buscar_proveedores_por_nif():
    """
    Devuelve una lista de proveedores cuyo NIF contenga el texto buscado.
    """
    q = (request.args.get("q") or "").strip()
    if not q:
        # Si no se envía término de búsqueda, devolvemos lista vacía.
        return jsonify([])

    # Normalizamos un poco el texto (mayúsculas, sin espacios).
    q_norm = q.upper().replace(" ", "")

    # Buscamos por NIF que contenga q_norm.
    filas = ejecutar_consulta(
        """
        SELECT idtbl_proveedores, NIF, Nombre_Razon_Social
        FROM bd_tbl_comunes.tbl_proveedores
        WHERE REPLACE(UPPER(NIF), ' ', '') LIKE %s
        ORDER BY NIF
        LIMIT 15
        """,
        params=(f"%%{q_norm}%%",),
        devolver_dict=True,
        database="bd_tbl_comunes",
    )

    return jsonify(filas)
