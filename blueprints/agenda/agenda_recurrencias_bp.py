# -*- coding: utf-8 -*-
from __future__ import annotations

from flask import Blueprint, render_template, request, redirect, url_for, flash
from services.helpers import login_required, rol_required
from db import ejecutar_query, ejecutar_non_query

# ============================================================================
# BLUEPRINT DE RECURRENCIAS DE AGENDA
# ============================================================================
# Propósito: Sistema completo de CRUD para gestionar recurrencias de eventos 
#            en agenda municipal de vía pública (terrazas, vados, contenedores, etc.)
# URL Prefix: /agenda/recurrencias
# Acceso: Solo usuarios con rol "gestor" o "super_admin"
# DB: Base de datos "agenda" (MySQL)
# Patrón: Soft delete usando campo 'activo' (1=activo, 0=desactivado)
# ============================================================================

agenda_recurrencias_bp = Blueprint(
    "agenda_recurrencias_bp",
    __name__,
    url_prefix="/agenda/recurrencias",
)

# ============================================================================
# 1. HELPERS SQL (Funciones de bajo nivel para acceso a datos)
# ============================================================================
# Separación de responsabilidades: SQL aislado de las vistas Flask
# Todas usan la BD "agenda" y los helpers de db.py

def _ar_listar_recurrencias():
    """
    Lista todas las recurrencias (con info básica de tipo de evento y calle).
    
    Returns:
        list: Lista de diccionarios con cada recurrencia y sus datos relacionados.
    
    Campos devueltos:
        - idtbl_agenda_recurrencias: PK único
        - idtbl_tipos_evento_via_publica: FK tipo de evento
        - titulo_base, descripcion_base: Texto del evento
        - origen_tabla, origen_id: Referencia al evento origen (si existe)
        - rrule: Regla de repetición (ex: FREQ=WEEKLY;DAY=MON)
        - duracion_dias: Duración en días
        - all_day_default: 1=todo el día, 0=con hora específica
        - idtbl_calles: FK calle
        - creado_en, actualizado_en: Timestamps
        - activo: 1=activo, 0=desactivado (soft delete)
        - tipo_evento: DESCRIPCIÓN del tipo (JOIN)
        - nombre_calle: Nombre de la calle (JOIN)
    """
    sql = """
        SELECT
            r.idtbl_agenda_recurrencias,
            r.idtbl_tipos_evento_via_publica,
            r.titulo_base,
            r.descripcion_base,
            r.origen_tabla,
            r.origen_id,
            r.rrule,
            r.duracion_dias,
            r.all_day_default,
            r.idtbl_calles,
            r.creado_en,
            r.actualizado_en,
            r.activo,
            tev.descripcion AS tipo_evento,
            c.Nombre_Calle  AS nombre_calle
        FROM tbl_agenda_recurrencias AS r
        LEFT JOIN tbl_tipos_evento_via_publica AS tev
            ON r.idtbl_tipos_evento_via_publica = tev.idtbl_tipos_evento_via_publica
        LEFT JOIN tbl_calles AS c
            ON r.idtbl_calles = c.idtbl_calles
        ORDER BY r.creado_en DESC
    """
    return ejecutar_query(sql, nombre_bd="agenda")


def _ar_obtener_recurrencia(id_recurrencia: int):
    """
    Obtiene una recurrencia concreta por ID.
    
    Args:
        id_recurrencia: ID único de la recurrencia (PK).
    
    Returns:
        dict|None: Diccionario con la recurrencia o None si no existe.
    """
    sql = """
        SELECT
            r.idtbl_agenda_recurrencias,
            r.idtbl_tipos_evento_via_publica,
            r.titulo_base,
            r.descripcion_base,
            r.origen_tabla,
            r.origen_id,
            r.rrule,
            r.duracion_dias,
            r.all_day_default,
            r.idtbl_calles,
            r.creado_en,
            r.actualizado_en,
            r.activo,
            tev.descripcion AS tipo_evento,
            c.Nombre_Calle  AS nombre_calle
        FROM tbl_agenda_recurrencias AS r
        LEFT JOIN tbl_tipos_evento_via_publica AS tev
            ON r.idtbl_tipos_evento_via_publica = tev.idtbl_tipos_evento_via_publica
        LEFT JOIN tbl_calles AS c
            ON r.idtbl_calles = c.idtbl_calles
        WHERE r.idtbl_agenda_recurrencias = %(id)s
    """
    filas = ejecutar_query(
        sql,
        params={"id": id_recurrencia},
        nombre_bd="agenda",
    )
    return filas[0] if filas else None


def _ar_insertar_recurrencia(datos: dict) -> None:
    """
    Inserta una nueva recurrencia en tbl_agenda_recurrencias.
    
    Args:
        datos: Diccionario con los campos:
            - idtbl_tipos_evento_via_publica: FK tipo de evento
            - titulo_base: Título del evento recurrente
            - descripcion_base: Descripción del evento
            - origen_tabla: Nombre de tabla origen (opcional)
            - origen_id: ID en tabla origen (opcional)
            - rrule: Regla RRULE de repetición
            - duracion_dias: Duración en días (0 si no aplica)
            - all_day_default: 1=todo el día, 0=con hora
            - idtbl_calles: FK calle
            - activo: 1=activo por defecto
    
    Notas:
        - creado_en y actualizado_en se ponen automáticamente con NOW()
        - No devuelve valor (inserta directamente)
    """
    sql = """
        INSERT INTO tbl_agenda_recurrencias (
            idtbl_tipos_evento_via_publica,
            titulo_base,
            descripcion_base,
            origen_tabla,
            origen_id,
            rrule,
            duracion_dias,
            all_day_default,
            idtbl_calles,
            creado_en,
            actualizado_en,
            activo
        )
        VALUES (
            %(idtbl_tipos_evento_via_publica)s,
            %(titulo_base)s,
            %(descripcion_base)s,
            %(origen_tabla)s,
            %(origen_id)s,
            %(rrule)s,
            %(duracion_dias)s,
            %(all_day_default)s,
            %(idtbl_calles)s,
            NOW(),
            NOW(),
            %(activo)s
        )
    """
    ejecutar_non_query(sql, datos, "agenda")


def _ar_actualizar_recurrencia(id_recurrencia: int, datos: dict) -> None:
    """
    Actualiza una recurrencia existente en tbl_agenda_recurrencias.
    
    Args:
        id_recurrencia: ID de la recurrencia a actualizar (PK).
        datos: Diccionario con los campos a actualizar (mêmes que en insert, excepto PK).
    
    Notas:
        - actualizado_en se renueva automáticamente con NOW()
        - creado_en NO se modifica
        - El ID se añade automáticamente al diccionario datos como %(id)s
    """
    sql = """
        UPDATE tbl_agenda_recurrencias SET
            idtbl_tipos_evento_via_publica = %(idtbl_tipos_evento_via_publica)s,
            titulo_base                    = %(titulo_base)s,
            descripcion_base               = %(descripcion_base)s,
            origen_tabla                   = %(origen_tabla)s,
            origen_id                      = %(origen_id)s,
            rrule                          = %(rrule)s,
            duracion_dias                  = %(duracion_dias)s,
            all_day_default                = %(all_day_default)s,
            idtbl_calles                   = %(idtbl_calles)s,
            actualizado_en                 = NOW(),
            activo                         = %(activo)s
        WHERE idtbl_agenda_recurrencias = %(id)s
    """
    datos["id"] = id_recurrencia
    ejecutar_non_query(sql, datos, "agenda")


def _ar_cambiar_activo(id_recurrencia: int, activo: int) -> None:
    """
    Activa/desactiva una recurrencia (soft delete).
    
    Args:
        id_recurrencia: ID de la recurrencia (PK).
        activo: 1=activar, 0=desactivar.
    
    Notas:
        - NO elimina el registro, solo cambia campo 'activo'
        - actualizado_en se renueva con NOW()
        - Patrón de soft delete para mantener histórico
    """
    sql = """
        UPDATE tbl_agenda_recurrencias
        SET activo = %(activo)s, actualizado_en = NOW()
        WHERE idtbl_agenda_recurrencias = %(id)s
    """
    ejecutar_non_query(
        sql,
        {"id": id_recurrencia, "activo": activo},
        "agenda",
    )


def _ar_listar_tipos_evento():
    """
    Lista tipos de evento de vía pública (para selects en formularios).
    
    Returns:
        list: Lista de diccionarios con:
            - idtbl_tipos_evento_via_publica: PK
            - descripcion: Nombre del tipo (ex: "Terraza", "Vado", "Contenedor")
    
    Orden: Alphabetico por descripcion.
    """
    sql = """
        SELECT
            idtbl_tipos_evento_via_publica,
            descripcion
        FROM tbl_tipos_evento_via_publica
        ORDER BY descripcion
    """
    return ejecutar_query(sql, nombre_bd="agenda")


def _ar_listar_calles():
    """
    Lista calles disponibles (para selects en formularios).
    
    Returns:
        list: Lista de diccionarios con:
            - idtbl_calles: PK
            - Nombre_Calle: Nombre de la calle
    
    Orden: Alphabetico por Nombre_Calle.
    """
    sql = """
        SELECT
            idtbl_calles,
            Nombre_Calle
        FROM tbl_calles
        ORDER BY Nombre_Calle
    """
    return ejecutar_query(sql, nombre_bd="agenda")


# ============================================================================
# 2. VISTAS (Routes del Blueprint)
# ============================================================================
# Cada route tiene:
# - Decoradores: @login_required + @rol_required("gestor", "super_admin")
# - HTTP methods: GET (ver) / POST (procesar)
# - Flash messages: feedback al usuario (success/error)
# - Redirección: siempre al listado después de CRUD

# 2.1 Listado de todas las recurrencias
# ----------------------------------------------------------------------------

@agenda_recurrencias_bp.route("/", methods=["GET"])
@login_required
@rol_required("gestor", "super_admin")
def ar_listar_recurrencias():
    """
    Route: / (GET)
    Función: Listar todas las recurrencias activas/inactivas.
    
    Template: agenda/recurrencias/agenda_recurrencias_listar.html
    Variables:
        - recurrencias: Lista de diccionarios con cada recurrencia + datos relacionados.
    """
    recurrencias = _ar_listar_recurrencias()
    return render_template(
        "agenda/recurrencias/agenda_recurrencias_listar.html",
        recurrencias=recurrencias,
    )


# 2.2 Crear nueva recurrencia
# ----------------------------------------------------------------------------

@agenda_recurrencias_bp.route("/nuevo", methods=["GET", "POST"])
@login_required
@rol_required("gestor", "super_admin")
def ar_nueva_recurrencia():
    """
    Route: /nuevo (GET | POST)
    Función: Crear una nueva recurrencia.
    
    GET:
        - Muestra formulario con selects de tipos_evento y calles.
        - Template: agenda/recurrencias/agenda_recurrencias_form.html
        - Variables:
            - modo: "crear"
            - tipos_evento: Lista de tipos de evento
            - calles: Lista de calles
            - recurrencia: None (no hay dato previo)
    
    POST:
        - Procesar datos del formulario.
        - Validación: Conversión de duracion_dias y all_day_default a int.
        - Inserta en DB con _ar_insertar_recurrencia().
        - Flash: "Recurrencia creada correctamente." (success)
        - Redirige al listado.
    
    Campos del formulario:
        - idtbl_tipos_evento_via_publica: FK tipo de evento
        - titulo_base: Título
        - descripcion_base: Descripción
        - origen_tabla: Tabla origen (opcional)
        - origen_id: ID origen (opcional)
        - rrule: Regla RRULE
        - duracion_dias: Duración (default 0)
        - all_day_default: Todo el día (default 0)
        - idtbl_calles: FK calle
        - activo: 1 por defecto (activo)
    """
    if request.method == "POST":
        datos = {
            "idtbl_tipos_evento_via_publica": request.form.get("idtbl_tipos_evento_via_publica"),
            "titulo_base": request.form.get("titulo_base"),
            "descripcion_base": request.form.get("descripcion_base"),
            "origen_tabla": request.form.get("origen_tabla"),
            "origen_id": request.form.get("origen_id"),
            "rrule": request.form.get("rrule"),
            "duracion_dias": int(request.form.get("duracion_dias") or 0),
            "all_day_default": int(request.form.get("all_day_default") or 0),
            "idtbl_calles": request.form.get("idtbl_calles"),
            "activo": int(request.form.get("activo", 1)),
        }

        _ar_insertar_recurrencia(datos)
        flash("Recurrencia creada correctamente.", "success")
        return redirect(url_for("agenda_recurrencias_bp.ar_listar_recurrencias"))

    tipos_evento = _ar_listar_tipos_evento()
    calles = _ar_listar_calles()

    return render_template(
        "agenda/recurrencias/agenda_recurrencias_form.html",
        modo="crear",
        tipos_evento=tipos_evento,
        calles=calles,
        recurrencia=None,
    )


# 2.3 Editar recurrencia existente
# ----------------------------------------------------------------------------

@agenda_recurrencias_bp.route("/<int:id_recurrencia>/editar", methods=["GET", "POST"])
@login_required
@rol_required("gestor", "super_admin")
def ar_editar_recurrencia(id_recurrencia: int):
    """
    Route: /<id_recurrencia>/editar (GET | POST)
    Función: Editar una recurrencia existente.
    
    GET:
        - Obtiene recurrencia por ID con _ar_obtener_recurrencia().
        - Si no existe: Flash "Recurrencia no encontrada." + redirige al listado.
        - Muestra formulario con datos pre-cargados.
        - Template: agenda/recurrencias/agenda_recurrencias_form.html
        - Variables:
            - modo: "editar"
            - recurrencia: Diccionario con datos de la recurrencia
            - tipos_evento: Lista de tipos (para select)
            - calles: Lista de calles (para select)
    
    POST:
        - Procesar datos actualizados del formulario.
        - Same validación que en creación (int conversion).
        - Actualiza en DB con _ar_actualizar_recurrencia().
        - Flash: "Recurrencia actualizada correctamente." (success)
        - Redirige al listado.
    
    Parámetros:
        - id_recurrencia: PK de la recurrencia a editar (extraído de la URL).
    """
    recurrencia = _ar_obtener_recurrencia(id_recurrencia)
    if not recurrencia:
        flash("Recurrencia no encontrada.", "error")
        return redirect(url_for("agenda_recurrencias_bp.ar_listar_recurrencias"))

    if request.method == "POST":
        datos = {
            "idtbl_tipos_evento_via_publica": request.form.get("idtbl_tipos_evento_via_publica"),
            "titulo_base": request.form.get("titulo_base"),
            "descripcion_base": request.form.get("descripcion_base"),
            "origen_tabla": request.form.get("origen_tabla"),
            "origen_id": request.form.get("origen_id"),
            "rrule": request.form.get("rrule"),
            "duracion_dias": int(request.form.get("duracion_dias") or 0),
            "all_day_default": int(request.form.get("all_day_default") or 0),
            "idtbl_calles": request.form.get("idtbl_calles"),
            "activo": int(request.form.get("activo", 1)),
        }

        _ar_actualizar_recurrencia(id_recurrencia, datos)
        flash("Recurrencia actualizada correctamente.", "success")
        return redirect(url_for("agenda_recurrencias_bp.ar_listar_recurrencias"))

    tipos_evento = _ar_listar_tipos_evento()
    calles = _ar_listar_calles()

    return render_template(
        "agenda/recurrencias/agenda_recurrencias_form.html",
        modo="editar",
        recurrencia=recurrencia,
        tipos_evento=tipos_evento,
        calles=calles,
    )


# 2.4 Activar / desactivar (soft delete)
# ----------------------------------------------------------------------------

@agenda_recurrencias_bp.route(
    "/<int:id_recurrencia>/toggle-activo",
    methods=["POST"],
)
@login_required
@rol_required("gestor", "super_admin")
def ar_toggle_activo(id_recurrencia: int):
    """
    Route: /<id_recurrencia>/toggle-activo (POST)
    Función: Activar o desactivar una recurrencia (soft delete).
    
    POST:
        - Obtiene recurrencia por ID.
        - Si no existe: Flash "Recurrencia no encontrada." + redirige.
        - Calcula nuevo_estado: 0 si estaba activo, 1 si estaba desactivado.
        - Actualiza con _ar_cambiar_activo().
        - Flash message:
            - "Recurrencia desactivada." si nuevo_estado == 0
            - "Recurrencia activada." si nuevo_estado == 1
        - Redirige al listado.
    
    Parámetros:
        - id_recurrencia: PK de la recurrencia (de la URL).
    
    Notas:
        - Solo POST (no se puede acceder por GET).
        - Toggle automático: invierte el estado actual.
    """
    recurrencia = _ar_obtener_recurrencia(id_recurrencia)
    if not recurrencia:
        flash("Recurrencia no encontrada.", "error")
        return redirect(url_for("agenda_recurrencias_bp.ar_listar_recurrencias"))

    nuevo_estado = 0 if recurrencia["activo"] else 1
    _ar_cambiar_activo(id_recurrencia, nuevo_estado)

    msg = "Recurrencia desactivada." if nuevo_estado == 0 else "Recurrencia activada."
    flash(msg, "success")

    return redirect(url_for("agenda_recurrencias_bp.ar_listar_recurrencias"))