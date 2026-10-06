from django.shortcuts import get_object_or_404, render
from cuentas.models import Rol
from cuentas.permisos import rol_requerido
from django.core.exceptions import PermissionDenied

from .models import ProyeccionArea


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