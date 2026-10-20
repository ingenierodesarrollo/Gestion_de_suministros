from datetime import timedelta

from django import forms
from django.contrib import admin
from django.db import models
from django.db.models import Count
from django.utils import timezone

from .models import (
    DIAS_AVISO_VENCIMIENTO, Categoria, DocumentoProveedor, EnvioProveedor, Peso, Proveedor, Requisito, TipoDocumento,
)


class ArchivoPrivadoInput(forms.ClearableFileInput):
    """Campo para subir el PDF sin el enlace "Actualmente: ...": los archivos son privados y no se abren desde /admin/."""

    def is_initial(self, value):
        return False


ARCHIVO_PRIVADO = {models.FileField: {"widget": ArchivoPrivadoInput}}

NOMBRES_VIGENCIA = {
    "vigente": "Vigente",
    "por_vencer": "Por vencer",
    "vencido": "Vencido",
    "sin_vencimiento": "No vence",
}


@admin.display(description="archivo guardado")
def archivo_guardado(obj):
    if obj and obj.archivo:
        return "Sí (privado: se abre desde el sistema, no desde aquí)"
    return "No"


# ---------- Catálogos del FR-GDS-14 ----------

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activa", "num_proveedores")
    list_filter = ("activa",)
    search_fields = ("nombre",)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(total_proveedores=Count("proveedores"))

    @admin.display(description="proveedores", ordering="total_proveedores")
    def num_proveedores(self, obj):
        return obj.total_proveedores


class PesoInline(admin.TabularInline):
    model = Peso
    extra = 0
    verbose_name = "peso por categoría"
    verbose_name_plural = "pesos por categoría (1 o 2)"


@admin.register(Requisito)
class RequisitoAdmin(admin.ModelAdmin):
    list_display = ("numero", "bloque", "texto", "activo")
    list_display_links = ("numero", "texto")
    list_filter = ("bloque", "activo")
    search_fields = ("texto",)
    inlines = [PesoInline]


@admin.register(Peso)
class PesoAdmin(admin.ModelAdmin):
    list_display = ("requisito", "categoria", "valor")
    list_filter = ("categoria", "valor", "requisito__bloque")
    search_fields = ("requisito__texto", "categoria__nombre")
    list_select_related = ("requisito", "categoria")


@admin.register(TipoDocumento)
class TipoDocumentoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "vence", "vigencia_dias", "requisito", "activo")
    list_filter = ("vence", "activo")
    search_fields = ("nombre",)
    list_select_related = ("requisito",)


# ---------- Proveedores y sus documentos ----------

class VigenciaFilter(admin.SimpleListFilter):
    """Filtra los documentos por vigencia, igual que DocumentoProveedor.estado_vigencia."""
    title = "vigencia"
    parameter_name = "vigencia"

    def lookups(self, request, model_admin):
        return list(NOMBRES_VIGENCIA.items())

    def queryset(self, request, queryset):
        hoy = timezone.localdate()
        aviso = hoy + timedelta(days=DIAS_AVISO_VENCIMIENTO)
        if self.value() == "vencido":
            return queryset.filter(fecha_vencimiento__lt=hoy)
        if self.value() == "por_vencer":
            return queryset.filter(fecha_vencimiento__gte=hoy, fecha_vencimiento__lte=aviso)
        if self.value() == "vigente":
            return queryset.filter(fecha_vencimiento__gt=aviso)
        if self.value() == "sin_vencimiento":
            return queryset.filter(fecha_vencimiento__isnull=True)
        return queryset


@admin.display(description="vigencia")
def vigencia(obj):
    if not obj or not obj.pk:
        return "-"
    return NOMBRES_VIGENCIA[obj.estado_vigencia()]


class DocumentoInline(admin.TabularInline):
    model = DocumentoProveedor
    extra = 0
    fields = ("tipo", "fecha_expedicion", "fecha_vencimiento", vigencia, "archivo", archivo_guardado, "enlace_drive", "observaciones")
    readonly_fields = (vigencia, archivo_guardado)
    formfield_overrides = ARCHIVO_PRIVADO


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ("razon_social", "nit", "categoria", "tipo_persona", "estado", "num_documentos")
    list_filter = ("estado", "categoria", "tipo_persona")
    search_fields = ("razon_social", "nit")
    list_select_related = ("categoria",)
    readonly_fields = ("creado",)
    fieldsets = (
        ("Datos del proveedor", {"fields": ("nit", "razon_social", "tipo_persona", "categoria", "estado")}),
        ("Contacto", {"fields": ("contacto_nombre", "contacto_correo", "contacto_telefono")}),
        ("Registro", {"fields": ("creado",)}),
    )
    inlines = [DocumentoInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(total_documentos=Count("documentos"))

    @admin.display(description="documentos", ordering="total_documentos")
    def num_documentos(self, obj):
        return obj.total_documentos

    def save_formset(self, request, form, formset, change):
        # Los documentos nuevos quedan a nombre de quien los registró.
        for documento in formset.save(commit=False):
            if not documento.registrado_por_id:
                documento.registrado_por = request.user
            documento.save()
        for borrado in formset.deleted_objects:
            borrado.delete()
        formset.save_m2m()


@admin.register(DocumentoProveedor)
class DocumentoProveedorAdmin(admin.ModelAdmin):
    list_display = ("proveedor", "tipo", "fecha_vencimiento", vigencia, "tiene_archivo")
    list_filter = (VigenciaFilter, "tipo")
    search_fields = ("proveedor__razon_social", "proveedor__nit", "tipo__nombre")
    list_select_related = ("proveedor", "tipo")
    autocomplete_fields = ("proveedor",)
    readonly_fields = (vigencia, archivo_guardado, "registrado_por", "creado")
    fieldsets = (
        (None, {"fields": ("proveedor", "tipo", "fecha_expedicion", "fecha_vencimiento", vigencia)}),
        ("Archivo", {"fields": ("archivo", archivo_guardado, "enlace_drive", "observaciones")}),
        ("Registro", {"fields": ("registrado_por", "creado")}),
    )
    formfield_overrides = ARCHIVO_PRIVADO

    @admin.display(description="archivo", boolean=True)
    def tiene_archivo(self, obj):
        return bool(obj.archivo or obj.enlace_drive)

    def save_model(self, request, obj, form, change):
        if not obj.registrado_por_id:
            obj.registrado_por = request.user
        super().save_model(request, obj, form, change)


# ---------- Bandeja de envíos ----------

@admin.register(EnvioProveedor)
class EnvioProveedorAdmin(admin.ModelAdmin):
    """Aquí solo se consultan los envíos y se registran a mano. Procesarlos o descartarlos se hace en la bandeja del sistema."""
    list_display = ("recibido", "razon_social", "nit", "tipo", "estado", "proveedor", "sugerido", "origen")
    list_filter = ("estado", "origen", "tipo")
    search_fields = ("nit", "razon_social", "nombre_original")
    list_select_related = ("tipo", "proveedor")
    date_hierarchy = "recibido"
    formfield_overrides = ARCHIVO_PRIVADO
    fieldsets = (
        ("Lo que envió el proveedor", {"fields": ("nit", "razon_social", "tipo", "archivo", archivo_guardado, "nombre_original", "recibido")}),
        ("Revisión", {"fields": ("estado", "proveedor", "sugerido", "documento", "revisado_por", "fecha_revision", "motivo_descarte")}),
        ("Datos técnicos", {"classes": ("collapse",), "fields": ("origen", "id_externo")}),
    )
    # Lo que se llena al revisar el envío: nunca se escribe a mano.
    campos_de_revision = ("estado", "proveedor", "sugerido", "documento", "revisado_por", "fecha_revision", "motivo_descarte", "origen", "id_externo")

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return ("nombre_original", "recibido", archivo_guardado) + self.campos_de_revision
        # Ya creado: lo enviado tampoco se cambia.
        return ("nit", "razon_social", "tipo", "nombre_original", "recibido", archivo_guardado) + self.campos_de_revision

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            # Al registrar a mano solo se piden los datos del envío.
            return (("Lo que envió el proveedor", {"fields": ("nit", "razon_social", "tipo", "archivo")}),)
        fieldsets = super().get_fieldsets(request, obj)
        # Ya guardado, el archivo no se vuelve a subir: se muestra solo si existe.
        enviado = tuple(f for f in fieldsets[0][1]["fields"] if f != "archivo")
        return ((fieldsets[0][0], {"fields": enviado}),) + tuple(fieldsets[1:])

    def has_change_permission(self, request, obj=None):
        # La lista se puede abrir; un envío ya guardado solo se ve (se procesa en la bandeja del sistema).
        if obj is not None:
            return False
        return super().has_change_permission(request, obj)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.origen = "manual"
        super().save_model(request, obj, form, change)

    @admin.display(description="proveedor sugerido (por NIT)")
    def sugerido(self, obj):
        if obj.proveedor_id:
            return "-"
        sugerido = obj.proveedor_sugerido()
        return sugerido or "Ninguno con ese NIT"
