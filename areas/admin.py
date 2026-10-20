from django.contrib import admin
from cuentas.models import Rol

from .models import Area

@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ("nombre","codigo_area","activa", "coordinadores")
    search_fields = ("nombre", "codigo_area")
    list_filter = ("activa",)

    @admin.display(description="coordinadores")
    def coordinadores(self, obj):
        nombres = obj.usuarios.filter(rol=Rol.COORDINADOR, activo=True).order_by("nombre").values_list("nombre", flat=True)
        return ", ".join(nombres) or "Sin coordinador"
