"""
Módulo: btn_edificios_form_bp.py
--------------------------------
Este blueprint gestiona el formulario de EDIFICIOS MUNICIPALES.

Funcionalidad principal:
- Mostrar un formulario para crear/editar registros de `tbl_edificios_municipales`.
- Desplegable superior para seleccionar rápidamente un edificio existente.
- Navegación entre registros (anterior / siguiente).
- Guardar (INSERT / UPDATE) el edificio.
- Eliminar el edificio actual.
- Rellenar automáticamente el campo `foto_edificios` como "<inmueble>.jpg" si se deja vacío.

Columnas usadas de la tabla `tbl_edificios_municipales`:
    Idtbl_edificios_municipales (PK),
    inmueble,
    idtbl_tipos_de_vias,
    idtbl_calles,
    calefaccion,
    numero_calderas,
    ascensores,
    numero_registro_ascensor,
    idtbl_ascensor,
    idtbl_calefaccion,
    documentos_adjuntos,
    idtbl_numero_catastro,
    escaleras_mecanicas,
    numero_escaleras_mecanicas,
    altura,
    perimetro_canalones,
    numero_edificio,
    Observaciones,
    tipo_de_edificio,
    idtbl_servicio,
    idtbl_inspeccion,
    idtbl_bienes,
    calderas_control_remoto,
    acceso_remoto,
    alarma,
    consumo_remoto,
    idtbl_caldera,
    numero,
    idtbl_organo_contable,
    foto_edificios,
    Limpieza
"""

# ============================================================
# 0. IMPORTS
# ============================================================

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    abort,
)
from db import ejecutar_query, ejecutar_non_query
import re

# ============================================================
# 1. DEFINICIÓN DEL BLUEPRINT
#    - Nombre interno: btn_edificios_form_bp
#    - Prefijo de URL: /inventario/edificios
# ============================================================

btn_edificios_form_bp = Blueprint(
    "btn_edificios_form_bp",
    __name__,
    url_prefix="/inventario/edificios",
)


# ============================================================
# 2. RUTA PRINCIPAL DEL FORMULARIO
# ------------------------------------------------------------
#  - GET /inventario/edificios/form          → nuevo registro
#  - GET /inventario/edificios/form/<id>     → editar registro
#  Esta función solo delega en _renderizar_formulario.
# ============================================================


@btn_edificios_form_bp.route("/form", methods=["GET"], defaults={"edificio_id": None})
@btn_edificios_form_bp.route("/form/<int:edificio_id>", methods=["GET"])
def btn_edificios_form(edificio_id):
    """
    Muestra el formulario de edificios.
    Si edificio_id es None: modo "nuevo".
    Si edificio_id tiene valor: modo "editar" para ese ID.
    """
    return _renderizar_formulario(edificio_id=edificio_id)


# ============================================================
# 3. GUARDAR EDIFICIO (INSERT / UPDATE)
# ============================================================
# Ruta: POST /inventario/edificios/form/guardar
#
# Funcionalidad:
# - Lee TODOS los campos del formulario HTML
# - Normaliza foto_edificios si está vacío (inmueble → nombre_archivo.jpg)
# - Decide INSERT o UPDATE según edificio_id esté presente
# - Ejecuta query parametrizada con 30 campos
# - Manejo completo de errores con flash messages
# - Redirecciona al formulario original
#
# Variables esperadas del HTML:
# - edificio_id (oculto, para UPDATE)
# - inmueble (obligatorio)
# - foto_edificios (opcional, se auto-genera si vacío)
# - 28 campos más (IDs, números, textos libres)
#
# Importar antes:
# import re
# from flask import flash, redirect, request, url_for
# ============================================================

# ============================================================
# 3. GUARDAR (INSERT / UPDATE)
# ------------------------------------------------------------
#  - POST /inventario/edificios/form/guardar
#  Decide automáticamente si hace INSERT o UPDATE según
#  venga o no "edificio_id" en el formulario.
# ============================================================


@btn_edificios_form_bp.route("/form/guardar", methods=["POST"])
def edificios_guardar():
    """
    Guarda un edificio:
      - Si edificio_id viene informado → UPDATE.
      - Si no viene → INSERT (nuevo registro).

    Además:
      - Si el campo foto_edificios viene vacío pero inmueble tiene valor,
        se rellena automáticamente con una versión normalizada de inmueble:
        * sin puntos
        * espacios → guiones bajos
        * solo letras, números y guion bajo
        * en minúsculas
        * añadiendo ".jpg" al final
    """
    # 3.1 Leer ID del formulario (oculto). Si viene → UPDATE; si no → INSERT.
    edificio_id = request.form.get("edificio_id")

    # 3.2 Campo principal: nombre del edificio
    inmueble = (request.form.get("inmueble") or "").strip()

    # 3.3 Foto escrita por el usuario (si la hay)
    foto_edificios_manual = (request.form.get("foto_edificios") or "").strip()

    # 3.4 Si el campo foto_edificios viene vacío, lo calculamos
    #     a partir de "inmueble" normalizado.
    foto_edificios = foto_edificios_manual
    if not foto_edificios and inmueble:
        # quitar puntos
        normalized_inmueble = inmueble.replace(".", " ")
        # reemplazar espacios por guiones bajos
        normalized_inmueble = "_".join(normalized_inmueble.split())
        # eliminar caracteres no alfanuméricos ni guion bajo
        normalized_inmueble = re.sub(r"[^a-zA-Z0-9_]", "", normalized_inmueble)
        # pasar a minúsculas
        normalized_inmueble = normalized_inmueble.lower()
        # montar nombre de archivo
        foto_edificios = f"{normalized_inmueble}.jpg"

    # 3.5 Diccionario con todos los campos que se guardan
    datos = {
        "inmueble": inmueble or None,
        "idtbl_tipos_de_vias": request.form.get("idtbl_tipos_de_vias") or None,
        "idtbl_calles": request.form.get("idtbl_calles") or None,
        "calefaccion": request.form.get("calefaccion") or None,
        "numero_calderas": request.form.get("numero_calderas") or None,
        "ascensores": request.form.get("ascensores") or None,
        "numero_registro_ascensor": request.form.get("numero_registro_ascensor")
        or None,
        "idtbl_ascensor": request.form.get("idtbl_ascensor") or None,
        "idtbl_calefaccion": request.form.get("idtbl_calefaccion") or None,
        "documentos_adjuntos": request.form.get("documentos_adjuntos") or None,
        "idtbl_numero_catastro": request.form.get("idtbl_numero_catastro") or None,
        "escaleras_mecanicas": request.form.get("escaleras_mecanicas") or None,
        "numero_escaleras_mecanicas": request.form.get("numero_escaleras_mecanicas")
        or None,
        "altura": request.form.get("altura") or None,
        "perimetro_canalones": request.form.get("perimetro_canalones") or None,
        "numero_edificio": request.form.get("numero_edificio") or None,
        "Observaciones": request.form.get("Observaciones") or None,
        "tipo_de_edificio": request.form.get("tipo_de_edificio") or None,
        "idtbl_servicio": request.form.get("idtbl_servicio") or None,
        "idtbl_inspeccion": request.form.get("idtbl_inspeccion") or None,
        "idtbl_bienes": request.form.get("idtbl_bienes") or None,
        "calderas_control_remoto": request.form.get("calderas_control_remoto") or None,
        "acceso_remoto": request.form.get("acceso_remoto") or None,
        "alarma": request.form.get("alarma") or None,
        "consumo_remoto": request.form.get("consumo_remoto") or None,
        "idtbl_caldera": request.form.get("idtbl_caldera") or None,
        "numero": request.form.get("numero") or None,
        "idtbl_organo_contable": request.form.get("idtbl_organo_contable") or None,
        "foto_edificios": foto_edificios or None,
        "Limpieza": request.form.get("Limpieza") or None,
    }

    # 3.6 Construir SQL y parámetros según sea UPDATE o INSERT
    if edificio_id:
        sql = """
            UPDATE tbl_edificios_municipales SET
                inmueble = %s,
                idtbl_tipos_de_vias = %s,
                idtbl_calles = %s,
                calefaccion = %s,
                numero_calderas = %s,
                ascensores = %s,
                numero_registro_ascensor = %s,
                idtbl_ascensor = %s,
                idtbl_calefaccion = %s,
                documentos_adjuntos = %s,
                idtbl_numero_catastro = %s,
                escaleras_mecanicas = %s,
                numero_escaleras_mecanicas = %s,
                altura = %s,
                perimetro_canalones = %s,
                numero_edificio = %s,
                Observaciones = %s,
                tipo_de_edificio = %s,
                idtbl_servicio = %s,
                idtbl_inspeccion = %s,
                idtbl_bienes = %s,
                calderas_control_remoto = %s,
                acceso_remoto = %s,
                alarma = %s,
                consumo_remoto = %s,
                idtbl_caldera = %s,
                numero = %s,
                idtbl_organo_contable = %s,
                foto_edificios = %s,
                Limpieza = %s
            WHERE Idtbl_edificios_municipales = %s
        """
        params = tuple(datos.values()) + (edificio_id,)
        accion = "actualizado"
    else:
        sql = """
            INSERT INTO tbl_edificios_municipales (
                inmueble,
                idtbl_tipos_de_vias,
                idtbl_calles,
                calefaccion,
                numero_calderas,
                ascensores,
                numero_registro_ascensor,
                idtbl_ascensor,
                idtbl_calefaccion,
                documentos_adjuntos,
                idtbl_numero_catastro,
                escaleras_mecanicas,
                numero_escaleras_mecanicas,
                altura,
                perimetro_canalones,
                numero_edificio,
                Observaciones,
                tipo_de_edificio,
                idtbl_servicio,
                idtbl_inspeccion,
                idtbl_bienes,
                calderas_control_remoto,
                acceso_remoto,
                alarma,
                consumo_remoto,
                idtbl_caldera,
                numero,
                idtbl_organo_contable,
                foto_edificios,
                Limpieza
            ) VALUES (
                %s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,
                %s,%s,%s,%s,%s,
                %s,%s,%s,%s
            )
        """
        params = tuple(datos.values())
        accion = "creado"

    # 3.7 Ejecutar y redirigir
    ejecutar_non_query(sql, params, nombre_bd="inventario")
    flash(f"Edificio {accion} correctamente", "success")
    return redirect(
        url_for("btn_edificios_form_bp.btn_edificios_form")
    )  # ============================================================


# 4. ELIMINAR
# ------------------------------------------------------------
#  - POST /inventario/edificios/form/eliminar
#  Recibe el ID por POST y borra el registro.
# ============================================================


@btn_edificios_form_bp.route("/form/eliminar", methods=["POST"])
def edificios_eliminar():
    """
    Elimina un edificio identificado por edificio_id (enviado por POST).
    Si no se envía ID, muestra un mensaje de error.
    """
    try:
        # 4.1 Leer ID del formulario
        edificio_id = request.form.get("edificio_id", type=int)
        if not edificio_id:
            flash("No se proporcionó ID de edificio", "danger")
            return redirect(url_for("btn_edificios_form_bp.btn_edificios_form"))

        # 4.2 Borrar registro en base de datos
        ejecutar_non_query(
            "DELETE FROM tbl_edificios_municipales WHERE Idtbl_edificios_municipales = %s",
            (edificio_id,),
            nombre_bd="inventario",
        )

        # 4.3 Feedback
        flash("Edificio eliminado", "warning")
        return redirect(url_for("btn_edificios_form_bp.btn_edificios_form"))

    except Exception as e:
        flash(f"Error al eliminar: {e}", "danger")
        return redirect(url_for("btn_edificios_form_bp.btn_edificios_form"))


# ============================================================
# 5. FUNCIÓN AUXILIAR: RENDERIZAR FORMULARIO
# ------------------------------------------------------------
#  Carga:
#   - Datos del edificio (si se edita).
#   - IDs anterior y siguiente para navegar.
#   - Lista completa de edificios para el desplegable superior.
#   - Desplegables de tipos de vías y calles.
#  Y devuelve la plantilla "inventario/edificios_form.html".
# ============================================================


def _renderizar_formulario(edificio_id):
    """
    Carga todos los datos necesarios para pintar el formulario:

    - edificio: dict con los datos del edificio seleccionado (o None si es uno nuevo).
    - edificios_lista: lista de todos los edificios (id + inmueble) para el combo de arriba.
    - prev_id / next_id: IDs del registro anterior y siguiente para navegación.
    - tipos_de_vias: opciones para el select de tipo de vía.
    - calles: opciones para el select de calles.
    """
    edificio = None
    prev_id = None
    next_id = None
    accion = "nuevo"

    # 5.1 Si hay ID, cargar el edificio concreto y preparar navegación
    if edificio_id:
        # 5.1.1 Cargar datos del edificio
        filas = ejecutar_query(
            """
            SELECT
                Idtbl_edificios_municipales AS id,
                inmueble,
                idtbl_tipos_de_vias,
                idtbl_calles,
                calefaccion,
                numero_calderas,
                ascensores,
                numero_registro_ascensor,
                idtbl_ascensor,
                idtbl_calefaccion,
                documentos_adjuntos,
                idtbl_numero_catastro,
                escaleras_mecanicas,
                numero_escaleras_mecanicas,
                altura,
                perimetro_canalones,
                numero_edificio,
                Observaciones,
                tipo_de_edificio,
                idtbl_servicio,
                idtbl_inspeccion,
                idtbl_bienes,
                calderas_control_remoto,
                acceso_remoto,
                alarma,
                consumo_remoto,
                idtbl_caldera,
                numero,
                idtbl_organo_contable,
                foto_edificios,
                Limpieza
            FROM tbl_edificios_municipales
            WHERE Idtbl_edificios_municipales = %s
            """,
            (edificio_id,),
            nombre_bd="inventario",
        )

        print(
            "DEBUG EDIFICIO:", edificio_id, "len(filas) =", len(filas), "filas =", filas
        )

        if not filas:
            abort(404, f"Edificio {edificio_id} no encontrado")

        edificio = filas[0]
        accion = "editar"

        # 5.1.3 Calcular ID siguiente (next_id)
        next_row = ejecutar_query(
            """
            SELECT Idtbl_edificios_municipales AS id
            FROM tbl_edificios_municipales
            WHERE Idtbl_edificios_municipales > %s
            ORDER BY Idtbl_edificios_municipales ASC
            LIMIT 1
            """,
            (edificio_id,),
            nombre_bd="inventario",
        )
        if next_row:
            next_id = next_row[0]["id"]

    # 5.2 Desplegable superior: todos los edificios (id + nombre)
    edificios_lista = ejecutar_query(
        """
        SELECT Idtbl_edificios_municipales AS id, inmueble
        FROM tbl_edificios_municipales
        ORDER BY inmueble
        """,
        nombre_bd="inventario",
    )

    # 5.3 Desplegables auxiliares para campos idtbl_...
    tipos_de_vias = ejecutar_query(
        "SELECT idtbl_tipos_de_vias, tipos_de_vias FROM tbl_tipos_de_vias ORDER BY tipos_de_vias",
        nombre_bd="bd_tbl_comunes",
    )

    calles = ejecutar_query(
        "SELECT idtbl_calles, calles FROM tbl_calles ORDER BY calles",
        nombre_bd="bd_tbl_comunes",
    )

    # 5.4 Renderizar plantilla con todos los datos necesarios
    return render_template(
        "inventario/edificios_form.html",
        edificio=edificio,
        edificios_lista=edificios_lista,
        tipos_de_vias=tipos_de_vias,
        calles=calles,
        accion=accion,
        prev_id=prev_id,
        next_id=next_id,
    )
