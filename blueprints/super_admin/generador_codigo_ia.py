# =============================================================================
# 🧠 generador_codigo_ia.py – Motor de generación de código IA
# =============================================================================
# 🎯 OBJETIVO:
#   A partir de un prompt en lenguaje natural, devolver código listo para pegar
#   siguiendo SIEMPRE estas reglas:
#
#   1) SI ES PANEL/MÓDULO:
#        - Generar SOLO blueprints (Python).
#        - Con introducción arriba.
#        - Código separado por secciones y subsecciones.
#        - Títulos explicativos + iconitos.
#        - Comentarios "COMIENZA" y "TERMINA" en cada bloque.
#
#   2) SI ES BTN/BOTÓN:
#        - Generar blueprint + HTML del botón.
#        - Ambos con el mismo estilo de secciones/subsecciones + iconitos.
#        - Comentarios "COMIENZA" y "TERMINA".
#
#   3) TODO EL CÓDIGO SALE EN UN SOLO TEXTO, listo para copiar.
# =============================================================================

from textwrap import dedent


def generar_codigo(prompt: str) -> str:
    """
    Dado un prompt en texto libre, genera código con la estructura acordada.
    """
    p = prompt.lower()

    # ¿Parece que pide un botón?
    es_boton = any(x in p for x in ["btn ", "botón", "boton", "button"])

    if es_boton:
        return _generar_para_boton(prompt)
    else:
        return _generar_para_panel_modulo(prompt)


# =============================================================================
# 1️⃣ GENERACIÓN PARA PANELES / MÓDULOS (SOLO BLUEPRINTS)
# =============================================================================
def _generar_para_panel_modulo(prompt: str) -> str:
    """
    Genera un ejemplo de blueprint para panel/módulo con la estructura pedida.
    """

    codigo = f"""
    # =============================================================================
    # 🧠 BLUEPRINT – PANEL/MÓDULO GENERADO POR IA
    # =============================================================================
    # 🎯 INTRODUCCIÓN
    # -----------------------------------------------------------------------------
    # Código generado automáticamente a partir del prompt:
    #   "{prompt}"
    #
    # Este archivo define:
    #   - Un blueprint de panel principal.
    #   - Rutas para acceder al panel.
    #   - Estructura básica preparada para añadir módulos y botones.
    #
    # Todo va separado por secciones y subsecciones, explicado en los títulos,
    # con iconitos y con comentarios de "COMIENZA" y "TERMINA" en cada bloque.
    # =============================================================================


    # =============================================================================
    # 1️⃣ IMPORTACIONES PRINCIPALES
    # -----------------------------------------------------------------------------
    # COMIENZA: importaciones de Flask y utilidades propias.
    # TERMINA: justo antes de definir el Blueprint del panel.
    # -----------------------------------------------------------------------------
    from flask import Blueprint, render_template, redirect, url_for  # 🌐 Rutas y vistas
    from services.helpers import rol_required                        # 🎭 Control de roles
    # =============================================================================
    # 1️⃣ TERMINAN IMPORTACIONES
    # =============================================================================


    # =============================================================================
    # 2️⃣ DEFINICIÓN DEL BLUEPRINT DEL PANEL
    # -----------------------------------------------------------------------------
    # COMIENZA: creación del Blueprint del panel.
    # TERMINA: justo antes de las funciones de vista.
    # -----------------------------------------------------------------------------
    panel_control_vp_bp = Blueprint(
        "panel_control_vp_bp",     # 🏷 Nombre interno del blueprint
        __name__,
        url_prefix="/control_vp",  # 🌐 Prefijo de URL del panel
    )
    # =============================================================================
    # 2️⃣ TERMINA DEFINICIÓN DEL BLUEPRINT
    # =============================================================================


    # =============================================================================
    # 3️⃣ VISTA PRINCIPAL DEL PANEL
    # -----------------------------------------------------------------------------
    # COMIENZA: ruta "/" del panel de control.
    # TERMINA: retorno de la plantilla del panel.
    # -----------------------------------------------------------------------------
    @panel_control_vp_bp.route("/", methods=["GET"])
    @rol_required("super_admin")
    def panel_control_vp():
        \"\"\"
        🧩 Panel 'Control VP'.

        Aquí se mostrarán los módulos de:
          - Contenedores
          - Obras
          - Vados
          - Terrazas
        \"\"\"
        return render_template("control_vp/panel_control_vp.html")
    # =============================================================================
    # 3️⃣ TERMINA VISTA PRINCIPAL DEL PANEL
    # =============================================================================
    """
    return dedent(codigo).strip()


# =============================================================================
# 2️⃣ GENERACIÓN PARA BOTONES (BLUEPRINT + HTML)
# =============================================================================
def _generar_para_boton(prompt: str) -> str:
    """
    Genera blueprint + HTML para un botón, con toda la estructura pedida.
    """

    nombre_bp = "btn_generico_accion_bp"
    ruta_bp = "/btn_generico_accion"

    codigo_bp = f"""
    # =============================================================================
    # 🔘 {nombre_bp}.py – Botón de acción generado por IA
    # =============================================================================
    # 🎯 INTRODUCCIÓN
    # -----------------------------------------------------------------------------
    # Código de botón generado automáticamente a partir del prompt:
    #   "{prompt}"
    #
    # Este archivo define:
    #   - Un blueprint de botón (acción individual).
    #   - Una ruta que ejecuta la acción (normalmente un redirect).
    #
    # Todo separado por secciones y subsecciones explicadas en los títulos,
    # con iconitos y comentarios "COMIENZA" y "TERMINA".
    # =============================================================================


    # =============================================================================
    # 1️⃣ IMPORTACIONES PRINCIPALES
    # -----------------------------------------------------------------------------
    # COMIENZA: importaciones de Flask y helpers de rol.
    # TERMINA: justo antes de definir el Blueprint.
    # -----------------------------------------------------------------------------
    from flask import Blueprint, redirect, url_for      # 🌐 Rutas y redirecciones
    from services.helpers import rol_required           # 🎭 Control de roles
    # =============================================================================
    # 1️⃣ TERMINAN IMPORTACIONES
    # =============================================================================


    # =============================================================================
    # 2️⃣ DEFINICIÓN DEL BLUEPRINT DEL BOTÓN
    # -----------------------------------------------------------------------------
    # COMIENZA: creación del Blueprint del botón.
    # TERMINA: justo antes de la función de vista.
    # -----------------------------------------------------------------------------
    {nombre_bp} = Blueprint(
        "{nombre_bp}",            # 🏷 Nombre interno del blueprint
        __name__,
        url_prefix="{ruta_bp}",   # 🌐 Prefijo de URL del botón
    )
    # =============================================================================
    # 2️⃣ TERMINA DEFINICIÓN DEL BLUEPRINT DEL BOTÓN
    # =============================================================================


    # =============================================================================
    # 3️⃣ VISTA DEL BOTÓN · ACCIÓN
    # -----------------------------------------------------------------------------
    # COMIENZA: definición de la ruta del botón.
    # TERMINA: retorno del redirect (o acción) y cierre de la función.
    # -----------------------------------------------------------------------------
    @{nombre_bp}.route("/", methods=["GET"])
    @rol_required("gestor", "super_admin")
    def btn_generico_accion():
        \"\"\"Acción generada por IA a partir del prompt.

        Aquí puedes poner la lógica real de tu botón, normalmente un redirect
        a otro módulo o una acción concreta.
        \"\"\"
        # TODO: cambiar 'destino_bp.vista_destino' por tu endpoint real
        return redirect(url_for("destino_bp.vista_destino"))
    # =============================================================================
    # 3️⃣ TERMINA VISTA DEL BOTÓN
    # =============================================================================
    """

    codigo_html = """
    <!-- =============================================================================
         🔘 HTML DEL BOTÓN – Fragmento para usar en un panel o módulo
         =============================================================================
         🎯 INTRODUCCIÓN
         -------------------------------------------------------------------------
         Este fragmento HTML representa un botón de acción profesional
         generado por la IA. Incluye:
           - Iconito representativo.
           - Texto corto y claro.
           - Estructura limpia con secciones comentadas.
         ============================================================================= -->

    <!-- =============================================================================
         1️⃣ SECCIÓN: BOTÓN DE ACCIÓN INDIVIDUAL
         ---------------------------------------------------------------------------
         COMIENZA: enlace <a> que actúa como botón.
         TERMINA: cierre del </a>.
         ---------------------------------------------------------------------------
         DETALLES:
           - href → url_for del endpoint del botón.
           - Icono + texto corto "Acción generada".
         ============================================================================= -->
    <a href="{{ url_for('btn_generico_accion_bp.btn_generico_accion') }}"
       class="btn-action">
      <div style="display:flex; flex-direction:column;">
        <div>
          ⚙️ <strong>Acción generada</strong>
        </div>
        <div style="font-size:0.8rem; color:#4b5563; margin-top:2px;">
          Botón creado automáticamente por la IA según tu descripción.
        </div>
      </div>
    </a>
    <!-- =============================================================================
         1️⃣ TERMINA BOTÓN DE ACCIÓN INDIVIDUAL
         ============================================================================= -->
    """

    return dedent(codigo_bp).strip() + "\n\n\n" + dedent(codigo_html).strip()
