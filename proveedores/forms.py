from django import forms

from .models import Proveedor


class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = [
            "nit", "razon_social", "tipo_persona", "categoria",
            "contacto_nombre", "contacto_correo", "contacto_telefono", "estado",
        ]
