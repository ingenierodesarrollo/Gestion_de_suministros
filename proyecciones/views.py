from django.shortcuts import get_object_or_404, redirect, render
from cuentas.models import Rol
from cuentas.permisos import rol_requerido
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.utils import timezone

from .models import EstadoProyeccion, Linea, ProyeccionArea
from .forms import AutorizadoFormSet ,LineaForm


@rol_requerido(Rol.COORDINADOR, Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def mi_proyeccion(request):
    """Lista las proyecciones del área del usuario que inició sesión."""
    proyecciones = ProyeccionArea.objects.filter(area=request.user.area).select_related('periodo', 'area')
    return render(request, 'proyecciones/mi_proyeccion.html', {'proyecciones': proyecciones})

@rol_requerido(Rol.COORDINADOR, Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def detalle_proyeccion(request, pk):
    """Muestra las líneas de una proyección con su total y costo."""
    proyeccion = get_object_or_404(ProyeccionArea, pk=pk)
    # Un coordinador no puede ver proyecciones de otra área cambiando el número en la dirección.
    if request.user.es_coordinador and proyeccion.area_id != request.user.area_id:
        raise PermissionDenied
    lineas = proyeccion.lineas.select_related('unidad')
    costo_total = sum(linea.costo for linea in lineas)
    return render(request, 'proyecciones/detalle.html', {
        'proyeccion': proyeccion, 'lineas': lineas, 'costo_total': costo_total,
    })
    
def _obtener_proyeccion(request, pk):
    """Trae la proyección y bloquea a un coordinador si no es de su área."""
    proyeccion = get_object_or_404(ProyeccionArea, pk=pk)
    if request.user.es_coordinador and proyeccion.area_id != request.user.area_id:
        raise PermissionDenied
    return proyeccion


@rol_requerido(Rol.COORDINADOR, Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def agregar_linea(request, pk):
    proyeccion = _obtener_proyeccion(request, pk)
    if proyeccion.estado != EstadoProyeccion.BORRADOR:
        raise PermissionDenied  # ya enviada: el área no la cambia
    form = LineaForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        linea = form.save(commit=False)  # aún no guarda: falta decirle a qué proyección pertenece
        linea.proyeccion = proyeccion
        linea.save()
        return redirect('proyecciones:detalle', pk=proyeccion.pk)
    return render(request, 'proyecciones/linea_form.html',
                  {'form': form, 'proyeccion': proyeccion, 'titulo': 'Agregar línea'})


def _linea_editable(request, pk):
    """Trae la línea solo si es del área del usuario y la proyección sigue en borrador."""
    linea = get_object_or_404(Linea, pk=pk)
    proyeccion = _obtener_proyeccion(request, linea.proyeccion_id)
    if proyeccion.estado != EstadoProyeccion.BORRADOR:
        raise PermissionDenied
    return linea, proyeccion


@rol_requerido(Rol.COORDINADOR, Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def editar_linea(request, pk):
    linea, proyeccion = _linea_editable(request, pk)
    form = LineaForm(request.POST or None, instance=linea)  # instance = llena el formulario con lo que ya tiene
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('proyecciones:detalle', pk=proyeccion.pk)
    return render(request, 'proyecciones/linea_form.html',
                  {'form': form, 'proyeccion': proyeccion, 'titulo': 'Editar línea'})


@rol_requerido(Rol.COORDINADOR, Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def borrar_linea(request, pk):
    linea, proyeccion = _linea_editable(request, pk)
    if request.method == 'POST':  # solo borra con el botón, nunca con solo abrir un enlace
        linea.delete()
    return redirect('proyecciones:detalle', pk=proyeccion.pk)

@rol_requerido(Rol.COORDINADOR, Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def enviar_proyeccion(request, pk):
    proyeccion = _obtener_proyeccion(request, pk)
    if request.method == 'POST' and proyeccion.estado == EstadoProyeccion.BORRADOR:
        if not proyeccion.lineas.exists():
            messages.error(request, 'Agrega al menos una linea antes de enviar.')
        else:
            proyeccion.estado = EstadoProyeccion.ENVIADA
            proyeccion.fecha_envio = timezone.now()
            proyeccion.save(update_fields=['estado', 'fecha_envio'])
            messages.success(request, 'Proyeccion enviada. Ya no se puede modificar')
    return redirect('proyecciones:detalle', pk=proyeccion.pk)

@rol_requerido(Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def revision(request):
    """Todas las proyecciones de todas las áreas, para los administradores."""
    proyecciones = ProyeccionArea.objects.select_related('periodo', 'area')
    return render(request, 'proyecciones/revision.html', {'proyecciones': proyecciones})

@rol_requerido(Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def revisar_proyeccion(request, pk):
    proyeccion = get_object_or_404(ProyeccionArea, pk=pk)
    if proyeccion.estado == EstadoProyeccion.BORRADOR:
        messages.error(request, 'Esa proyección aún no ha sido enviada.')
        return redirect('proyecciones:revision')
    formset = AutorizadoFormSet(request.POST or None, queryset=proyeccion.lineas.select_related('unidad'))
    if request.method == 'POST' and formset.is_valid():
        formset.save()
        messages.success(request, 'Cantidades autorizadas guardadas.')
        return redirect('proyecciones:revisar', pk=proyeccion.pk)
    return render(request, 'proyecciones/revisar.html', {'proyeccion': proyeccion, 'formset': formset})

@rol_requerido(Rol.ADMINISTRADOR, Rol.DESARROLLADOR)
def aprobar_proyeccion(request, pk):
    proyeccion = get_object_or_404(ProyeccionArea, pk=pk)
    if request.method == 'POST' and proyeccion.estado == EstadoProyeccion.ENVIADA:
        if proyeccion.lineas.filter(cantidad_autorizada__isnull=True).exists():
            messages.error(request, 'Llena la cantidad autorizada de todas las líneas antes de aprobar.')
        else:
            proyeccion.estado = EstadoProyeccion.APROBADA
            proyeccion.aprobada_por = request.user  # queda registrado quién aprobó
            proyeccion.fecha_aprobacion = timezone.now()
            proyeccion.save(update_fields=['estado', 'aprobada_por', 'fecha_aprobacion'])
            messages.success(request, 'Proyección aprobada.')
    return redirect('proyecciones:revisar', pk=proyeccion.pk)