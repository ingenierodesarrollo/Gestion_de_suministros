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
- Hecho: login y roles; el coordinador agrega, edita y borra líneas y envía; el administrador revisa, llena lo autorizado y aprueba; 13 pruebas automáticas; panel /admin/ con estilos propios.
- Pendiente: total y costo en vivo en el formulario, Producto sugerido, Bitácora y Ajuste, meta charset/viewport en las plantillas.
- Fase 2 (después): proveedores y portal interno de documentos.

**Reglas de trabajo:** master solo con lo probado; rama de trabajo fase1-proyeccion; sin push hasta que la clínica apruebe GitHub; cada etiqueta de plantilla ({% %} y {{ }}) en una sola línea; colores azul #172554 y rojo #991b1b (el rojo solo para alertas y borrar).

## Plantilla (copiar para cada entrada nueva)

### AAAA-MM-DD · Título corto
- **Qué se hizo:**
- **Archivos principales:**
- **Cómo se probó:**
- **Commit:**
- **Decisiones:**
- **Pendiente / siguiente paso:**

---

### 2026-10-07 · Pruebas automáticas y estilos del panel
- **Qué se hizo:** 13 pruebas automáticas de la proyección; paso de la rama fase1-proyeccion a master; estilos del panel /admin/ (azul oscuro, rojo solo en borrar).
- **Archivos principales:** proyecciones/tests.py, static/css/estilos.css, static/css/admin.css, templates/admin/base_site.html, config/urls.py.
- **Cómo se probó:** python manage.py test (13 pruebas OK) y revisión visual de /admin/.
- **Commit:** (el código corto lo ves con git log --oneline)
- **Decisiones:** colores azul #172554 y rojo #991b1b; 0 es una cantidad autorizada válida y vacío bloquea la aprobación.
- **Pendiente / siguiente paso:** total y costo en vivo en el formulario de línea; Producto sugerido; Bitácora y Ajuste.