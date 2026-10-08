from datetime import date
from django.db import transaction
from areas.models import Area
from .models import Periodo, ProyeccionArea
from cuentas.models import Rol, Usuario


@transaction.atomic
def abrir_periodo(anio, fecha_limite, usuario):
    """Crea el periodo (si no existe) y una proyección en borrador por cada área activa.
    Lo que ya existe no se toca. Devuelve (periodo, cantidad_creadas)."""
    periodo, _ = Periodo.objects.get_or_create(
        anio=anio,
        defaults={
            'fecha_apertura': date.today(),
            'fecha_limite': fecha_limite,
            'abierto_por': usuario,
        },
    )
    creadas = 0
    for area in Area.objects.filter(activa=True):
        coordinador = Usuario.objects.filter(area=area, rol=Rol.COORDINADOR, activo=True).first()
        _, nueva = ProyeccionArea.objects.get_or_create(
            periodo=periodo,
            area=area,
            defaults={'responsable': coordinador or usuario},
        )
        if nueva:
            creadas += 1
    return periodo, creadas