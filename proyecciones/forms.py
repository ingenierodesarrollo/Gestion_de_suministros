from django import forms
from django.forms import modelformset_factory

from .models import Linea


class LineaForm(forms.ModelForm):
    """Lo que el coordinador llena por cada producto. La cantidad autorizada no aparece: es solo para administradores."""

    class Meta:
        model = Linea
        fields = ['producto', 'dependencia', 'serie', 'unidad', *Linea.MESES, 'precio_unitario_est']
        widgets = {
            'producto': forms.TextInput(attrs={'list': 'productos-sugeridos',
                        'autocomplete': 'off'   })
        }
        
AutorizadoFormSet = modelformset_factory(Linea, fields=['cantidad_autorizada'], extra = 0) 
       