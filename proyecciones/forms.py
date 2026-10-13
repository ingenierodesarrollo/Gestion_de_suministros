from django import forms
from django.forms import modelformset_factory
from datetime import date

from .models import EstadoPeriodo, EstadoProyeccion ,Linea, Periodo


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
    
    def clean_anio(self):
        anio = self.cleaned_data['anio']
        if Periodo.objects.filter(anio=anio, estado=EstadoPeriodo.CERRADO).exists():
            raise forms.ValidationError('Ese periodo esta cerrado. Reábrelo primero en Revisión')
        return anio

    def clean_fecha_limite(self):
        fecha = self.cleaned_data['fecha_limite']
        if fecha < date.today():
            raise forms.ValidationError('La fecha límite no puede ser anterior a hoy.')
        return fecha
    
class CorreccionLineaForm(forms.ModelForm):
    """Lo que un administrador puede cambiar de una línea ya enviada o aprobada. Siempre con justificación."""

    motivo = forms.CharField(label='Justificación del cambio', widget=forms.Textarea(attrs={'rows': 3}))

    class Meta:
        model = Linea
        fields = ['producto', 'dependencia', 'serie', 'unidad', *Linea.MESES,
                  'precio_unitario_est', 'cantidad_autorizada']
        widgets = {
            'producto': forms.TextInput(attrs={'list': 'productos-sugeridos', 'autocomplete': 'off'})
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
            # En una proyeccion aprobada el autorizado ya existe: no se puede dejar vacio.
        if self.instance.proyeccion.estado == EstadoProyeccion.APROBADA:
            self.fields ['cantidad_autorizada'].required = True
       