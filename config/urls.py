"""URL configuration for config project."""
from django.contrib import admin
from django.urls import include, path

# Títulos del panel /admin/ (en la app se llama "Opciones avanzadas").
admin.site.site_header = 'Sistema de Gestión de Suministros'
admin.site.site_title = 'Opciones avanzadas · Gestión de suministros'
admin.site.index_title = 'Opciones avanzadas'
admin.site.site_url = '/'

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("cuentas.urls")),
    path("proyecciones/", include("proyecciones.urls")),
    path("configuracion/", include("configuracion.urls")),
    path("proveedores/", include("proveedores.urls")),
    path("portal/", include("portal.urls")),
]
