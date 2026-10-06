from django.shortcuts import get_object_or_404, redirect, render
from cuentas.models import Rol
from cuentas.permisos import rol_requerido
from django.core.exceptions import PermissionDenied

from .models import EstadoProyeccion, ProyeccionArea
from .forms import LineaForm


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
    return render(request, 'proyecciones/linea_form.html', {'form': form, 'proyeccion': proyeccion})    