from django import forms
from areas.models import Area
from proyecciones.models import ProductoSugerido, UnidadMedida


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