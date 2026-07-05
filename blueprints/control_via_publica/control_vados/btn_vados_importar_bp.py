from __future__ import annotations

"""
=============================================================================
BTN_VADOS_IMPORTAR_BP · IMPORTAR VADOS DESDE EXCEL
=============================================================================

Funcionalidad:
- GET  /vados_importar/  → formulario para subir un XLS/XLSX
- POST /vados_importar/  → procesa el fichero, calcula % de éxito y
                           si es ≥ 96 % inserta en tbl_vados.

Reglas de negocio:
1. Se leen los datos del Excel desde el formulario.
2. Para cada fila:
   - Se resuelve idtbl_proveedores por NIF (consulta a bd_tbl_comunes.tbl_proveedores).
   - Se valida que existan los campos básicos:
       idtbl_tipos_de_vias, idtbl_calles, numero_vado.
   - Se prepara el registro para tbl_vados.
3. Se calcula el porcentaje de filas válidas.
4. Si el % de éxito es ≥ 96 %, se insertan todas las filas válidas en
   control_via_publica.tbl_vados.
   Si es < 96 %, no se inserta nada (rollback lógico).
5. Se devuelve un resumen JSON:
   - status: "ok" o "rollback"
   - total_filas, validas, errores, porcentaje_ok
   - detalle_errores (máx. 50 filas).

Requisitos:
- Usuario logueado con rol "gestor" o "super_admin".
- Formulario con:
  - file: fichero Excel
  - idtbl_gestores: ID del gestor que realiza la importación.

Base de datos:
- Origen: fichero Excel.
- Destino: control_via_publica.tbl_vados
- Proveedores: bd_tbl_comunes.tbl_proveedores (por NIF).

Autor: (tu nombre)
Fecha: 2026-06-14
=============================================================================
"""

import io
from typing import Any

import pandas as pd
from flask import Blueprint, current_app, jsonify, render_template, request
from services.helpers import (
    login_required,
    rol_required,
    ejecutar_consulta,
    ejecutar_non_query,
)

btn_vados_importar_bp = Blueprint(
    "btn_vados_importar_bp",
    __name__,
    url_prefix="/vados_importar",
)


# 1. GET: formulario
# ------------------
@btn_vados_importar_bp.get("/")
@login_required
@rol_required("gestor", "super_admin")
def btn_vados_importar_formulario() -> str:
    """
    Muestra el formulario para subir el fichero Excel de vados.

    Ruta:
        GET /vados_importar/

    Plantilla:
        templates/vados_importar/vados_importar.html
    """
    return render_template("vados_importar/vados_importar.html")


# 2. POST: procesar importación
# -----------------------------
@btn_vados_importar_bp.post("/")
@login_required
@rol_required("gestor", "super_admin")
def btn_vados_importar():
    """
    Procesa el Excel de vados y realiza la importación a tbl_vados
    sólo si el porcentaje de filas válidas es ≥ 96 %.

    Devuelve:
        - JSON con resumen y HTTP 200 si status == "ok"
        - JSON con resumen y HTTP 400 si status == "rollback" o error grave
    """
    # 2.1. Fichero
    file = request.files.get("file")
    if not file:
        return jsonify({"ok": False, "error": "No se ha enviado ningún fichero"}), 400

    # 2.2. Gestor
    try:
        id_gestor = int(request.form.get("idtbl_gestores") or 0)
    except ValueError:
        id_gestor = 0

    if id_gestor <= 0:
        return jsonify({"ok": False, "error": "idtbl_gestores inválido"}), 400

    # 2.3. Leer Excel
    try:
        content = file.read()
        df = pd.read_excel(
            io.BytesIO(content),
            dtype=str,
            keep_default_na=False,
            na_values=[],
        )
        df = df.fillna("")
    except Exception as exc:
        current_app.logger.exception("Error leyendo Excel de vados")
        return jsonify({"ok": False, "error": f"Error leyendo Excel: {exc}"}), 400

    # 2.4. Normalizar nombres de columnas (las que esperamos)
    df = df.rename(
        columns={
            "Desc_OT": "Desc_OT",
            "numero_vado": "numero_vado",
            "Via_OT": "Via_OT",
            "Numero": "Numero",
            "Puerta": "Puerta",
            "NIF_SP_OT": "NIF_SP_OT",
            "Nombre_SP_OT": "Nombre_SP_OT",
            "NIF": "NIF",
            "tipo_operacion": "tipo_operacion",
            "idtbl_calles": "idtbl_calles",
            "idtbl_tipos_de_vias": "idtbl_tipos_de_vias",
            "superficie": "superficie",
            "anchura": "anchura",
        }
    )

    total_filas = len(df)
    if total_filas == 0:
        return jsonify({"ok": False, "error": "El fichero no contiene filas"}), 400

        # 3. Helper de proveedores con caché
    # ----------------------------------
    # Estos helpers permiten:
    #   - Normalizar el NIF recibido desde el Excel.
    #   - Resolver el idtbl_proveedores correspondiente en bd_tbl_comunes.tbl_proveedores.
    #   - Cachear resultados para evitar consultas repetidas a la base de datos.

    cache_proveedores: dict[str, int | None] = {}

    def normalizar_nif(nif: str | None) -> str:
        """
        Normaliza el NIF recibido desde el Excel para facilitar la comparación.

        Reglas de normalización:
          - None -> "" (cadena vacía).
          - Se aplica strip() para eliminar espacios al principio y al final.
          - Se convierte a mayúsculas con upper().
          - Se eliminan los espacios internos.

        Ejemplos:
          - "  12345678z "  -> "12345678Z"
          - "12 345 678 Z"  -> "12345678Z"
        """
        return (nif or "").strip().upper().replace(" ", "")

    def get_id_proveedor_por_nif(nif: str | None) -> int | None:
        """
        Devuelve el idtbl_proveedores asociado a un NIF, utilizando caché local.

        Comportamiento:
          - Primero normaliza el NIF (normalizar_nif).
          - Si tras normalizar el NIF queda vacío, devuelve None directamente.
          - Si el NIF normalizado ya está en la caché, devuelve el valor cacheado
            (que puede ser un id entero o None si no se encontró anteriormente).
          - Si no está en caché:
              · Consulta bd_tbl_comunes.tbl_proveedores.
              · Si se encuentra, devuelve idtbl_proveedores (entero) y lo cachea.
              · Si no se encuentra, devuelve None y cachea None.

        Manejo de errores:
          - Si se produce cualquier excepción al ejecutar la consulta SQL:
              · Se registra un error en el log (current_app.logger.error).
              · Se cachea el NIF con valor None.
              · Se devuelve None.
          - En ningún caso una excepción en esta función interrumpe el flujo
            general de la importación: la fila se tratará como sin proveedor
            encontrado y el bucle seguirá con el resto de filas.
        """
        nif_norm = normalizar_nif(nif)
        if not nif_norm:
            return None

        # Consultar primero en caché para evitar repetir SELECT para el mismo NIF
        if nif_norm in cache_proveedores:
            return cache_proveedores[nif_norm]

        try:
            filas = ejecutar_consulta(
                """
                SELECT idtbl_proveedores
                FROM bd_tbl_comunes.tbl_proveedores
                WHERE UPPER(REPLACE(TRIM(NIF), ' ', '')) = %s
                """,
                params=(nif_norm,),
                devolver_dict=False,
                database="bd_tbl_comunes",
            )
            idp = filas[0][0] if filas else None

            # Guarda en caché aunque sea None (NIF no encontrado)
            cache_proveedores[nif_norm] = idp

            if idp is None:
                current_app.logger.warning(
                    f"[IMPORTAR VADOS] NIF no encontrado en proveedores: '{nif_norm}'"
                )

            return idp

        except Exception as exc:
            # Loguea el error pero no rompe la importación
            current_app.logger.error(
                f"[IMPORTAR VADOS] Error buscando proveedor por NIF '{nif_norm}': {exc}"
            )
            cache_proveedores[nif_norm] = None
            return None

        # 4. Recorrer filas: validar y preparar registros válidos
    # -------------------------------------------------------
    registros_validos: list[tuple[Any, ...]] = []
    errores = 0
    detalle_errores: list[dict[str, Any]] = []

    # Contadores relacionados con proveedores
    proveedores_localizados = 0        # filas con idtbl_proveedores != None
    proveedores_no_encontrados = 0     # filas con NIF informado pero sin proveedor

    for idx, row in df.iterrows():
        try:
            raw_id_tipo_via = (row.get("idtbl_tipos_de_vias") or "").strip()
            raw_id_calle = (row.get("idtbl_calles") or "").strip()
            numero_vado = (row.get("numero_vado") or "").strip()
            tipo_operacion = (row.get("tipo_operacion") or "").strip()
            desc_ot = (row.get("Desc_OT") or "").strip()
            via_ot = (row.get("Via_OT") or "").strip()
            puerta = (row.get("Puerta") or "").strip()
            nif_sp_ot = (row.get("NIF_SP_OT") or "").strip()
            nombre_sp_ot = (row.get("Nombre_SP_OT") or "").strip()
            nif_proveedor = (row.get("NIF") or "").strip()

            # superficie / anchura (pueden venir con coma decimal)
            superficie_raw = (row.get("superficie") or "").replace(",", ".")
            anchura_raw = (row.get("anchura") or "").replace(",", ".")
            superficie = float(superficie_raw) if superficie_raw else None
            anchura = float(anchura_raw) if anchura_raw else None

            # 4.1. Validación básica: campos vitales
            if not raw_id_tipo_via or not raw_id_calle:
                raise ValueError(
                    f"idtbl_tipos_de_vias o idtbl_calles vacío "
                    f"(idtbl_tipos_de_vias='{raw_id_tipo_via}', idtbl_calles='{raw_id_calle}')"
                )
            if not numero_vado:
                raise ValueError(
                    f"numero_vado vacío (idtbl_tipos_de_vias='{raw_id_tipo_via}', "
                    f"idtbl_calles='{raw_id_calle}')"
                )

            # 4.2. Conversión de tipos
            id_tipo_via = int(raw_id_tipo_via)
            id_calle = int(raw_id_calle)

            # 4.3. Resolver proveedor por NIF
            id_proveedor = get_id_proveedor_por_nif(nif_proveedor)

            # Si hay NIF informado y no se encuentra proveedor, la fila es ERROR
            if nif_proveedor and id_proveedor is None:
                proveedores_no_encontrados += 1
                raise ValueError(f"Proveedor no encontrado para NIF '{nif_proveedor}'")

            if id_proveedor is not None:
                proveedores_localizados += 1

            # 4.4. Preparar tupla para INSERT (solo si todo lo anterior es válido)
            registros_validos.append(
                (
                    id_tipo_via,
                    id_calle,
                    395,          # idtbl_municipios fijo
                    id_proveedor,
                    numero_vado,
                    None,         # idtbl_vado_anterior
                    None,         # idtbl_propietario_anterior
                    None,         # fecha_baja
                    None,         # fecha_cambio
                    id_gestor,
                    tipo_operacion,
                    0,            # baja = activo
                    desc_ot,
                    superficie,
                    anchura,
                    via_ot,
                    puerta,
                    nif_sp_ot,
                    nombre_sp_ot,
                )
            )

        except Exception as exc_row:
            errores += 1
            detalle_errores.append(
                {
                    "fila": int(idx) + 1,
                    "error": str(exc_row),
                    "numero_vado": row.get("numero_vado"),
                    "NIF": row.get("NIF"),
                    "idtbl_calles": row.get("idtbl_calles"),
                    "idtbl_tipos_de_vias": row.get("idtbl_tipos_de_vias"),
                }
            )

    validas = len(registros_validos)
    porcentaje_ok = round(validas * 100.0 / total_filas, 2) if total_filas else 0.0

    # 5. Regla del 96 % (rollback lógico)
    # -----------------------------------
    # Si el porcentaje de filas válidas es < 96 %, no insertamos nada.
    if porcentaje_ok < 96.0:
        resumen = {
            "ok": False,
            "status": "rollback",
            "total_filas": total_filas,
            "validas": validas,
            "insertados": 0,
            "errores": errores,
            "porcentaje_ok": porcentaje_ok,
            "detalle_errores": detalle_errores[:50],
            "proveedores_localizados": proveedores_localizados,
            "proveedores_no_encontrados": proveedores_no_encontrados,
            "mensaje": (
                "Importación cancelada. El porcentaje de filas válidas "
                "es inferior al 96 %. No se ha insertado ningún registro."
            ),
        }
        return jsonify(resumen), 400

    # 6. Insertar las filas válidas en tbl_vados
    # ------------------------------------------
    insert_sql = """
        INSERT INTO tbl_vados (
            idtbl_tipos_de_vias,
            idtbl_calles,
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
            Desc_OT,
            superficie,
            anchura,
            Via_OT,
            Puerta,
            NIF_SP_OT,
            Nombre_SP_OT
        )
        VALUES (
            %s, %s, %s, %s,
            %s, %s, %s,
            CURDATE(), %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s, %s
        )
    """

    insertados = 0
    for params in registros_validos:
        try:
            ejecutar_non_query(
                insert_sql,
                params=params,
                database="control_via_publica",
            )
            insertados += 1
        except Exception as exc_ins:
            errores += 1
            detalle_errores.append(
                {
                    "fila": None,
                    "error": f"Error al insertar en BD: {exc_ins}",
                    "numero_vado": params[4],
                    "NIF": None,
                }
            )

    # 7. Construir resumen final
    # --------------------------
    resumen = {
        "ok": True,
        "status": "ok",
        "total_filas": total_filas,
        "validas": validas,
        "insertados": insertados,
        "errores": errores,
        "porcentaje_ok": porcentaje_ok,
        "detalle_errores": detalle_errores[:50],
        "proveedores_localizados": proveedores_localizados,
        "proveedores_no_encontrados": proveedores_no_encontrados,
        "mensaje": (
            "Importación correcta. Se han insertado las filas válidas. "
            f"{proveedores_localizados} filas con proveedor asignado y "
            f"{proveedores_no_encontrados} filas con NIF sin proveedor."
        ),
    }

    return jsonify(resumen), 200