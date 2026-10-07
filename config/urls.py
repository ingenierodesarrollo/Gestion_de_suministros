"""URL configuration for config project."""
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = 'Gestión de suministros'
admin.site.site_title = 'Gestión de suministros'
admin.site.index_title = 'Panel de administración'

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("cuentas.urls")),
    path("proyecciones/", include("proyecciones.urls")),
]