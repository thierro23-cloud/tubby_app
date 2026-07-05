# blueprints/parquin/__init__.py
"""
🏗 Este archivo es como el PORTERO del módulo PARQUIN.
🚪 Su trabajo es: decirle a la app Flask qué blueprints del parquin existen
    y registrarlos todos (enchufarlos) para que funcionen las rutas.
"""

from flask import Flask  # 🧩 Solo para el tipo de la función


def register_parquin_blueprints(app: Flask):
    """
    🧠 Esta función recibe la APP principal de Flask
    y le añade (registra) todos los blueprints que viven
    dentro de la carpeta parquin.
    """

    # 🧩 Blueprint de ACCESOS
    from .accesos_bp import accesos_bp

    # 🧩 Blueprint de ASIGNAR PLAZAS (nuevo de usuarios/proveedores)
    from .asignar_plazas_bp import asignar_plazas_bp

    # 🧩 Blueprint de ASIGNAR PLAZAS A PROVEEDORES (módulo nuevo)
    from .asignar_plazas_proveedores_bp import asignar_plazas_proveedores_bp

    # 🧩 Blueprint de CAMIONES
    from .camiones_bp import camiones_bp

    # 🧩 Blueprint de CONSULTAS DEL PARQUIN (si lo usas)
    from .consultas_proveedores_parquin_bp import consultas_proveedores_parquin_bp

    # 🧩 Blueprint del PANEL GENERAL DEL PARQUIN
    from .panel_parquin_bp import panel_parquin_bp

    # 🧩 Blueprint del PLANO (si mantienes uno independiente)
    from .plano_bp import plano_bp

    # 🧩 Blueprint de PLAZAS
    from .plazas_bp import plazas_bp

    # 🧩 Blueprint de RESERVAS DE PLAZAS
    from .reservas_plazas import reservas_plazas_bp

    # 🧩 Blueprint de HISTÓRICO DE PLAZAS
    from .historico_plazas_bp import historico_plazas_bp

    # 🚪 Registrar todos en la app
    app.register_blueprint(accesos_bp)
    app.register_blueprint(asignar_plazas_bp)
    app.register_blueprint(asignar_plazas_proveedores_bp)
    app.register_blueprint(camiones_bp)
    app.register_blueprint(consultas_proveedores_parquin_bp)
    app.register_blueprint(panel_parquin_bp)
    app.register_blueprint(plano_bp)
    app.register_blueprint(plazas_bp)
    app.register_blueprint(reservas_plazas_bp)
    app.register_blueprint(historico_plazas_bp)  # 👈 aquí se engancha el histórico

    print("✅ Todos los blueprints de PARQUIN registrados correctamente")
