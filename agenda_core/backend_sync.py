# agenda_core/backend_sync.py
# =============================================================================
# 🔁 SINCRONIZACIÓN DE OBRAS CON LA AGENDA GENÉRICA
# =============================================================================
# Este módulo actúa como adaptador entre:
#   - La tabla tbl_obras (DR, LOME, LOMI, etc.)
#   - El backend genérico de agenda (agenda_core/backend_agenda.py)
#
# NO toca lógica de negocio de obras ni de agenda.
# Solo:
#   - Lee configuración en tbl_agenda_sync_config.
#   - Selecciona obras que deben sincronizarse.
#   - Llama a crear_evento_agenda / actualizar_evento_agenda / añadir_calle_a_evento.
#   - Actualiza idtbl_agenda y fecha_sync_agenda en tbl_obras.
# =============================================================================

from datetime import datetime
from typing import Any, Dict, List, Optional

from db import ejecutar_query, ejecutar_non_query

from agenda_core.backend_agenda import (
    crear_evento_agenda,
    actualizar_evento_agenda,
    añadir_calle_a_evento,
)

NOMBRE_BD = "control_via_publica"
ORIGEN_TABLA_OBRAS = "tbl_obras"


# -----------------------------------------------------------------------------
# Configuración
# -----------------------------------------------------------------------------
def obtener_config_sync(
    origen_tabla: str = ORIGEN_TABLA_OBRAS,
) -> Optional[Dict[str, Any]]:
    """
    Devuelve la configuración de sincronización para una tabla origen.
    Usa tbl_agenda_sync_config para no hardcodear nombres de campos.
    """
    sql = """
        SELECT *
        FROM tbl_agenda_sync_config
        WHERE origen_tabla = %s
          AND activo = 1
        LIMIT 1
    """
    filas = ejecutar_query(sql, (origen_tabla,), nombre_bd=NOMBRE_BD)
    return filas[0] if filas else None


# -----------------------------------------------------------------------------
# Selección de obras a sincronizar
# -----------------------------------------------------------------------------
def obtener_obras_pendientes_sync(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Devuelve las obras candidatas a sincronizar con la agenda.

    Criterios mínimos:
      - Tienen fecha de inicio (campo_fecha_inicio no nulo).
      - Opcionalmente, filtra por estado_licencia según valores_estado_incl.
    """
    campo_fecha_inicio = cfg["campo_fecha_inicio"]
    campo_estado = cfg.get("campo_estado")
    valores_estado_incl = cfg.get("valores_estado_incl")

    filtros = [f"{campo_fecha_inicio} IS NOT NULL"]
    params: List[Any] = []

    if campo_estado and valores_estado_incl:
        estados = [e.strip() for e in valores_estado_incl.split(",") if e.strip()]
        if estados:
            placeholders = ", ".join(["%s"] * len(estados))
            filtros.append(f"{campo_estado} IN ({placeholders})")
            params.extend(estados)

    where_clause = " AND ".join(filtros)

    sql = f"""
        SELECT *
        FROM {ORIGEN_TABLA_OBRAS}
        WHERE {where_clause}
    """

    return ejecutar_query(sql, tuple(params), nombre_bd=NOMBRE_BD)


# -----------------------------------------------------------------------------
# Construcción de datos para agenda
# -----------------------------------------------------------------------------
def construir_titulo_obra(obra: Dict[str, Any], cfg: Dict[str, Any]) -> str:
    """
    Construye el título del evento a partir de la obra.
    """
    numero_expediente = obra.get("numero_expediente") or ""
    tipo_de_obra = obra.get("tipo_de_obra") or ""
    partes = [p for p in [tipo_de_obra, numero_expediente] if p]
    return " - ".join(partes) if partes else "Obra"


def construir_descripcion_obra(obra: Dict[str, Any], cfg: Dict[str, Any]) -> str:
    """
    Construye la descripción del evento.

    De momento usamos observaciones; más adelante se puede enriquecer con
    solicitante, ref_catastral, etc.
    """
    observaciones = obra.get("observaciones") or ""
    return observaciones


def extraer_fechas_obra(obra: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Obtiene fecha_inicio y fecha_fin de la obra según los campos definidos
    en la configuración.
    """
    campo_fecha_inicio = cfg["campo_fecha_inicio"]
    campo_fecha_fin = cfg["campo_fecha_fin"]

    return {
        "fecha_inicio": obra.get(campo_fecha_inicio),
        "fecha_fin": obra.get(campo_fecha_fin),
    }


def obtener_id_calle_principal(obra: Dict[str, Any]) -> Optional[int]:
    """
    Devuelve el idtbl_calles principal de la obra (si lo hay).
    """
    return obra.get("idtbl_calles")


# -----------------------------------------------------------------------------
# Actualización de tbl_obras tras sync
# -----------------------------------------------------------------------------
def marcar_sync_obra(id_obra: int, id_agenda: Optional[int]) -> None:
    """
    Actualiza idtbl_agenda y fecha_sync_agenda en tbl_obras.
    """
    sql = """
        UPDATE tbl_obras
        SET idtbl_agenda = %s,
            fecha_sync_agenda = %s
        WHERE idtbl_obras = %s
    """
    params = (
        id_agenda,
        datetime.now(),
        id_obra,
    )
    ejecutar_non_query(sql, params, nombre_bd=NOMBRE_BD)


# -----------------------------------------------------------------------------
# Lógica principal de sync
# -----------------------------------------------------------------------------
def sincronizar_obras_con_agenda() -> Dict[str, Any]:
    """
    Punto de entrada principal de la sincronización de obras con la agenda.

    Flujo:
      1) Lee configuración de tbl_agenda_sync_config.
      2) Obtiene obras candidatas a sync.
      3) Para cada obra:
         - Si no tiene idtbl_agenda -> crear evento.
         - Si tiene idtbl_agenda -> actualizar evento.
      4) Actualiza idtbl_agenda y fecha_sync_agenda en tbl_obras.
    """
    cfg = obtener_config_sync(ORIGEN_TABLA_OBRAS)
    if not cfg:
        return {
            "ok": False,
            "mensaje": "No existe configuración activa de sync para tbl_obras",
            "creados": 0,
            "actualizados": 0,
        }

    obras = obtener_obras_pendientes_sync(cfg)
    creados = 0
    actualizados = 0

    for obra in obras:
        id_obra = obra.get("idtbl_obras")
        if not id_obra:
            continue

        id_agenda = obra.get(cfg.get("campo_id_agenda", "idtbl_agenda"))
        fechas = extraer_fechas_obra(obra, cfg)
        titulo = construir_titulo_obra(obra, cfg)
        descripcion = construir_descripcion_obra(obra, cfg)
        id_calle = obtener_id_calle_principal(obra)

        # Usamos el backend genérico de agenda
        if id_agenda:
            # Actualizar evento existente
            actualizar_evento_agenda(
                id_agenda=id_agenda,
                titulo=titulo,
                descripcion=descripcion,
                fecha_inicio=fechas["fecha_inicio"],
                fecha_fin=fechas["fecha_fin"],
                codigo_tipo_evento=cfg["codigo_tipo_evento"],
            )
            actualizados += 1
            marcar_sync_obra(id_obra, id_agenda)
        else:
            # Crear evento nuevo
            nuevo_id_agenda = crear_evento_agenda(
                titulo=titulo,
                descripcion=descripcion,
                fecha_inicio=fechas["fecha_inicio"],
                fecha_fin=fechas["fecha_fin"],
                codigo_tipo_evento=cfg["codigo_tipo_evento"],
                origen_tabla=ORIGEN_TABLA_OBRAS,
                origen_id=id_obra,
            )

            if nuevo_id_agenda:
                creados += 1
                marcar_sync_obra(id_obra, nuevo_id_agenda)

                # Asignar calle principal si existe
                if id_calle:
                    añadir_calle_a_evento(
                        id_agenda=nuevo_id_agenda,
                        id_calle=id_calle,
                        sentido="AMBOS",
                    )

    return {
        "ok": True,
        "mensaje": "Sincronización de obras con agenda completada",
        "creados": creados,
        "actualizados": actualizados,
    }
