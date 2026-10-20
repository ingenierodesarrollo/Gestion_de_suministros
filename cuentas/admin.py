from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import BaseUserCreationForm, UserChangeForm
from django.contrib.auth.models import Group

from .models import Usuario

class UsuarioCreacionForm(BaseUserCreationForm):
    class Meta:
        model = Usuario
        fields = ("correo","nombre","rol","area")
        
class UsuarioEdicionForm(UserChangeForm):
    class Meta:
        model = Usuario
        fields = "__all__"
        
@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    form =UsuarioEdicionForm
    add_form = UsuarioCreacionForm
    
    list_display = ("nombre", "correo", "rol", "area", "activo")
    list_filter = ("rol", "activo")
    search_fields = ("nombre", "correo")
    ordering = ("nombre",)
    
    fieldsets = (
        (None, {"fields": ("correo", "password")}),
        ("Datos", {"fields": ("nombre", "rol", "area", "activo")}),
        ("Permisos técnicos", {"fields": ("is_superuser",)}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("correo", "nombre", "rol", "area", "password1", "password2"),
        }),
    )

    def get_fieldsets(self, request, obj=None):
        """La casilla de superusuario solo la ven los desarrolladores: los permisos salen del rol."""
        fieldsets = super().get_fieldsets(request, obj)
        if obj and not (request.user.is_superuser or request.user.es_desarrollador):
            fieldsets = [f for f in fieldsets if f[0] != "Permisos técnicos"]
        return fieldsets


# Los grupos no se usan: lo que cada quien puede hacer sale de su rol (ver cuentas/models.py).
admin.site.unregister(Group)
