from django.conf import settings
from django.db import models


class EstadoPeriodo(models.TextChoices):
    ABIERTO = 'abierto', 'Abierto'
    CERRADO = 'cerrado', 'Cerrado'


class Periodo(models.Model):
    """Año de la proyección de compras, con sus fechas de apertura y límite."""

    anio = models.PositiveSmallIntegerField('año', unique=True)
    fecha_apertura = models.DateField('fecha de apertura')
    fecha_limite = models.DateField('fecha límite de envío')
    estado = models.CharField(
        'estado', max_length=10, choices=EstadoPeriodo.choices, default=EstadoPeriodo.ABIERTO
    )
    abierto_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='abierto por',
        on_delete=models.PROTECT,
        related_name='periodos_abiertos',
    )

    class Meta:
        verbose_name = 'periodo'
        verbose_name_plural = 'periodos'
        ordering = ['-anio']

    def __str__(self):
        return str(self.anio)


class UnidadMedida(models.Model):
    """Unidad en que se pide un producto: Unidad, Caja x 100, Litro..."""

    nombre = models.CharField('nombre', max_length=40, unique=True)

    class Meta:
        verbose_name = 'unidad de medida'
        verbose_name_plural = 'unidades de medida'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre
    
class EstadoProyeccion(models.TextChoices):
    BORRADOR = 'borrador', 'Borrador'
    ENVIADA = 'enviada', 'Enviada'
    APROBADA = 'aprobada', 'Aprobada'


class ProyeccionArea(models.Model):
    """Proyección anual de compras de un área."""

    periodo = models.ForeignKey(
        Periodo, verbose_name='periodo', on_delete=models.PROTECT, related_name='proyecciones'
    )
    area = models.ForeignKey(
        'areas.Area', verbose_name='área', on_delete=models.PROTECT, related_name='proyecciones'
    )
    estado = models.CharField(
        'estado', max_length=10, choices=EstadoProyeccion.choices, default=EstadoProyeccion.BORRADOR
    )
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='responsable',
        on_delete=models.PROTECT,
        related_name='proyecciones_a_cargo',
    )
    fecha_envio = models.DateTimeField('fecha de envío', null=True, blank=True)
    aprobada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='aprobada por',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='proyecciones_aprobadas',
    )
    fecha_aprobacion = models.DateTimeField('fecha de aprobación', null=True, blank=True)
    observaciones = models.TextField('observaciones', blank=True)

    class Meta:
        verbose_name = 'proyección de área'
        verbose_name_plural = 'proyecciones de área'
        ordering = ['-periodo__anio', 'area__nombre']
        constraints = [
            models.UniqueConstraint(
                fields=['periodo', 'area'], name='una_proyeccion_por_periodo_y_area'
            )
        ]

    def __str__(self):
        return f'{self.area} · {self.periodo}'