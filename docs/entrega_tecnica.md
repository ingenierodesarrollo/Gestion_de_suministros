# Gestión de suministros · Entrega técnica

Documento para el desarrollador que continúa el proyecto. Fecha de entrega: 21/10/2026.

## 1. Estado del repositorio

- Repositorio privado: github.com/ingenierodesarrollo/Gestion_de_suministros
- Rama de entrega: **master**. El punto de partida es el commit de la rama master al momento de la entrega.
- Sin cambios pendientes; master sincronizada con origin/master.
- Pruebas: 230 de 230 aprobadas. `makemigrations --check`: sin cambios pendientes.
- Las ramas `fase1-proyeccion` y `fase2-proveedores` son históricas y ya están contenidas en master. No se usan.

## 2. Instalación en Windows

Programas necesarios: Git, Python 3.13, Docker Desktop y un editor de código.

```
git clone https://github.com/ingenierodesarrollo/Gestion_de_suministros.git
cd Gestion_de_suministros
git checkout master
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Variables de `.env` (los valores se entregan por canal seguro o se generan; nunca se suben):

| Variable | Uso |
|---|---|
| `DJANGO_SECRET_KEY` | Obligatoria. Generar con `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DJANGO_DEBUG` | `True` en desarrollo, `False` en servidor |
| `DJANGO_ALLOWED_HOSTS` | Lista separada por comas |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | Datos de la base de datos |
| `POSTGRES_HOST`, `POSTGRES_PORT` | `localhost` y `5433` en desarrollo |
| `DJANGO_PRODUCCION` | Solo en el servidor: `True` activa HTTPS, cookies seguras y HSTS |

Luego:

```
docker compose up -d
python manage.py migrate
python manage.py createsuperuser
python manage.py check
python manage.py makemigrations --check
python manage.py test
python manage.py runserver
```

`createsuperuser` pide correo, nombre y clave, y crea el usuario con rol "desarrollador". El sistema queda en http://127.0.0.1:8000/.

## 3. Arquitectura

| App | Responsabilidad |
|---|---|
| `config` | `settings.py` (todo se lee de `.env`) y URL raíz |
| `cuentas` | Usuario propio (ingresa con correo), roles, permisos, ingreso, cambio de clave obligatorio, bloqueo por intentos |
| `areas` | Modelo `Area` |
| `proyecciones` | Periodo, proyección por área, líneas, revisión, aprobación, bitácora, ajustes, consolidado y Excel |
| `configuracion` | Pantallas de áreas y coordinadores, unidades, productos sugeridos y usuarios (sin modelos propios) |
| `proveedores` | Catálogos FR-GDS-14, proveedores, documentos, bandeja de envíos y entrega de PDF |
| `portal` | Registro público del proveedor y portal para subir PDF (sin modelos propios) |

### Modelos y relaciones

- `Usuario`: rol coordinador, administrador, desarrollador o proveedor. El coordinador se liga a un `Area`; el usuario proveedor, a un `Proveedor`.
- `Periodo` (año único, abierto o cerrado) tiene varias `ProyeccionArea` (una por periodo y área; estados borrador, enviada y aprobada). Cada proyección tiene varias `Linea` (12 meses, precio estimado, cantidad autorizada) y cada línea varios `Ajuste`.
- `Bitacora` registra movimientos de cualquier tabla (tabla + id del registro). `UnidadMedida` y `ProductoSugerido` son catálogos.
- `Categoria`, `Requisito` y `Peso` (requisito por categoría, valor 1 o 2): catálogo FR-GDS-14 cargado por las migraciones de datos `proveedores/0002` y `proveedores/0004`.
- `Proveedor` (NIT único; se detecta igual con o sin dígito de verificación) pertenece a una `Categoria` y tiene varios `DocumentoProveedor`, cada uno de un `TipoDocumento`.
- `EnvioProveedor` es la bandeja (pendiente, procesado o descartado). Al procesarse queda ligado uno a uno con un `DocumentoProveedor`.

### Dónde está la lógica

- Proyecciones: `proyecciones/servicios.py` (abrir periodo, bitácora, correcciones y ajustes), `importar.py`, `exportar.py` y `consolidado.py`.
- Proveedores: `proveedores/servicios.py` (vigencia), `forms_bandeja.py` (procesar envío) y métodos de `models.py` (`validar_pdf`, `con_mismo_nit`, `estado_vigencia`).
- Permisos: decorador `rol_requerido` en `cuentas/permisos.py`, usado en cada vista; `has_perm` e `is_staff` en `cuentas/models.py` para `/admin/`.

### Pruebas

Archivos `tests*.py` y `test_*.py` dentro de cada app (230 pruebas). Las que manejan PDF usan `@override_settings(MEDIA_ROOT=...)` con una carpeta temporal.

### PDF privados

- Se guardan en `archivos_privados/` (`MEDIA_ROOT`), en `envios/AAAA/MM/` y `documentos/AAAA/MM/` con nombre aleatorio.
- Validación: extensión `.pdf`, cabecera `%PDF-` y máximo 10 MB.
- Ninguna URL publica esa carpeta. Se entregan solo por `envio_archivo` y `documento_archivo` en `proveedores/bandeja.py`, restringidas a administrador y desarrollador. En `/admin/` no se muestra enlace al archivo.

## 4. Funcionalidad terminada

- **Proyecciones (Fase 1):** el administrador abre el periodo y se crea una proyección en borrador por cada área activa. El coordinador, solo en su área, agrega, edita o borra líneas, o las importa desde Excel, y envía. El administrador revisa, registra las cantidades autorizadas y aprueba. Las correcciones posteriores exigen justificación; si la proyección ya estaba aprobada se guarda un `Ajuste`. El periodo se puede cerrar y reabrir.
- **Excel:** plantilla descargable; la lectura busca las columnas por nombre (sirve también para formatos FR-GDS-11 anteriores); límites de 2000 filas, 5 MB y 9.999.999 por mes; vista previa antes de confirmar; actualiza líneas existentes. Consolidado anual en pantalla y en Excel, con una hoja por área.
- **Bitácora y ajustes:** la bitácora solo admite inserciones; la pantalla muestra los últimos 200 movimientos. Bitácora y ajustes son de solo lectura en `/admin/`.
- **Proveedores (Fase 2):** lista con búsqueda y filtro por estado, ficha con documentos vigentes y anteriores, alta y edición. Vigencia de cada documento: vigente, por vencer (30 días), vencido o sin vencimiento.
- **Portal de proveedores:** registro público que crea la ficha (estado "en revisión") y el usuario proveedor. El proveedor sube PDF eligiendo el tipo y ve sus envíos, con el motivo si fueron descartados.
- **Bandeja documental:** el administrador abre el PDF y procesa el envío (vincula al proveedor y calcula el vencimiento con la vigencia del tipo) o lo descarta con motivo. Protegida contra doble procesamiento.
- **Configuración:** áreas con asignación de coordinadores, unidades, productos sugeridos y usuarios. Los usuarios nuevos o con clave reiniciada deben cambiarla al ingresar.
- **Seguridad:** bloqueo por correo tras 5 intentos fallidos durante 15 minutos, cierre de sesión tras 30 minutos de inactividad, rol comprobado en cada vista y protección CSRF.

## 5. Pendientes y decisiones abiertas

- **Evaluación anual FR-GDS-14:** falta el modelo de evaluación, el cálculo por requisitos y pesos, el puntaje y su efecto en el estado del proveedor.
- **Documentos obligatorios por categoría:** no existe un modelo que los defina; hoy los tipos de documento son generales.
- **Aprobación de proveedores:** hoy es solo el campo "estado", editable a mano. Falta definir el flujo y quién aprueba.
- **Despliegue en Ubuntu Server 24.04:** no hay archivos de despliegue (servidor de aplicación, servidor web, servicio del sistema, archivos estáticos).
- **HTTPS:** definir el certificado y la configuración del proxy.
- **Copias de seguridad:** no existen. Deben cubrir la base de datos y `archivos_privados/`.

### Deuda técnica conocida

- `docs/avances.md` ya está actualizado; mantenerlo al día en cada sesión.
- PDF huérfanos y duplicados: al descartar un envío o borrar un documento o proveedor, el archivo no se borra del disco; al procesar un envío el PDF queda copiado en `envios/` y en `documentos/`.
- El proveedor no puede volver a descargar los PDF que envió.
- Un administrador puede crear o editar usuarios con rol desarrollador desde Configuración → Usuarios.
- Producción: faltan `CSRF_TRUSTED_ORIGINS` y `SECURE_PROXY_SSL_HEADER`; `SECURE_HSTS_SECONDS` está en 3600.
- El bloqueo de intentos es solo por correo (aviso `axes.W006` silenciado); revisar si el sistema se publica en internet.
- Falta `.gitattributes`: los fines de línea dependen de la configuración de cada equipo.
- Hay textos visibles con trato de "tú" por corregir (en `proveedores/models.py`, `proyecciones/views.py`, `proyecciones/forms.py` y `templates/proyecciones/detalle.html`).
- `requirements.txt` mezcla rangos y versiones fijas.
- `DJANGO_PRODUCCION` no está en `.env.example`.

## 6. Operación

- Día a día: `docker compose up -d`, activar `.venv` y `python manage.py runserver`. Apagar con `docker compose down` (los datos se conservan en el volumen).
- Todas las pruebas: `python manage.py test`. Una app: `python manage.py test proveedores`.
- Migraciones pendientes: `python manage.py makemigrations --check` y `python manage.py showmigrations`.
- Crear un periodo: Revisión → Abrir periodo (`/proyecciones/abrir-periodo/`).
- Crear usuarios: Configuración → Usuarios (`/configuracion/usuarios/`) o `/admin/`. Los proveedores se registran solos en `/portal/registro/`.

Rutas principales:

| Ruta | Pantalla |
|---|---|
| `/ingresar/`, `/salir/`, `/cambiar-clave/` | Ingreso y clave |
| `/proyecciones/mi-proyeccion/` | Proyecciones del área del coordinador |
| `/proyecciones/revision/` | Revisión de todas las áreas y periodos |
| `/proyecciones/consolidado/` | Consolidado anual y descarga en Excel |
| `/proyecciones/bitacora/` | Bitácora |
| `/configuracion/` | Panel de configuración |
| `/proveedores/` | Lista de proveedores |
| `/proveedores/bandeja/` | Bandeja de envíos |
| `/portal/`, `/portal/registro/` | Portal y registro de proveedores |
| `/admin/` | Opciones avanzadas |

No versionado: `.env`, `.venv/`, `archivos_privados/`, `staticfiles/`, `db.sqlite3` y el volumen Docker `datos_postgres`.

## 7. Seguridad y confidencialidad

- No comparta ni suba `.env`, `archivos_privados/`, copias de la base de datos ni el volumen de Docker.
- No incluya contraseñas, tokens ni datos reales en el código, las pruebas, los commits o los tickets.
- En pruebas y ejemplos use solo datos ficticios (correos con dominio `.test`, NIT inventados).
- Por canal seguro, y nunca en el repositorio, se entregan: el acceso a GitHub, las credenciales del servidor y de la base de datos de producción, la clave secreta de producción y las copias de seguridad.

## 8. Reglas de desarrollo

- Conservar CRLF en los archivos (Windows, `core.autocrlf=true`).
- Cada etiqueta de plantilla (`{% %}` y `{{ }}`) completa en una sola línea.
- Interfaz en español y con trato de "usted".
- Colores: azul `#172554` y rojo `#991b1b` (el rojo solo para alertas y borrar).
- Comprobar permisos en cada vista con `rol_requerido` y, para coordinadores, verificar el área.
- Correr `python manage.py test` antes de cada commit.
- Commits pequeños y descriptivos, sin líneas `Co-Authored-By` ni menciones a herramientas.
- No editar los documentos Word de la clínica.

## 9. Lista de confirmación

- [ ] Tengo acceso al repositorio privado
- [ ] Cloné la rama master
- [ ] Creé `.venv` e instalé `requirements.txt`
- [ ] Configuré `.env` y PostgreSQL responde en el puerto 5433
- [ ] `migrate` corrió sin errores y `makemigrations --check` no detecta cambios
- [ ] `python manage.py test`: 230 pruebas OK
- [ ] Creé mi usuario de desarrollo
- [ ] El sistema corre en local y puedo ingresar
- [ ] Entiendo los pendientes (sección 5) y qué datos son privados (sección 7)
