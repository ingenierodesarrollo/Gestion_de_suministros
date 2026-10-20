from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from cuentas.models import Rol, Usuario
from proveedores.models import Categoria, Proveedor


class RegistroProveedorForm(forms.Form):
    """El proveedor se registra solo: se crean su ficha (en revisión) y su usuario."""
    nit = forms.CharField(
        label="NIT", max_length=20,
        validators=Proveedor._meta.get_field("nit").validators,
        help_text="Solo números y, si quieres, el dígito de verificación: 900123456-7",
    )
    razon_social = forms.CharField(label="Razón social", max_length=200)
    tipo_persona = forms.ChoiceField(label="Tipo de persona", choices=Proveedor.TIPOS_PERSONA)
    categoria = forms.ModelChoiceField(label="¿Qué le ofrece a la clínica?", queryset=Categoria.objects.all())
    contacto_nombre = forms.CharField(label="Nombre de la persona de contacto", max_length=120)
    correo = forms.EmailField(label="Correo (con este correo inicias sesión)")
    contacto_telefono = forms.CharField(label="Teléfono", max_length=30, required=False)
    clave1 = forms.CharField(label="Clave", widget=forms.PasswordInput)
    clave2 = forms.CharField(label="Repite la clave", widget=forms.PasswordInput)

    def clean_nit(self):
        nit = self.cleaned_data["nit"].strip()
        if Proveedor.objects.filter(nit=nit).exists():
            raise ValidationError("Ya hay un proveedor registrado con ese NIT. Si es su empresa, comuníquese con la clínica.")
        return nit

    def clean_correo(self):
        correo = Usuario.objects.normalize_email(self.cleaned_data["correo"])
        if Usuario.objects.filter(correo__iexact=correo).exists():
            raise ValidationError("Ese correo ya tiene una cuenta. Inicie sesión o use otro correo.")
        return correo

    def clean(self):
        datos = super().clean()
        clave1, clave2 = datos.get("clave1"), datos.get("clave2")
        if clave1 and clave2:
            if clave1 != clave2:
                self.add_error("clave2", "Las dos claves no coinciden.")
            else:
                # Las mismas reglas de clave que el resto del sistema (largo, no muy común, no solo números...).
                usuario = Usuario(correo=datos.get("correo", ""), nombre=datos.get("contacto_nombre", ""))
                try:
                    validate_password(clave1, usuario)
                except ValidationError as error:
                    self.add_error("clave1", error)
        return datos

    @transaction.atomic
    def guardar(self):
        """Crea la ficha y el usuario juntos: si algo falla, no queda ninguno de los dos a medias."""
        datos = self.cleaned_data
        proveedor = Proveedor.objects.create(
            nit=datos["nit"],
            razon_social=datos["razon_social"],
            tipo_persona=datos["tipo_persona"],
            categoria=datos["categoria"],
            contacto_nombre=datos["contacto_nombre"],
            contacto_correo=datos["correo"],
            contacto_telefono=datos["contacto_telefono"],
        )
        return Usuario.objects.create_user(
            datos["correo"], datos["contacto_nombre"], datos["clave1"],
            rol=Rol.PROVEEDOR, proveedor=proveedor,
        )
