"""
Configuración de Django para el sistema de gestión de suministros.

Los valores sensibles (clave secreta, contraseña de la base de datos) NO se
escriben aquí: se leen del archivo .env, que nunca se sube al repositorio.
Usa .env.example como plantilla.
"""

import os
from pathlib import Path
import sys

from dotenv import load_dotenv
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

# Carga las variables del archivo .env (si existe) en el entorno.
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.environ['DJANGO_SECRET_KEY']

DEBUG = os.environ.get('DJANGO_DEBUG', 'False') == 'True'

ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h.strip()
]


# Aplicaciones

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'axes',
    # Apps propias
    'areas',
    'cuentas',
    'proyecciones',
    'configuracion',
    "proveedores",
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'cuentas.middleware.ForzarCambioClaveMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Base de datos: PostgreSQL 18

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'suministros'),
        'USER': os.environ.get('POSTGRES_USER', 'suministros'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
        'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
        'PORT': os.environ.get('POSTGRES_PORT', '5433'),
    }
}


# Usuarios e inicio de sesión

AUTH_USER_MODEL = 'cuentas.Usuario'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'inicio'
LOGOUT_REDIRECT_URL = 'login'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',  # debe ir primero: es quien bloquea
    'django.contrib.auth.backends.ModelBackend',
]
AXES_USERNAME_FORM_FIELD = 'username'         # el formulario de ingreso envía el correo con este nombre
AXES_FAILURE_LIMIT = 5                        # intentos fallidos permitidos
AXES_COOLOFF_TIME = timedelta(minutes=15)     # cuánto dura el bloqueo
AXES_LOCKOUT_PARAMETERS = ['username']        # se bloquea al correo, no a la computadora
AXES_RESET_ON_SUCCESS = True                  # un ingreso correcto reinicia la cuenta de fallos
AXES_LOCKOUT_TEMPLATE = 'cuentas/bloqueado.html'
# axes.W006: se bloquea por correo y no por computador a propósito (PCs compartidos en la clínica).
# Revisar si el sistema se publica en internet.
SILENCED_SYSTEM_CHECKS = ['axes.W006']


# Cierre de sesión por inactividad: 30 minutos sin usar el sistema
SESSION_COOKIE_AGE = 30 * 60
SESSION_SAVE_EVERY_REQUEST = True


# Idioma y zona horaria

LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True


# Archivos estáticos (CSS, JavaScript, imágenes)

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

if 'test' in sys.argv:
    # Solo al correr las pruebas: un cifrado rápido. En el sistema real se sigue usando el seguro.
    PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
    
# Producción (en el servidor): una sola variable activa la seguridad extra.
# En tu computador no se define y todo sigue igual.
if os.environ.get('DJANGO_PRODUCCION') == 'True':
    SECURE_SSL_REDIRECT = True        # manda todo a HTTPS
    SESSION_COOKIE_SECURE = True      # la cookie de sesión solo viaja cifrada
    CSRF_COOKIE_SECURE = True         # la cookie anti-formularios-falsos, igual
    SECURE_HSTS_SECONDS = 3600        # el navegador recuerda "solo HTTPS" por 1 hora (se sube después)
    
    


