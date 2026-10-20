from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render

from cuentas.models import Rol
from cuentas.permisos import rol_requerido
from proveedores.models import EnvioProveedor

from .forms import EnvioPortalForm, RegistroProveedorForm


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
    """Ficha del proveedor, formulario para subir un PDF y lista de lo que ha enviado."""
    proveedor = request.user.proveedor
    # El envío nace ya ligado a su ficha: el proveedor no puede elegir otra empresa ni otro NIT.
    nuevo = EnvioProveedor(
        origen="portal", proveedor=proveedor,
        nit=proveedor.nit, razon_social=proveedor.razon_social,
    )
    form = EnvioPortalForm(request.POST or None, request.FILES or None, instance=nuevo)
    if request.method == "POST" and form.is_valid():
        envio = form.save()
        messages.success(request, f"Recibimos su documento «{envio.tipo}». La clínica lo revisará.")
        # Redirigir evita que, al recargar la página, el mismo archivo se envíe dos veces.
        return redirect("portal:inicio")
    envios = proveedor.envios.select_related("tipo")
    return render(request, "portal/inicio.html", {"proveedor": proveedor, "form": form, "envios": envios})
