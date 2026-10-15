"""Arma el consolidado de un año: cada área con sus líneas."""
from decimal import Decimal

from .models import EstadoProyeccion, Linea, ProyeccionArea

ESTADOS_INCLUIDOS = [EstadoProyeccion.ENVIADA, EstadoProyeccion.APROBADA]
MESES_CORTOS = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']


def consolidado_por_area(periodo):
    """Cada área enviada o aprobada, con sus líneas (y los 12 meses en lista) y su costo total."""
    proyecciones = (ProyeccionArea.objects
                    .filter(periodo=periodo, estado__in=ESTADOS_INCLUIDOS)
                    .select_related('area')
                    .prefetch_related('lineas__unidad')
                    .order_by('area__nombre'))
    resultado = []
    for p in proyecciones:
        lineas = list(p.lineas.all())
        resultado.append({
            'proyeccion': p,
            'filas': [{'linea': l, 'meses': [getattr(l, m) for m in Linea.MESES]} for l in lineas],
            'costo_total': sum((l.costo for l in lineas), Decimal('0')),
        })
    return resultado


