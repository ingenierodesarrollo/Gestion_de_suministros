from django import forms
from django.forms import modelformset_factory
from datetime import date

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

class AbrirPeriodoForm(forms.Form):
    anio = forms.IntegerField(label='Año', min_value=2025, max_value=2100)
    fecha_limite = forms.DateField(
        label='Fecha límite de envío',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )

    def clean_fecha_limite(self):
        fecha = self.cleaned_data['fecha_limite']
        if fecha < date.today():
            raise forms.ValidationError('La fecha límite no puede ser anterior a hoy.')
        return fecha
       