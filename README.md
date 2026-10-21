# Gestión de suministros

Sistema web para automatizar la gestión de suministros de la clínica: proyección anual de compras (FR-GDS-11) y gestión de proveedores con sus documentos (FR-GDS-14). Es un sistema independiente: no se conecta a otros sistemas de la clínica.

## Tecnología

- Python 3.13 y Django 5.2
- PostgreSQL 18 en Docker (puerto 5433)
- openpyxl (Excel) y django-axes (bloqueo por intentos fallidos)
- Desarrollo en Windows. Servidor previsto: Ubuntu Server 24.04 (despliegue pendiente).

## Instalación rápida en Windows

Programas necesarios: Git, Python 3.13 y Docker Desktop.

```
git clone https://github.com/ingenierodesarrollo/Gestion_de_suministros.git
cd Gestion_de_suministros
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Llene `.env` (la clave secreta se genera con `python -c "import secrets; print(secrets.token_urlsafe(50))"`). Luego:

```
docker compose up -d
python manage.py migrate
python manage.py createsuperuser
python manage.py check
python manage.py test
python manage.py runserver
```

Abra http://127.0.0.1:8000/ e ingrese con el correo y la clave del superusuario.

## Comandos habituales

| Para | Comando |
|---|---|
| Encender la base de datos | `docker compose up -d` |
| Apagar la base de datos (conserva los datos) | `docker compose down` |
| Activar el entorno | `.venv\Scripts\activate` |
| Iniciar el servidor | `python manage.py runserver` |
| Correr todas las pruebas | `python manage.py test` |
| Correr las pruebas de una app | `python manage.py test proveedores` |
| Revisar migraciones pendientes | `python manage.py makemigrations --check` |
| Ver migraciones aplicadas | `python manage.py showmigrations` |

## Estructura

| App | Responsabilidad |
|---|---|
| `config` | Configuración (lee `.env`) y URL raíz |
| `cuentas` | Usuario, roles, permisos, ingreso y cambio de clave |
| `areas` | Áreas de la clínica |
| `proyecciones` | Proyección anual de compras, bitácora, ajustes, consolidado y Excel |
| `configuracion` | Pantallas de áreas, coordinadores, unidades, productos y usuarios |
| `proveedores` | Proveedores, documentos, catálogos FR-GDS-14 y bandeja de envíos |
| `portal` | Registro y portal de los proveedores |

## Seguridad: qué no se sube al repositorio

- `.env` (claves y contraseñas)
- `archivos_privados/` (PDF de los proveedores)
- La base de datos, sus copias y el volumen de Docker
- Cualquier dato real: en pruebas y ejemplos se usan solo datos ficticios

## Documentación

- [Entrega técnica](docs/entrega_tecnica.md)
- [Registro de avances](docs/avances.md)
