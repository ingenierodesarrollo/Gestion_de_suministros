from django.contrib import admin

from .models import Periodo, UnidadMedida

@admin.register(Periodo)
class PeriodoAdmin(admin.ModelAdmin):
    list_display = ('anio', 'estado', 'fecha_apertura', 'fecha_limite', 'abierto_por')


@admin.register(UnidadMedida)
class UnidadMedidaAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)