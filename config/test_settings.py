"""Configuración de pruebas para el TP3.

Sobreescribe la base de datos por SQLite (archivo temporal) para poder
ejecutar el conjunto de pruebas sin necesidad de crear una base de datos
de prueba en PostgreSQL (operación que requiere permiso CREATE DATABASE
que el usuario configurado no tiene en este entorno).

No se toca settings.py ni .env. Solo se usa al ejecutar:
    python manage.py test --settings=config.test_settings
"""

from .settings import *  # noqa: F401,F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db_test.sqlite3',
    }
}
