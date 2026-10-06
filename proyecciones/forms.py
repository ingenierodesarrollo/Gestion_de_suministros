from django import forms

from .models import Linea


class LineaForm(forms.ModelForm):
    """Lo que el coordinador llena por cada producto. La cantidad autorizada no aparece: es solo para administradores."""

    class Meta:
        model = Linea
        fields = ['producto', 'serie', 'unidad', *Linea.MESES, 'precio_unitario_est']