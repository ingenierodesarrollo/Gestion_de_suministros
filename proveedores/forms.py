from django import forms
from django.db.models import Q

from .models import Categoria, Proveedor


class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = [
            "nit", "razon_social", "tipo_persona", "categoria",
            "contacto_nombre", "contacto_correo", "contacto_telefono", "estado",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Solo categorías activas. Si el proveedor ya tenía una que luego se desactivó,
        # esa sigue apareciendo para que no se pierda al editar.
        filtro = Q(activa=True)
        if self.instance.pk and self.instance.categoria_id:
            filtro |= Q(pk=self.instance.categoria_id)
        self.fields["categoria"].queryset = Categoria.objects.filter(filtro)
