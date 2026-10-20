from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render

from cuentas.models import Rol
from cuentas.permisos import rol_requerido

from .forms import RegistroProveedorForm


def registro(request):
    """Página pública: cualquier proveedor puede crear su cuenta."""
    if request.user.is_authenticated:
        return redirect("inicio")
    form = RegistroProveedorForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = form.guardar()
        login(request, usuario, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, "Su cuenta quedó creada. La clínica revisará sus datos.")
        return redirect("portal:inicio")
    return render(request, "portal/registro.html", {"form": form})


@rol_requerido(Rol.PROVEEDOR)
def inicio(request):
    return render(request, "portal/inicio.html", {"proveedor": request.user.proveedor})
