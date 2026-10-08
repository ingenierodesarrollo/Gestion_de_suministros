# Registro de avances

Una entrada por sesión de trabajo, la más reciente arriba. Corta y sencilla.
Los datos de prueba son siempre inventados.

## Contexto actual (actualizar al cerrar cada sesión)

**Qué es:** sistema web para automatizar la gestión de suministros de la clínica (compras, inventario, proveedores). Sistema independiente: no se conecta a otros sistemas de la clínica.
**Para quién:** sobre todo la coordinadora de gestión de suministros.
**Datos:** solo inventados; los reales son confidenciales.

**Tecnología:** Django 5.2 + PostgreSQL 18 en Docker (puerto 5433), Python 3.13, desarrollo en Windows. Servidor final: máquina virtual Ubuntu en la clínica.
**Cómo arrancar:** `docker compose up -d` y luego `python manage.py runserver`.

**Roles:** coordinador (solo su área), administrador (coordinadora de suministros y un doctor, mismos permisos) y desarrollador (acceso a todo).

**Fase 1 · Proyección de compras (FR-GDS-11)**
- Hecho: login y roles; el coordinador agrega, edita y borra líneas y envía; el administrador revisa, llena lo autorizado y aprueba; 14 pruebas automáticas; panel /admin/ con estilos propios; plantilla base (base.html) en todas las pantallas; total y costo en vivo al escribir una línea; campo dependencia (texto opcional) en la línea; productos sugeridos que se administran en el panel y se ofrecen al escribir el producto.
- Pendiente: pantalla para abrir el periodo y crear las proyecciones de todas las áreas; Bitácora y Ajuste (entrega 1b); pase de apariencia con los bocetos; pregunta abierta con la coordinadora sobre qué es "dependencia".

**Reglas de trabajo:** master solo con lo probado; rama de trabajo fase1-proyeccion; sin push hasta que la clínica apruebe GitHub; cada etiqueta de plantilla ({% %} y {{ }}) en una sola línea; colores azul #172554 y rojo #991b1b (el rojo solo para alertas y borrar).

## Plantilla (copiar para cada entrada nueva)

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