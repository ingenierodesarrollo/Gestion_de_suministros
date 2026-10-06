from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import BaseUserCreationForm, UserChangeForm

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
        ("Permisos técnicos", {"fields": ("is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("correo", "nombre", "rol", "area", "password1", "password2"),
        }),
    )
