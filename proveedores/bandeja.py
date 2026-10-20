from django.contrib import messages
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from cuentas.models import Rol
from cuentas.permisos import rol_requerido

from .forms_bandeja import DescartarEnvioForm, ProcesarEnvioForm
from .models import DocumentoProveedor, EnvioProveedor

ROLES = (Rol.ADMINISTRADOR, Rol.DESARROLLADOR)


def _entregar_pdf(campo, nombre):
    """Entrega un PDF guardado en archivos_privados/. Solo se llega aquí después de revisar el rol."""
    if not campo:
        raise Http404("Este registro no tiene archivo.")
    try:
        archivo = campo.open("rb")
    except FileNotFoundError:
        raise Http404("El archivo ya no está en el servidor.")
    respuesta = FileResponse(archivo, content_type="application/pdf", filename=nombre or "documento.pdf")
    respuesta["Content-Disposition"] = f'inline; filename="{(nombre or "documento.pdf").replace(chr(34), "")}"'
    respuesta["X-Content-Type-Options"] = "nosniff"
    return respuesta


@rol_requerido(*ROLES)
def bandeja_lista(request):
    estado = request.GET.get("estado", "pendiente")
    envios = EnvioProveedor.objects.select_related("tipo", "proveedor")
    if estado in dict(EnvioProveedor.ESTADOS):
        envios = envios.filter(estado=estado)
    else:
        estado = ""
    return render(request, "proveedores/bandeja_lista.html", {
        "envios": envios, "estado": estado, "estados": EnvioProveedor.ESTADOS,
        "pendientes": EnvioProveedor.objects.filter(estado="pendiente").count(),
    })


def _pantalla_detalle(request, envio, procesar=None, descartar=None):
    pendiente = envio.estado == "pendiente"
    return render(request, "proveedores/bandeja_detalle.html", {
        "envio": envio,
        "sugerido": envio.proveedor or envio.proveedor_sugerido(),
        "form_procesar": procesar or (ProcesarEnvioForm(envio=envio) if pendiente else None),
        "form_descartar": descartar or (DescartarEnvioForm() if pendiente else None),
    })


@rol_requerido(*ROLES)
def bandeja_detalle(request, pk):
    envio = get_object_or_404(EnvioProveedor.objects.select_related("tipo", "proveedor", "documento", "revisado_por"), pk=pk)
    return _pantalla_detalle(request, envio)


@rol_requerido(*ROLES)
def envio_procesar(request, pk):
    if request.method != "POST":
        return redirect("proveedores:bandeja_detalle", pk=pk)
    with transaction.atomic():
        # select_for_update: si dos personas procesan a la vez, la segunda ve que ya no está pendiente.
        envio = get_object_or_404(EnvioProveedor.objects.select_for_update(of=("self",)).select_related("tipo", "proveedor"), pk=pk)
        if envio.estado != "pendiente":
            messages.error(request, "Este envío ya fue revisado.")
            return redirect("proveedores:bandeja_detalle", pk=pk)
        form = ProcesarEnvioForm(request.POST, envio=envio)
        if form.is_valid():
            documento = form.guardar(request.user)
            messages.success(request, f"Documento registrado en la ficha de {documento.proveedor.razon_social}.")
            return redirect("proveedores:bandeja")
    return _pantalla_detalle(request, envio, procesar=form)


@rol_requerido(*ROLES)
def envio_descartar(request, pk):
    if request.method != "POST":
        return redirect("proveedores:bandeja_detalle", pk=pk)
    with transaction.atomic():
        envio = get_object_or_404(EnvioProveedor.objects.select_for_update(of=("self",)).select_related("tipo", "proveedor"), pk=pk)
        if envio.estado != "pendiente":
            messages.error(request, "Este envío ya fue revisado.")
            return redirect("proveedores:bandeja_detalle", pk=pk)
        form = DescartarEnvioForm(request.POST)
        if form.is_valid():
            envio.estado = "descartado"
            envio.motivo_descarte = form.cleaned_data["motivo"].strip()
            envio.revisado_por = request.user
            envio.fecha_revision = timezone.now()
            envio.save()
            messages.success(request, "Envío descartado. El proveedor verá el motivo en su portal.")
            return redirect("proveedores:bandeja")
    return _pantalla_detalle(request, envio, descartar=form)


@rol_requerido(*ROLES)
def envio_archivo(request, pk):
    envio = get_object_or_404(EnvioProveedor, pk=pk)
    return _entregar_pdf(envio.archivo, envio.nombre_original)


@rol_requerido(*ROLES)
def documento_archivo(request, pk):
    documento = get_object_or_404(DocumentoProveedor, pk=pk)
    return _entregar_pdf(documento.archivo, f"{documento.tipo}.pdf")
