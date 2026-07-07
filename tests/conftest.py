# conftest.py
# ============================================================================
# 🧪 CONFIGURACIÓN CENTRALIZADA DE PYTEST
# ============================================================================
# - Define fixtures reutilizables para todos los tests
# - Configura el entorno de prueba
# - Proporciona cliente HTTP, contexto de app, etc.
# ============================================================================

import pytest
import sys
import os

# Añadir la raíz del proyecto a sys.path para imports correctos
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app import app as flask_app


# ============================================================================
# FIXTURE: app
# ============================================================================
@pytest.fixture
def app():
    """
    Crea una instancia de Flask configurada para testing.
    
    - TESTING = True (desactiva error catching durante request handling)
    - Crea contexto de aplicación
    - Preserva el contexto durante el test
    """
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False  # Desactivar CSRF en tests
    
    yield flask_app


# ============================================================================
# FIXTURE: client
# ============================================================================
@pytest.fixture
def client(app):
    """
    Cliente HTTP de prueba para hacer requests sin servidor real.
    
    Uso:
        def test_index(client):
            response = client.get('/')
            assert response.status_code == 200
    """
    return app.test_client()


# ============================================================================
# FIXTURE: runner
# ============================================================================
@pytest.fixture
def runner(app):
    """
    CLI runner para probar comandos de línea de comandos (si los hay).
    
    Uso:
        def test_cli_command(runner):
            result = runner.invoke(my_command, ['arg'])
            assert result.exit_code == 0
    """
    return app.test_cli_runner()


# ============================================================================
# FIXTURE: app_context
# ============================================================================
@pytest.fixture
def app_context(app):
    """
    Contexto de aplicación Flask para tests que necesiten acceso a:
    - current_app
    - g (almacenamiento por request)
    - Acceso a configuración de la app
    
    Uso:
        def test_with_context(app_context):
            from flask import current_app
            assert current_app.config['TESTING'] is True
    """
    with app.app_context():
        yield app


# ============================================================================
# CONFIGURACIÓN DE PYTEST
# ============================================================================
def pytest_configure(config):
    """
    Hook que se ejecuta antes de los tests.
    Útil para setup global.
    """
    # Registrar markers personalizados
    config.addinivalue_line(
        "markers", "unit: tests unitarios (sin BD ni requests reales)"
    )
    config.addinivalue_line(
        "markers", "integration: tests de integración (con BD o servicios)"
    )
    config.addinivalue_line(
        "markers", "slow: tests lentos que pueden tardar"
    )


# ============================================================================
# CONFIGURACIÓN DE LOGGING PARA TESTS
# ============================================================================
@pytest.fixture(scope="session", autouse=True)
def configure_logging():
    """
    Configura logging para tests.
    Útil para debugging cuando algo falla.
    """
    import logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
