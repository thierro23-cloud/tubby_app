# =============================================================================
# 🚀 SUPER ADMIN · DISCOVERY POR CONVENCIÓN + AUDITORÍA + ESTADÍSTICAS
# =============================================================================
# RESPONSABILIDADES:
#   1️⃣ Descubrir automáticamente paneles, módulos y botones por convención
#       de nombres de blueprints y endpoints.
#   2️⃣ Mostrar un resumen profesional de auditoría en la cabecera:
#       - Intentos de login últimos 7 días (totales, correctos, fallidos).
#       - Gestores activos en los últimos 30 días.
#       - Último login del super_admin actual.
#   3️⃣ Mostrar actividad reciente (últimos eventos de audit_log).
#   4️⃣ Mostrar estadísticas contextuales según el módulo seleccionado:
#       - Contenedores (instalados, retirados, totales, por año).
#       - Parquin Río Torio (plazas libres/ocupadas).
#   5️⃣ Preparar iconografía de contenedores y camiones:
#       - Contenedor verde (instalado).
#       - Contenedor azul (retirado).
#       - Camión rojo (plaza ocupada).
#       - Camión verde (plaza libre).
#       - Camión azul (ocupada especial) → pendiente de icono físico.
# =============================================================================

from flask import (
    Blueprint,
    request,
    render_template,
    current_app,
    session,
    url_for,
    redirect,
    flash,
)
from flask_login import login_required, current_user

from db import ejecutar_query, get_connection
from tools.utils import obtener_todos_los_endpoints



# =============================================================================
# 1️⃣ BLUEPRINT DEL SUPER ADMIN
# =============================================================================

super_admin_bp = Blueprint(
    "super_admin_bp",
    __name__,
    url_prefix="/super_admin",
)


# =============================================================================
# 2️⃣ SERVICIO · SUPER ADMIN DISCOVERY POR CONVENCIÓN
# =============================================================================


class SuperAdminSimpleService:
    """
    Discovery automático por convención:

      PANEL (columna 1):
        - Blueprint: panel_<panel_id>_bp

      MÓDULO (columna 2):
        - Blueprint: modulo_<panel_id>_<modulo_id>_bp

      BOTONES (columna 3):
        - Vista:     btn_<modulo_id>_<nombre_btn>
        - Blueprint:
            · modulo_<panel_id>_<modulo_id>_bp
            · btn_<modulo_id>_..._bp
    """

    # -------------------------------------------------------------------------
    # 2.1️⃣ Utilidad · Humanizar nombres técnicos para mostrarlos en HTML
    # -------------------------------------------------------------------------
    @staticmethod
    def humanizar(texto: str) -> str:
        """
        Convierte identificadores técnicos en texto legible.

        Reglas:
          - Elimina prefijos: panel_, modulo_, btn_
          - Elimina sufijo:   _bp
          - Sustituye '_' por espacio
          - Aplica Title Case
        """
        for prefijo in ("panel_", "modulo_", "btn_"):
            if texto.startswith(prefijo):
                texto = texto[len(prefijo):]

        if texto.endswith("_bp"):
            texto = texto[:-3]

        return texto.replace("_", " ").strip().title()

    # -------------------------------------------------------------------------
    # 2.2️⃣ Obtener paneles → 1ª columna (PANEL)
    # -------------------------------------------------------------------------
    @staticmethod
    def obtener_paneles() -> list[dict]:
        paneles: set[str] = set()

        for rule in current_app.url_map.iter_rules():
            endpoint = rule.endpoint

            if "static" in endpoint:
                continue

            partes = endpoint.split(".")
            if len(partes) < 2:
                continue

            bp_name = partes[0]

            if bp_name.startswith("panel_") and bp_name.endswith("_bp"):
                paneles.add(bp_name)

        return [{"nombre": n} for n in sorted(paneles)]

    # -------------------------------------------------------------------------
    # 2.3️⃣ Obtener módulos del panel seleccionado → 2ª columna (MÓDULO)
    # -------------------------------------------------------------------------
    @staticmethod
    def obtener_modulos(panel_seleccionado: str | None) -> list[dict]:
        if not panel_seleccionado:
            return []

        if not (
            panel_seleccionado.startswith("panel_")
            and panel_seleccionado.endswith("_bp")
        ):
            return []

        panel_id = panel_seleccionado[len("panel_"): -len("_bp")]
        prefijo_modulo = f"modulo_{panel_id}_"

        modulos: set[str] = set()

        for rule in current_app.url_map.iter_rules():
            endpoint = rule.endpoint
            if "static" in endpoint:
                continue

            partes = endpoint.split(".")
            if len(partes) < 2:
                continue

            bp_name = partes[0]

            if bp_name.startswith(prefijo_modulo) and bp_name.endswith("_bp"):
                modulos.add(bp_name)

        return [
            {
                "nombre": n,
                "texto": SuperAdminSimpleService.humanizar(n),
            }
            for n in sorted(modulos)
        ]

    # -------------------------------------------------------------------------
    # 2.4️⃣ _blueprints_de_modulo
    # -------------------------------------------------------------------------
    @staticmethod
    def _blueprints_de_modulo(modulo_seleccionado: str) -> set[str]:
        """
        Dado un módulo:

            modulo_<panel_id>_<modulo_id>_bp

        devuelve el conjunto de blueprints que consideramos "del módulo" para
        buscar botones:

          1) El propio blueprint del módulo.
          2) Cualquier blueprint:

                btn_<modulo_id>_..._bp
        """
        blueprints_modulo: set[str] = {modulo_seleccionado}

        partes = modulo_seleccionado.split("_")
        if len(partes) >= 4 and partes[0] == "modulo" and partes[-1] == "bp":
            # Caso especial control_via_publica
            if partes[1] == "control" and partes[2] == "via" and partes[3] == "publica":
                modulo_id = partes[-2]
            else:
                modulo_id = "_".join(partes[2:-1])

            prefijo_btn = f"btn_{modulo_id}_"

            for bp_name in current_app.blueprints.keys():
                if bp_name.startswith(prefijo_btn) and bp_name.endswith("_bp"):
                    blueprints_modulo.add(bp_name)

        return blueprints_modulo

    # -------------------------------------------------------------------------
    # 2.5️⃣ obtener_botones → 3ª columna (BOTONES)
    # -------------------------------------------------------------------------
    @staticmethod
    def obtener_botones(
        panel_seleccionado: str | None, modulo_seleccionado: str | None
    ) -> list[dict]:

        if not panel_seleccionado or not modulo_seleccionado:
            return []

        botones: list[dict] = []

        blueprints_modulo = SuperAdminSimpleService._blueprints_de_modulo(
            modulo_seleccionado
        )

        modulo_clean = modulo_seleccionado.replace("modulo_", "").replace("_bp", "")
        partes_modulo = modulo_clean.split("_", 1)
        modulo_id = partes_modulo[1] if len(partes_modulo) == 2 else modulo_clean

        for rule in current_app.url_map.iter_rules():
            endpoint = rule.endpoint
            url = str(rule)

            if "static" in endpoint:
                continue

            partes = endpoint.split(".")
            if len(partes) < 2:
                continue

            bp_name = partes[0]
            view_name = partes[1]

            if bp_name not in blueprints_modulo:
                continue

            if not view_name.startswith("btn_"):
                continue

            prefix_modulo = f"btn_{modulo_id}_"
            if view_name.startswith(prefix_modulo):
                nombre_btn_sin_modulo = "btn_" + view_name[len(prefix_modulo):]
            else:
                nombre_btn_sin_modulo = view_name

            texto = SuperAdminSimpleService.humanizar(nombre_btn_sin_modulo)

            botones.append(
                {
                    "nombre": view_name,
                    "blueprint": bp_name,
                    "url": url,
                    "texto": texto,
                }
            )

        botones.sort(key=lambda b: (b["texto"] or b["nombre"]).lower())
        return botones


# 


# =============================================================================
# 3️⃣ ESTADÍSTICAS CONTEXTUALES PARA LA COLUMNA 4
# =============================================================================

def obtener_stats_contenedores() -> dict:
    """
    Estadísticas globales de contenedores en control_via_publica:
      - instalados (sin retirada)
      - retirados
      - totales
      - totales por año de expediente

    Además, define la iconografía de contenedores:
      - contenedor_verde → instalados
      - contenedor_azul  → retirados
    """
    instalados = ejecutar_query(
        """
        SELECT COUNT(*) AS c
        FROM tbl_control_contenedores
        WHERE fecha_retirada IS NULL
        """,
        (),
        nombre_bd="control_via_publica",
    )[0]["c"]

    retirados = ejecutar_query(
        """
        SELECT COUNT(*) AS c
        FROM tbl_control_contenedores
        WHERE fecha_retirada IS NOT NULL
        """,
        (),
        nombre_bd="control_via_publica",
    )[0]["c"]

    totales = instalados + retirados

    por_anio = ejecutar_query(
        """
        SELECT anio_expediente AS anio, COUNT(*) AS total
        FROM tbl_control_contenedores
        GROUP BY anio_expediente
        ORDER BY anio_expediente DESC
        """,
        (),
        nombre_bd="control_via_publica",
    )

    return {
        "tipo": "contenedores",
        "titulo": "Contenedores",
        "resumen": {
            "instalados": instalados,
            "retirados": retirados,
            "totales": totales,
        },
        "por_anio": por_anio,
        "iconos": {
            "instalados": url_for("static", filename="imagen/contenedor_verde.png"),
            "retirados": url_for("static", filename="imagen/contenedor_azul.png"),
        },
    }


def obtener_stats_parquin_rio_torio() -> dict:
    """
    Estadísticas globales del parquin Rio Torio (todas las filas):
      - plazas libres
      - plazas ocupadas
      - plazas totales

    Basado en:
      - BD: parquin_camiones
      - Tabla: tbl_plazas
      - Una plaza está ocupada si idtbl_usuarios IS NOT NULL.

    Iconografía preparada:
      - camion_rojo.png  → plaza ocupada
      - camion_verde.png → plaza libre
      - camion_azul.png  → otro tipo de ocupación (pendiente de icono físico).
    """
    conn = get_connection("parquin_camiones")
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN idtbl_usuarios IS NULL THEN 1 ELSE 0 END) AS libres,
            SUM(CASE WHEN idtbl_usuarios IS NOT NULL THEN 1 ELSE 0 END) AS ocupadas
        FROM tbl_plazas
        """)
    row = cursor.fetchone() or {"total": 0, "libres": 0, "ocupadas": 0}

    cursor.close()
    conn.close()

    return {
        "tipo": "parquin_rio_torio",
        "titulo": "Parquin Rio Torio",
        "resumen": {
            "totales": row["total"],
            "libres": row["libres"],
            "ocupadas": row["ocupadas"],
        },
        "iconos": {
            "ocupada": url_for("static", filename="imagen/camion_rojo.png"),
            "libre": url_for("static", filename="imagen/camion_verde.png"),
            "ocupada_especial": url_for("static", filename="imagen/camion_azul.png"),
        },
    }


# =============================================================================
# 4️⃣ RESUMEN PROFESIONAL DE AUDITORÍA PARA CABECERA
# =============================================================================

def obtener_resumen_auditoria() -> dict:
    """
    Calcula métricas globales de auditoría para mostrar en la cabecera
    del panel super_admin:

      - intentos_7d        → intentos de login últimos 7 días.
      - exitosos_7d        → logins correctos últimos 7 días.
      - fallidos_7d        → logins fallidos últimos 7 días.
      - gestores_activos_30d → nº de gestores con al menos un login
                               exitoso en los últimos 30 días.
      - ultimo_login_actual → fecha del último login exitoso del super_admin
                              actual (si hay idtbl_gestores en sesión).
    """
    resumen = {
        "intentos_7d": 0,
        "exitosos_7d": 0,
        "fallidos_7d": 0,
        "gestores_activos_30d": 0,
        "ultimo_login_actual": None,
    }

    conn = get_connection()
    if not conn:
        return resumen

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(exito = 1) AS exitosos,
                SUM(exito = 0) AS fallidos
            FROM tbl_auditoria_intentos
            WHERE fecha >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            """)
        row = cursor.fetchone() or {}
        resumen["intentos_7d"] = row.get("total", 0) or 0
        resumen["exitosos_7d"] = row.get("exitosos", 0) or 0
        resumen["fallidos_7d"] = row.get("fallidos", 0) or 0

        cursor.execute("""
            SELECT COUNT(DISTINCT idtbl_gestores) AS activos
            FROM tbl_auditoria_intentos
            WHERE exito = 1
              AND fecha >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            """)
        row = cursor.fetchone() or {}
        resumen["gestores_activos_30d"] = row.get("activos", 0) or 0

        id_gestor = session.get("idtbl_gestores")
        if id_gestor:
            cursor.execute(
                """
                SELECT MAX(fecha) AS ultimo_login
                FROM tbl_auditoria_intentos
                WHERE idtbl_gestores = %s AND exito = 1
                """,
                (id_gestor,),
            )
            row = cursor.fetchone() or {}
            resumen["ultimo_login_actual"] = row.get("ultimo_login")

    finally:
        cursor.close()
        conn.close()

    return resumen


# =============================================================================
# 5️⃣ ACTIVIDAD RECIENTE DESDE audit_log
# =============================================================================

def obtener_actividad_reciente(limit: int = 10) -> list[dict]:
    """
    Devuelve los últimos 'limit' eventos desde audit_log para mostrarlos
    en una tabla compacta en el panel super_admin.
    """
    eventos: list[dict] = []

    conn = get_connection("bd_tbl_comunes")
    if not conn:
        return eventos

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT
                fecha,
                accion,
                modulo,
                endpoint,
                ip
            FROM audit_log
            ORDER BY fecha DESC
            LIMIT %s
            """,
            (limit,),
        )
        eventos = cursor.fetchall() or []
    finally:
        cursor.close()
        conn.close()

    return eventos


# =============================================================================
# 6️⃣ RUTA PRINCIPAL · /super_admin/ → RENDERIZA PLANTILLA
# =============================================================================

@super_admin_bp.route("/")
def super_admin():
    """
    👑 SUPER ADMIN · Vista principal HTML.

    1) Descubre paneles.
    2) Determina panel_seleccionado.
    3) Descubre módulos del panel.
    4) Determina modulo_seleccionado.
    5) Descubre botones del módulo.
    6) Calcula estadísticas contextuales (stats) según el módulo.
    7) Calcula resumen de auditoría para la cabecera.
    8) Recupera actividad reciente desde audit_log.
    9) Renderiza super_admin.html.
    """
    paneles = SuperAdminSimpleService.obtener_paneles()

    panel_seleccionado = request.args.get("panel")
    if not panel_seleccionado and paneles:
        panel_seleccionado = paneles[0]["nombre"]

    modulos = SuperAdminSimpleService.obtener_modulos(panel_seleccionado)

    modulo_seleccionado = request.args.get("modulo")
    if not modulo_seleccionado and modulos:
        modulo_seleccionado = modulos[0]["nombre"]

    botones = SuperAdminSimpleService.obtener_botones(
        panel_seleccionado,
        modulo_seleccionado,
    )

    stats = None
    
    if modulo_seleccionado == "modulo_parquin_rio_torio_bp":
        stats = obtener_stats_parquin_rio_torio()

    resumen_auditoria = obtener_resumen_auditoria()
    ultimos_eventos = obtener_actividad_reciente(limit=10)

    return render_template(
        "super_admin/super_admin.html",
        paneles=paneles,
        modulos=modulos,
        botones=botones,
        panel_seleccionado=panel_seleccionado,
        modulo_seleccionado=modulo_seleccionado,
        stats=stats,
        resumen_auditoria=resumen_auditoria,
        ultimos_eventos=ultimos_eventos,
    )


@super_admin_bp.route("/endpoints")
def super_admin_endpoints():
    """
    Vista de diagnóstico que muestra todos los endpoints registrados
    en la aplicación Flask.
    """
    endpoints = obtener_todos_los_endpoints()
    endpoints_ordenados = sorted(endpoints, key=lambda e: e["rule"])

    return render_template("diagnostico/endpoints.html", endpoints=endpoints_ordenados)