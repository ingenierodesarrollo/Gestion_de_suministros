from django.contrib import admin

from .models import Linea, Periodo, ProductoSugerido, ProyeccionArea, UnidadMedida, Ajuste, Bitacora

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
    
@admin.register(ProductoSugerido)
class ProductoSugeridoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activo')
    list_filter = ('activo',)
    search_fields = ('nombre',)

class SoloLectura(admin.ModelAdmin):
    """Tablas de rastro: se ven en el panel, pero no se agregan, editan ni borran."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Bitacora)
class BitacoraAdmin(SoloLectura):
    list_display = ('fecha_hora', 'usuario', 'accion', 'tabla', 'registro_id', 'campo', 'valor_anterior', 'valor_nuevo')
    list_filter = ('accion',)


@admin.register(Ajuste)
class AjusteAdmin(SoloLectura):
    list_display = ('fecha', 'linea', 'campo', 'valor_aprobado', 'valor_nuevo', 'hecho_por')