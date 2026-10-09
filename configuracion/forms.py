from django import forms
from areas.models import Area
from proyecciones.models import ProductoSugerido, UnidadMedida
from django.contrib.auth.forms import BaseUserCreationForm
from cuentas.models import Usuario

class AreaForm(forms.ModelForm):
    class Meta:
        model = Area
        fields = ['nombre', 'codigo_area', 'activa']
        
class UnidadForm(forms.ModelForm):
    class Meta:
        model = UnidadMedida
        fields = ['nombre']


class ProductoForm(forms.ModelForm):
    class Meta:
        model = ProductoSugerido
        fields = ['nombre', 'activo']
        
class UsuarioCrearForm(BaseUserCreationForm):
    """Pide correo, nombre, rol, área y la clave dos veces."""

    class Meta:
        model = Usuario
        fields = ('correo', 'nombre', 'rol', 'area')


class UsuarioEditarForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ['nombre', 'correo', 'rol', 'area', 'activo']