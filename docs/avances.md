# Registro de avances

Una entrada por sesión de trabajo, la más reciente arriba. Corta y sencilla.
Los datos de prueba son siempre inventados.

## Contexto actual (actualizar al cerrar cada sesión)

**Qué es:** sistema web para automatizar la gestión de suministros de la clínica (compras, inventario, proveedores). Sistema independiente: no se conecta a otros sistemas de la clínica.
**Para quién:** sobre todo la coordinadora de gestión de suministros.
**Datos:** solo inventados; los reales son confidenciales.

**Tecnología:** Django 5.2 + PostgreSQL 18 en Docker (puerto 5433), Python 3.13, desarrollo en Windows. Servidor final: máquina virtual Ubuntu en la clínica.
**Cómo arrancar:** `docker compose up -d` y luego `python manage.py runserver`.

**Roles:** coordinador (solo su área), administrador (coordinadora de suministros y un doctor, mismos permisos), desarrollador (acceso a todo) y proveedor (solo su portal).

**Fase 1 · Proyección de compras (FR-GDS-11)** — completa
- Hecho: login y roles; apertura de periodo que crea una proyección en borrador por área activa; cerrar y reabrir periodo; el coordinador agrega, edita y borra líneas, las importa desde Excel y envía; el administrador revisa, llena lo autorizado y aprueba; correcciones con justificación y Ajuste si la proyección ya estaba aprobada; Bitácora (solo se agregan filas); consolidado anual en pantalla y en Excel; plantilla Excel descargable; productos sugeridos; cálculo en vivo.
- Pendiente: pregunta abierta con la coordinadora sobre qué es "dependencia".

**Fase 2 · Proveedores (FR-GDS-14)** — en curso
- Hecho: catálogos FR-GDS-14 (categorías, requisitos y pesos); proveedores con NIT sin duplicados; tipos de documento y documentos con vencimiento (vigente, por vencer, vencido); portal de proveedores con registro y subida de PDF; bandeja de envíos para procesar o descartar; PDF privados entregados solo por vista con permisos.
- Pendiente: evaluación anual con cálculo por requisitos y pesos; documentos obligatorios por categoría; flujo de aprobación de proveedores.

**Configuración:** áreas con asignación de coordinadores, unidades, productos sugeridos y usuarios (con cambio de clave obligatorio).

**Pruebas:** 230 pruebas automáticas, todas OK.

**Pendiente general:** despliegue en Ubuntu Server 24.04, HTTPS y copias de seguridad. Detalle y deuda técnica en docs/entrega_tecnica.md.

**Reglas de trabajo:** master solo con lo probado; el repositorio está en GitHub (privado) y master es la rama de entrega; cada etiqueta de plantilla ({% %} y {{ }}) en una sola línea; interfaz en español con trato de "usted"; colores azul #172554 y rojo #991b1b (el rojo solo para alertas y borrar); pruebas antes de cada commit.

## Plantilla (copiar para cada entrada nueva)

### 2026-10-21 · Documentación de entrega
- **Qué se hizo:** README.md con instalación y comandos; docs/entrega_tecnica.md con estado, arquitectura, funcionalidad, pendientes, deuda técnica y reglas; actualización de este registro con las fases 1 y 2.
- **Archivos principales:** README.md, docs/entrega_tecnica.md, docs/avances.md.
- **Cómo se probó:** python manage.py check, makemigrations --check y python manage.py test (230 pruebas OK).
- **Commit:** (el código corto lo ves con git log --oneline)
- **Decisiones:** master es la única rama de entrega; las ramas fase1-proyeccion y fase2-proveedores quedan como historial.
- **Pendiente / siguiente paso:** evaluación FR-GDS-14, documentos obligatorios por categoría, aprobación de proveedores, despliegue, HTTPS y copias de seguridad.

---

### 2026-10-08 · Plantilla base, cálculo en vivo y productos sugeridos
- **Qué se hizo:** plantilla base para todas las pantallas (con meta charset y viewport); total y costo en vivo con JavaScript; campo dependencia en la línea; modelo ProductoSugerido administrable en /admin/ y conectado al campo Producto.
- **Archivos principales:** templates/base.html, static/js/linea_form.js, proyecciones/models.py, forms.py, views.py, tests.py.
- **Cómo se probó:** python manage.py test (14 pruebas OK) y revisión a mano con el coordinador.
- **Commit:** (el código corto lo ves con git log --oneline)
- **Decisiones:** dependencia como texto opcional hasta confirmar con la coordinadora qué significa; los productos sugeridos son solo una ayuda, la línea sigue siendo texto libre.
- **Pendiente / siguiente paso:** apertura de periodo, Bitácora y Ajuste, pase de apariencia.

---

### 2026-10-07 · Pruebas automáticas y estilos del panel
- **Qué se hizo:** 13 pruebas automáticas de la proyección; paso de la rama fase1-proyeccion a master; estilos del panel /admin/ (azul oscuro, rojo solo en borrar).
- **Archivos principales:** proyecciones/tests.py, static/css/estilos.css, static/css/admin.css, templates/admin/base_site.html, config/urls.py.
- **Cómo se probó:** python manage.py test (13 pruebas OK) y revisión visual de /admin/.
- **Commit:** (el código corto lo ves con git log --oneline)
- **Decisiones:** colores azul #172554 y rojo #991b1b; 0 es una cantidad autorizada válida y vacío bloquea la aprobación.
- **Pendiente / siguiente paso:** total y costo en vivo en el formulario de línea; Producto sugerido; Bitácora y Ajuste.
