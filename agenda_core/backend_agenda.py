# agenda_core/backend_agenda.py
# =============================================================================
# 📅 BACKEND AGENDA DE VÍA PÚBLICA
# =============================================================================
# 0️⃣ RESUMEN DEL MÓDULO
# -----------------------------------------------------------------------------
# Este módulo implementa la lógica GENÉRICA de agenda para todas las
# actividades que afectan a la vía pública. No sabe nada de negocio concreto
# (obras, contenedores, terrazas, mercados, etc.). Solo trabaja con:
#
#   - Códigos de tipo de evento (ej.: 'OBRA', 'CONTENEDOR', 'CARRERA').
#   - Identificadores de calles (idtbl_calles de bd_tbl_comunes.tbl_calles).
#   - Referencias genéricas al “origen” del evento (origen_tabla, origen_id).
#
# Se estructura en 8 bloques:
#
#   1️⃣ UTILIDADES INTERNAS               → Resolución de tipos, LAST_INSERT_ID.
#   2️⃣ CREAR EVENTO AGENDA               → Inserta en tbl_agenda_via_publica.
#   3️⃣ AÑADIR CALLES                     → Inserta en tbl_agenda_calles_afectadas.
#   4️⃣ CONSULTA POR CALLE                → Usa vw_agenda_via_publica_por_calle.
#   5️⃣ CONSULTA GENERAL                  → Agenda global por rango de fechas.
#   6️⃣ CONFIGURACIÓN DE SINCRONIZACIÓN   → (BD) Metadatos tabla→agenda.
#   7️⃣ SINCRONIZACIÓN CON TABLAS ORIGEN  → Batch genérico (ej. tbl_obras).
#   8️⃣ RECURRENCIAS CON RRULE            → Definición y expansión por periodo.
#
# Este diseño permite:
#   - Añadir nuevos tipos de eventos sin cambiar la lógica básica de agenda.
#   - Sincronizar automáticamente tablas de negocio con la agenda.
#   - Soportar eventos recurrentes (primer finde de septiembre, fechas fijas).
# =============================================================================

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from db import ejecutar_query, ejecutar_non_query


# =============================================================================
# 1️⃣ UTILIDADES INTERNAS (NO EXPUESTAS FUERA DEL MÓDULO)
# =============================================================================

def _obtener_id_tipo_evento(codigo_tipo: str) -> int:
    """
    Devuelve idtbl_tipos_evento_via_publica para un código lógico de evento.

    Parámetros:
      - codigo_tipo:
          Código lógico del tipo de evento (texto), tal y como está definido
          en tbl_tipos_evento_via_publica.codigo. Ejemplos típicos:
            * 'OBRA'
            * 'CONTENEDOR'
            * 'CARRERA_POPULAR'

    Comportamiento:
      - SELECT a tbl_tipos_evento_via_publica en control_via_publica.
      - Si no hay ninguna fila con ese código, lanza ValueError para
        detectar errores de programación (ej.: escribir 'OBRAS' en lugar
        de 'OBRA').

    Devuelve:
      - idtbl_tipos_evento (int).

    Lanza:
      - ValueError si el código no existe.
    """
    filas = ejecutar_query(
        """
        SELECT idtbl_tipos_evento
        FROM tbl_tipos_evento_via_publica
        WHERE codigo = %s
        """,
        (codigo_tipo,),
        nombre_bd="control_via_publica",
    )
    if not filas:
        raise ValueError(f"Tipo de evento desconocido: {codigo_tipo}")
    return filas[0]["idtbl_tipos_evento"]


def _last_insert_id() -> int:
    """
    Devuelve el último ID autoincrement generado en la conexión actual.

    Uso típico:
      - Se llama inmediatamente después de un INSERT en tbl_agenda_via_publica
        para recuperar el idtbl_agenda del evento recién creado.

    Notas:
      - En MySQL, LAST_INSERT_ID() es por conexión; ejecutar_non_query y
        ejecutar_query deben compartir contexto para que sea correcto.
    """
    fila = ejecutar_query(
        "SELECT LAST_INSERT_ID() AS id",
        (),
        nombre_bd="control_via_publica",
    )[0]
    return fila["id"]


# =============================================================================
# 2️⃣ CREAR EVENTO (SIN CALLES TODAVÍA)
# =============================================================================

def crear_evento_agenda(
    codigo_tipo: str,
    titulo: str,
    descripcion: Optional[str],
    fecha_inicio: datetime,
    fecha_fin: datetime,
    all_day: bool,
    origen_tabla: Optional[str],
    origen_id: Optional[int],
    idtbl_agenda_recurrencias: Optional[int] = None,
) -> int:
    """
    Crea un evento genérico de agenda en tbl_agenda_via_publica.

    2.1 Comportamiento:
      - Resuelve idtbl_tipos_evento a partir de codigo_tipo.
      - Inserta una fila en tbl_agenda_via_publica.
      - Devuelve idtbl_agenda.

    2.2 Campos clave en tbl_agenda_via_publica:
      - idtbl_tipos_evento      (FK a tbl_tipos_evento_via_publica).
      - titulo, descripcion.
      - fecha_inicio, fecha_fin.
      - all_day                 (0/1).
      - origen_tabla, origen_id.
      - (opcional) idtbl_agenda_recurrencias para vincular instancias
        generadas desde una regla recurrente.

    2.3 Parámetros:
      - codigo_tipo:
          Código lógico del tipo de evento:
            * 'OBRA'
            * 'CONTENEDOR'
            * 'CARRERA_POPULAR'
            * etc.

      - titulo:
          Título visible en la agenda.

      - descripcion:
          Texto opcional con detalles.

      - fecha_inicio / fecha_fin:
          Datetime de inicio/fin ya calculados según la lógica de negocio.

      - all_day:
          True si ocupa todo el día (se guarda como 1), False si no (0).

      - origen_tabla / origen_id:
          Referencia al expediente origen (ej.: 'tbl_obras', idtbl_obras).

      - idtbl_agenda_recurrencias:
          Opcional; si este evento es instancia de una regla recurrente,
          se guarda el idtbl_agenda_recurrencias correspondiente.

    2.4 Devuelve:
      - idtbl_agenda (int).
    """
    id_tipo = _obtener_id_tipo_evento(codigo_tipo)

    # Nota: es recomendable añadir la columna opcional idtbl_agenda_recurrencias
    # en tbl_agenda_via_publica:
    #
    #   ALTER TABLE tbl_agenda_via_publica
    #     ADD COLUMN idtbl_agenda_recurrencias INT NULL;
    #
    sql = """
        INSERT INTO tbl_agenda_via_publica (
            idtbl_tipos_evento,
            titulo,
            descripcion,
            fecha_inicio,
            fecha_fin,
            all_day,
            origen_tabla,
            origen_id,
            idtbl_agenda_recurrencias
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    ejecutar_non_query(
        sql,
        (
            id_tipo,
            titulo,
            descripcion,
            fecha_inicio,
            fecha_fin,
            1 if all_day else 0,
            origen_tabla,
            origen_id,
            idtbl_agenda_recurrencias,
        ),
        nombre_bd="control_via_publica",
    )

    return _last_insert_id()


# =============================================================================
# 3️⃣ AÑADIR CALLES A UN EVENTO
# =============================================================================

def añadir_calle_a_evento(
    id_agenda: int,
    id_calle: int,
    numero_via_desde: Optional[str] = None,
    numero_via_hasta: Optional[str] = None,
    sentido: Optional[str] = None,  # 'AMBOS', 'IDA', 'VUELTA'
    observaciones: Optional[str] = None,
) -> None:
    """
    Asocia una calle (y opcionalmente un tramo) a un evento de agenda.

    3.1 Inserta una fila en tbl_agenda_calles_afectadas:

      - idtbl_agenda          → id_agenda.
      - idtbl_calles          → id_calle.
      - numero_via_desde/hasta.
      - sentido.
      - observaciones.

    3.2 Uso típico:
      - Obras: una calle principal, tramo opcional.
      - Mercados/carreras: varias llamadas, una por cada calle del recorrido.
    """
    sql = """
        INSERT INTO tbl_agenda_calles_afectadas (
            idtbl_agenda,
            idtbl_calles,
            numero_via_desde,
            numero_via_hasta,
            sentido,
            observaciones
        ) VALUES (%s, %s, %s, %s, %s, %s)
    """

    ejecutar_non_query(
        sql,
        (
            id_agenda,
            id_calle,
            numero_via_desde,
            numero_via_hasta,
            sentido,
            observaciones,
        ),
        nombre_bd="control_via_publica",
    )


def añadir_varias_calles_a_evento(
    id_agenda: int,
    calles: List[Dict[str, Any]],
) -> None:
    """
    Atajo para asociar varias calles a un mismo evento.

    3.3 Parámetros:
      - id_agenda:
          idtbl_agenda.

      - calles:
          Lista de dicts con:
            {
              "id_calle": 123,              # obligatorio
              "numero_via_desde": "1",      # opcional
              "numero_via_hasta": "20",     # opcional
              "sentido": "AMBOS",           # opcional
              "observaciones": "Tramo X"    # opcional
            }
    """
    for c in calles:
        añadir_calle_a_evento(
            id_agenda=id_agenda,
            id_calle=c["id_calle"],
            numero_via_desde=c.get("numero_via_desde"),
            numero_via_hasta=c.get("numero_via_hasta"),
            sentido=c.get("sentido"),
            observaciones=c.get("observaciones"),
        )


# =============================================================================
# 4️⃣ CONSULTA · AGENDA POR CALLE (VW)
# =============================================================================

def obtener_agenda_por_calle(
    id_calle: int,
    fecha_desde: Optional[datetime] = None,
    fecha_hasta: Optional[datetime] = None,
    codigos_tipo: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Devuelve eventos de vw_agenda_via_publica_por_calle para una calle.

    4.1 Vista:
      - Une:
          * tbl_agenda_via_publica
          * tbl_agenda_calles_afectadas
          * bd_tbl_comunes.tbl_calles
          * bd_tbl_comunes.tbl_tipos_de_vias
      - Expone:
          * idtbl_calles, idtbl_tipos_de_vias, nombre_calle.
          * codigo_tipo_evento, nombre_tipo_evento, prioridad.
          * fecha_inicio, fecha_fin, all_day.
          * numero_via_desde/hasta, sentido, observaciones_tramo.
          * origen_tabla, origen_id.

    4.2 Filtros:
      - Siempre:
          idtbl_calles = %s
      - fecha_desde:
          fecha_fin >= fecha_desde
      - fecha_hasta:
          fecha_inicio <= fecha_hasta
      - codigos_tipo:
          codigo_tipo_evento IN (...)

    4.3 Orden:
      - ORDER BY fecha_inicio, prioridad DESC
    """
    params: List[Any] = [id_calle]
    filtros = ["idtbl_calles = %s"]

    if fecha_desde:
        filtros.append("fecha_fin >= %s")
        params.append(fecha_desde)

    if fecha_hasta:
        filtros.append("fecha_inicio <= %s")
        params.append(fecha_hasta)

    if codigos_tipo:
        placeholders = ", ".join(["%s"] * len(codigos_tipo))
        filtros.append(f"codigo_tipo_evento IN ({placeholders})")
        params.extend(codigos_tipo)

    where_clause = " AND ".join(filtros)

    sql = f"""
        SELECT *
        FROM vw_agenda_via_publica_por_calle
        WHERE {where_clause}
        ORDER BY fecha_inicio, prioridad DESC
    """

    filas = ejecutar_query(
        sql,
        tuple(params),
        nombre_bd="control_via_publica",
    )
    return filas


# =============================================================================
# 5️⃣ CONSULTA · AGENDA GENERAL (POR FECHA)
# =============================================================================

def obtener_agenda_general(
    fecha_desde: datetime,
    fecha_hasta: datetime,
    codigos_tipo: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Devuelve eventos que se solapan con [fecha_desde, fecha_hasta]
    para todas las calles, usando vw_agenda_via_publica_por_calle.

    5.1 Criterio de solape:
      - fecha_inicio < fecha_hasta
      - fecha_fin    >= fecha_desde

    5.2 Parámetros:
      - fecha_desde:
          Inicio del rango.
      - fecha_hasta:
          Fin del rango.
      - codigos_tipo:
          Lista de códigos para filtrar (ej. ['OBRA', 'CONTENEDOR']).

    5.3 Orden:
      - ORDER BY nombre_calle, fecha_inicio, prioridad DESC
    """
    params: List[Any] = [fecha_desde, fecha_hasta]
    filtros = [
        "fecha_inicio < %s",
        "fecha_fin    >= %s",
    ]

    if codigos_tipo:
        placeholders = ", ".join(["%s"] * len(codigos_tipo))
        filtros.append(f"codigo_tipo_evento IN ({placeholders})")
        params.extend(codigos_tipo)

    where_clause = " AND ".join(filtros)

    sql = f"""
        SELECT *
        FROM vw_agenda_via_publica_por_calle
        WHERE {where_clause}
        ORDER BY nombre_calle, fecha_inicio, prioridad DESC
    """

    filas = ejecutar_query(
        sql,
        tuple(params),
        nombre_bd="control_via_publica",
    )
    return filas


# =============================================================================
# 6️⃣ CONFIGURACIÓN DE SINCRONIZACIÓN (TABLA DE METADATOS)
# =============================================================================
# Tabla sugerida en control_via_publica (documentación):
#
#   CREATE TABLE tbl_agenda_sync_config (
#       idtbl_agenda_sync_config INT AUTO_INCREMENT PRIMARY KEY,
#       codigo_tipo_evento       VARCHAR(50) NOT NULL,  -- 'OBRA', 'CONTENEDOR'
#       tabla_origen             VARCHAR(100) NOT NULL, -- 'tbl_obras'
#       campo_id_origen          VARCHAR(100) NOT NULL, -- 'idtbl_obras'
#       campo_fecha_inicio       VARCHAR(100) NOT NULL, -- 'fecha_obras_inicio'
#       campo_fecha_fin          VARCHAR(100) NULL,     -- 'fecha_obras_fin'
#       campo_titulo             VARCHAR(100) NULL,     -- si hay campo directo
#       plantilla_titulo         VARCHAR(255) NULL,     -- 'Obra {numero_expediente}'
#       campo_descripcion        VARCHAR(100) NULL,
#       campo_id_calle           VARCHAR(100) NULL,
#       all_day_default          TINYINT(1) NOT NULL DEFAULT 1,
#       dias_fin_por_defecto     INT NULL,
#       activo                   TINYINT(1) NOT NULL DEFAULT 1
#   );
#
# Y en cada tabla de origen (ej. tbl_obras) es recomendable añadir:
#
#   ALTER TABLE tbl_obras
#     ADD COLUMN idtbl_agenda INT NULL,
#     ADD COLUMN fecha_sync_agenda DATETIME NULL;
#
# Con ello se evita crear eventos duplicados y se sabe si ya está sincronizado.


# =============================================================================
# 7️⃣ SINCRONIZACIÓN CON TABLAS ORIGEN (EJEMPLO OBRAS)
# =============================================================================

def sincronizar_agenda_para(codigo_tipo_evento: str) -> int:
    """
    Sincroniza eventos de agenda para un tipo concreto (ej. 'OBRA') usando
    tbl_agenda_sync_config y la tabla origen correspondiente.

    7.1 Flujo general:
      - Lee la configuración en tbl_agenda_sync_config.
      - Construye un SELECT dinámico sobre la tabla origen.
      - Para cada fila origen sin idtbl_agenda:
          * Calcula fecha_inicio, fecha_fin.
          * Construye título y descripción.
          * Crea evento de agenda.
          * Asocia calle si procede.
          * Actualiza idtbl_agenda y fecha_sync_agenda en la tabla origen.

    7.2 Devuelve:
      - Número de eventos creados.
    """
    cfgs = ejecutar_query(
        """
        SELECT *
        FROM tbl_agenda_sync_config
        WHERE codigo_tipo_evento = %s
          AND activo = 1
        """,
        (codigo_tipo_evento,),
        nombre_bd="control_via_publica",
    )
    if not cfgs:
        return 0

    cfg = cfgs[0]
    tabla_origen = cfg["tabla_origen"]
    campo_id = cfg["campo_id_origen"]
    campo_f_ini = cfg["campo_fecha_inicio"]
    campo_f_fin = cfg["campo_fecha_fin"]
    campo_titulo = cfg["campo_titulo"]
    plantilla_titulo = cfg["plantilla_titulo"]
    campo_desc = cfg["campo_descripcion"]
    campo_id_calle = cfg["campo_id_calle"]
    all_day_default = bool(cfg["all_day_default"])
    dias_fin_def = cfg["dias_fin_por_defecto"]

    sql_select = f"""
        SELECT *
        FROM {tabla_origen}
        WHERE idtbl_agenda IS NULL
    """

    filas = ejecutar_query(
        sql_select,
        (),
        nombre_bd="control_via_publica",
    )

    creados = 0

    for fila in filas:
        id_origen = fila[campo_id]

        # 7.3 Extraer fechas
        fecha_inicio = fila.get(campo_f_ini)
        fecha_fin = fila.get(campo_f_fin)

        if not fecha_inicio:
            # Si no hay fecha de inicio, no tiene sentido agendar
            continue

        if not fecha_fin:
            if dias_fin_def is not None:
                fecha_fin = fecha_inicio + timedelta(days=dias_fin_def)
            else:
                fecha_fin = fecha_inicio

        # 7.4 Construir título
        if campo_titulo and campo_titulo in fila:
            titulo = str(fila[campo_titulo]) if fila[campo_titulo] is not None else ""
        elif plantilla_titulo:
            titulo = plantilla_titulo.format(**fila)
        else:
            titulo = codigo_tipo_evento

        # 7.5 Descripción
        descripcion = None
        if campo_desc and campo_desc in fila and fila[campo_desc] is not None:
            descripcion = str(fila[campo_desc])

        # 7.6 Crear evento genérico
        id_agenda = crear_evento_agenda(
            codigo_tipo=codigo_tipo_evento,
            titulo=titulo,
            descripcion=descripcion,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            all_day=all_day_default,
            origen_tabla=tabla_origen,
            origen_id=id_origen,
        )

        # 7.7 Asociar calle opcionalmente
        if campo_id_calle and campo_id_calle in fila and fila[campo_id_calle] is not None:
            añadir_calle_a_evento(
                id_agenda=id_agenda,
                id_calle=fila[campo_id_calle],
                sentido="AMBOS",
            )

        # 7.8 Marcar sincronizado en tabla origen
        sql_update = f"""
            UPDATE {tabla_origen}
            SET idtbl_agenda = %s,
                fecha_sync_agenda = NOW()
            WHERE {campo_id} = %s
        """

        ejecutar_non_query(
            sql_update,
            (id_agenda, id_origen),
            nombre_bd="control_via_publica",
        )

        creados += 1

    return creados


# =============================================================================
# 8️⃣ RECURRENCIAS CON RRULE (python-dateutil)
# =============================================================================
# Uso de la librería python-dateutil.rrule para estándares iCalendar. [web:31]
#
# Ejemplos de RRULE:
#   - "Cada año el 15 de agosto":
#       RRULE:FREQ=YEARLY;BYMONTH=8;BYMONTHDAY=15
#
#   - "Primer fin de semana de septiembre":
#       RRULE:FREQ=YEARLY;BYMONTH=9;BYDAY=SA,SU;BYSETPOS=1
#
#   - "Cada lunes del año":
#       RRULE:FREQ=WEEKLY;BYDAY=MO
#
#   - "Cada 2 semanas los lunes, 10 veces":
#       RRULE:FREQ=WEEKLY;INTERVAL=2;BYDAY=MO;COUNT=10
#
#   - "Último día de cada mes durante 12 meses":
#       RRULE:FREQ=MONTHLY;BYMONTHDAY=-1;COUNT=12
#
# Tabla (ya existente) en control_via_publica:
#
#   tbl_agenda_recurrencias:
#       idtbl_agenda_recurrencias INT PK
#       idtbl_tipos_evento_via_publica INT NOT NULL
#       titulo_base               VARCHAR(255) NOT NULL
#       descripcion_base          VARCHAR(255) NULL
#       origen_tabla              VARCHAR(100) NULL
#       origen_id                 INT NULL
#       rrule                     TEXT NOT NULL
#       duracion_dias             INT NOT NULL DEFAULT 1
#       all_day_default           TINYINT(1) NOT NULL DEFAULT 1
#       idtbl_calles              INT NULL
#       creado_en                 DATETIME NOT NULL
#       actualizado_en            DATETIME NOT NULL
#       activo                    TINYINT(1) NOT NULL DEFAULT 1

from dateutil.rrule import rrulestr


def generar_instancias_recurrentes(
    fecha_desde: datetime,
    fecha_hasta: datetime,
) -> int:
    """
    Genera instancias de eventos recurrentes en tbl_agenda_via_publica
    para el rango [fecha_desde, fecha_hasta], usando RRULE de python-dateutil.

    8.1 Flujo:
      - Lee tbl_agenda_recurrencias (activo = 1).
      - Para cada recurrencia:
          * Parsea rrule con rrulestr().
          * Genera todas las fechas en el rango
            (rule.between(fecha_desde, fecha_hasta)).
          * Para cada fecha:
              - Crea evento en tbl_agenda_via_publica:
                  · tipo de evento (por idtbl_tipos_evento_via_publica).
                  · titulo_base, descripcion_base.
                  · origen_tabla/origen_id → opcional.
                  · idtbl_agenda_recurrencias → vínculo a la regla.
              - Asocia calle (idtbl_calles) si se ha definido.
      - Devuelve número de instancias creadas.

    8.2 Uso recomendado:
      - Tarea batch (cron/CLI) que genere instancias para:
          · El año actual.
          · El rango visible en la agenda.
      - Se puede llamar desde agenda_bp antes de cargar la agenda si
        quieres asegurar que las recurrencias están materializadas.
    """
    recurrencias = ejecutar_query(
        """
        SELECT
            idtbl_agenda_recurrencias,
            idtbl_tipos_evento_via_publica,
            titulo_base,
            descripcion_base,
            origen_tabla,
            origen_id,
            rrule,
            duracion_dias,
            all_day_default,
            idtbl_calles
        FROM tbl_agenda_recurrencias
        WHERE activo = 1
        """,
        (),
        nombre_bd="control_via_publica",
    )

    creados = 0

    for rec in recurrencias:
        id_rec = rec["idtbl_agenda_recurrencias"]
        id_tipo_evento = rec["idtbl_tipos_evento_via_publica"]
        titulo_base = rec["titulo_base"]
        descripcion_base = rec.get("descripcion_base")
        origen_tabla = rec.get("origen_tabla")
        origen_id = rec.get("origen_id")
        rrule_str = rec["rrule"]
        duracion_dias = rec["duracion_dias"]
        all_day_default = bool(rec["all_day_default"])
        id_calle = rec.get("idtbl_calles")

        # 8.3 Parsear RRULE
        try:
            rrule_full = f"DTSTART:20200101T000000Z\n{rrule_str}"
            rule = rrulestr(rrule_full)
        except Exception:
            continue

        # 8.4 Generar ocurrencias en el rango
        try:
            fechas_inicio = list(
                rule.between(fecha_desde, fecha_hasta, inc=True)
            )
        except Exception:
            continue

        for f_ini in fechas_inicio:
            if f_ini.tzinfo is not None:
                f_ini = f_ini.replace(tzinfo=None)

            f_fin = f_ini + timedelta(days=duracion_dias - 1)

            # Nota: aquí no usamos codigo_tipo, sino directamente id_tipo_evento.
            # Podemos insertar “a mano” el id en tbl_agenda_via_publica.
            sql_insert = """
                INSERT INTO tbl_agenda_via_publica (
                    idtbl_tipos_evento,
                    titulo,
                    descripcion,
                    fecha_inicio,
                    fecha_fin,
                    all_day,
                    origen_tabla,
                    origen_id,
                    idtbl_agenda_recurrencias
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            ejecutar_non_query(
                sql_insert,
                (
                    id_tipo_evento,
                    titulo_base,
                    descripcion_base,
                    f_ini,
                    f_fin,
                    1 if all_day_default else 0,
                    origen_tabla,
                    origen_id,
                    id_rec,
                ),
                nombre_bd="control_via_publica",
            )

            id_agenda = _last_insert_id()

            if id_calle:
                añadir_calle_a_evento(
                    id_agenda=id_agenda,
                    id_calle=id_calle,
                    sentido="AMBOS",
                )

            creados += 1

    return creados
# =============================================================================
# 9️⃣ UTILIDADES ESPECÍFICAS · CONTENEDORES
# =============================================================================
# Helpers para trabajar con eventos de tipo CONTENEDORES a partir de
# tbl_control_contenedores, usando siempre idtbl_contenedor como origen_id.
# =============================================================================

def cerrar_evento_contenedor_por_id(
    idtbl_contenedor: int,
    fecha_retirada: Optional[datetime] = None,
) -> None:
    """
    Cierra el evento de agenda asociado a una colocación de contenedor.

    Convención:
      - Los eventos se crean con:
          codigo_tipo  = 'CONTENEDORES'
          origen_tabla = 'tbl_control_contenedores'
          origen_id    = idtbl_contenedor (colocación)

    Comportamiento:
      - Busca el último evento ACTIVO/PENDIENTE para ese origen_id.
      - Marca su estado como 'CERRADO'.
      - Si se pasa fecha_retirada, la guarda como fecha_fin_real.
    """
    if not idtbl_contenedor:
        return

    filas = ejecutar_query(
        """
        SELECT a.idtbl_agenda
        FROM tbl_agenda_via_publica a
        JOIN tbl_tipos_evento_via_publica t
              ON t.idtbl_tipos_evento = a.idtbl_tipos_evento
        WHERE t.codigo = 'CONTENEDORES'
          AND a.origen_tabla = 'tbl_control_contenedores'
          AND a.origen_id = %s
          AND (a.estado IS NULL OR a.estado IN ('ACTIVO', 'PENDIENTE'))
        ORDER BY a.fecha_inicio DESC
        LIMIT 1
        """,
        (idtbl_contenedor,),
        nombre_bd="control_via_publica",
    )

    if not filas:
        return

    id_agenda = filas[0]["idtbl_agenda"]

    if fecha_retirada is not None:
        sql_update = """
            UPDATE tbl_agenda_via_publica
            SET estado = 'CERRADO',
                fecha_fin_real = %s
            WHERE idtbl_agenda = %s
        """
        params = (fecha_retirada, id_agenda)
    else:
        sql_update = """
            UPDATE tbl_agenda_via_publica
            SET estado = 'CERRADO'
            WHERE idtbl_agenda = %s
        """
        params = (id_agenda,)

    ejecutar_non_query(
        sql_update,
        params,
        nombre_bd="control_via_publica",
    )