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