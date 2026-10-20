from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy

from .forms import CambiarClaveForm


@login_required
def inicio(request):
    if request.user.es_proveedor:
        return redirect("portal:inicio")
    return render(request, "inicio.html")


class CambiarClaveView(PasswordChangeView):
    """Cada usuario cambia su propia clave. Al lograrlo se quita la marca de cambio obligatorio."""

    form_class = CambiarClaveForm
    template_name = 'cuentas/cambiar_clave.html'
    success_url = reverse_lazy('inicio')

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        usuario = form.user
        usuario.debe_cambiar_clave = False
        usuario.save(update_fields=['debe_cambiar_clave'])
        return respuesta