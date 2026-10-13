"""Arma el consolidado de un año: cada área con sus líneas y la suma por producto."""
from decimal import Decimal

from .models import EstadoProyeccion, Linea, ProyeccionArea

ESTADOS_INCLUIDOS = [EstadoProyeccion.ENVIADA, EstadoProyeccion.APROBADA]
MESES_CORTOS = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']


def _clave(texto):
    """Nombre normalizado para juntar productos: minúsculas y sin espacios de más."""
    return ' '.join(texto.lower().split())


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


def consolidado_por_producto(periodo):
    """Suma entre áreas de cada producto con la misma unidad."""
    lineas = (Linea.objects
              .filter(proyeccion__periodo=periodo, proyeccion__estado__in=ESTADOS_INCLUIDOS)
              .select_related('unidad', 'proyeccion__area'))
    grupos = {}
    for l in lineas:
        clave = (_clave(l.producto), l.unidad_id)
        if clave not in grupos:
            grupos[clave] = {'producto': l.producto, 'unidad': l.unidad.nombre, 'meses': [0] * 12,
                             'total': 0, 'autorizado': None, 'costo': Decimal('0'), 'areas': set()}
        g = grupos[clave]
        for i, mes in enumerate(Linea.MESES):
            g['meses'][i] += getattr(l, mes)
        g['total'] += l.total_anual
        if l.cantidad_autorizada is not None:
            g['autorizado'] = (g['autorizado'] or 0) + l.cantidad_autorizada
        g['costo'] += l.costo
        g['areas'].add(l.proyeccion.area.nombre)
    filas = sorted(grupos.values(), key=lambda g: _clave(g['producto']))
    for g in filas:
        g['areas'] = ', '.join(sorted(g['areas']))
    return filas