from django.contrib import admin
from .models import Area

@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ("nombre","codigo_area","activa")
    search_fields = ("nombre", "codigo_area")
    list_filter = ("activa",)