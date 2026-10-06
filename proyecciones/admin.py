from django.contrib import admin

from .models import Linea, Periodo, ProyeccionArea, UnidadMedida

@admin.register(Periodo)
class PeriodoAdmin(admin.ModelAdmin):
    list_display = ('anio', 'estado', 'fecha_apertura', 'fecha_limite', 'abierto_por')


@admin.register(UnidadMedida)
class UnidadMedidaAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)
    
class LineaInline(admin.TabularInline):
    model = Linea
    extra = 1
    readonly_fields = ('total_anual', 'costo')
    
@admin.register(ProyeccionArea)
class ProyeccionAreaAdmin(admin.ModelAdmin):
    list_display = ('area','periodo','estado','responsable')
    list_filter = ('periodo','estado')   
    inlines = [LineaInline]