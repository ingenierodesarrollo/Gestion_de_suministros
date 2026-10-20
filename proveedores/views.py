from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from cuentas.models import Rol
from cuentas.permisos import rol_requerido

from .forms import ProveedorForm
from .models import Proveedor
from .servicios import documentos_actuales, resumen_vigencia

ROLES = (Rol.ADMINISTRADOR, Rol.DESARROLLADOR)


@rol_requerido(*ROLES)
def proveedores_lista(request):
    q = request.GET.get("q", "").strip()
    estado = request.GET.get("estado", "")
    proveedores = Proveedor.objects.select_related("categoria").prefetch_related("documentos__tipo")
    if q:
        proveedores = proveedores.filter(Q(razon_social__icontains=q) | Q(nit__icontains=q))
    if estado:
        proveedores = proveedores.filter(estado=estado)
    filas = [
        {"proveedor": p, "resumen": resumen_vigencia(documentos_actuales(p))}
        for p in proveedores
    ]
    return render(request, "proveedores/lista.html", {
        "filas": filas, "q": q, "estado": estado, "estados": Proveedor.ESTADOS,
    })


@rol_requerido(*ROLES)
def proveedor_detalle(request, pk):
    proveedor = get_object_or_404(Proveedor.objects.select_related("categoria"), pk=pk)
    actuales = documentos_actuales(proveedor)
    ids_actuales = {doc.pk for doc in actuales}
    anteriores = [doc for doc in proveedor.documentos.select_related("tipo") if doc.pk not in ids_actuales]
    return render(request, "proveedores/detalle.html", {
        "proveedor": proveedor, "actuales": actuales, "anteriores": anteriores,
        "resumen": resumen_vigencia(actuales),
    })


@rol_requerido(*ROLES)
def proveedor_guardar(request, pk=None):
    """Sirve para crear (sin pk) y para editar (con pk)."""
    proveedor = get_object_or_404(Proveedor, pk=pk) if pk else None
    form = ProveedorForm(request.POST or None, instance=proveedor)
    if request.method == "POST" and form.is_valid():
        proveedor = form.save()
        messages.success(request, "Proveedor guardado.")
        return redirect("proveedores:detalle", pk=proveedor.pk)
    titulo = "Editar proveedor" if proveedor else "Nuevo proveedor"
    return render(request, "configuracion/form_simple.html", {
        "form": form, "titulo": titulo, "volver": "proveedores:lista",
    })
