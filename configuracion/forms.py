from django import forms
from areas.models import Area
from proyecciones.models import ProductoSugerido, UnidadMedida
from django.contrib.auth.forms import BaseUserCreationForm
from cuentas.models import Rol, Usuario


class CoordinadoresAreaField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, usuario):
        etiqueta = f'{usuario.nombre} <{usuario.correo}>'
        area_actual = getattr(self, 'area_actual', None)
        if usuario.area_id and usuario.area_id != getattr(area_actual, 'pk', None):
            etiqueta += f' (hoy en {usuario.area.codigo_area} - {usuario.area.nombre})'
        return etiqueta


class AreaForm(forms.ModelForm):
    coordinadores = CoordinadoresAreaField(
        label='Coordinadores del área',
        queryset=Usuario.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Area
        fields = ['nombre', 'codigo_area', 'activa']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        campo = self.fields['coordinadores']
        campo.queryset = Usuario.objects.filter(
            rol=Rol.COORDINADOR, activo=True,
        ).select_related('area').order_by('nombre', 'correo')
        campo.area_actual = self.instance if self.instance.pk else None
        # Sin coordinadores la lista sale vacía y parece un error: se explica qué hacer.
        if not campo.queryset.exists():
            campo.help_text = (
                'Todavía no hay coordinadores activos. Créelos en Configuración → Usuarios '
                'y luego vuelva aquí para asignarlos.'
            )
        if self.instance.pk:
            self.initial['coordinadores'] = campo.queryset.filter(area=self.instance)

    def clean_coordinadores(self):
        coordinadores = self.cleaned_data['coordinadores']
        if not self.instance.pk:
            return coordinadores
        elegidos = coordinadores.values_list('pk', flat=True)
        retirados = Usuario.objects.filter(
            rol=Rol.COORDINADOR, activo=True, area=self.instance,
        ).exclude(pk__in=elegidos).order_by('nombre')
        if retirados:
            raise forms.ValidationError([
                f'Para quitar a {usuario.nombre} de esta área, asígnelo a otra área o desactívelo desde Usuarios.'
                for usuario in retirados
            ])
        return coordinadores
        
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
