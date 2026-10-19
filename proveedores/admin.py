from django.contrib import admin

from .models import Categoria, DocumentoProveedor, Peso, Proveedor, Requisito, TipoDocumento

admin.site.register(Categoria)
admin.site.register(Requisito)
admin.site.register(Peso)
admin.site.register(TipoDocumento)


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ("razon_social", "nit", "categoria", "estado")
    search_fields = ("razon_social", "nit")


@admin.register(DocumentoProveedor)
class DocumentoProveedorAdmin(admin.ModelAdmin):
    list_display = ("proveedor", "tipo", "fecha_vencimiento")