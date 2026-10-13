from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError


class CambiarClaveForm(PasswordChangeForm):
    """Pide la clave actual y la nueva dos veces, y no deja repetir la actual."""

    def clean_new_password1(self):
        nueva = self.cleaned_data['new_password1']
        if self.user.check_password(nueva):
            raise ValidationError('La clave nueva debe ser distinta de la actual.')
        return nueva