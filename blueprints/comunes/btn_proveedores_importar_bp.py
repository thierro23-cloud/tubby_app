# 1. IMPORTS Y DEFINICIÓN DEL BLUEPRINT
# ------------------------------------
# - Se importan las herramientas de Flask para definir rutas,
#   renderizar plantillas y devolver respuestas JSON.
# - Se importan las funciones de acceso a BD (ejecutar_query, ejecutar_non_query).
# - Se importan los decoradores de autenticación y autorización.
# - Se crea un Blueprint para agrupar las rutas relacionadas con proveedores.

from flask import Blueprint, render_template, request, jsonify
from db import ejecutar_query, ejecutar_non_query
from services.helpers import login_required, rol_required
import csv
import io

btn_proveedores_importar_bp = Blueprint(
    "btn_proveedores_importar_bp",
    __name__,
    url_prefix="/comunes/proveedores",
)


# 2. FUNCIONES DE NORMALIZACIÓN
# -----------------------------
# Estas funciones preparan los datos (NIF y nombre) para que tengan un formato
# homogéneo antes de compararlos o guardarlos en la base de datos.


def normalizar_nif(nif: str | None) -> str:
    """
    2.1 Normalizar NIF

    - Asegura que el NIF no sea None (lo sustituye por cadena vacía).
    - Elimina espacios al principio y al final con strip().
    - Elimina espacios internos con replace(" ", "").
    - Convierte a mayúsculas con upper().

    Ejemplo:
        " h052 35825 " -> "H05235825"
    """
    return (nif or "").strip().upper().replace(" ", "")


def normalizar_nombre(nombre: str | None) -> str:
    """
    2.2 Normalizar nombre

    - Asegura que el nombre no sea None.
    - Elimina espacios al principio y al final.
    - Mantiene los espacios internos (entre palabras).
    """
    return (nombre or "").strip()


# 3. ACCESO A PROVEEDORES EN BD
# -----------------------------
# Aquí definimos funciones auxiliares para buscar un proveedor por NIF
# y para insertar un proveedor nuevo en la tabla bd_tbl_comunes.tbl_proveedores.


def buscar_proveedor_por_nif(nif: str | None):
    """
    3.1 Buscar proveedor por NIF

    - Normaliza el NIF recibido.
    - Busca en bd_tbl_comunes.tbl_proveedores un registro cuyo NIF,
      una vez normalizado en SQL (TRIM + REPLACE + UPPER),
      coincida con el NIF normalizado en Python.
    - Devuelve la primera fila como dict (Idtbl_proveedores, NIF, Nombre_Razon_Social)
      o None si no encuentra nada.
    """
    sql = """
        SELECT Idtbl_proveedores, NIF, Nombre_Razon_Social
        FROM tbl_proveedores
        WHERE UPPER(REPLACE(TRIM(NIF), ' ', '')) = %s
        LIMIT 1
    """
    rows = ejecutar_query(
        sql,
        params=(normalizar_nif(nif),),
        nombre_bd="bd_tbl_comunes",
    )
    return rows[0] if rows else None


def insertar_proveedor(nif: str | None, nombre: str | None):
    """
    3.2 Insertar proveedor nuevo

    - Inserta un nuevo proveedor en bd_tbl_comunes.tbl_proveedores
      con NIF y Nombre_Razon_Social normalizados.
    - Otros campos de la tabla quedarán con sus valores por defecto.
    """
    sql = """
        INSERT INTO tbl_proveedores (NIF, Nombre_Razon_Social)
        VALUES (%s, %s)
    """
    return ejecutar_non_query(
        sql,
        params=(normalizar_nif(nif), normalizar_nombre(nombre)),
        nombre_bd="bd_tbl_comunes",
    )


# 4. RUTA /importar: FORMULARIO Y PROCESO DE IMPORTACIÓN
# ------------------------------------------------------
# Esta ruta soporta:
#   - GET  -> muestra el formulario de subida del CSV.
#   - POST -> procesa el CSV, evita duplicados, inserta proveedores nuevos
#             y devuelve un resumen JSON.


@btn_proveedores_importar_bp.route("/importar", methods=["GET", "POST"])
@login_required
@rol_required("su")
def btn_proveedores_importar():
    """
    4.1 Endpoint de importación de proveedores

    - GET:
        Muestra el formulario HTML para subir un fichero CSV de proveedores.

    - POST:
        Procesa el fichero CSV enviado en el campo 'archivo'.
        Formato esperado (delimitador ';'):
            NIF;nombre_razon_social
        Por cada fila:
        - Comprueba que hay NIF y nombre.
        - Busca si el proveedor ya existe por NIF.
        - Si existe, lo marca como 'existe' y no lo inserta.
        - Si no existe, lo inserta como nuevo.
        - Devuelve un JSON con:
            ok, insertados, existentes, errores, resultado.
    """
    # 4.2 Si es GET: devolver el formulario
    if request.method == "GET":
        return render_template("comunes/proveedores/importar_proveedores.html")

    # 4.3 Si es POST: procesar el CSV

    # 4.3.1 Obtener el archivo
    archivo = request.files.get("archivo")
    if not archivo:
        return jsonify({"ok": False, "msg": "No has enviado ningún archivo"}), 400

    # 4.3.2 Leer el archivo como texto (UTF-8) y eliminar posible BOM
    contenido = archivo.stream.read().decode("utf-8-sig", errors="ignore")
    contenido = contenido.lstrip("\ufeff")

    # 4.3.3 Crear un DictReader para leer el CSV delimitado por ';'
    #      Se espera que la primera línea contenga las cabeceras:
    #      NIF;nombre_razon_social
    lector = csv.DictReader(io.StringIO(contenido), delimiter=";")

    # 4.3.4 Inicializar contadores y estructuras de control de resultados
    insertados = 0
    existentes = 0
    errores: list[str] = []
    resultado: list[dict] = []

    # 4.3.5 Recorrer cada fila de datos del CSV
    #        start=2 porque la fila 1 suele ser la cabecera.
    for i, fila in enumerate(lector, start=2):
        # Para debug opcional:
        # print("DEBUG fila", i, "keys:", list(fila.keys()), "values:", list(fila.values()))

        # 4.3.5.1 Extraer NIF y nombre usando las claves reales del CSV
        #         En tu CSV, la cabecera del nombre es 'nombre_razon_social'
        nif = fila.get("NIF")
        nombre = fila.get("nombre_razon_social") or fila.get("Nombre_Razon_Social")

        # 4.3.5.2 Validar que existan ambos campos
        if not nif or not nombre:
            errores.append(
                f"Fila {i}: faltan nif o nombre (keys={list(fila.keys())}, "
                f"values={list(fila.values())})"
            )
            continue

        # 4.3.5.3 Comprobar si el proveedor ya existe por NIF
        existente = buscar_proveedor_por_nif(nif)

        if existente:
            # Ya existe: sumamos al contador y guardamos detalle
            existentes += 1
            resultado.append(
                {
                    "fila": i,
                    "estado": "existe",
                    "id": existente["Idtbl_proveedores"],
                    "nif": normalizar_nif(nif),
                    "nombre": normalizar_nombre(nombre),
                }
            )
            continue

        # 4.3.5.4 Si no existe, intentamos insertarlo como nuevo
        try:
            insertar_proveedor(nif, nombre)
            insertados += 1
            resultado.append(
                {
                    "fila": i,
                    "estado": "insertado",
                    "nif": normalizar_nif(nif),
                    "nombre": normalizar_nombre(nombre),
                }
            )
        except Exception as e:
            # Si hay un error en BD, lo registramos
            errores.append(f"Fila {i}: {str(e)}")

    # 4.4 Construir y devolver el resumen JSON
    return jsonify(
        {
            "ok": True,
            "insertados": insertados,
            "existentes": existentes,
            "errores": errores,
            "resultado": resultado,
        }
    )
