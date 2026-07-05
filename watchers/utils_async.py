"""
blueprints/control_via_publica/utils_async.py

UTILS ASYNC · PDFs EN VÍA PÚBLICA

RESPONSABILIDADES PRINCIPALES
-----------------------------
1) CONTENEDORES
   - Orquestar el flujo asíncrono de PDFs de contenedores (colocación / retirada).
   - Normalizar CSV, rutas y carpetas de trabajo:
       · contenedores/entrada_pdf
       · contenedores/para_revision
       · contenedores/pendientes_validacion
       · contenedores/solo_retirada
       · contenedores/papelera
   - Insertar registros en tbl_contenedores_pendientes.
   - Evitar duplicidad de CSV en pendientes y control.
   - Disparar el backend industrial (contenedores_core.backend_contenedores).
   - Crear eventos de agenda en casos auto_guardado.

2) OBRAS
   - Procesar PDFs de obras en obras/entrada_pdf.
   - Disparar backend industrial de obras (obras_core.backend_obras).
   - Insertar en tbl_obras.

3) STUBS PARA FUTURO
   - procesar_pdf_inicial (bandeja general).
   - procesar_pdf_entrada_terrazas (terrazas/entrada_pdf).

NOTA:
  - Este módulo NO expone rutas HTTP, se invoca desde watchers o desde
    otros blueprints (por ejemplo, btn_contenedores_admin_uploads_bp).
"""

# =============================================================================
# 1️⃣ IMPORTS
# =============================================================================
import json
import os
import shutil
import logging
import re
from typing import Dict, Any

from flask import current_app
import PyPDF2  # ⛔ Necesario: pip install PyPDF2

from db import ejecutar_query, ejecutar_non_query

# Backend industrial de CONTENEDORES
from contenedores_core.backend_contenedores import procesar_pdf_core

# Backend industrial de OBRAS
from obras_core.backend_obras import procesar_pdf_core_obras

logger = logging.getLogger(__name__)
logger.info("[UTILS_ASYNC] Módulo utils_async cargado desde %s", __file__)


# =============================================================================
# 2️⃣ RUTAS DE CARPETAS · CONTENEDORES (RELATIVAS A root_path)
# =============================================================================

def _carpeta_contenedores_base() -> str:
    """
    Devuelve la carpeta base de contenedores dentro de la app:
      <root_path>/contenedores
    """
    return os.path.join(current_app.root_path, "contenedores")


def _ensure_contenedores_dirs() -> None:
    """
    Asegura que existen las subcarpetas de trabajo de contenedores:
      - entrada_pdf
      - para_revision
      - pendientes_validacion
      - solo_retirada
      - papelera
    """
    base = _carpeta_contenedores_base()
    for sub in [
        "entrada_pdf",
        "para_revision",
        "pendientes_validacion",
        "solo_retirada",
        "papelera",
        "colocacion",  # añadida para auto_guardado
    ]:
        os.makedirs(os.path.join(base, sub), exist_ok=True)


def _ruta_pdf(subcarpeta: str, nombre_pdf: str) -> str:
    """
    Construye la ruta absoluta a un PDF de contenedores dado subcarpeta y nombre.
    """
    base = _carpeta_contenedores_base()
    return os.path.join(base, subcarpeta, nombre_pdf)


def _nombre_pdf_por_csv(csv_value: str | None, nombre_por_defecto: str) -> str:
    """
    Devuelve el nombre de archivo físico a partir de un CSV:
      - Si csv_value es None, devuelve nombre_por_defecto.
      - Si csv_value ya tiene '.', se respeta (posible extensión).
      - En caso contrario, se añade .pdf.
    """
    if not csv_value:
        return nombre_por_defecto
    if "." in csv_value:
        return csv_value
    return f"{csv_value}.pdf"


# =============================================================================
# 3️⃣ SQL BASE PARA PENDIENTES Y CHEQUEO DE CSV (CONTENEDORES)
# =============================================================================

SQL_INSERT_PENDIENTE = """
INSERT INTO tbl_contenedores_pendientes (
    nombre_pdf,
    ruta_pdf,
    datos_extraidos_json,
    estado,
    motivo,
    csv,
    csv_retirada,
    fecha_creacion
) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
"""

SQL_UPDATE_A_PENDIENTE = """
UPDATE tbl_contenedores_pendientes
SET ruta_pdf = %s,
    estado = %s,
    fecha_revision = NOW()
WHERE idtbl_contenedores_pendientes = %s
"""

SQL_SELECT_PENDIENTE = """
SELECT *
FROM tbl_contenedores_pendientes
WHERE idtbl_contenedores_pendientes = %s
"""

SQL_EXISTE_CSV_EN_PENDIENTES_O_CONTROL = """
SELECT origen
FROM (
    SELECT 'pendientes_csv' AS origen
    FROM tbl_contenedores_pendientes
    WHERE csv = %s
    UNION ALL
    SELECT 'pendientes_csv_retirada' AS origen
    FROM tbl_contenedores_pendientes
    WHERE csv_retirada = %s
    UNION ALL
    SELECT 'control_csv' AS origen
    FROM tbl_control_contenedores
    WHERE csv = %s
    UNION ALL
    SELECT 'control_csv_retirada' AS origen
    FROM tbl_control_contenedores
    WHERE csv_retirada = %s
) AS t
LIMIT 1
"""

SQL_SELECT_UPLOAD_POR_NOMBRE = """
SELECT
    idtbl_contenedores_uploads,
    idtbl_gestor,
    fecha_subida
FROM tbl_contenedores_uploads
WHERE nombre_guardado = %s
ORDER BY idtbl_contenedores_uploads DESC
LIMIT 1
"""


def _csv_existe_en_pendientes_o_control(csv_val: str | None) -> bool:
    """
    Indica si un CSV ya existe:
      - en tbl_contenedores_pendientes (csv o csv_retirada),
      - o en tbl_control_contenedores (csv o csv_retirada).

    Devuelve True si encuentra cualquier coincidencia.
    """
    if not csv_val:
        return False

    filas = ejecutar_query(
        SQL_EXISTE_CSV_EN_PENDIENTES_O_CONTROL,
        (csv_val, csv_val, csv_val, csv_val),
        nombre_bd="control_via_publica",
    )
    return bool(filas)


def _insertar_pendiente_en_revision(
    nombre_pdf: str,
    datos: Dict[str, Any],
    motivo: str,
    csv: str | None,
    csv_retirada: str | None,
    ruta_relativa: str,
    estado_inicial: str = "REVISION",
) -> int:
    """
    Inserta un registro en tbl_contenedores_pendientes con estado inicial (por defecto 'REVISION').

    Parámetros:
      - nombre_pdf: nombre físico del PDF.
      - datos: dict con datos extraídos (se almacena en JSON).
      - motivo: motivo textual del estado.
      - csv, csv_retirada: CSV de instalación / retirada (pueden ser None).
      - ruta_relativa: carpeta lógica (para_revision, solo_retirada, etc.).
      - estado_inicial: estado de workflow (por defecto 'REVISION').

    Devuelve:
      - idtbl_contenedores_pendientes recién insertado.
    """
    datos_json = json.dumps(datos, ensure_ascii=False)

    csv_val = csv or "CSV_NULL"
    csv_retirada_val = csv_retirada or "CSV_NULL"

    ejecutar_non_query(
        SQL_INSERT_PENDIENTE,
        (
            nombre_pdf,
            ruta_relativa,
            datos_json,
            estado_inicial,
            motivo,
            csv_val,
            csv_retirada_val,
        ),
        nombre_bd="control_via_publica",
    )

    row = ejecutar_query(
        "SELECT LAST_INSERT_ID() AS id",
        (),
        nombre_bd="control_via_publica",
    )[0]
    return row["id"]


# =============================================================================
# 4️⃣ ENRIQUECIMIENTO DE DATOS (TEXTO + METADATOS PDF)
# =============================================================================

def _set_if_missing(datos: Dict[str, Any], clave: str, valor: str | None) -> None:
    """
    Solo asigna datos[clave] = valor.strip() si:
      - valor no es None ni vacío, y
      - datos[clave] no existe o es cadena vacía.
    """
    if not valor:
        return
    actual = datos.get(clave)
    if actual is None or (isinstance(actual, str) and not actual.strip()):
        datos[clave] = valor.strip()


def _enriquecer_con_metadatos_pdf(ruta_pdf: str, datos: Dict[str, Any]) -> Dict[str, Any]:
    """
    Segunda pasada sobre el TEXTO del PDF (CONTENEDORES):

    Solo rellena campos secundarios si faltan:
      - solicitante_nombre / solicitante_nif
      - representado_nombre / representado_nif
      - lugar_ubicacion / fecha_colocacion / tamano_contenedor

    NO toca csv ni csv_retirada.
    """
    try:
        full_text = ""
        with open(ruta_pdf, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                full_text += page.extract_text() or ""

        texto = full_text.replace("\n", " ").replace("\t", " ")

        m = re.search(r"Nombre\s+solicitante:\s*([A-ZÁÉÍÓÚÑ\s\.]+)", texto)
        _set_if_missing(datos, "solicitante_nombre", m.group(1) if m else None)

        m = re.search(r"NIF\s+interesado:\s*([0-9A-Z]+)", texto, re.IGNORECASE)
        _set_if_missing(datos, "solicitante_nif", m.group(1) if m else None)

        m = re.search(r"Nombre\s+representado:\s*([A-ZÁÉÍÓÚÑ\s\.]+)", texto)
        _set_if_missing(datos, "representado_nombre", m.group(1) if m else None)

        m = re.search(r"Nif\s+representado:\s*([0-9A-Z]+)", texto, re.IGNORECASE)
        _set_if_missing(datos, "representado_nif", m.group(1) if m else None)

        m = re.search(
            r"LUGAR\s+DE\s+UBICACIÓN:\s*([^F]+?)\s*FECHA\s+DE\s+COLOCACIÓN",
            texto,
        )
        _set_if_missing(datos, "lugar_ubicacion", m.group(1) if m else None)

        m = re.search(
            r"FECHA\s+DE\s+COLOCACIÓN:\s*([0-9]{2}/[0-9]{2}/[0-9]{4})",
            texto,
        )
        _set_if_missing(datos, "fecha_colocacion", m.group(1) if m else None)

        m = re.search(
            r"TAMAÑO\s+CONTENEDOR:\s*([^\s].*?)(?:EN\s+LOS\s+LUGARES|$)",
            texto,
        )
        _set_if_missing(datos, "tamano_contenedor", m.group(1) if m else None)

        return datos

    except Exception as e:
        current_app.logger.error(
            f"[UTILS_ASYNC] Error enriqueciendo metadatos PDF (texto): {e!r}"
        )
        return datos


def _volcar_metadatos_pdf(ruta_pdf: str, datos: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tercera pasada: lee metadatos internos (info/XMP) del PDF y los guarda
    en datos['debug_metadatos_pdf'] para diagnóstico.
    """
    try:
        with open(ruta_pdf, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            info = reader.metadata

        metadatos: dict[str, str] = {}
        if info:
            for clave, valor in info.items():
                if valor is None:
                    continue
                metadatos[str(clave)] = str(valor)

        if "debug_metadatos_pdf" not in datos:
            datos["debug_metadatos_pdf"] = metadatos

        return datos

    except Exception as e:
        current_app.logger.error(
            f"[UTILS_ASYNC] Error leyendo metadatos internos del PDF: {e!r}"
        )
        return datos


# =============================================================================
# 5️⃣ FUNCIÓN PÚBLICA · PROCESAR PDF DESDE contenedores/entrada_pdf
# =============================================================================

from agenda_core.backend_agenda import (
    crear_evento_agenda,
    añadir_calle_a_evento,
)
from datetime import datetime, timedelta


def procesar_pdf_entrada(nombre_pdf: str) -> Dict[str, Any]:
    """
    Punto único de entrada para procesar un PDF desde contenedores/entrada_pdf.

    Flujo general:
      1) Verifica existencia del PDF en contenedores/entrada_pdf.
      2) (Opcional) Recupera el id del gestor que lo subió desde tbl_contenedores_uploads.
      3) Llama al backend industrial (procesar_pdf_core) para extraer datos y estado.
      4) Hace 2 pasadas extra (texto + metadatos internos).
      5) Aplica filtro global de CSV (unicidad).
      6) Rutea por estado:
           - auto_guardado: auto-inserción en control + PDF a colocacion + evento agenda.
           - solo_retirada: pendiente en solo_retirada.
           - resto: pendientes en para_revision.
    """
    _ensure_contenedores_dirs()

    # 5.1️⃣ Ruta inicial en entrada_pdf
    ruta_inicial = _ruta_pdf("entrada_pdf", nombre_pdf)

    if not os.path.exists(ruta_inicial):
        current_app.logger.error(
            f"[UTILS_ASYNC] PDF no encontrado en entrada_pdf: {ruta_inicial}"
        )
        return {
            "estado": "pendiente_validacion",
            "motivo": "Archivo no encontrado en entrada_pdf",
            "datos": {"nombre_pdf": nombre_pdf},
        }

    # 5.2️⃣ Recuperar info de subida (gestor, fecha_subida) si existe
    idtbl_gestor_subida = None
    fecha_subida = None
    try:
        fila_upload = ejecutar_query(
            SQL_SELECT_UPLOAD_POR_NOMBRE,
            (nombre_pdf,),
            nombre_bd="control_via_publica",
        )
        if fila_upload:
            fila = fila_upload[0]
            idtbl_gestor_subida = fila.get("idtbl_gestor")
            fecha_subida = fila.get("fecha_subida")
    except Exception as e:
        current_app.logger.error(
            f"[UTILS_ASYNC] Error recuperando upload para {nombre_pdf}: {e!r}"
        )

    # 5.3️⃣ Llamar al backend industrial de CONTENEDORES
    resultado = procesar_pdf_core(ruta_inicial)
    estado = resultado.get("estado")
    motivo = resultado.get("motivo")
    datos = resultado.get("datos") or {}

    # Anotar gestor/fecha_subida en datos para uso posterior (control/agenda)
    if idtbl_gestor_subida is not None:
        datos.setdefault("idtbl_gestor_subida", idtbl_gestor_subida)
    if fecha_subida is not None:
        datos.setdefault("fecha_subida", str(fecha_subida))

    # 5.4️⃣ Segunda y tercera pasada: texto + metadatos internos
    datos = _enriquecer_con_metadatos_pdf(ruta_inicial, datos)
    datos = _volcar_metadatos_pdf(ruta_inicial, datos)

    resultado["datos"] = datos

    # 5.5️⃣ Normalizar nombre para flujo (nombre_pdf_core)
    nombre_pdf_core = datos.get("nombre_pdf") or nombre_pdf

    # 5.6️⃣ Normalizar CSVs
    raw_csv = datos.get("csv")
    csv = raw_csv.strip() if isinstance(raw_csv, str) else None

    raw_csv_retirada = datos.get("csv_retirada")
    csv_retirada = (
        raw_csv_retirada.strip()
        if isinstance(raw_csv_retirada, str)
        else None
    )

    current_app.logger.info(
        f"[UTILS_ASYNC] Resultado core para {nombre_pdf_core}: "
        f"estado={estado}, motivo={motivo}, csv={csv!r}, csv_retirada={csv_retirada!r}"
    )

    # 5.7️⃣ FILTRO GLOBAL DE CSV (duplicados)
    if csv:
        if _csv_existe_en_pendientes_o_control(csv):
            nombre_destino = _nombre_pdf_por_csv(csv, nombre_pdf_core)
            ruta_papelera = _ruta_pdf("papelera", nombre_destino)
            try:
                shutil.move(ruta_inicial, ruta_papelera)
                ruta_final = ruta_papelera
                current_app.logger.warning(
                    f"[UTILS_ASYNC] CSV duplicado ({csv}), PDF enviado a papelera: {ruta_papelera}"
                )
            except Exception as e:
                current_app.logger.error(
                    f"[UTILS_ASYNC] Error moviendo PDF duplicado a papelera: {e!r}"
                )
                ruta_final = ruta_inicial

            resultado["ruta_final_pdf"] = ruta_final
            resultado["id_pendiente"] = 0
            resultado["motivo"] = (
                motivo or "CSV duplicado detectado en pendientes o control"
            )
            resultado["estado"] = "descartado_csv_duplicado"
            return resultado

        current_app.logger.info(
            f"[UTILS_ASYNC] CSV {csv} NO existe todavía en pendientes ni en control; se continúa flujo normal."
        )

    # 5.8️⃣ Caso SIN CSV → para_revision
    if not csv:
        current_app.logger.info(
            f"[UTILS_ASYNC] PDF {nombre_pdf_core} sin CSV; se envía a para_revision (csv=NULL)."
        )

        id_pendiente = _insertar_pendiente_en_revision(
            nombre_pdf=nombre_pdf_core,
            datos=datos,
            motivo=motivo or "CSV no encontrado / no legible",
            csv=None,
            csv_retirada=csv_retirada or None,
            ruta_relativa="para_revision",
            estado_inicial="REVISION",
        )

        ruta_destino = _ruta_pdf("para_revision", nombre_pdf_core)
        try:
            shutil.move(ruta_inicial, ruta_destino)
            current_app.logger.info(
                f"[UTILS_ASYNC] PDF sin CSV movido a para_revision: {ruta_destino} (id_pendiente={id_pendiente})"
            )
        except Exception as e:
            current_app.logger.error(
                f"[UTILS_ASYNC] Error moviendo PDF sin CSV a para_revision: {e!r}"
            )

        resultado["ruta_final_pdf"] = ruta_destino
        resultado["id_pendiente"] = id_pendiente
        resultado["estado"] = "pendiente_validacion"
        return resultado

    # 5.9️⃣ CON CSV (no duplicado) → ruteo por estado
    nombre_pdf_csv = _nombre_pdf_por_csv(csv, nombre_pdf_core)

    # 5.9.a️⃣ auto_guardado → guardado inmediato en control, PDF a colocacion + evento agenda
    if estado == "auto_guardado":
        ruta_colocacion = _ruta_pdf("colocacion", nombre_pdf_csv)
        try:
            shutil.move(ruta_inicial, ruta_colocacion)
            ruta_final = ruta_colocacion
            current_app.logger.info(
                f"[UTILS_ASYNC] PDF auto-guardado y movido a colocacion: {ruta_colocacion}"
            )
        except Exception as e:
            current_app.logger.error(
                f"[UTILS_ASYNC] Error moviendo PDF a colocacion (auto_guardado): {e!r}"
            )
            ruta_final = ruta_inicial

        # 5.9.a.1️⃣ Crear evento en agenda con vigencia de 6 meses
        try:
            _crear_evento_agenda_contenedor(datos)
        except Exception as e:
            current_app.logger.error(
                f"[UTILS_ASYNC] Error creando evento de agenda para contenedor: {e!r}",
                exc_info=True,
            )

        resultado["ruta_final_pdf"] = ruta_final
        resultado["id_pendiente"] = None
        return resultado

    # 5.9.b️⃣ solo_retirada → solo_retirada (PDF de retirada sin colocación asociada)
    if estado == "solo_retirada":
        id_pendiente = _insertar_pendiente_en_revision(
            nombre_pdf=nombre_pdf_csv,
            datos=datos,
            motivo=motivo or "Retirada sin colocación asociada",
            csv=csv or None,
            csv_retirada=csv or None,  # usamos mismo CSV como csv_retirada
            ruta_relativa="solo_retirada",
            estado_inicial="REVISION",
        )

        ruta_destino = _ruta_pdf("solo_retirada", nombre_pdf_csv)
        try:
            shutil.move(ruta_inicial, ruta_destino)
            current_app.logger.info(
                f"[UTILS_ASYNC] PDF movido a solo_retirada: {ruta_destino} (id_pendiente={id_pendiente})"
            )
        except Exception as e:
            current_app.logger.error(
                f"[UTILS_ASYNC] Error moviendo PDF a solo_retirada: {e!r}"
            )

        resultado["ruta_final_pdf"] = ruta_destino
        resultado["id_pendiente"] = id_pendiente
        return resultado

    # 5.9.c️⃣ resto de casos con CSV → flujo normal a para_revision con <csv>.pdf
    id_pendiente = _insertar_pendiente_en_revision(
        nombre_pdf=nombre_pdf_csv,
        datos=datos,
        motivo=motivo or "Pendiente de revisión manual",
        csv=csv or None,
        csv_retirada=csv_retirada or None,
        ruta_relativa="para_revision",
        estado_inicial="REVISION",
    )

    ruta_destino = _ruta_pdf("para_revision", nombre_pdf_csv)
    try:
        shutil.move(ruta_inicial, ruta_destino)
        current_app.logger.info(
            f"[UTILS_ASYNC] PDF movido a para_revision: {ruta_destino} (id_pendiente={id_pendiente})"
        )
    except Exception as e:
        current_app.logger.error(
            f"[UTILS_ASYNC] Error moviendo PDF a para_revision: {e!r}"
        )

    resultado["ruta_final_pdf"] = ruta_destino
    resultado["id_pendiente"] = id_pendiente
    return resultado


# =============================================================================
# 5.9.a️⃣ BIS · CREAR EVENTO DE AGENDA PARA CONTENEDORES AUTO-GUARDADOS
# =============================================================================

def _crear_evento_agenda_contenedor(datos: Dict[str, Any]) -> None:
    """
    Crea un evento en la agenda de vía pública para un contenedor auto-guardado.

    DATOS ESPERADOS EN `datos`:
      - csv: código único del contenedor.
      - fecha_colocacion: fecha inicio (string dd/mm/yyyy).
      - lugar_ubicacion: descripción del lugar.
      - idtbl_calles: ID de la calle afectada (debe existir).
      - tamano_contenedor: descripción opcional.

    REGLAS:
      - fecha_inicio: fecha_colocacion parseada.
      - fecha_fin: fecha_inicio + ~6 meses (6*30 días).
      - all_day: True (ocupación todo el día).
      - codigo_tipo: 'CONTENEDORES' (debe existir en tbl_tipos_evento_via_publica).
      - origen_tabla: 'tbl_control_contenedores' (coherente con agenda_bp).
      - origen_id: csv del contenedor (puede cambiarse a idtbl_control_contenedores
                   cuando se sincronice totalmente con control).
      - descripción: incluye aviso de permanencia máxima de 6 meses.
    """
    try:
        csv = datos.get("csv")
        if not csv:
            current_app.logger.warning(
                "[AGENDA_CONTENEDORES] No se puede crear evento sin CSV"
            )
            return

        # Parsear fecha de colocación (dd/mm/yyyy)
        fecha_colocacion_str = datos.get("fecha_colocacion")
        if not fecha_colocacion_str:
            current_app.logger.warning(
                f"[AGENDA_CONTENEDORES] CSV {csv}: falta fecha_colocacion"
            )
            return

        try:
            fecha_inicio = datetime.strptime(fecha_colocacion_str, "%d/%m/%Y")
        except ValueError:
            current_app.logger.error(
                f"[AGENDA_CONTENEDORES] CSV {csv}: formato fecha_colocacion inválido: {fecha_colocacion_str}"
            )
            return

        # Fecha fin: ~6 meses después (aprox. 6*30 días)
        fecha_fin = fecha_inicio + timedelta(days=6 * 30)

        # Título del evento
        lugar = datos.get("lugar_ubicacion", "ubicación no especificada")
        tamano = datos.get("tamano_contenedor", "")
        titulo = f"Contenedor {csv}"
        if tamano:
            titulo += f" - {tamano}"

        # Descripción con regla de 6 meses
        descripcion = (
            f"Colocación de contenedor en {lugar}. "
            f"Este contenedor puede permanecer un máximo de 6 meses en la misma ubicación. "
            f"Revisar si transcurrido el plazo se ha retirado o movido."
        )

        # Crear evento en agenda
        id_agenda = crear_evento_agenda(
            codigo_tipo="CONTENEDORES",
            titulo=titulo,
            descripcion=descripcion,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            all_day=True,
            origen_tabla="tbl_control_contenedores",
            origen_id=csv,  # Usamos CSV como identificador (se puede cambiar a id_control)
        )

        current_app.logger.info(
            f"[AGENDA_CONTENEDORES] Evento creado: id_agenda={id_agenda}, CSV={csv}"
        )

        # Asociar calle afectada (si existe)
        idtbl_calles = datos.get("idtbl_calles")
        if idtbl_calles:
            añadir_calle_a_evento(
                id_agenda=id_agenda,
                id_calle=idtbl_calles,
                numero_via_desde=None,
                numero_via_hasta=None,
                sentido="AMBOS",
                observaciones=lugar,
            )
            current_app.logger.info(
                f"[AGENDA_CONTENEDORES] Calle {idtbl_calles} asociada al evento {id_agenda}"
            )
        else:
            current_app.logger.warning(
                f"[AGENDA_CONTENEDORES] CSV {csv}: no se pudo asociar calle (falta idtbl_calles)"
            )

    except Exception as e:
        current_app.logger.error(
            f"[AGENDA_CONTENEDORES] Error creando evento de agenda: {e!r}",
            exc_info=True,
        )


# =============================================================================
# 6️⃣ PASAR DE PARA_REVISION → PENDIENTES_VALIDACION (CONTENEDORES)
# =============================================================================

def pasar_a_pendientes(id_pendiente: int) -> bool:
    """
    6.1️⃣ Mueve un pendiente desde para_revision → pendientes_validacion
          y actualiza su estado en tbl_contenedores_pendientes.
    """
    _ensure_contenedores_dirs()

    rows = ejecutar_query(
        SQL_SELECT_PENDIENTE,
        (id_pendiente,),
        nombre_bd="control_via_publica",
    )

    if not rows:
        current_app.logger.error(
            f"[UTILS_ASYNC] pasar_a_pendientes: pendiente {id_pendiente} no encontrado"
        )
        return False

    pendiente = rows[0]
    nombre_pdf = pendiente["nombre_pdf"]
    ruta_pdf = pendiente["ruta_pdf"]
    estado = pendiente["estado"]

    if estado != "REVISION" or ruta_pdf != "para_revision":
        current_app.logger.warning(
            f"[UTILS_ASYNC] pasar_a_pendientes: pendiente {id_pendiente} no está en REVISION/para_revision "
            f"(estado={estado}, ruta_pdf={ruta_pdf})"
        )

    ruta_origen = _ruta_pdf("para_revision", nombre_pdf)
    ruta_destino = _ruta_pdf("pendientes_validacion", nombre_pdf)

    try:
        shutil.move(ruta_origen, ruta_destino)
        current_app.logger.info(
            f"[UTILS_ASYNC] PDF {nombre_pdf} movido a pendientes_validacion: {ruta_destino}"
        )
    except Exception as e:
        current_app.logger.error(
            f"[UTILS_ASYNC] Error moviendo PDF a pendientes_validacion: {e!r}"
        )
        return False

    ejecutar_non_query(
        SQL_UPDATE_A_PENDIENTE,
        (
            "pendientes_validacion",
            "PENDIENTE",
            id_pendiente,
        ),
        nombre_bd="control_via_publica",
    )

    return True


# =============================================================================
# 7️⃣ DESCARTAR PENDIENTE + BORRAR PDF (CONTENEDORES)
# =============================================================================

def descartar_pendiente(id_pendiente: int) -> bool:
    """
    7.1️⃣ Elimina un pendiente y borra su PDF físico (sea cual sea su carpeta actual).
    """
    _ensure_contenedores_dirs()

    rows = ejecutar_query(
        SQL_SELECT_PENDIENTE,
        (id_pendiente,),
        nombre_bd="control_via_publica",
    )

    if not rows:
        current_app.logger.error(
            f"[UTILS_ASYNC] descartar_pendiente: pendiente {id_pendiente} no encontrado"
        )
        return False

    pendiente = rows[0]
    nombre_pdf = pendiente["nombre_pdf"]
    ruta_pdf = pendiente["ruta_pdf"]

    ruta_archivo = _ruta_pdf(ruta_pdf, nombre_pdf)
    try:
        if os.path.exists(ruta_archivo):
            os.remove(ruta_archivo)
            current_app.logger.info(
                f"[UTILS_ASYNC] PDF eliminado: {ruta_archivo}"
            )
    except Exception as e:
        current_app.logger.error(
            f"[UTILS_ASYNC] Error eliminando PDF {ruta_archivo}: {e!r}"
        )

    ejecutar_non_query(
        """
        DELETE FROM tbl_contenedores_pendientes
        WHERE idtbl_contenedores_pendientes = %s
        """,
        (id_pendiente,),
        nombre_bd="control_via_publica",
    )

    return True


# =============================================================================
# 7️⃣ BIS · BANDEJA INICIAL (STUB) · CLASIFICACIÓN GENERAL
# =============================================================================

def procesar_pdf_inicial(nombre_pdf: str) -> dict:
    """
    Stub temporal para procesar un PDF en la carpeta inicial (bandeja general).

    FUTURO:
      - Extraer texto/metadatos.
      - Decidir si el PDF es de contenedores, obras, terrazas, vados, etc.
      - Renombrar/normalizar (ej. <csv>.pdf o <expediente>.pdf).
      - Mover a la carpeta entrada_pdf correspondiente del módulo.
      - (Opcional) Crear registros en una agenda global.
    """
    current_app.logger.info(
        f"[UTILS_ASYNC] procesar_pdf_inicial llamado con {nombre_pdf!r}, "
        "pero todavía no está implementado."
    )

    return {
        "estado": "pendiente",
        "motivo": "procesar_pdf_inicial no implementado todavía",
        "tipo": None,
        "ruta_final_pdf": None,
        "ruta_csv": None,
    }


# =============================================================================
# 7️⃣ TER · TERRAZAS (STUB)
# =============================================================================

def procesar_pdf_entrada_terrazas(nombre_pdf: str) -> dict:
    """
    Stub temporal para procesar un PDF en terrazas/entrada_pdf.

    FUTURO:
      - Extracción de datos específica de terrazas.
      - Generación de CSV o identificador único si aplica.
      - Creación de registros de pendientes/agenda.
      - Movimiento del PDF a la carpeta adecuada.
    """
    current_app.logger.info(
        f"[UTILS_ASYNC] procesar_pdf_entrada_terrazas llamado con {nombre_pdf!r}, "
        "pero todavía no está implementado."
    )

    return {
        "estado": "pendiente",
        "motivo": "procesar_pdf_entrada_terrazas no implementado todavía",
        "id_pendiente": None,
        "ruta_final_pdf": None,
    }


# =============================================================================
# 8️⃣ UTILS ASYNC · OBRAS
# =============================================================================
# Este bloque añade soporte básico para:
#   - Procesar PDFs de obras que llegan a obras/entrada_pdf.
#   - Extraer datos administrativos mediante un backend específico.
#   - Insertar un registro en tbl_obras con esos datos.
# =============================================================================

def _carpeta_obras_base() -> str:
    """
    8.1️⃣ Devuelve la carpeta base de obras dentro de la app:
          <root_path>/obras
    """
    return os.path.join(current_app.root_path, "obras")


def _ensure_obras_dirs() -> None:
    """
    8.2️⃣ Asegura que existe la subcarpeta entrada_pdf para obras.
    """
    base = _carpeta_obras_base()
    os.makedirs(os.path.join(base, "entrada_pdf"), exist_ok=True)


def _ruta_pdf_obras(subcarpeta: str, nombre_pdf: str) -> str:
    """
    8.3️⃣ Construye la ruta absoluta a un PDF de obras dado subcarpeta y nombre.
    """
    base = _carpeta_obras_base()
    return os.path.join(base, subcarpeta, nombre_pdf)


def procesar_pdf_entrada_obras(nombre_pdf: str) -> dict:
    """
    8.4️⃣ Procesa un PDF que llega a obras/entrada_pdf y crea un registro en tbl_obras.

    Flujo general:
      1) Verifica existencia del PDF en obras/entrada_pdf.
      2) Llama al backend procesar_pdf_core_obras para extraer datos.
      3) Completa campos necesarios (ruta_pdf_principal, fechas).
      4) Inserta un registro en tbl_obras.
      5) Devuelve dict con estado, motivo, id_obra y ruta_final_pdf.

    NOTA:
      - Este flujo NO aplica la lógica de CSV único de contenedores.
      - Si quieres evitar duplicar obras por numero_expediente o csv_documento,
        deberás añadir un chequeo similar al de contenedores.
    """
    _ensure_obras_dirs()

    # 8.4.1️⃣ Ruta del PDF en obras/entrada_pdf
    ruta_pdf = _ruta_pdf_obras("entrada_pdf", nombre_pdf)

    if not os.path.exists(ruta_pdf):
        current_app.logger.error(
            f"[UTILS_ASYNC_OBRAS] PDF no encontrado en obras/entrada_pdf: {ruta_pdf}"
        )
        return {
            "estado": "error",
            "motivo": "Archivo no encontrado en obras/entrada_pdf",
            "id_obra": None,
            "ruta_final_pdf": None,
        }

    # 8.4.2️⃣ Llamar al backend de OBRAS para extraer datos del PDF
    resultado_core = procesar_pdf_core_obras(ruta_pdf)
    estado_core = resultado_core.get("estado")
    motivo_core = resultado_core.get("motivo")
    datos = resultado_core.get("datos") or {}

    if estado_core != "ok":
        current_app.logger.error(
            f"[UTILS_ASYNC_OBRAS] Error en backend de obras: {motivo_core}"
        )
        return {
            "estado": "error",
            "motivo": motivo_core,
            "id_obra": None,
            "ruta_final_pdf": ruta_pdf,
        }

    # 8.4.3️⃣ Completar ruta_pdf_principal relativa a root_path
    datos["ruta_pdf_principal"] = os.path.relpath(ruta_pdf, current_app.root_path)

    # 8.4.4️⃣ Preparar campos para INSERT en tbl_obras
    numero_expediente   = datos.get("numero_expediente")
    tipo_expediente     = datos.get("tipo_expediente")
    ref_catastral       = datos.get("ref_catastral")
    solicitante_nombre  = datos.get("solicitante_nombre")
    solicitante_nif     = datos.get("solicitante_nif")
    representado_nombre = datos.get("representado_nombre")
    representado_nif    = datos.get("representado_nif")
    presupuesto         = datos.get("presupuesto")
    tasa                = datos.get("tasa")
    csv_documento       = datos.get("csv_documento")  # opcional, puede ser None
    ruta_pdf_principal  = datos.get("ruta_pdf_principal")
    # Por ahora, fecha_documento se deja como NULL (parseo pendiente)
    fecha_documento     = None
    estado_licencia     = datos.get("estado_licencia")

    # 8.4.5️⃣ INSERT en tbl_obras (añade más campos según se necesite)
    sql = """
        INSERT INTO tbl_obras (
            numero_expediente,
            tipo_expediente,
            ref_catastral,
            solicitante_nombre,
            solicitante_nif,
            representado_nombre,
            representado_nif,
            presupuesto,
            tasa,
            csv_documento,
            ruta_pdf_principal,
            fecha_documento,
            estado_licencia,
            fecha_obras_inicio,
            fecha_obras_fin,
            franja_horaria,
            requiere_contenedores
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s,
            NULL, NULL, NULL, 0
        )
    """

    ejecutar_non_query(
        sql,
        (
            numero_expediente,
            tipo_expediente,
            ref_catastral,
            solicitante_nombre,
            solicitante_nif,
            representado_nombre,
            representado_nif,
            presupuesto,
            tasa,
            csv_documento,
            ruta_pdf_principal,
            fecha_documento,
            estado_licencia,
        ),
        nombre_bd="control_via_publica",
    )

    row = ejecutar_query(
        "SELECT LAST_INSERT_ID() AS id",
        (),
        nombre_bd="control_via_publica",
    )[0]
    id_obra = row["id"]

    current_app.logger.info(
        f"[UTILS_ASYNC_OBRAS] Obra insertada en tbl_obras: id={id_obra}, expediente={numero_expediente}"
    )

    return {
        "estado": "insertado",
        "motivo": motivo_core or "Obra insertada correctamente",
        "id_obra": id_obra,
        "ruta_final_pdf": ruta_pdf,
    }